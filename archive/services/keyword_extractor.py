import re


SEARCH_STOPWORDS = {
    "괴담",
    "조회",
    "검색",
    "검색어",
    "관련",
    "대해",
    "대한",
    "같은",
    "처럼",
    "이런",
    "저런",
    "어떤",
    "혹시",
    "좀",
    "알려",
    "알려줘",
    "알려줘요",
    "알려주세요",
    "찾아",
    "찾아줘",
    "찾아줘요",
    "찾아주세요",
    "찾아봐",
    "보여",
    "보여줘",
    "보여줘요",
    "보여주세요",
    "추천",
    "추천해줘",
    "추천해줘요",
    "추천해주세요",
    "있어",
    "있나요",
    "있는",
    "없는",
    "이야기",
    "얘기",
    "기록",
    "본문",
    "열람",
    "해줘",
    "해줘요",
    "해주세요",
    "주세요",
    "싶어",
    "거",
    "것",
    "날",
    "오는",
}

SHORT_SEARCH_KEYWORDS = {
    "개",
    "귀",
    "꿈",
    "눈",
    "문",
    "물",
    "밤",
    "방",
    "발",
    "뱀",
    "불",
    "손",
    "숲",
    "쥐",
    "집",
    "칼",
    "피",
}

LONG_KOREAN_SUFFIXES = (
    "으로부터",
    "에서부터",
    "에게서",
    "한테서",
    "이라면서",
    "라면서",
    "이라고",
    "라고",
    "으로써",
    "으로서",
    "처럼",
    "보다",
    "까지",
    "부터",
    "에서",
    "에게",
    "한테",
    "마다",
    "밖에",
    "으로",
)

SINGLE_KOREAN_PARTICLES = ("이", "가", "을", "를", "은", "는", "만", "도", "에", "의")

VERB_LIKE_SUFFIXES = (
    "해줘요",
    "해주세요",
    "해줘",
    "달라는",
    "라는",
    "다고",
    "더라",
    "는데",
    "지만",
    "거나",
    "하고",
    "하는",
    "되는",
    "있는",
    "없는",
)

PREDICATE_ENDINGS = ("하", "해", "되", "돼", "오", "가", "보", "달", "줘", "들리")

PHRASE_LEADERS = {
    "검은",
    "까만",
    "깊은",
    "낡은",
    "늦은",
    "버려진",
    "붉은",
    "빨간",
    "어두운",
    "오래된",
    "하얀",
    "흰",
}

PHRASE_BREAKERS = {
    "금기",
    "도시전설",
    "목격담",
    "실화괴담",
}

PHRASE_TAILS = {
    "거울",
    "교통사고",
    "그림자",
    "마스크",
    "목소리",
    "사고",
    "소리",
    "신발",
    "엘리베이터",
    "인형",
    "터널",
    "근무",
}

PREDICATE_WORDS = {
    "가는",
    "나오는",
    "달라는",
    "들리는",
    "보이는",
    "씌워",
    "오는",
}


def extract_keywords(question: str, limit: int = 6) -> list[str]:
    """질문에서 검색에 사용할 핵심 키워드를 규칙 기반으로 정제해 추출한다."""
    raw_tokens = extract_search_tokens(question)
    cleaned_tokens = []
    for token in raw_tokens:
        cleaned_token = normalize_search_keyword(token)
        if not cleaned_token:
            continue

        if cleaned_token not in cleaned_tokens:
            cleaned_tokens.append(cleaned_token)

    phrase_candidates = make_phrase_candidates(cleaned_tokens)
    keywords = unique_preserve_order([*phrase_candidates, *cleaned_tokens])[:limit]
    if keywords:
        return keywords

    return [question]


def extract_search_tokens(question: str) -> list[str]:
    """검색어 후보가 될 한글/영문/숫자 토큰을 뽑는다."""
    return re.findall(r"[가-힣A-Za-z0-9]+", question)


def normalize_search_keyword(token: str) -> str:
    """요청어, 조사, 일부 어미를 제거해 DB 검색에 맞는 단어로 정리한다."""
    cleaned_token = token.strip()
    if not cleaned_token:
        return ""

    if is_stopword(cleaned_token):
        return ""

    cleaned_token = strip_korean_suffix(cleaned_token)
    if is_stopword(cleaned_token):
        return ""

    if cleaned_token in PREDICATE_WORDS:
        return ""

    if not is_meaningful_keyword(cleaned_token):
        return ""

    return cleaned_token


def strip_korean_suffix(token: str) -> str:
    """검색을 방해하는 흔한 조사와 요청형 어미를 가볍게 걷어낸다."""
    for suffix in (*VERB_LIKE_SUFFIXES, *LONG_KOREAN_SUFFIXES):
        if not token.endswith(suffix):
            continue

        candidate = token[:-len(suffix)]
        if is_meaningful_keyword(candidate):
            return candidate

    for suffix in SINGLE_KOREAN_PARTICLES:
        if not token.endswith(suffix):
            continue

        candidate = token[:-len(suffix)]
        if len(token) >= 4 or candidate in SHORT_SEARCH_KEYWORDS:
            if is_meaningful_keyword(candidate):
                return candidate

    return token


def make_phrase_candidates(tokens: list[str]) -> list[str]:
    """띄어쓴 고유명/제목형 표현을 보존하기 위해 짧은 인접 토큰을 묶는다."""
    phrases = []
    for left, right in zip(tokens, tokens[1:]):
        if not can_join_phrase(left, right):
            continue

        phrase = f"{left} {right}"
        if phrase not in phrases:
            phrases.append(phrase)

    return phrases[:2]


def can_join_phrase(left: str, right: str) -> bool:
    """동사형 표현을 피하면서 제목/명사구에 가까운 짧은 인접어만 묶는다."""
    if right in PHRASE_BREAKERS:
        return False

    if right in PHRASE_LEADERS:
        return False

    if len(left) > 6 or len(right) > 6:
        return False

    if len(left) == 1:
        return False

    if looks_like_predicate(left) or looks_like_predicate(right):
        return False

    if len(right) == 1:
        return left in PHRASE_LEADERS and right in SHORT_SEARCH_KEYWORDS

    if left in PHRASE_LEADERS:
        return True

    return right in PHRASE_TAILS


def looks_like_predicate(token: str) -> bool:
    """복합 검색어로 묶기 애매한 동사/형용사형 토큰을 거른다."""
    return token in PREDICATE_WORDS or token.endswith(PREDICATE_ENDINGS)


def is_stopword(token: str) -> bool:
    return token in SEARCH_STOPWORDS or token.lower() in SEARCH_STOPWORDS


def is_meaningful_keyword(token: str) -> bool:
    return len(token) >= 2 or token in SHORT_SEARCH_KEYWORDS


def unique_preserve_order(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        compare_key = value.lower()
        if compare_key in seen:
            continue

        seen.add(compare_key)
        result.append(value)

    return result


def extract_fallback_keywords(question: str, primary_keywords: list[str], limit: int = 4) -> list[str]:
    """정제 검색 실패 시 원문 토큰으로 한 번 더 찾아보기 위한 후보를 만든다."""
    primary_set = {keyword.lower() for keyword in primary_keywords}
    fallback_keywords = []
    for token in extract_search_tokens(question):
        cleaned_token = token.strip()
        if is_stopword(cleaned_token):
            continue

        if not is_meaningful_keyword(cleaned_token):
            continue

        compare_key = cleaned_token.lower()
        if compare_key in primary_set:
            continue

        if cleaned_token not in fallback_keywords:
            fallback_keywords.append(cleaned_token)

        if len(fallback_keywords) >= limit:
            break

    return fallback_keywords
