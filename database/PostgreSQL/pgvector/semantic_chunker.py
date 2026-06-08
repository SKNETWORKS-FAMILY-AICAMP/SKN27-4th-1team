"""pgvector 임베딩을 위한 문장 기준 청킹 유틸리티.

임베딩 파이프라인은 긴 원본 기록을 여러 개의 청크로 나누어 저장한다.
이 모듈은 단순히 N글자마다 자르지 않고, 문단과 문장 경계를 우선해서
청크가 검색 결과로 나왔을 때도 읽기 쉬운 형태를 유지한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


DEFAULT_TARGET_SIZE = 900
DEFAULT_MAX_SIZE = 1200
DEFAULT_MIN_SIZE = 80
DEFAULT_OVERLAP_SENTENCES = 1

# 빈 줄이 1개 이상 이어지는 부분은 문단 경계로 본다.
# 괴담/설화 데이터는 문단 단위 맥락이 중요해서 먼저 문단을 살린 뒤 문장으로 쪼갠다.
_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n+")
_WHITESPACE_RE = re.compile(r"[ \t\r\f\v]+")

# 영어/일본어/한국어 문장 끝 후보를 넓게 잡는다.
# 완벽한 형태소 분석이 아니라, 임베딩용 청크가 문장 중간에서 끊기는 일을 줄이는 목적이다.
_SENTENCE_RE = re.compile(
    r".+?(?:[.!?…。]|다|요|니다|습니다|했다|였다|한다|된다|있다|없다)(?=\s+|$)"
)


@dataclass(frozen=True)
class TextChunk:
    """임베딩 저장을 위해 준비된 단일 텍스트 청크."""

    chunk_index: int
    content: str


def normalize_text(text: str) -> str:
    """문단 경계는 유지하면서 공백과 줄바꿈을 정리한다."""

    # Windows/Unix 줄바꿈을 통일해야 문단 분리 정규식이 안정적으로 동작한다.
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = []
    for paragraph in _PARAGRAPH_SPLIT_RE.split(text):
        # 문단 안쪽의 줄바꿈은 한 문장처럼 이어 붙인다.
        # 원본 JSON에는 보기 좋게 줄바꿈된 문장이 많아서 그대로 두면 짧은 조각이 너무 많이 생긴다.
        lines = [_WHITESPACE_RE.sub(" ", line).strip() for line in paragraph.split("\n")]
        normalized = " ".join(line for line in lines if line)
        if normalized:
            paragraphs.append(normalized)
    return "\n\n".join(paragraphs)


def split_paragraphs(text: str) -> list[str]:
    """텍스트를 비어 있지 않은 정규화된 문단 목록으로 나눈다."""

    normalized = normalize_text(text)
    if not normalized:
        return []
    return [paragraph.strip() for paragraph in _PARAGRAPH_SPLIT_RE.split(normalized) if paragraph.strip()]


def split_sentences(text: str, max_sentence_size: int = DEFAULT_MAX_SIZE) -> list[str]:
    """문단 하나를 문장에 가까운 단위로 나눈다.

    문장 하나가 여전히 너무 길면 max_sentence_size 근처의 문장부호나
    공백을 기준으로 다시 나눈다. 긴 문단을 위한 보조 처리다.
    """

    text = normalize_text(text).replace("\n\n", " ").strip()
    if not text:
        return []

    # 문장 끝 패턴에 걸리는 부분을 우선 문장 후보로 사용한다.
    matches = list(_SENTENCE_RE.finditer(text))
    sentences = [match.group(0).strip() for match in matches]

    # 마지막 문장이 마침표 없이 끝나는 경우가 있어서, 정규식이 못 잡은 나머지도 보존한다.
    matched_until = matches[-1].end() if matches else 0
    remainder = text[matched_until:].strip()
    if remainder:
        sentences.append(remainder)
    if not sentences:
        sentences = [text]

    result: list[str] = []
    for sentence in sentences:
        # 문장 하나가 너무 길면 그대로 임베딩하지 않고 보조 분할한다.
        # 이 처리가 없으면 긴 문단 하나가 max_size를 훌쩍 넘을 수 있다.
        result.extend(_split_long_sentence(sentence, max_sentence_size))
    return result


def chunk_text(
    text: str,
    *,
    title: str = "",
    target_size: int = DEFAULT_TARGET_SIZE,
    max_size: int = DEFAULT_MAX_SIZE,
    min_size: int = DEFAULT_MIN_SIZE,
    overlap_sentences: int = DEFAULT_OVERLAP_SENTENCES,
) -> list[TextChunk]:
    """텍스트를 문장 기준 임베딩 청크로 나눈다.

    Args:
        text: 청킹할 원본 텍스트.
        title: 선택 제목. 값이 있으면 각 청크 앞에 붙여 검색 결과의 맥락을 유지한다.
        target_size: 청크를 나누고 싶은 권장 길이.
        max_size: 청크가 넘지 않도록 관리하는 최대 길이.
        min_size: 너무 짧은 마지막 청크를 앞 청크에 합치기 위한 최소 길이.
        overlap_sentences: 다음 청크에 반복해서 넣을 이전 청크 끝 문장 수.
    """

    if target_size <= 0 or max_size <= 0:
        raise ValueError("target_size and max_size must be positive.")
    if target_size > max_size:
        raise ValueError("target_size must be less than or equal to max_size.")
    if min_size < 0:
        raise ValueError("min_size must be non-negative.")

    # 제목은 모든 청크 앞에 붙인다.
    # 검색 결과에서 청크 본문만 나와도 어느 기록인지 바로 알 수 있게 하기 위해서다.
    title = normalize_text(title).replace("\n\n", " ").strip()
    sentences: list[str] = []

    # 전체 텍스트를 문단 -> 문장 순서로 분해한다.
    # 글자 수 기준으로 바로 자르면 문장 중간이 끊겨 검색 품질과 가독성이 떨어진다.
    for paragraph in split_paragraphs(text):
        sentences.extend(split_sentences(paragraph, max_sentence_size=max_size))

    if not sentences:
        return []

    chunks: list[list[str]] = []
    current: list[str] = []

    for sentence in sentences:
        candidate = [*current, sentence]
        candidate_text = _join_sentences(candidate)

        # target_size는 "이쯤에서 자르면 좋다"는 권장 길이다.
        # 다음 문장을 붙였을 때 target_size를 넘으면 현재 청크를 먼저 확정한다.
        if current and len(candidate_text) > target_size:
            chunks.append(current)

            # 다음 청크가 완전히 단절되지 않도록 이전 청크 끝 문장을 조금 복사한다.
            # RAG 검색에서는 앞뒤 맥락이 조금 겹치는 편이 답변 품질에 유리하다.
            current = _overlap_tail(current, overlap_sentences)

        current.append(sentence)

        # max_size는 실제 저장 전에 넘지 않게 막는 강한 기준이다.
        # target_size보다 길어져도 괜찮지만, max_size 근처에서는 강제로 끊는다.
        if len(_join_sentences(current)) >= max_size:
            chunks.append(current)
            current = _overlap_tail(current, overlap_sentences)

    if current:
        chunks.append(current)

    merged = _merge_tiny_tail(chunks, min_size=min_size, max_size=max_size)
    output: list[TextChunk] = []
    for index, sentence_group in enumerate(merged):
        content = _join_sentences(sentence_group)
        if title:
            content = f"{title}\n\n{content}"
        output.append(TextChunk(chunk_index=index, content=content.strip()))
    return output


def chunk_record(
    *,
    title: str,
    parts: list[str],
    target_size: int = DEFAULT_TARGET_SIZE,
    max_size: int = DEFAULT_MAX_SIZE,
    min_size: int = DEFAULT_MIN_SIZE,
    overlap_sentences: int = DEFAULT_OVERLAP_SENTENCES,
) -> list[dict[str, str | int]]:
    """제목과 여러 본문 조각을 받아 저장하기 쉬운 dict 청크 목록을 만든다."""

    # DB 테이블마다 본문 후보 컬럼이 다를 수 있으므로 parts 리스트로 받는다.
    # 예: horror_stories는 preview/content, myth_entities는 description/history 등을 합칠 수 있다.
    body = "\n\n".join(str(part).strip() for part in parts if str(part or "").strip())
    chunks = chunk_text(
        body,
        title=title,
        target_size=target_size,
        max_size=max_size,
        min_size=min_size,
        overlap_sentences=overlap_sentences,
    )
    return [{"chunk_index": chunk.chunk_index, "content": chunk.content} for chunk in chunks]


def _split_long_sentence(sentence: str, max_size: int) -> list[str]:
    if len(sentence) <= max_size:
        return [sentence]

    pieces: list[str] = []
    remaining = sentence.strip()
    while len(remaining) > max_size:
        # 긴 문장을 무조건 max_size에서 자르지 않고, 근처의 문장부호/공백을 먼저 찾는다.
        split_at = _best_split_index(remaining, max_size)
        pieces.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        pieces.append(remaining)
    return pieces


def _best_split_index(text: str, max_size: int) -> int:
    window = text[:max_size]

    # 문장부호가 너무 앞쪽에 있으면 청크가 과하게 짧아지므로 55% 이후의 문장부호만 사용한다.
    punctuation_candidates = [window.rfind(mark) for mark in ("。", ".", "!", "?", "…", ",", "，", ";", "；")]
    best_punctuation = max(punctuation_candidates)
    if best_punctuation >= max_size * 0.55:
        return best_punctuation + 1

    # 문장부호가 없으면 공백 기준으로 끊는다. 그래도 너무 앞쪽 공백은 피한다.
    whitespace = window.rfind(" ")
    if whitespace >= max_size * 0.45:
        return whitespace + 1

    # 적당한 경계가 전혀 없으면 마지막 수단으로 max_size에서 자른다.
    return max_size


def _join_sentences(sentences: list[str]) -> str:
    return " ".join(sentence.strip() for sentence in sentences if sentence.strip()).strip()


def _overlap_tail(sentences: list[str], overlap_sentences: int) -> list[str]:
    if overlap_sentences <= 0:
        return []
    return sentences[-overlap_sentences:].copy()


def _merge_tiny_tail(chunks: list[list[str]], *, min_size: int, max_size: int) -> list[list[str]]:
    if len(chunks) <= 1:
        return chunks

    # 마지막 청크가 너무 짧으면 검색 결과로 나왔을 때 의미가 부족할 수 있다.
    # 그래서 max_size를 넘지 않는 선에서 앞 청크에 붙인다.
    tail = chunks[-1]
    tail_text = _join_sentences(tail)
    previous_text = _join_sentences(chunks[-2])

    if len(tail_text) < min_size and len(previous_text) + 1 + len(tail_text) <= max_size:
        deduped_tail = tail.copy()

        # overlap 때문에 앞 청크의 마지막 문장과 tail의 첫 문장이 같을 수 있다.
        # 병합할 때는 같은 문장을 한 번만 남겨 최종 content 중복을 막는다.
        while deduped_tail and chunks[-2] and deduped_tail[0] == chunks[-2][-1]:
            deduped_tail.pop(0)
        chunks[-2].extend(deduped_tail)
        chunks.pop()

    return chunks


if __name__ == "__main__":
    sample = (
        "폐교 음악실에서 들리는 세 번째 이름.\n\n"
        "비가 오는 날이면 복도 끝에서 발자국이 시작됩니다. "
        "이름을 세 번 부르면 거울 안쪽에서 누군가 대답합니다. "
        "기록자는 다음 날 같은 장소에서 발견됩니다."
    )
    for chunk in chunk_text(sample, title="샘플 괴담", target_size=80, max_size=120):
        print(f"[{chunk.chunk_index}] {chunk.content}\n")
