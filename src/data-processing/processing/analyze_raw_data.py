"""
전처리 전에 괴담/신화 원천 JSON 파일의 상태를 분석한다.

이 스크립트는 원본 데이터를 수정하지 않는다. 본문 정리 규칙, 키워드
추출 규칙, 최종 컬럼을 정하기 위한 데이터 프로파일 보고서만 생성한다.

참고한 reference 개념:
- Data Cleaning: 컬럼별 결측치 확인, 중복/노이즈 점검
- Pandas 기초/심화: 데이터 구조 확인, 새 컬럼 설계 전 사전 분석
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any


# 프로젝트 기준 경로를 잡아서 어디에서 실행해도 같은 폴더를 바라보게 한다.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "database" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "database" / "processed"

# 기본 분석 결과는 사람이 읽기 쉬운 Markdown으로 저장한다.
# 구조화된 JSON 분석 결과가 필요할 때만 WRITE_PROFILE_JSON을 True로 바꾼다.
PROFILE_JSON = PROCESSED_DIR / "raw_data_profile.json"
PROFILE_MD = PROCESSED_DIR / "raw_data_profile.md"
WRITE_PROFILE_JSON = False


# 전처리 전에 원문에서 얼마나 자주 등장하는지 확인할 노이즈 후보들이다.
NOISE_PATTERNS = {
    "hash_symbol": re.compile(r"#"),
    "slash_symbol": re.compile(r"/"),
    "square_brackets": re.compile(r"[\[\]]"),
    "caret_symbol": re.compile(r"\^"),
    "citation_numbers": re.compile(r"\[\d+\]"),
    "markdown_links": re.compile(r"\[[^\]]+\]\([^)]+\)"),
    "urls": re.compile(r"https?://\S+|www\.\S+"),
    "html_tags": re.compile(r"<[^>]+>"),
    "script_or_dom_noise": re.compile(
        r"JSON\.parse|localStorage|document\.|window\.|function\s*\(|addEventListener",
        re.IGNORECASE,
    ),
    "css_noise": re.compile(
        r"-webkit-|visibility\s*:|position\s*:|display\s*:|@keyframes|transform\s*:",
        re.IGNORECASE,
    ),
    "extra_whitespace": re.compile(r"[ \t]{2,}"),
    "repeated_newlines": re.compile(r"\n{3,}"),
}

# 본문으로 쓰일 가능성이 높은 컬럼 이름 후보들이다.
TEXT_FIELD_NAMES = {
    "content",
    "description",
    "behavior",
    "history",
    "signs",
    "weakness",
    "summary",
    "summary_ko",
    "lead_text",
    "lead_text_ko",
}

# 제목과 키워드 추출에 도움 되는 메타데이터 컬럼 후보들이다.
TITLE_FIELD_NAMES = {"title", "name", "title_ko"}
METADATA_HINTS = {
    "category",
    "subcategory",
    "primary_type",
    "region",
    "country",
    "origin",
    "habitat",
    "habitats",
    "tags",
    "source",
    "source_site",
    "horror_level",
}


def read_json(path: Path) -> list[dict[str, Any]]:
    """원천 JSON 파일을 읽고, 리스트 형태 데이터인지 확인한다."""
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError(f"{path.name} 파일은 JSON 리스트 형태여야 합니다.")
    return data


def compact_type_name(value: Any) -> str:
    """컬럼별 타입 분포를 보기 쉽도록 짧은 타입 이름으로 바꾼다."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return type(value).__name__


def is_non_empty(value: Any) -> bool:
    """결측치나 빈 문자열, 빈 리스트, 빈 딕셔너리를 비어 있는 값으로 판단한다."""
    return value not in (None, "", [], {})


def string_stats(values: list[str]) -> dict[str, Any]:
    """문자열 컬럼의 길이와 한글/영문/숫자 비율을 요약한다."""
    lengths = [len(value) for value in values]
    korean_counts = [len(re.findall(r"[가-힣]", value)) for value in values]
    english_counts = [len(re.findall(r"[A-Za-z]", value)) for value in values]
    digit_counts = [len(re.findall(r"\d", value)) for value in values]

    return {
        "min_length": min(lengths) if lengths else 0,
        "avg_length": round(mean(lengths), 2) if lengths else 0,
        "max_length": max(lengths) if lengths else 0,
        "avg_korean_chars": round(mean(korean_counts), 2) if korean_counts else 0,
        "avg_english_chars": round(mean(english_counts), 2) if english_counts else 0,
        "avg_digit_chars": round(mean(digit_counts), 2) if digit_counts else 0,
    }


def analyze_noise(values: list[str]) -> dict[str, dict[str, int]]:
    """문자열 값들에서 노이즈 후보 패턴이 몇 행에 몇 번 나타나는지 센다."""
    result: dict[str, dict[str, int]] = {}
    for pattern_name, pattern in NOISE_PATTERNS.items():
        row_count = 0
        total_count = 0
        for value in values:
            matches = pattern.findall(value)
            if matches:
                row_count += 1
                total_count += len(matches)
        result[pattern_name] = {
            "rows_with_pattern": row_count,
            "total_matches": total_count,
        }
    return result


def sample_values(values: list[Any], limit: int = 3) -> list[Any]:
    """보고서에서 컬럼 내용을 빠르게 확인할 수 있도록 대표 샘플을 뽑는다."""
    samples = []
    for value in values:
        if not is_non_empty(value):
            continue
        if isinstance(value, str):
            samples.append(value.replace("\n", " ")[:160])
        else:
            samples.append(value)
        if len(samples) >= limit:
            break
    return samples


def infer_text_status(text_candidates: dict[str, Any]) -> str:
    """본문 후보의 길이와 스크립트 노이즈 비율로 본문 사용 가능 상태를 추정한다."""
    if not text_candidates:
        return "metadata_only"

    # 가장 긴 평균 길이를 가진 본문 후보를 기준으로 데이터 품질을 판단한다.
    best = max(
        text_candidates.values(),
        key=lambda item: item["stats"]["avg_length"],
    )
    avg_length = best["stats"]["avg_length"]
    script_rows = best["noise_patterns"]["script_or_dom_noise"]["rows_with_pattern"]
    css_rows = best["noise_patterns"]["css_noise"]["rows_with_pattern"]
    total_rows = best["non_empty_count"]

    # 스크립트나 CSS 노이즈가 절반 이상이면 본문 재수집이 필요하다고 본다.
    if total_rows and (script_rows / total_rows >= 0.5 or css_rows / total_rows >= 0.5):
        return "needs_recrawl"
    # 평균 길이가 충분하면 일단 본문 기반 전처리가 가능하다고 본다.
    if avg_length >= 80:
        return "valid_text"
    return "metadata_only"


def find_keyword_inputs(rows: list[dict[str, Any]], all_columns: list[str]) -> dict[str, Any]:
    """키워드 추출에 활용할 수 있는 제목, 기존 키워드, 메타데이터 컬럼을 찾는다."""
    existing_keyword_columns = []
    metadata_columns = []
    title_columns = []

    for column in all_columns:
        values = [row.get(column) for row in rows]
        if column.lower() in {"keywords", "keyword", "tags"}:
            existing_keyword_columns.append(column)
        if column in TITLE_FIELD_NAMES:
            title_columns.append(column)
        if column in METADATA_HINTS:
            non_empty = sum(1 for value in values if is_non_empty(value))
            metadata_columns.append(
                {
                    "column": column,
                    "non_empty_count": non_empty,
                    "samples": sample_values(values),
                }
            )

    return {
        "title_columns": title_columns,
        "existing_keyword_columns": existing_keyword_columns,
        "metadata_columns": metadata_columns,
    }


def analyze_metadata_quality(rows: list[dict[str, Any]], all_columns: list[str]) -> list[dict[str, Any]]:
    """metadata 후보 컬럼의 길이, 노이즈, 샘플을 분석한다."""
    metadata_quality = []

    for column in all_columns:
        if column not in METADATA_HINTS:
            continue

        values = [row.get(column) for row in rows]
        text_values = []
        for value in values:
            if isinstance(value, list):
                text_values.extend(str(item) for item in value if item is not None)
            elif isinstance(value, dict):
                text_values.extend(str(item) for item in value.values() if item is not None)
            elif value is not None:
                text_values.append(str(value))

        if not text_values:
            metadata_quality.append(
                {
                    "column": column,
                    "non_empty_count": 0,
                    "avg_length": 0,
                    "noise_patterns": {},
                    "samples": [],
                }
            )
            continue

        stats = string_stats(text_values)
        metadata_quality.append(
            {
                "column": column,
                "non_empty_count": sum(1 for value in values if is_non_empty(value)),
                "avg_length": stats["avg_length"],
                "noise_patterns": analyze_noise(text_values),
                "samples": sample_values(values),
            }
        )

    return metadata_quality


def analyze_file(path: Path) -> dict[str, Any]:
    """JSON 파일 하나를 분석해 컬럼, 본문 후보, 키워드 후보 정보를 만든다."""
    rows = read_json(path)
    row_count = len(rows)
    all_columns = sorted({key for row in rows for key in row.keys()})

    columns: dict[str, Any] = {}
    text_candidates: dict[str, Any] = {}

    for column in all_columns:
        # 각 컬럼의 타입, 비어 있지 않은 값 개수, 샘플을 먼저 기록한다.
        values = [row.get(column) for row in rows]
        type_counts = Counter(compact_type_name(value) for value in values)
        non_empty_count = sum(1 for value in values if is_non_empty(value))

        column_profile: dict[str, Any] = {
            "types": dict(sorted(type_counts.items())),
            "non_empty_count": non_empty_count,
            "missing_or_empty_count": row_count - non_empty_count,
            "samples": sample_values(values),
        }

        string_values = [value for value in values if isinstance(value, str)]
        if string_values:
            # 문자열 컬럼은 길이와 문자 구성까지 확인해야 본문 후보인지 판단할 수 있다.
            stats = string_stats(string_values)
            column_profile["string_stats"] = stats

            # 이름상 본문 후보이거나 평균 길이가 긴 문자열은 본문 후보로 따로 분석한다.
            is_named_text_field = column in TEXT_FIELD_NAMES
            is_long_text_field = stats["avg_length"] >= 60
            if is_named_text_field or is_long_text_field:
                text_candidates[column] = {
                    "non_empty_count": non_empty_count,
                    "stats": stats,
                    "noise_patterns": analyze_noise(string_values),
                    "samples": sample_values(string_values),
                }

        columns[column] = column_profile

    keyword_inputs = find_keyword_inputs(rows, all_columns)

    return {
        "file_name": path.name,
        "row_count": row_count,
        "columns": columns,
        "text_candidates": text_candidates,
        "keyword_inputs": keyword_inputs,
        "metadata_quality": analyze_metadata_quality(rows, all_columns),
        "recommended_text_status": infer_text_status(text_candidates),
    }


def build_markdown(profile: dict[str, Any]) -> str:
    """JSON 프로파일을 사람이 읽기 쉬운 Markdown 보고서로 바꾼다."""
    lines: list[str] = []
    lines.append("# 원천 데이터 프로파일")
    lines.append("")
    lines.append("이 문서는 원천 JSON을 전처리하기 전에 데이터 상태를 분석한 결과이다.")
    lines.append("원본 데이터는 수정하지 않았다.")
    lines.append("")

    for file_profile in profile["files"]:
        lines.append(f"## {file_profile['file_name']}")
        lines.append("")
        lines.append(f"- 데이터 개수: {file_profile['row_count']}")
        lines.append(f"- 추천 본문 상태: `{file_profile['recommended_text_status']}`")
        lines.append(f"- 컬럼 수: {len(file_profile['columns'])}")
        lines.append("")

        lines.append("### 본문 후보 컬럼")
        lines.append("")
        if file_profile["text_candidates"]:
            lines.append("| 컬럼 | 비어있지 않은 행 | 평균 길이 | 평균 한글 | 평균 영문 | 주요 노이즈 |")
            lines.append("| --- | ---: | ---: | ---: | ---: | --- |")
            for column, info in file_profile["text_candidates"].items():
                stats = info["stats"]
                # 실제로 한 번 이상 발견된 노이즈만 보고서에 표시한다.
                noisy = [
                    name
                    for name, noise in info["noise_patterns"].items()
                    if noise["rows_with_pattern"] > 0
                ]
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            f"`{column}`",
                            str(info["non_empty_count"]),
                            str(stats["avg_length"]),
                            str(stats["avg_korean_chars"]),
                            str(stats["avg_english_chars"]),
                            ", ".join(noisy[:6]) if noisy else "-",
                        ]
                    )
                    + " |"
                )
        else:
            lines.append("본문 후보로 볼 만한 긴 문자열 컬럼이 없다.")
        lines.append("")

        lines.append("### 키워드 추출 후보")
        lines.append("")
        keyword_inputs = file_profile["keyword_inputs"]
        lines.append(
            "- 제목 컬럼: "
            + (
                ", ".join(f"`{name}`" for name in keyword_inputs["title_columns"])
                if keyword_inputs["title_columns"]
                else "없음"
            )
        )
        lines.append(
            "- 기존 키워드/태그 컬럼: "
            + (
                ", ".join(f"`{name}`" for name in keyword_inputs["existing_keyword_columns"])
                if keyword_inputs["existing_keyword_columns"]
                else "없음"
            )
        )
        if keyword_inputs["metadata_columns"]:
            metadata_names = [f"`{item['column']}`" for item in keyword_inputs["metadata_columns"]]
            lines.append("- 메타데이터 후보 컬럼: " + ", ".join(metadata_names))
        else:
            lines.append("- 메타데이터 후보 컬럼: 없음")
        lines.append("")

        lines.append("### metadata 품질 분석")
        lines.append("")
        metadata_quality = file_profile["metadata_quality"]
        if metadata_quality:
            lines.append("| 컬럼 | 비어있지 않은 행 | 평균 길이 | 주요 노이즈 | 샘플 |")
            lines.append("| --- | ---: | ---: | --- | --- |")
            for item in metadata_quality:
                noisy = [
                    name
                    for name, noise in item["noise_patterns"].items()
                    if noise["rows_with_pattern"] > 0
                ]
                sample_text = json.dumps(item["samples"][0], ensure_ascii=False) if item["samples"] else ""
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            f"`{item['column']}`",
                            str(item["non_empty_count"]),
                            str(item["avg_length"]),
                            ", ".join(noisy[:6]) if noisy else "-",
                            sample_text,
                        ]
                    )
                    + " |"
                )
        else:
            lines.append("metadata 후보 컬럼이 없다.")
        lines.append("")

        lines.append("### 컬럼 요약")
        lines.append("")
        lines.append("| 컬럼 | 타입 | 비어있지 않은 행 | 샘플 |")
        lines.append("| --- | --- | ---: | --- |")
        for column, info in file_profile["columns"].items():
            samples = info["samples"]
            sample_text = json.dumps(samples[0], ensure_ascii=False) if samples else ""
            lines.append(
                f"| `{column}` | {json.dumps(info['types'], ensure_ascii=False)} | "
                f"{info['non_empty_count']} | {sample_text} |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    """원천 JSON 전체를 분석하고 Markdown 보고서를 생성한다."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # raw 폴더의 모든 JSON 파일을 분석 대상으로 삼는다.
    files = sorted(RAW_DIR.glob("*.json"))
    profile = {
        "raw_dir": str(RAW_DIR.relative_to(PROJECT_ROOT)),
        "processed_dir": str(PROCESSED_DIR.relative_to(PROJECT_ROOT)),
        "file_count": len(files),
        "files": [analyze_file(path) for path in files],
    }

    if WRITE_PROFILE_JSON:
        with PROFILE_JSON.open("w", encoding="utf-8") as file:
            json.dump(profile, file, ensure_ascii=False, indent=2)
        print(f"생성 완료: {PROFILE_JSON}")

    # 분석 결과를 사람이 읽기 좋은 Markdown으로 저장한다.
    PROFILE_MD.write_text(build_markdown(profile), encoding="utf-8")

    print(f"생성 완료: {PROFILE_MD}")


if __name__ == "__main__":
    main()
