"""
database/data 안의 원천 JSON을 읽어 database/processed에 전처리 결과를 저장한다.

현재 기본 목표는 DCInside 수집 데이터만 전처리하는 것이다.
`verified_korean_horror_master.json`과 `ultimate_global_mythology_1000.json`은
나중에 다시 필요할 수 있으므로 함수와 경로를 남겨 두고, 실행 플래그만 False로 둔다.
`misin.json`은 PostgreSQL/pgvector 전처리 대상이 아니므로 이 스크립트에서 제외한다.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from cleaning_rules import (
    clean_dcinside_text,
    clean_metadata_value,
    clean_mythology_text,
    clean_thering_text,
)
from keyword_extractor import (
    extract_dcinside_keywords,
    extract_mythology_keywords,
    extract_thering_keywords,
)


# 이 파일은 src/data-processing/processing 안에 있으므로 parents[3]이 프로젝트 루트다.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "database" / "data"
PROCESSED_DIR = PROJECT_ROOT / "database" / "processed"


# 기본 실행 대상은 DCInside뿐이다.
PROCESS_DCINSIDE = True

# 나중에 다시 전처리하고 싶으면 아래 값을 True로 바꾸면 된다.
# PROCESS_VERIFIED = True
# PROCESS_MYTHOLOGY = True
PROCESS_VERIFIED = False
PROCESS_MYTHOLOGY = False

# misin.json은 현재 서비스에서 별도 테이블로 단순 적재되는 데이터라 전처리하지 않는다.
PROCESS_MISIN = False


DCINSIDE_RAW_FILE = DATA_DIR / "dcinside_horror_filtered.json"
VERIFIED_RAW_FILE = DATA_DIR / "verified_korean_horror_master.json"
MYTHOLOGY_RAW_FILE = DATA_DIR / "ultimate_global_mythology_1000.json"
MISIN_RAW_FILE = DATA_DIR / "misin.json"

DCINSIDE_OUTPUT_FILE = PROCESSED_DIR / "dcinside_horror_processed.json"
VERIFIED_OUTPUT_FILE = PROCESSED_DIR / "verified_korean_horror_processed.json"
MYTHOLOGY_OUTPUT_FILE = PROCESSED_DIR / "ultimate_global_mythology_processed.json"


DCINSIDE_CATEGORY_MAP = {
    "[경험]": "WITNESS",
    "[괴담]": "WITNESS",
    "[사건/사고]": "WITNESS",
    "[창작]": "CREATION",
}

DCINSIDE_CATEGORY_LABELS = {
    "WITNESS": "목격담",
    "CREATION": "창작담",
}


def read_json(path: Path) -> list[dict[str, Any]]:
    """JSON 리스트 파일을 읽고, 리스트가 아니면 바로 알려 준다."""
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError(f"{path.name} 파일은 JSON 리스트 형태여야 한다.")
    return data


def write_json(path: Path, rows: list[dict[str, Any]]) -> None:
    """전처리 결과를 사람이 확인하기 쉬운 UTF-8 JSON으로 저장한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(rows, file, ensure_ascii=False, indent=2)


def build_processed_row(
    document_id: str,
    source: str,
    source_id: Any,
    title: str,
    url: str,
    description: str,
    cleaned_text: str,
    description_length: int,
    cleaned_text_length: int,
    removed_patterns: list[str],
    noise_types: list[str],
    keywords: list[str],
    keyword_count: int,
    keyword_basis: str,
    text_status: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """최종 processed 데이터의 공통 컬럼 구조를 만든다."""
    return {
        "document_id": document_id,
        "source": source,
        "source_id": source_id,
        "title": title,
        "url": url,
        "description": description,
        "cleaned_text": cleaned_text,
        "description_length": description_length,
        "cleaned_text_length": cleaned_text_length,
        "removed_patterns": removed_patterns,
        "noise_types": noise_types,
        "keywords": keywords,
        "keyword_count": keyword_count,
        "keyword_basis": keyword_basis,
        "text_status": text_status,
        "metadata": metadata,
    }


def build_source_id(*parts: Any) -> str:
    """원본에 ID가 없을 때도 같은 데이터는 같은 ID가 나오도록 해시 ID를 만든다."""
    raw_key = "||".join(str(part or "").strip() for part in parts)
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]


def build_document_id(source: str, source_id: Any) -> str:
    """출처와 원본 ID를 합쳐 processed 안에서 사용할 고유 ID를 만든다."""
    source_key = str(source or "unknown").strip().lower().replace(" ", "_")
    return f"{source_key}_{source_id}"


def clean_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """metadata 값은 삭제하지 않고, 문자열 노이즈만 가볍게 정리한다."""
    return {key: clean_metadata_value(value) for key, value in metadata.items()}


def remove_dcinside_title_tag(title: str) -> str:
    """[경험], [창작] 같은 DCInside 분류 태그를 제목 후보에서 제거한다."""
    return re.sub(r"^\[[^\]]+\]\s*", "", title or "").strip()


def infer_dcinside_category(title: str) -> str | None:
    """DCInside 제목 태그를 서비스 게시판 분류값으로 변환한다."""
    stripped_title = (title or "").strip()
    for raw_tag, category in DCINSIDE_CATEGORY_MAP.items():
        if stripped_title.startswith(raw_tag):
            return category
    return None


def make_title_from_content(content: str, limit: int = 40) -> str:
    """제목이 태그뿐인 DCInside 글은 본문 앞부분으로 임시 제목을 만든다."""
    first_line = re.split(r"[\n.!?。！？]", content.strip(), maxsplit=1)[0]
    compact = re.sub(r"\s+", " ", first_line).strip()
    if not compact:
        return "제목 없음"
    return compact[:limit].strip()


def preprocess_dcinside(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """DCInside 수집 데이터를 공통 processed 구조로 전처리한다."""
    processed_rows = []

    for index, row in enumerate(rows, start=1):
        raw_title = str(row.get("title") or "")
        raw_content = str(row.get("content") or "")
        category = infer_dcinside_category(raw_title)

        # 분류가 불명확하거나 본문이 비어 있으면 PostgreSQL 적재와 같은 기준으로 제외한다.
        if category is None or not raw_content.strip():
            continue

        cleaning_result = clean_dcinside_text(raw_content)
        source = str(row.get("source") or "dcinside")
        source_id = build_source_id(source, raw_title, raw_content, row.get("region"), index)
        title_without_tag = remove_dcinside_title_tag(raw_title)
        title = title_without_tag or make_title_from_content(cleaning_result.cleaned_text)
        metadata = clean_metadata(
            {
                "raw_title": raw_title,
                "category": category,
                "category_label": DCINSIDE_CATEGORY_LABELS.get(category, category),
                "region": row.get("region"),
                "row_index": index,
            }
        )
        keyword_result = extract_dcinside_keywords(
            title=title,
            cleaned_text=cleaning_result.cleaned_text,
            metadata=metadata,
        )

        processed_rows.append(
            build_processed_row(
                document_id=build_document_id(source, source_id),
                source=source,
                source_id=source_id,
                title=title,
                url="",
                description=cleaning_result.description,
                cleaned_text=cleaning_result.cleaned_text,
                description_length=cleaning_result.description_length,
                cleaned_text_length=cleaning_result.cleaned_text_length,
                removed_patterns=cleaning_result.removed_patterns,
                noise_types=cleaning_result.noise_types,
                keywords=keyword_result.keywords,
                keyword_count=keyword_result.keyword_count,
                keyword_basis=keyword_result.keyword_basis,
                text_status="valid_text",
                metadata=metadata,
            )
        )

    return processed_rows


def preprocess_verified(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """검증된 한국 괴담 데이터를 공통 processed 구조로 전처리한다."""
    processed_rows = []

    for index, row in enumerate(rows, start=1):
        content = str(row.get("content") or "")
        if not content.strip():
            continue

        cleaning_result = clean_thering_text(content)
        source = str(row.get("source") or "verified_korean_horror")
        source_id = build_source_id(source, row.get("title"), content, row.get("region"), index)
        metadata = clean_metadata(
            {
                "region": row.get("region"),
                "row_index": index,
            }
        )
        keyword_result = extract_thering_keywords(
            title=str(row.get("title") or ""),
            cleaned_text=cleaning_result.cleaned_text,
            metadata=metadata,
        )

        processed_rows.append(
            build_processed_row(
                document_id=build_document_id(source, source_id),
                source=source,
                source_id=source_id,
                title=str(row.get("title") or ""),
                url="",
                description=cleaning_result.description,
                cleaned_text=cleaning_result.cleaned_text,
                description_length=cleaning_result.description_length,
                cleaned_text_length=cleaning_result.cleaned_text_length,
                removed_patterns=cleaning_result.removed_patterns,
                noise_types=cleaning_result.noise_types,
                keywords=keyword_result.keywords,
                keyword_count=keyword_result.keyword_count,
                keyword_basis=keyword_result.keyword_basis,
                text_status="valid_text",
                metadata=metadata,
            )
        )

    return processed_rows


def preprocess_mythology(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """세계 요괴/신화 데이터를 공통 processed 구조로 전처리한다."""
    processed_rows = []

    for index, row in enumerate(rows, start=1):
        description = str(row.get("description") or "")
        if not description.strip():
            continue

        cleaning_result = clean_mythology_text(description)
        source = str(row.get("source") or "mythology")
        source_id = build_source_id(source, row.get("name"), description, row.get("origin"), index)
        metadata = clean_metadata(
            {
                "origin": row.get("origin"),
                "habitats": row.get("habitats"),
                "weakness": row.get("weakness"),
                "row_index": index,
            }
        )
        keyword_result = extract_mythology_keywords(
            name=str(row.get("name") or ""),
            cleaned_text=cleaning_result.cleaned_text,
            metadata=metadata,
        )

        processed_rows.append(
            build_processed_row(
                document_id=build_document_id(source, source_id),
                source=source,
                source_id=source_id,
                title=str(row.get("name") or ""),
                url="",
                description=cleaning_result.description,
                cleaned_text=cleaning_result.cleaned_text,
                description_length=cleaning_result.description_length,
                cleaned_text_length=cleaning_result.cleaned_text_length,
                removed_patterns=cleaning_result.removed_patterns,
                noise_types=cleaning_result.noise_types,
                keywords=keyword_result.keywords,
                keyword_count=keyword_result.keyword_count,
                keyword_basis=keyword_result.keyword_basis,
                text_status="valid_text",
                metadata=metadata,
            )
        )

    return processed_rows


def main() -> None:
    """설정된 처리 대상만 전처리하고 개별 processed JSON을 저장한다."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if PROCESS_DCINSIDE:
        dcinside_rows = preprocess_dcinside(read_json(DCINSIDE_RAW_FILE))
        write_json(DCINSIDE_OUTPUT_FILE, dcinside_rows)
        print(f"생성 완료: {DCINSIDE_OUTPUT_FILE} ({len(dcinside_rows)}건)")

    if PROCESS_VERIFIED:
        verified_rows = preprocess_verified(read_json(VERIFIED_RAW_FILE))
        write_json(VERIFIED_OUTPUT_FILE, verified_rows)
        print(f"생성 완료: {VERIFIED_OUTPUT_FILE} ({len(verified_rows)}건)")

    if PROCESS_MYTHOLOGY:
        mythology_rows = preprocess_mythology(read_json(MYTHOLOGY_RAW_FILE))
        write_json(MYTHOLOGY_OUTPUT_FILE, mythology_rows)
        print(f"생성 완료: {MYTHOLOGY_OUTPUT_FILE} ({len(mythology_rows)}건)")

    if PROCESS_MISIN:
        raise RuntimeError("misin.json은 현재 전처리 대상이 아니다. PostgreSQL 단순 적재 쪽에서 처리한다.")


if __name__ == "__main__":
    main()
