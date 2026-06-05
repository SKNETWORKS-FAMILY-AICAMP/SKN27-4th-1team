"""
문서별 대표 키워드를 추출하는 규칙을 모아둔 파일이다.

이 파일은 원천 JSON을 직접 읽거나 processed 파일을 저장하지 않는다.
정리된 본문, 제목, 기존 키워드, 메타데이터를 받아 대표 키워드와
키워드 추출 기준 설명을 반환한다.

참고한 reference 개념:
- Integer Encoding: 단어 빈도 기반 어휘 후보 추출, 불용어 제외
- 형태소 분석 & 어휘집 & Padding: 토큰화, 품사/명사 중심 후보 추출 흐름
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable


# 너무 일반적이어서 대표 키워드로 보기 어려운 한국어 표현이다.
KOREAN_STOPWORDS = {
    "이야기",
    "본문",
    "사람",
    "친구",
    "생각",
    "정도",
    "순간",
    "느낌",
    "어디",
    "무엇",
    "그것",
    "그때",
    "그런데",
    "저희",
    "제가",
    "그냥",
    "계속",
    "기억",
    "함께",
    "들은",
    "일했던",
    "아는",
    "밤늦게",
    "일행",
    "모두들",
    "피곤하여",
    "운전자",
    "타고",
    "너무",
    "차를",
    "하나",
    "때문",
    "관련",
    "기록",
    "전설",
    "존재",
    "기원",
    "문헌",
    "구전",
    "오늘날",
    "흔적",
}


# 영어 설명 데이터에서 너무 흔하게 나오는 단어를 제외한다.
ENGLISH_STOPWORDS = {
    "the",
    "and",
    "are",
    "was",
    "were",
    "with",
    "from",
    "that",
    "this",
    "also",
    "known",
    "said",
    "into",
    "their",
    "they",
    "have",
    "has",
    "been",
    "being",
    "about",
    "after",
    "before",
    "between",
    "recorded",
    "historical",
    "mysterious",
    "occult",
    "entity",
    "entities",
}


@dataclass
class KeywordResult:
    """키워드 추출 결과를 한 번에 전달하기 위한 자료 구조다."""

    keywords: list[str]
    keyword_count: int
    keyword_basis: str


def normalize_keyword(value: object) -> str:
    """키워드 후보를 비교하기 쉽도록 앞뒤 공백과 일부 기호를 정리한다."""
    text = "" if value is None else str(value)
    text = re.sub(r"\s+", " ", text)
    text = text.strip(" \t\r\n,.;:!?\"'[]{}")
    return text.strip()


def flatten_values(values: Iterable[Any]) -> list[str]:
    """문자열, 리스트, None이 섞인 값을 키워드 후보 문자열 목록으로 펼친다."""
    flattened: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, list):
            flattened.extend(flatten_values(value))
        else:
            keyword = normalize_keyword(value)
            if keyword:
                flattened.append(keyword)
    return flattened


def unique_preserve_order(values: Iterable[str]) -> list[str]:
    """중복 키워드를 제거하되 처음 등장한 순서는 유지한다."""
    seen = set()
    result = []
    for value in values:
        normalized = normalize_keyword(value)
        compare_key = normalized.lower()
        if not normalized or compare_key in seen:
            continue
        seen.add(compare_key)
        result.append(normalized)
    return result


def extract_korean_terms(text: str, limit: int = 20) -> list[str]:
    """본문에서 2글자 이상의 한국어 명사 후보를 빈도 기반으로 뽑는다."""
    terms = re.findall(r"[가-힣]{2,}", text)
    filtered_terms = []

    for term in terms:
        normalized_term = normalize_korean_term(term)
        if (
            normalized_term
            and normalized_term not in KOREAN_STOPWORDS
            and not normalized_term.endswith(
            (
                "입니다",
                "합니다",
                "하였다",
                "했다",
                "했다가",
                "했다고",
                "있었다",
                "있었다고",
                "더랍니다",
                "랍니다",
                "에게",
                "으로",
                "하고",
                "에서",
            )
        )
        ):
            filtered_terms.append(normalized_term)

    return [term for term, _ in Counter(filtered_terms).most_common(limit)]


def normalize_korean_term(term: str) -> str:
    """한국어 후보 단어 끝의 조사나 서술형 어미를 가볍게 정리한다."""
    term = term.strip()
    term = re.sub(r"(으로|에게|에서|하며|하고|였다|했다|였다가|했다가)$", "", term)
    term = re.sub(r"(은|는|이|가|을|를|의)$", "", term)
    return term if len(term) >= 2 else ""


def extract_english_terms(text: str, limit: int = 20) -> list[str]:
    """영어 설명에서 3글자 이상의 의미 있는 단어 후보를 빈도 기반으로 뽑는다."""
    terms = re.findall(r"[A-Za-z][A-Za-z'-]{2,}", text.lower())
    filtered_terms = [
        term
        for term in terms
        if term not in ENGLISH_STOPWORDS and len(term) >= 3
    ]
    return [term for term, _ in Counter(filtered_terms).most_common(limit)]


def extract_title_terms(title: str) -> list[str]:
    """제목에서 회차 번호 같은 장식 표현을 줄이고 핵심 제목 후보를 뽑는다."""
    if not title:
        return []

    cleaned_title = re.sub(r"제\d+화", "", title)
    cleaned_title = re.sub(r"당신에게도 일어난 무서운 이야기", "", cleaned_title)
    cleaned_title = cleaned_title.strip(" -")

    candidates = [cleaned_title] if cleaned_title else []
    candidates.extend(extract_korean_terms(cleaned_title, limit=5))
    return unique_preserve_order(candidates)


def choose_keywords(candidates: Iterable[str], limit: int = 8) -> list[str]:
    """후보 목록에서 너무 짧거나 중복된 값을 제외하고 상위 키워드를 고른다."""
    chosen = []
    for candidate in unique_preserve_order(candidates):
        if len(candidate) < 2:
            continue
        if candidate in KOREAN_STOPWORDS or candidate.lower() in ENGLISH_STOPWORDS:
            continue
        chosen.append(candidate)
        if len(chosen) >= limit:
            break
    return chosen


def extract_thering_keywords(
    title: str,
    cleaned_text: str,
    existing_keywords: Iterable[Any] | None = None,
    metadata: dict[str, Any] | None = None,
    limit: int = 8,
) -> KeywordResult:
    """thering 괴담 데이터에 맞춰 대표 키워드를 추출한다."""
    metadata = metadata or {}
    existing_keywords = existing_keywords or []

    candidates: list[str] = []
    candidates.extend(flatten_values(existing_keywords))
    candidates.extend(extract_title_terms(title))
    candidates.extend(flatten_values([metadata.get("category"), metadata.get("subcategory")]))
    candidates.extend(extract_korean_terms(cleaned_text, limit=30))

    keywords = choose_keywords(candidates, limit=limit)
    basis = (
        "기존 keywords, 제목의 사건/장소 단서, category/subcategory, "
        "본문에서 반복되는 한국어 핵심 명사를 기준으로 추출했다."
    )

    return KeywordResult(
        keywords=keywords,
        keyword_count=len(keywords),
        keyword_basis=basis,
    )


def extract_mythology_keywords(
    name: str,
    cleaned_text: str,
    metadata: dict[str, Any] | None = None,
    limit: int = 8,
) -> KeywordResult:
    """global mythology 데이터에 맞춰 대표 키워드를 추출한다."""
    metadata = metadata or {}

    candidates: list[str] = []
    candidates.extend(flatten_values([name]))
    candidates.extend(flatten_values([metadata.get("origin"), metadata.get("habitats")]))
    candidates.extend(extract_korean_terms(str(metadata.get("signs", "")), limit=8))
    candidates.extend(extract_korean_terms(str(metadata.get("weakness", "")), limit=8))
    candidates.extend(extract_korean_terms(cleaned_text, limit=20))
    candidates.extend(extract_english_terms(cleaned_text, limit=20))

    keywords = choose_keywords(candidates, limit=limit)
    basis = (
        "name, origin, habitats, signs, weakness와 본문의 한국어/영어 핵심어를 "
        "함께 사용해 존재 유형, 지역, 특징, 대처법 중심으로 추출했다."
    )

    return KeywordResult(
        keywords=keywords,
        keyword_count=len(keywords),
        keyword_basis=basis,
    )
