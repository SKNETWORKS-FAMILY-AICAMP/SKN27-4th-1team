from typing import Any

from archive.services.search_policy import GENERIC_RECORD_NAMES, GENERIC_SEARCH_TERMS


def is_relevant_record(
    keywords: list[str],
    strong_values: list[Any],
    weak_values: list[Any],
    single_keyword_weak_match_count: int = 2,
) -> bool:
    """넓은 OR 검색 후보 중 실제 핵심 키워드와 충분히 맞는 기록만 남긴다."""
    significant_keywords = get_significant_keywords(keywords)
    strong_text = normalize_match_text(*strong_values)
    weak_text = normalize_match_text(*weak_values)
    combined_text = f"{strong_text} {weak_text}".strip()
    if not combined_text:
        return False

    if has_keyword_match(significant_keywords, strong_text):
        return True

    if has_phrase_keyword_match(significant_keywords, combined_text):
        return True

    matched_keyword_count = count_matched_keywords(significant_keywords, combined_text)
    if len(significant_keywords) >= 2:
        return matched_keyword_count >= 2

    return count_keyword_occurrences(significant_keywords, weak_text) >= single_keyword_weak_match_count


def is_generic_record_name(name: str, keywords: list[str]) -> bool:
    """장르 대표 문서는 사용자가 그 제목을 직접 찾을 때만 노출한다."""
    normalized_name = str(name).strip().lower()
    if normalized_name not in GENERIC_RECORD_NAMES:
        return False

    return not has_keyword_match(get_significant_keywords(keywords), normalized_name)


def score_record_text(keywords: list[str], *values: Any) -> int:
    """검색 결과 정렬을 위해 키워드 등장 횟수 기반 점수를 계산한다."""
    score = 0
    for index, value in enumerate(values):
        text = str(value).lower() if value else ""
        if not text:
            continue

        weight = 4 if index == 0 else 1
        for keyword in keywords:
            score += text.count(keyword.lower()) * weight

    return score


def get_significant_keywords(keywords: list[str]) -> list[str]:
    """여러 키워드가 있을 때 장르/요청성 넓은 단어보다 구체 단어를 우선한다."""
    significant_keywords = [
        keyword
        for keyword in keywords
        if keyword.replace(" ", "").lower() not in GENERIC_SEARCH_TERMS
    ]
    return significant_keywords or keywords


def normalize_match_text(*values: Any) -> str:
    return " ".join(str(value).lower() for value in values if value)


def has_keyword_match(keywords: list[str], text: str) -> bool:
    return any(keyword.lower() in text for keyword in keywords)


def has_phrase_keyword_match(keywords: list[str], text: str) -> bool:
    return any(" " in keyword and keyword.lower() in text for keyword in keywords)


def count_matched_keywords(keywords: list[str], text: str) -> int:
    return sum(1 for keyword in keywords if keyword.lower() in text)


def count_keyword_occurrences(keywords: list[str], text: str) -> int:
    return sum(text.count(keyword.lower()) for keyword in keywords)
