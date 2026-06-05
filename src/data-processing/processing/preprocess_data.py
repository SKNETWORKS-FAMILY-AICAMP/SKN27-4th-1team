"""
원천 JSON을 읽어 전처리된 processed JSON 파일을 생성한다.

이 파일은 `cleaning_rules.py`와 `keyword_extractor.py`를 연결한다.
현재 정책상 `thering_horror.json`과 `ultimate_global_mythology_1000.json`을
우선 처리하고, `namu_asia_horror.json`은 본문 재확인이 필요하므로 기본
처리 대상에서 제외한다.

참고한 reference 개념:
- Pandas 기초: JSON records 형태 저장, 컬럼 단위 결과 구성
- Pandas 심화: apply처럼 행별 처리 함수를 적용하는 흐름
- Data Cleaning: 정리 전/후 비교 가능한 컬럼 생성
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cleaning_rules import (
    clean_metadata_value,
    clean_mythology_text,
    clean_thering_text,
    has_heavy_script_noise,
)
from keyword_extractor import extract_mythology_keywords, extract_thering_keywords


# 프로젝트 기준 경로를 잡아서 어디에서 실행해도 같은 폴더를 바라보게 한다.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "database" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "database" / "processed"


# namu 데이터는 content 품질이 의심되어 기본값을 False로 둔다.
PROCESS_NAMU = False
PROCESS_THERING = True
PROCESS_MYTHOLOGY = True


THERING_RAW_FILE = RAW_DIR / "thering_horror.json"
MYTHOLOGY_RAW_FILE = RAW_DIR / "ultimate_global_mythology_1000.json"
NAMU_RAW_FILE = RAW_DIR / "namu_asia_horror.json"

THERING_OUTPUT_FILE = PROCESSED_DIR / "thering_horror_processed.json"
MYTHOLOGY_OUTPUT_FILE = PROCESSED_DIR / "ultimate_global_mythology_processed.json"
NAMU_OUTPUT_FILE = PROCESSED_DIR / "namu_asia_horror_metadata_processed.json"
INTEGRATED_OUTPUT_FILE = PROCESSED_DIR / "integrated_horror_processed.json"


def read_json(path: Path) -> list[dict[str, Any]]:
    """JSON 리스트 파일을 읽어온다."""
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError(f"{path.name} 파일은 JSON 리스트 형태여야 합니다.")
    return data


def write_json(path: Path, rows: list[dict[str, Any]]) -> None:
    """전처리 결과를 UTF-8 JSON으로 저장한다."""
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


def build_document_id(source: str, source_id: Any) -> str:
    """출처와 원본 ID를 합쳐 통합 데이터셋 안에서 쓸 고유 ID를 만든다."""
    source_key = str(source or "unknown").strip().lower()
    source_key = source_key.replace(" ", "_")
    return f"{source_key}_{source_id}"


def clean_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """metadata 딕셔너리 안의 문자열 값을 보존하면서 가볍게 정리한다."""
    return {
        key: clean_metadata_value(value)
        for key, value in metadata.items()
    }


def preprocess_thering(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """thering 괴담 데이터를 공통 processed 구조로 전처리한다."""
    processed_rows = []

    for row in rows:
        cleaning_result = clean_thering_text(row.get("content"))
        metadata = clean_metadata({
            "category": row.get("category"),
            "subcategory": row.get("subcategory"),
            "country": row.get("country"),
            "horror_level": row.get("horror_level"),
            "date": row.get("date"),
            "date_raw": row.get("date_raw"),
            "series_number": row.get("series_number"),
            "submitter": row.get("submitter"),
            "comment_count": row.get("comment_count"),
            "has_image": row.get("has_image"),
        })
        keyword_result = extract_thering_keywords(
            title=str(row.get("title") or ""),
            cleaned_text=cleaning_result.cleaned_text,
            existing_keywords=row.get("keywords") or [],
            metadata=metadata,
        )

        processed_rows.append(
            build_processed_row(
                document_id=build_document_id(str(row.get("source") or "thering"), row.get("id")),
                source=str(row.get("source") or "thering"),
                source_id=row.get("id"),
                title=str(row.get("title") or ""),
                url=str(row.get("url") or ""),
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
    """global mythology 데이터를 공통 processed 구조로 전처리한다."""
    processed_rows = []

    for row in rows:
        description = str(row.get("description") or "")
        cleaning_result = clean_mythology_text(description)
        metadata = clean_metadata({
            "origin": row.get("origin"),
            "habitats": row.get("habitats"),
            "source_site": row.get("source_site"),
            "behavior": row.get("behavior"),
            "history": row.get("history"),
            "signs": row.get("signs"),
            "weakness": row.get("weakness"),
            "survival_rules": row.get("survival_rules"),
        })
        keyword_result = extract_mythology_keywords(
            name=str(row.get("name") or ""),
            cleaned_text=cleaning_result.cleaned_text,
            metadata=metadata,
        )

        processed_rows.append(
            build_processed_row(
                document_id=build_document_id(str(row.get("source_site") or "Wikipedia"), row.get("id")),
                source=str(row.get("source_site") or "Wikipedia"),
                source_id=row.get("id"),
                title=str(row.get("name") or ""),
                url=str(row.get("source_url") or ""),
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


def preprocess_namu_metadata(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """namu 데이터는 본문 대신 메타데이터만 공통 구조로 정리한다."""
    processed_rows = []

    for row in rows:
        description = str(row.get("content") or "")
        text_status = "needs_recrawl" if has_heavy_script_noise(description) else "metadata_only"
        metadata = clean_metadata({
            "primary_type": row.get("primary_type"),
            "region": row.get("region"),
            "tags": row.get("tags"),
            "habitat": row.get("habitat"),
            "gender": row.get("gender"),
            "form": row.get("form"),
            "danger": row.get("danger"),
            "origin": row.get("origin"),
        })

        processed_rows.append(
            build_processed_row(
                document_id=build_document_id(str(row.get("source") or "namu_wiki"), row.get("id")),
                source=str(row.get("source") or "namu_wiki"),
                source_id=row.get("id"),
                title=str(row.get("title") or ""),
                url=str(row.get("url") or ""),
                description="",
                cleaned_text="",
                description_length=0,
                cleaned_text_length=0,
                removed_patterns=[],
                noise_types=["script_or_dom_noise", "css_noise"] if text_status == "needs_recrawl" else [],
                keywords=[],
                keyword_count=0,
                keyword_basis="content가 스크립트/로딩 노이즈로 판단되어 본문 기반 키워드 추출을 보류했다.",
                text_status=text_status,
                metadata=metadata,
            )
        )

    return processed_rows


def main() -> None:
    """정책에 따라 원천 JSON을 전처리하고 processed JSON을 저장한다."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    integrated_rows: list[dict[str, Any]] = []

    if PROCESS_THERING:
        thering_rows = preprocess_thering(read_json(THERING_RAW_FILE))
        write_json(THERING_OUTPUT_FILE, thering_rows)
        integrated_rows.extend(thering_rows)
        print(f"생성 완료: {THERING_OUTPUT_FILE}")

    if PROCESS_MYTHOLOGY:
        mythology_rows = preprocess_mythology(read_json(MYTHOLOGY_RAW_FILE))
        write_json(MYTHOLOGY_OUTPUT_FILE, mythology_rows)
        integrated_rows.extend(mythology_rows)
        print(f"생성 완료: {MYTHOLOGY_OUTPUT_FILE}")

    if PROCESS_NAMU:
        namu_rows = preprocess_namu_metadata(read_json(NAMU_RAW_FILE))
        write_json(NAMU_OUTPUT_FILE, namu_rows)
        print(f"생성 완료: {NAMU_OUTPUT_FILE}")

    write_json(INTEGRATED_OUTPUT_FILE, integrated_rows)
    print(f"생성 완료: {INTEGRATED_OUTPUT_FILE}")


if __name__ == "__main__":
    main()
