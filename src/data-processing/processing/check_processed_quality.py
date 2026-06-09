"""
전처리된 integrated 데이터의 품질을 점검한다.

이 스크립트는 processed 데이터를 수정하거나 삭제하지 않는다.
문서 내부 반복, ID/URL/title 중복, 문서 간 유사 후보를 찾아 리포트만 생성한다.

참고한 reference 개념:
- Data Cleaning: 중복 제거 전 중복 여부 확인
- Pandas 심화: 그룹별 값 확인, 조건 기반 검토 후보 분리
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


# 프로젝트 기준 경로를 잡아서 어디에서 실행해도 같은 폴더를 바라보게 한다.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROCESSED_DIR = PROJECT_ROOT / "database" / "processed"

INTEGRATED_FILE = PROCESSED_DIR / "integrated_horror_processed.json"
QUALITY_JSON = PROCESSED_DIR / "quality_report.json"
QUALITY_MD = PROCESSED_DIR / "quality_report.md"

# 기본 품질 리포트는 사람이 읽기 쉬운 Markdown만 생성한다.
# 구조화된 JSON 리포트가 필요할 때만 True로 바꾼다.
WRITE_QUALITY_JSON = False


# 문서 간 유사도 비교는 비용이 커질 수 있으므로 제목이 비슷한 후보만 좁혀서 본문을 비교한다.
TITLE_SIMILARITY_THRESHOLD = 0.9
TEXT_SIMILARITY_THRESHOLD = 0.85
MAX_SIMILAR_TITLE_COMPARISONS = 20000
MAX_SIMILAR_CANDIDATES = 100


def read_json(path: Path) -> list[dict[str, Any]]:
    """JSON 리스트 파일을 읽어온다."""
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError(f"{path.name} 파일은 JSON 리스트 형태여야 합니다.")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    """품질 검토 결과를 JSON으로 저장한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def normalize_for_compare(text: object) -> str:
    """중복 비교를 위해 대소문자, 공백, 일부 기호를 단순화한다."""
    normalized = "" if text is None else str(text)
    normalized = normalized.lower()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"[\"'`.,;:!?()\[\]{}]", "", normalized)
    return normalized.strip()


def split_sentences(text: str) -> list[str]:
    """본문을 문장 단위로 나눠 내부 반복을 확인할 후보를 만든다."""
    rough_sentences = re.split(r"(?<=[.!?。！？])\s+|\n+", text)
    sentences = []
    for sentence in rough_sentences:
        normalized = sentence.strip()
        if len(normalized) >= 30:
            sentences.append(normalized)
    return sentences


def find_duplicate_values(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    """특정 컬럼 값이 여러 문서에서 반복되는 경우를 찾는다."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        value = normalize_for_compare(row.get(field))
        if value:
            groups[value].append(row)

    duplicates = []
    for value, grouped_rows in groups.items():
        if len(grouped_rows) <= 1:
            continue
        duplicates.append(
            {
                "value": value,
                "count": len(grouped_rows),
                "documents": summarize_rows(grouped_rows),
            }
        )
    return duplicates


def find_source_id_duplicates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """source와 source_id 조합이 중복되는 문서를 찾는다."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = f"{row.get('source')}::{row.get('source_id')}"
        groups[key].append(row)

    duplicates = []
    for key, grouped_rows in groups.items():
        if len(grouped_rows) <= 1:
            continue
        duplicates.append(
            {
                "value": key,
                "count": len(grouped_rows),
                "documents": summarize_rows(grouped_rows),
            }
        )
    return duplicates


def summarize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """리포트에 필요한 최소 문서 정보만 남긴다."""
    return [
        {
            "document_id": row.get("document_id"),
            "source": row.get("source"),
            "source_id": row.get("source_id"),
            "title": row.get("title"),
            "url": row.get("url"),
        }
        for row in rows
    ]


def find_internal_repetition(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """한 문서 안에서 같은 문장이 여러 번 반복되는 후보를 찾는다."""
    candidates = []

    for row in rows:
        sentences = split_sentences(str(row.get("cleaned_text") or ""))
        sentence_groups: dict[str, list[str]] = defaultdict(list)

        for sentence in sentences:
            key = normalize_for_compare(sentence)
            sentence_groups[key].append(sentence)

        repeated_sentences = [
            {
                "sentence": values[0][:240],
                "count": len(values),
            }
            for values in sentence_groups.values()
            if len(values) > 1
        ]

        if repeated_sentences:
            candidates.append(
                {
                    "document": summarize_rows([row])[0],
                    "repeated_sentences": repeated_sentences,
                }
            )

    return candidates


def find_mythology_field_overlap(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """mythology 데이터에서 description과 다른 설명 필드가 반복되는 후보를 찾는다."""
    candidates = []

    for row in rows:
        if str(row.get("source")).lower() != "wikipedia":
            continue

        description = str(row.get("description") or "")
        parts = [part.strip() for part in description.split("\n\n") if part.strip()]
        if len(parts) < 2:
            continue

        first_part = normalize_for_compare(parts[0])
        overlaps = []
        for part in parts[1:]:
            normalized_part = normalize_for_compare(part)
            if normalized_part and normalized_part in first_part:
                overlaps.append(part[:240])

        if overlaps:
            candidates.append(
                {
                    "document": summarize_rows([row])[0],
                    "overlap_count": len(overlaps),
                    "overlap_samples": overlaps[:5],
                }
            )

    return candidates


def find_similar_documents(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """제목과 본문이 매우 비슷한 문서 쌍을 중복 후보로 찾는다."""
    candidates = []
    title_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        title_key = normalize_for_compare(row.get("title"))
        if title_key:
            title_groups[title_key].append(row)

    for title_key, grouped_rows in title_groups.items():
        if len(grouped_rows) <= 1:
            continue

        for index, left in enumerate(grouped_rows):
            left_text = normalize_for_compare(left.get("cleaned_text"))[:1500]
            if not left_text:
                continue

            for right in grouped_rows[index + 1 :]:
                right_text = normalize_for_compare(right.get("cleaned_text"))[:1500]
                if not right_text:
                    continue

                text_similarity = SequenceMatcher(None, left_text, right_text).ratio()
                if text_similarity < TEXT_SIMILARITY_THRESHOLD:
                    continue

                candidates.append(
                    {
                        "left": summarize_rows([left])[0],
                        "right": summarize_rows([right])[0],
                        "title_similarity": 1.0,
                        "text_similarity": round(text_similarity, 3),
                        "judgement": "중복 후보이므로 삭제하지 말고 사람 검토가 필요함",
                    }
                )

    return candidates


def find_similar_title_pairs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """제목이 매우 유사한 문서 쌍을 본문 비교 전 단계의 검토 후보로 찾는다."""
    candidates = []
    comparison_count = 0
    short_rows = [
        row
        for row in rows
        if normalize_for_compare(row.get("title"))
    ]

    for index, left in enumerate(short_rows):
        left_title = normalize_for_compare(left.get("title"))
        left_text = normalize_for_compare(left.get("cleaned_text"))[:1500]

        for right in short_rows[index + 1 :]:
            comparison_count += 1
            if comparison_count > MAX_SIMILAR_TITLE_COMPARISONS:
                return candidates

            right_title = normalize_for_compare(right.get("title"))
            right_text = normalize_for_compare(right.get("cleaned_text"))[:1500]

            title_similarity = SequenceMatcher(None, left_title, right_title).ratio()
            if title_similarity < TITLE_SIMILARITY_THRESHOLD:
                continue

            text_similarity = 0
            if left_text and right_text:
                text_similarity = SequenceMatcher(None, left_text, right_text).ratio()

            candidates.append(
                {
                    "left": summarize_rows([left])[0],
                    "right": summarize_rows([right])[0],
                    "title_similarity": round(title_similarity, 3),
                    "text_similarity": round(text_similarity, 3),
                    "judgement": "제목 유사 후보이므로 삭제하지 말고 사람 검토가 필요함",
                }
            )

    return candidates


def build_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """품질 검토 항목을 모두 모아 하나의 리포트 딕셔너리로 만든다."""
    return {
        "summary": {
            "row_count": len(rows),
            "source_counts": count_by_source(rows),
        },
        "exact_duplicates": {
            "document_id": find_duplicate_values(rows, "document_id"),
            "source_and_source_id": find_source_id_duplicates(rows),
            "url": find_duplicate_values(rows, "url"),
            "title": find_duplicate_values(rows, "title"),
        },
        "internal_repetition_candidates": find_internal_repetition(rows),
        "mythology_field_overlap_candidates": find_mythology_field_overlap(rows),
        "similar_document_candidates": find_similar_documents(rows),
        "similar_title_candidates": find_similar_title_pairs(rows),
        "processing_notes": [
            {
                "issue": "mythology 설명 필드 중복",
                "found": (
                    "초기 전처리에서 description + behavior + history + signs + weakness를 "
                    "단순 결합해 description 안에 이미 포함된 behavior/history/weakness 내용이 "
                    "cleaned_text에 반복되는 문제가 발견되었다."
                ),
                "action": (
                    "processed의 description에는 원본 description만 저장하도록 수정했다. "
                    "behavior, history, signs, weakness, survival_rules는 삭제하지 않고 metadata에 보존했다."
                ),
                "result": "수정 후 mythology 필드 중복 후보가 0개로 감소했다.",
            },
            {
                "issue": "제목 유사 후보",
                "found": (
                    "thering 데이터에서 '<테두리 없는 거울> 계단의 하나코 - 1~完'처럼 "
                    "제목이 유사한 문서가 발견되었다."
                ),
                "action": (
                    "본문 유사도가 낮고 회차가 다른 시리즈물이므로 중복 삭제 대상이 아니라 "
                    "유지 대상으로 판단했다."
                ),
                "result": "제목 유사 후보는 삭제하지 않고 검토 기록으로만 남긴다.",
            },
        ],
        "note": "이 리포트는 삭제 대상이 아니라 검토 후보를 기록한 것이다.",
    }


def count_by_source(rows: list[dict[str, Any]]) -> dict[str, int]:
    """source별 문서 개수를 센다."""
    counts = CounterLike()
    for row in rows:
        counts.add(str(row.get("source") or "unknown"))
    return counts.to_dict()


class CounterLike:
    """간단한 개수 집계를 위해 사용하는 작은 도우미 클래스다."""

    def __init__(self) -> None:
        self.values: dict[str, int] = {}

    def add(self, key: str) -> None:
        self.values[key] = self.values.get(key, 0) + 1

    def to_dict(self) -> dict[str, int]:
        return dict(sorted(self.values.items()))


def build_markdown(report: dict[str, Any]) -> str:
    """품질 검토 JSON 리포트를 사람이 읽기 쉬운 Markdown으로 바꾼다."""
    lines = []
    lines.append("# 전처리 결과 품질 검토 리포트")
    lines.append("")
    lines.append("이 리포트는 중복 후보를 삭제하지 않고 검토 대상으로만 기록한다.")
    lines.append("")

    summary = report["summary"]
    lines.append("## 요약")
    lines.append("")
    lines.append(f"- 전체 문서 수: {summary['row_count']}")
    for source, count in summary["source_counts"].items():
        lines.append(f"- {source}: {count}")
    lines.append("")

    lines.append("## 처리 기록")
    lines.append("")
    for note in report["processing_notes"]:
        lines.append(f"### {note['issue']}")
        lines.append("")
        lines.append(f"- 발견 내용: {note['found']}")
        lines.append(f"- 처리 내용: {note['action']}")
        lines.append(f"- 결과: {note['result']}")
        lines.append("")

    lines.extend(build_duplicate_section("document_id 중복", report["exact_duplicates"]["document_id"]))
    lines.extend(build_duplicate_section("source + source_id 중복", report["exact_duplicates"]["source_and_source_id"]))
    lines.extend(build_duplicate_section("url 중복", report["exact_duplicates"]["url"]))
    lines.extend(build_duplicate_section("title 중복", report["exact_duplicates"]["title"]))

    lines.append("## 문서 내부 반복 후보")
    lines.append("")
    internal = report["internal_repetition_candidates"]
    lines.append(f"- 후보 수: {len(internal)}")
    for item in internal[:20]:
        document = item["document"]
        lines.append(f"- `{document['document_id']}` {document['title']}")
        for repeated in item["repeated_sentences"][:3]:
            lines.append(f"  - 반복 {repeated['count']}회: {repeated['sentence']}")
    lines.append("")

    lines.append("## mythology 필드 중복 후보")
    lines.append("")
    mythology = report["mythology_field_overlap_candidates"]
    lines.append(f"- 후보 수: {len(mythology)}")
    for item in mythology[:20]:
        document = item["document"]
        lines.append(f"- `{document['document_id']}` {document['title']}: 겹침 {item['overlap_count']}개")
        for sample in item["overlap_samples"][:3]:
            lines.append(f"  - {sample}")
    lines.append("")

    lines.append("## 문서 간 유사 후보")
    lines.append("")
    similar = report["similar_document_candidates"]
    lines.append(f"- 후보 수: {len(similar)}")
    for item in similar[:20]:
        left = item["left"]
        right = item["right"]
        lines.append(
            f"- `{left['document_id']}` / `{right['document_id']}` "
            f"title={item['title_similarity']}, text={item['text_similarity']}"
        )
        lines.append(f"  - {left['title']}")
        lines.append(f"  - {right['title']}")
    lines.append("")

    lines.append("## 제목 유사 후보")
    lines.append("")
    similar_titles = report["similar_title_candidates"]
    lines.append(f"- 후보 수: {len(similar_titles)}")
    for item in similar_titles[:20]:
        left = item["left"]
        right = item["right"]
        lines.append(
            f"- `{left['document_id']}` / `{right['document_id']}` "
            f"title={item['title_similarity']}, text={item['text_similarity']}"
        )
        lines.append(f"  - {left['title']}")
        lines.append(f"  - {right['title']}")
    lines.append("")

    return "\n".join(lines) + "\n"


def build_duplicate_section(title: str, duplicates: list[dict[str, Any]]) -> list[str]:
    """중복 항목 하나를 Markdown 섹션으로 만든다."""
    lines = [f"## {title}", "", f"- 후보 수: {len(duplicates)}"]
    for item in duplicates[:20]:
        lines.append(f"- 값: `{item['value']}` / 개수: {item['count']}")
        for document in item["documents"][:5]:
            lines.append(f"  - `{document['document_id']}` {document['title']}")
    lines.append("")
    return lines


def main() -> None:
    """통합 processed 파일을 분석하고 품질 검토 리포트를 저장한다."""
    rows = read_json(INTEGRATED_FILE)
    report = build_report(rows)

    if WRITE_QUALITY_JSON:
        write_json(QUALITY_JSON, report)
        print(f"생성 완료: {QUALITY_JSON}")

    QUALITY_MD.write_text(build_markdown(report), encoding="utf-8")

    print(f"생성 완료: {QUALITY_MD}")


if __name__ == "__main__":
    main()
