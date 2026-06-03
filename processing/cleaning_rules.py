"""
본문 정리 규칙을 모아둔 파일이다.

이 파일은 원천 JSON을 직접 읽거나 processed 파일을 저장하지 않는다.
텍스트 하나를 받아서 정리 결과, 제거한 패턴, 발견된 노이즈 유형을
반환하는 역할만 담당한다.

참고한 reference 개념:
- Data Cleaning: replace, 정규표현식, 문자열 정리
- Pandas 심화: 조건별 값 처리와 정리 규칙 분리
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


# 원문에서 먼저 탐지할 노이즈 후보들이다.
NOISE_DETECTORS = {
    "markdown_links": re.compile(r"\[[^\]]+\]\([^)]+\)"),
    "urls": re.compile(r"https?://\S+|www\.\S+"),
    "citation_numbers": re.compile(r"\[\d+\]"),
    "square_brackets": re.compile(r"[\[\]]"),
    "special_symbols": re.compile(r"[#^]"),
    "extra_whitespace": re.compile(r"[ \t]{2,}"),
    "repeated_newlines": re.compile(r"\n{3,}"),
    "html_tags": re.compile(r"<[^>]+>"),
    "script_or_dom_noise": re.compile(
        r"JSON\.parse|localStorage|document\.|window\.|function\s*\(|addEventListener",
        re.IGNORECASE,
    ),
    "css_noise": re.compile(
        r"-webkit-|visibility\s*:|position\s*:|display\s*:|@keyframes|transform\s*:",
        re.IGNORECASE,
    ),
}


# 실제 cleaned_text를 만들 때 적용할 제거/치환 규칙이다.
CLEANING_RULES = {
    "markdown_links": re.compile(r"\[([^\]]+)\]\([^)]+\)"),
    "urls": re.compile(r"https?://\S+|www\.\S+"),
    "citation_numbers": re.compile(r"\[\d+\]"),
    "square_brackets": re.compile(r"[\[\]]"),
    "special_symbols": re.compile(r"[#^]"),
    "html_tags": re.compile(r"<[^>]+>"),
    "extra_whitespace": re.compile(r"[ \t]{2,}"),
    "repeated_newlines": re.compile(r"\n{3,}"),
}


# 파일별 전처리 정책에서 사용할 기본 규칙 묶음이다.
THERING_RULES = (
    "markdown_links",
    "urls",
    "citation_numbers",
    "square_brackets",
    "special_symbols",
    "html_tags",
    "extra_whitespace",
    "repeated_newlines",
)

MYTHOLOGY_RULES = (
    "urls",
    "citation_numbers",
    "square_brackets",
    "special_symbols",
    "html_tags",
    "extra_whitespace",
    "repeated_newlines",
)


@dataclass
class CleaningResult:
    """본문 정리 결과를 한 번에 전달하기 위한 자료 구조다."""

    description: str
    cleaned_text: str
    description_length: int
    cleaned_text_length: int
    removed_patterns: list[str]
    noise_types: list[str]


def normalize_text_value(value: object) -> str:
    """None, 리스트, 숫자 등 다양한 값을 안전하게 문자열로 바꾼다."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(normalize_text_value(item) for item in value if item is not None)
    return str(value)


def join_text_parts(parts: Iterable[object], separator: str = "\n\n") -> str:
    """여러 본문 후보 컬럼을 하나의 설명문으로 합친다."""
    normalized_parts = [normalize_text_value(part).strip() for part in parts]
    non_empty_parts = [part for part in normalized_parts if part]
    return separator.join(non_empty_parts)


def detect_noise_types(text: str) -> list[str]:
    """원문에서 발견되는 노이즈 유형 이름을 반환한다."""
    return [
        noise_name
        for noise_name, pattern in NOISE_DETECTORS.items()
        if pattern.search(text)
    ]


def has_heavy_script_noise(text: str) -> bool:
    """스크립트나 CSS 노이즈가 심해 본문 정리보다 보류가 나은지 판단한다."""
    if not text:
        return False

    noise_types = set(detect_noise_types(text))
    has_script_noise = "script_or_dom_noise" in noise_types
    has_css_noise = "css_noise" in noise_types
    korean_char_count = len(re.findall(r"[가-힣]", text))

    return (has_script_noise or has_css_noise) and korean_char_count < 20


def clean_text(text: object, rules: Iterable[str]) -> CleaningResult:
    """지정한 규칙만 적용해 본문을 정리하고 제거 기록을 반환한다."""
    description = normalize_text_value(text)
    cleaned_text = description
    removed_patterns: list[str] = []
    noise_types = detect_noise_types(description)

    for rule_name in rules:
        pattern = CLEANING_RULES[rule_name]
        if not pattern.search(cleaned_text):
            continue

        removed_patterns.append(rule_name)

        if rule_name == "markdown_links":
            cleaned_text = pattern.sub(r"\1", cleaned_text)
        elif rule_name in {"extra_whitespace", "repeated_newlines"}:
            replacement = "\n\n" if rule_name == "repeated_newlines" else " "
            cleaned_text = pattern.sub(replacement, cleaned_text)
        else:
            cleaned_text = pattern.sub("", cleaned_text)

    cleaned_text = normalize_spacing(cleaned_text)

    return CleaningResult(
        description=description,
        cleaned_text=cleaned_text,
        description_length=len(description),
        cleaned_text_length=len(cleaned_text),
        removed_patterns=removed_patterns,
        noise_types=noise_types,
    )


def normalize_spacing(text: str) -> str:
    """정리 과정 뒤에 남은 공백과 줄바꿈을 한 번 더 정돈한다."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_thering_text(text: object) -> CleaningResult:
    """thering 데이터의 괴담 본문에 맞춘 정리 규칙을 적용한다."""
    return clean_text(text, THERING_RULES)


def clean_mythology_text(text: object) -> CleaningResult:
    """global mythology 데이터의 설명 본문에 맞춘 정리 규칙을 적용한다."""
    return clean_text(text, MYTHOLOGY_RULES)


def clean_metadata_value(value: object) -> object:
    """metadata 값을 삭제하지 않고 문자열 노이즈만 가볍게 정리한다."""
    if value is None:
        return None
    if isinstance(value, list):
        return [clean_metadata_value(item) for item in value]
    if isinstance(value, dict):
        return {key: clean_metadata_value(item) for key, item in value.items()}
    if not isinstance(value, str):
        return value

    cleaned_value = value
    for rule_name in ("markdown_links", "urls", "html_tags", "extra_whitespace", "repeated_newlines"):
        pattern = CLEANING_RULES[rule_name]
        if rule_name == "markdown_links":
            cleaned_value = pattern.sub(r"\1", cleaned_value)
        elif rule_name in {"extra_whitespace", "repeated_newlines"}:
            replacement = "\n\n" if rule_name == "repeated_newlines" else " "
            cleaned_value = pattern.sub(replacement, cleaned_value)
        else:
            cleaned_value = pattern.sub("", cleaned_value)

    return normalize_spacing(cleaned_value)
