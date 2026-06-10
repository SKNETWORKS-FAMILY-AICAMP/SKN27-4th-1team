import json
import logging
from typing import Any, Literal, TypedDict

from archive.services.archive_search import (
    get_random_archive_suggestions,
    get_random_archive_records,
    search_archive_records_for_question,
)
from archive.services.keyword_extractor import extract_keywords
from archive.services.prompt import (
    build_evaluation_prompt,
    build_generation_prompt,
    build_generation_retry_prompt,
    build_general_chat_prompt,
    build_intent_classification_prompt,
    build_revision_prompt,
    build_search_choice_prompt,
    build_tts_narration_prompt,
)
from archive.services.search_policy import SIMPLE_GENERAL_CHAT_MESSAGES
from common.llm_factory import get_llm, get_post_generation_llm


class ArchiveState(TypedDict, total=False):
    status: str
    question: str
    intent: str
    keywords: list[str]
    query_analysis: dict[str, Any]
    archive_context: dict[str, Any]
    conversation_history: list[dict[str, str]]
    search_results: list[dict[str, Any]]
    source_story: dict[str, Any]
    generated_story: str
    evaluation: dict[str, Any]
    is_passed: bool
    revise_count: int
    llm_response: str
    skip_evaluation: bool


BANNED_PHRASES = (
    "귀신이었다",
    "악령이었다",
    "괴물이었다",
    "무서웠다",
    "소름이 돋았다",
    "공포에 질렸다",
    "꿈이었다",
    "환각이었다",
)

LITERARY_PHRASES = (
    "아주 무서운 밤",
    "무서운 밤",
    "그날 밤",
    "어둠이 뒤덮",
    "완전히 어둠",
    "몸이 떨리기 시작",
    "몸이 떨렸다",
    "손이 떨렸다",
    "정적이 흘렀",
    "알 수 없는 공포",
    "불길한 예감",
    "기묘한 분위기",
    "섬뜩한 기분",
    "차가운 공기",
    "숨이 멎",
    "공포에 질",
    "그 순간 나는 알았다",
    "그 순간 알았다",
    "아직도 내 가슴",
    "가슴에 남아",
    "잊을 수 없다",
    "눈앞에 펼쳐",
    "서서히",
    "희미한 불빛",
)

COMMUNITY_MARKERS = (
    "근데",
    "그런데",
    "아니",
    "지금 생각하면",
    "정확히는",
    "기억",
    "아무튼",
    "이상한 게",
    "그때는",
    "나중에",
    "분명",
    "솔직히",
)

CRITERION_SCORE_KEYS = (
    "contradiction",
    "reinterpretation",
    "restraint",
    "realism",
    "tension_curve",
    "cliche_avoidance",
    "aftertaste",
    "community_voice",
    "anti_literary_style",
)


def intent_node(state: ArchiveState) -> dict[str, Any]:
    """사용자 입력의 의도와 검색 키워드를 분류한다."""
    if state.get("source_story"):
        keywords = state.get("keywords", [])
        return {
            "intent": state.get("intent", "archive_query"),
            "keywords": keywords,
            "query_analysis": state.get(
                "query_analysis",
                build_query_analysis_from_keywords(
                    state.get("question", ""),
                    keywords,
                ),
            ),
        }

    question = state.get("question", "")
    classification = classify_intent_and_keywords(
        question,
        state.get("conversation_history", []),
    )
    return classification


def general_chat_node(state: ArchiveState) -> dict[str, Any]:
    """일반 대화는 검색 없이 챗봇 기본 화자 프롬프트로 바로 응답한다."""
    question = state.get("question", "")
    suggestion_topics = []
    if not is_simple_general_chat(question):
        suggestion_topics = get_random_archive_suggestions()

    prompt = build_general_chat_prompt(
        question=question,
        conversation_history=state.get("conversation_history", []),
        suggestion_topics=suggestion_topics,
    )
    response = invoke_gemma_llm(prompt)
    return {
        "llm_response": response,
        "generated_story": response,
        "search_results": [],
        "source_story": {},
        "evaluation": {},
        "is_passed": True,
    }


def decide_intent_node(
    state: ArchiveState,
) -> Literal[
    "archive_query",
    "generate",
    "general_chat",
    "recommend_request",
    "tts_request",
    "tts_stop",
]:
    """분류된 intent 값에 따라 archive 검색 흐름과 일반 대화 흐름을 나눈다."""
    if state.get("source_story"):
        return "generate"

    elif state.get("intent") == "archive_query":
        return "archive_query"

    elif state.get("intent") == "tts_request":
        return "tts_request"

    elif state.get("intent") == "tts_stop":
        return "tts_stop"

    elif state.get("intent") == "recommend_request":
        return "recommend_request"

    return "general_chat"


def tts_node(state: ArchiveState) -> dict[str, Any]:
    """낭독 요청은 LLM을 호출하지 않고 view의 스트리밍 처리로 넘길 상태만 만든다."""
    return {
        "status": "tts_ready",
        "intent": "tts_request",
        "llm_response": "마지막으로 열린 기록을 낭독하겠습니다.",
        "search_results": [],
        "source_story": {},
        "evaluation": {},
        "is_passed": True,
        "skip_evaluation": True,
    }


def tts_stop_node(state: ArchiveState) -> dict[str, Any]:
    """음성 중지 요청은 프론트엔드 재생 정지 흐름에 맞춘 상태만 만든다."""
    return {
        "status": "tts_stopped",
        "intent": "tts_stop",
        "llm_response": "낭독을 멈추겠습니다.",
        "search_results": [],
        "source_story": {},
        "evaluation": {},
        "is_passed": True,
        "skip_evaluation": True,
    }


def build_message_response(
    message: str,
    keywords: list[str] | None = None,
    query_analysis: dict[str, Any] | None = None,
    feedback: str = "",
    status: str = "",
    is_passed: bool = True,
) -> dict[str, Any]:
    """검색/생성 없이 사용자에게 바로 보여줄 종료 상태를 만든다."""
    response = {
        "keywords": keywords or [],
        "search_results": [],
        "source_story": {},
        "generated_story": message,
        "llm_response": message,
        "skip_evaluation": True,
        "evaluation": {},
        "is_passed": is_passed,
    }
    if query_analysis is not None:
        response["query_analysis"] = query_analysis

    if feedback:
        response["evaluation"] = {"feedback": feedback}

    if status:
        response["status"] = status

    return response


def build_search_choice_response(
    question: str,
    search_results: list[dict[str, Any]],
    conversation_history: list[dict[str, str]],
    keywords: list[str],
    query_analysis: dict[str, Any],
) -> dict[str, Any]:
    """검색 결과와 검색 안내 LLM 응답을 LangGraph 상태로 묶는다."""
    choice_prompt = build_search_choice_prompt(
        question=question,
        search_results=search_results,
        conversation_history=conversation_history,
    )
    return {
        "keywords": keywords,
        "query_analysis": query_analysis,
        "search_results": search_results,
        "source_story": search_results[0],
        "llm_response": invoke_llm(choice_prompt),
        "skip_evaluation": True,
        "evaluation": {},
        "is_passed": True,
    }


def build_failed_evaluation(feedback: str) -> dict[str, Any]:
    """사전 검수 실패를 평가 JSON 형태로 만든다."""
    return {
        "keyword_passed": True,
        "consistency_passed": True,
        "style_passed": False,
        "atmosphere_passed": False,
        "criterion_scores": {
            key: 0
            for key in CRITERION_SCORE_KEYS
        },
        "score_total": 0.0,
        "automatic_penalties": [feedback],
        "feedback": feedback,
    }


def build_story_log_extra(
    source_story: dict[str, Any],
    feedback: str = "",
) -> dict[str, Any]:
    """생성/수정 로그에 공통으로 들어갈 기록 식별값을 만든다."""
    extra = {
        "record_type": source_story.get("type", ""),
        "record_id": source_story.get("id", ""),
    }
    if feedback:
        extra["feedback"] = feedback

    return extra


def decide_after_generate_node(state: ArchiveState) -> Literal["evaluate", "finish"]:
    """검토할 원본과 생성문이 있을 때만 평가 노드를 실행한다."""
    if state.get("skip_evaluation"):
        return "finish"

    elif not state.get("source_story"):
        return "finish"

    elif not state.get("generated_story", "").strip():
        return "finish"

    return "evaluate"


def get_empty_generation_message() -> str:
    """생성 모델이 본문을 돌려주지 않았을 때 사용자에게 보여줄 메시지를 만든다."""
    return "선택한 기록을 다시 엮지 못했습니다. 잠시 후 다시 시도해 주세요."


def extract_story_from_model_response(response: str) -> str:
    """JSON 응답이면 new_story만 꺼내고, 아니면 원문을 그대로 사용한다."""
    text = response.strip()
    parsed_response = parse_json_object(text)
    if parsed_response:
        story = parsed_response.get("new_story")
        if isinstance(story, str) and story.strip():
            return story.strip()

    return text


def detect_phrases(story: str, phrases: tuple[str, ...]) -> list[str]:
    """본문에 포함된 금지/패널티 표현을 찾는다."""
    found_phrases = []
    for phrase in phrases:
        if phrase in story:
            found_phrases.append(phrase)

    return found_phrases


def has_community_voice(story: str) -> bool:
    """커뮤니티 게시글 말투로 볼 만한 표지가 있는지 확인한다."""
    return any(marker in story for marker in COMMUNITY_MARKERS)


def calculate_evaluation_total(evaluation: dict[str, Any]) -> float:
    """criterion_scores 평균을 100점 만점 점수로 바꾼다."""
    scores = evaluation.get("criterion_scores", {})
    if not isinstance(scores, dict):
        return 0.0

    values = []
    for key in CRITERION_SCORE_KEYS:
        value = scores.get(key)
        if isinstance(value, int | float):
            values.append(max(0.0, min(10.0, float(value))))

    if not values:
        return 0.0

    return round((sum(values) / len(values)) * 10, 1)


def has_required_criterion_scores(evaluation: dict[str, Any]) -> bool:
    """평가 JSON에 9개 세부 점수가 모두 있는지 확인한다."""
    scores = evaluation.get("criterion_scores", {})
    if not isinstance(scores, dict):
        return False

    for key in CRITERION_SCORE_KEYS:
        if not isinstance(scores.get(key), int | float):
            return False

    return True


def apply_automatic_penalties(
    evaluation: dict[str, Any],
    story: str,
) -> dict[str, Any]:
    """소설체와 게시글 말투 부족을 자동 감점으로 반영한다."""
    final_total = calculate_evaluation_total(evaluation)
    existing_penalties = evaluation.get("automatic_penalties", [])
    automatic_penalties = []
    if isinstance(existing_penalties, list):
        automatic_penalties = [
            str(penalty)
            for penalty in existing_penalties
            if str(penalty).strip()
        ]

    banned_hits = detect_phrases(story, BANNED_PHRASES)
    if banned_hits:
        final_total = min(final_total, 70.0)
        automatic_penalties.append(
            f"직접 공포 표현 발견: {', '.join(banned_hits[:8])}",
        )

    literary_hits = detect_phrases(story, LITERARY_PHRASES)
    if literary_hits:
        final_total = min(final_total, 82.0)
        automatic_penalties.append(
            f"문학체 표현 발견: {', '.join(literary_hits[:8])}",
        )

    if len(literary_hits) >= 3:
        final_total = min(final_total, 74.0)
        automatic_penalties.append(
            "문학체 표현이 3개 이상 발견되어 게시글 느낌이 약함",
        )

    if not has_community_voice(story):
        final_total = min(final_total, 84.0)
        automatic_penalties.append("커뮤니티 게시글 말투 지표가 부족함")

    if story.strip().startswith(("어린 시절", "어릴 적", "그날 밤", "나는")):
        final_total = min(final_total, 82.0)
        automatic_penalties.append("도입부가 소설/회상문처럼 시작함")

    return {
        **evaluation,
        "score_total": round(final_total, 1),
        "automatic_penalties": automatic_penalties,
    }


def get_story_precheck_feedback(story: str) -> str:
    """LLM 결과가 화면에 보여도 되는 완성된 괴담 형태인지 먼저 확인한다."""
    text = story.strip()
    if not text:
        return "생성 본문이 비어 있습니다."

    first_line = text.splitlines()[0].strip()
    if first_line.startswith("#") or first_line.startswith("**"):
        return "제목이나 마크다운 형식이 남아 있습니다."

    if len(first_line) >= 2 and first_line[0].isdigit() and first_line[1] in [".", ")"]:
        return "번호 목록 형식이 남아 있습니다."

    if len(first_line) >= 3 and first_line[:2].isdigit() and first_line[2] in [".", ")"]:
        return "번호 목록 형식이 남아 있습니다."

    quote_feedback = get_unclosed_quote_feedback(text)
    if quote_feedback:
        return quote_feedback

    normalized_text = text.rstrip().rstrip('"\'”’)]}」』').rstrip(".!?,。！？…")
    final_token = normalized_text.split()[-1] if normalized_text.split() else ""
    fragment_feedback = get_trailing_fragment_feedback(normalized_text, final_token)
    if fragment_feedback:
        return fragment_feedback

    incomplete_suffixes = [
        "은",
        "는",
        "이",
        "가",
        "을",
        "를",
        "에",
        "의",
        "와",
        "과",
        "로",
        "으로",
        "에서",
        "에게",
        "한테",
        "부터",
        "까지",
        "처럼",
        "보다",
        "밖에",
        "만",
        "도",
        "조차",
        "마저",
        "랑",
        "하고",
        "그리고",
        "하지만",
        "근데",
        "그런데",
        "그래서",
        "왜냐하면",
    ]
    for suffix in incomplete_suffixes:
        if final_token == suffix:
            return "마지막 문장이 중간에서 끊긴 것으로 보입니다."

        if len(final_token) > len(suffix) and final_token.endswith(suffix):
            return "마지막 문장이 중간에서 끊긴 것으로 보입니다."

    return ""


def get_unclosed_quote_feedback(text: str) -> str:
    """닫히지 않은 따옴표가 있는지 확인한다."""
    quote_pairs = [
        ("‘", "’"),
        ("“", "”"),
        ("「", "」"),
        ("『", "』"),
    ]
    for opening_quote, closing_quote in quote_pairs:
        if text.count(opening_quote) > text.count(closing_quote):
            return "따옴표가 닫히지 않은 미완성 문장입니다."

    if text.count('"') % 2 == 1:
        return "따옴표가 닫히지 않은 미완성 문장입니다."

    return ""


def get_trailing_fragment_feedback(normalized_text: str, final_token: str) -> str:
    """마지막 문장이 단어 조각에서 끊겼는지 확인한다."""
    if not final_token:
        return ""

    trailing_fragment_patterns = [
        "의",
        "라는",
        "이라고",
        "이라",
        "라고",
        "같은",
    ]
    if len(final_token) <= 2:
        for pattern in trailing_fragment_patterns:
            if normalized_text.endswith(f"{pattern} {final_token}"):
                return "마지막 문장이 단어 중간에서 끊긴 것으로 보입니다."

    if len(final_token) == 1 and normalized_text[-1].isalnum():
        previous_text = normalized_text[:-1].rstrip()
        if previous_text.endswith(("의", "라는", "이라고", "이라", "라고")):
            return "마지막 문장이 단어 중간에서 끊긴 것으로 보입니다."

    return ""


def classify_intent_and_keywords(
    question: str,
    conversation_history: list[dict[str, str]],
) -> dict[str, Any]:
    """LLM으로 intent와 키워드를 함께 판정하고 실패 시 규칙 기반으로 폴백한다."""
    prompt = build_intent_classification_prompt(
        question=question,
        conversation_history=conversation_history,
    )
    try:
        classification = parse_intent_classification_response(invoke_llm(prompt))
        if classification:
            if classification["intent"] == "tts_request" and not is_tts_read_request(question):
                return classify_intent_and_keywords_by_rule(question)

            if classification["intent"] == "archive_query" and not classification["keywords"]:
                classification["keywords"] = extract_keywords(question)

            if classification["intent"] in ["archive_query", "recommend_request"]:
                classification["query_analysis"] = ensure_query_analysis(
                    question,
                    classification,
                )

            return classification
    except Exception:
        pass

    return classify_intent_and_keywords_by_rule(question)


def build_intent_classification(
    intent: str,
    keywords: list[str] | None = None,
    query_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """intent 분류 결과 dict를 같은 구조로 만든다."""
    return {
        "intent": intent,
        "keywords": keywords or [],
        "query_analysis": query_analysis or build_empty_query_analysis(),
    }


def classify_intent_and_keywords_by_rule(question: str) -> dict[str, Any]:
    """LLM 분류 실패 시 기존 규칙으로 intent와 키워드를 만든다."""
    normalized_question = question.lower().strip()
    tts_stop_markers = [
        "멈춰",
        "중지",
        "정지",
        "그만",
        "stop",
        "스톱",
    ]
    for marker in tts_stop_markers:
        if marker in normalized_question:
            return build_intent_classification("tts_stop")

    if is_tts_read_request(normalized_question):
        return build_intent_classification("tts_request")

    recommend_markers = [
        "추천",
        "추천해줘",
        "추천해주세요",
        "비슷한",
        "유사한",
    ]
    for marker in recommend_markers:
        if marker in normalized_question:
            recommendation_keywords = extract_recommendation_command_keywords(question)
            if recommendation_keywords:
                return build_intent_classification(
                    "archive_query",
                    recommendation_keywords,
                    build_query_analysis_from_keywords(
                        question,
                        recommendation_keywords,
                    ),
                )

            return build_intent_classification("recommend_request")

    archive_markers = [
        "괴담",
        "조회",
        "검색",
        "찾아",
        "알려",
        "보여",
        "추천",
        "열람",
        "기록",
        "금기",
        "귀신",
        "도시전설",
        "목격담",
        "본문",
    ]
    for marker in archive_markers:
        if marker in normalized_question:
            keywords = extract_keywords(question)
            return build_intent_classification(
                "archive_query",
                keywords,
                build_query_analysis_from_keywords(
                    question,
                    keywords,
                ),
            )

    if is_simple_general_chat(question):
        return build_intent_classification("general_chat")

    keywords = extract_keywords(question)
    return build_intent_classification(
        "archive_query",
        keywords,
        build_query_analysis_from_keywords(question, keywords),
    )


def parse_intent_classification_response(raw_response: str) -> dict[str, Any]:
    """LLM 라우팅 응답에서 intent와 keywords를 읽는다."""
    parsed_response = parse_json_object(raw_response)
    if not parsed_response:
        return {}

    intent = str(parsed_response.get("intent", "")).strip()
    valid_intents = [
        "archive_query",
        "general_chat",
        "recommend_request",
        "tts_request",
        "tts_stop",
    ]
    if intent not in valid_intents:
        return {}

    keywords = clean_classified_keywords(parsed_response.get("keywords", []))
    query_analysis = clean_classified_query_analysis(parsed_response)
    if intent in ["general_chat", "tts_request", "tts_stop"]:
        keywords = []
        query_analysis = build_empty_query_analysis()

    if intent in ["archive_query", "recommend_request"] and not keywords:
        keywords = query_analysis.get("core_keywords", [])

    return {
        "intent": intent,
        "keywords": keywords,
        "query_analysis": query_analysis,
    }


def ensure_query_analysis(question: str, classification: dict[str, Any]) -> dict[str, Any]:
    """분류 결과에 임베딩 검색용 query_analysis 기본값을 보강한다."""
    query_analysis = classification.get("query_analysis", {})
    if not isinstance(query_analysis, dict):
        return build_query_analysis_from_keywords(
            question,
            classification.get("keywords", []),
        )

    search_query = str(query_analysis.get("search_query", "")).strip()
    if search_query:
        return query_analysis

    keywords = classification.get("keywords", [])
    core_keywords = query_analysis.get("core_keywords", [])
    if not core_keywords and keywords:
        query_analysis = {
            **query_analysis,
            "core_keywords": keywords,
        }

    return {
        **query_analysis,
        "search_query": build_search_query_from_terms(
            query_analysis.get("core_keywords", []),
            query_analysis.get("modifier_terms", []),
            query_analysis.get("genre_terms", []),
            question,
            keywords,
        ),
    }


def clean_classified_query_analysis(value: dict[str, Any]) -> dict[str, Any]:
    """LLM이 반환한 세부 검색 분류를 사용 가능한 dict로 정리한다."""
    command_terms = clean_classified_keywords(value.get("command_terms", []))
    genre_terms = clean_classified_keywords(value.get("genre_terms", []))
    modifier_terms = clean_classified_keywords(value.get("modifier_terms", []))
    core_keywords = clean_classified_keywords(value.get("core_keywords", []))
    include_terms = clean_classified_keywords(value.get("include_terms", []))
    exclude_terms = clean_classified_keywords(value.get("exclude_terms", []))
    recommendation_mode = clean_classified_choice(
        value.get("recommendation_mode", ""),
        ["similar", "different", "exclude_only"],
        "similar",
    )
    exclude_reference = clean_classified_choice(
        value.get("exclude_reference", ""),
        [
            "none",
            "last_keywords",
            "last_record",
            "last_results",
            "last_type",
            "last_genre",
        ],
        "none",
    )
    exclude_scope = clean_classified_choice(
        value.get("exclude_scope", ""),
        ["none", "topic", "record", "type", "genre"],
        "none",
    )
    search_query = str(value.get("search_query", "")).strip()
    if search_query:
        return {
            "command_terms": command_terms,
            "genre_terms": genre_terms,
            "modifier_terms": modifier_terms,
            "core_keywords": core_keywords,
            "include_terms": include_terms,
            "exclude_terms": exclude_terms,
            "recommendation_mode": recommendation_mode,
            "exclude_reference": exclude_reference,
            "exclude_scope": exclude_scope,
            "search_query": search_query,
        }

    return {
        "command_terms": command_terms,
        "genre_terms": genre_terms,
        "modifier_terms": modifier_terms,
        "core_keywords": core_keywords,
        "include_terms": include_terms,
        "exclude_terms": exclude_terms,
        "recommendation_mode": recommendation_mode,
        "exclude_reference": exclude_reference,
        "exclude_scope": exclude_scope,
        "search_query": build_search_query_from_terms(
            core_keywords,
            modifier_terms,
            genre_terms,
        ),
    }


def build_empty_query_analysis() -> dict[str, Any]:
    """검색 대상이 없는 입력의 세부 분류 기본값을 만든다."""
    return {
        "command_terms": [],
        "genre_terms": [],
        "modifier_terms": [],
        "core_keywords": [],
        "include_terms": [],
        "exclude_terms": [],
        "recommendation_mode": "similar",
        "exclude_reference": "none",
        "exclude_scope": "none",
        "search_query": "",
    }


def build_query_analysis_from_keywords(
    question: str,
    keywords: list[str],
) -> dict[str, Any]:
    """규칙 기반 폴백 키워드를 임베딩 검색 분류 형태로 감싼다."""
    return {
        "command_terms": [],
        "genre_terms": [],
        "modifier_terms": [],
        "core_keywords": keywords,
        "include_terms": keywords,
        "exclude_terms": [],
        "recommendation_mode": "similar",
        "exclude_reference": "none",
        "exclude_scope": "none",
        "search_query": build_search_query_from_terms(
            keywords,
            [],
            [],
            question,
            keywords,
        ),
    }


def build_search_query_from_terms(
    core_keywords: list[str],
    modifier_terms: list[str],
    genre_terms: list[str],
    fallback_question: str = "",
    fallback_keywords: list[str] | None = None,
) -> str:
    """핵심어를 앞에 두고 임베딩 검색용 짧은 문장을 만든다."""
    terms = [
        *core_keywords,
        *modifier_terms,
        *genre_terms,
    ]
    search_query = " ".join(unique_preserve_order(terms)).strip()
    if search_query:
        return search_query

    keyword_query = " ".join(fallback_keywords or []).strip()
    if keyword_query:
        return keyword_query

    return fallback_question.strip()


def clean_classified_keywords(value: Any, limit: int = 5) -> list[str]:
    """LLM이 반환한 키워드를 검색 가능한 문자열 목록으로 정리한다."""
    if not isinstance(value, list):
        return []

    keywords = []
    for item in value:
        keyword = str(item).strip()
        if not keyword:
            continue

        if keyword in keywords:
            continue

        keywords.append(keyword)
        if len(keywords) >= limit:
            break

    return keywords


def clean_classified_choice(
    value: Any,
    allowed_values: list[str],
    default_value: str,
) -> str:
    """LLM이 반환한 단일 선택값을 허용 목록 안으로 정리한다."""
    cleaned_value = str(value).strip()
    if cleaned_value in allowed_values:
        return cleaned_value

    return default_value


def unique_preserve_order(values: list[str]) -> list[str]:
    """문자열 목록에서 순서를 유지하며 중복을 제거한다."""
    result = []
    seen = set()
    for value in values:
        normalized_value = str(value).lower().strip()
        if not normalized_value:
            continue

        if normalized_value in seen:
            continue

        result.append(str(value).strip())
        seen.add(normalized_value)

    return result


def parse_json_object(raw_response: str) -> dict[str, Any]:
    """문자열 응답에서 JSON 객체 하나를 파싱한다."""
    try:
        parsed_response = json.loads(raw_response)
        if isinstance(parsed_response, dict):
            return parsed_response
    except json.JSONDecodeError:
        start = raw_response.find("{")
        end = raw_response.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed_response = json.loads(raw_response[start:end + 1])
                if isinstance(parsed_response, dict):
                    return parsed_response
            except json.JSONDecodeError:
                pass

    return {}


def is_simple_general_chat(question: str) -> bool:
    """Check whether a short message should be routed to general chat."""
    return normalize_general_chat_message(question) in SIMPLE_GENERAL_CHAT_MESSAGES


def is_tts_read_request(question: str) -> bool:
    """마지막 생성 기록 낭독은 '읽어줘' 단독 명령일 때만 허용한다."""
    return normalize_general_chat_message(question) == "읽어줘"


def normalize_general_chat_message(value: str) -> str:
    """Normalize short chat messages for intent routing."""
    return "".join(char for char in value.lower().strip() if char.isalnum())


def extract_recommendation_command_keywords(question: str) -> list[str]:
    """추천 명령 자체를 제외하고 새 검색 소재가 있는지 확인한다."""
    ignored_terms = [
        "추천",
        "추천해줘",
        "추천해주세요",
        "비슷한",
        "유사한",
        "방금",
        "아까",
        "그거",
        "다른",
        "하나",
    ]
    ignored_values = {
        normalize_general_chat_message(term)
        for term in ignored_terms
    }
    keywords = []
    for keyword in extract_keywords(question):
        normalized_keyword = normalize_general_chat_message(keyword)
        if not normalized_keyword:
            continue

        if normalized_keyword in ignored_values:
            continue

        if "추천" in normalized_keyword:
            continue

        keywords.append(keyword)

    return keywords


def get_include_keywords_from_query_analysis(query_analysis: dict[str, Any]) -> list[str]:
    """LLM이 분류한 포함 조건을 추천 검색 키워드로 모은다."""
    return unique_preserve_order([
        *query_analysis.get("include_terms", []),
        *query_analysis.get("core_keywords", []),
    ])


def has_query_exclusions(query_analysis: dict[str, Any]) -> bool:
    """추천/검색에서 제외 조건이 있는지 확인한다."""
    if query_analysis.get("exclude_terms"):
        return True

    if query_analysis.get("exclude_reference", "none") != "none":
        return True

    if query_analysis.get("exclude_scope", "none") != "none":
        return True

    return False


def build_query_exclusions(
    query_analysis: dict[str, Any],
    archive_context: dict[str, Any],
) -> dict[str, Any]:
    """query_analysis의 제외 참조를 최근 archive context 기준으로 해석한다."""
    terms = list(query_analysis.get("exclude_terms", []))
    record_keys = []
    record_types = []
    exclude_reference = query_analysis.get("exclude_reference", "none")
    exclude_scope = query_analysis.get("exclude_scope", "none")

    if exclude_reference == "last_keywords":
        terms.extend(get_context_keywords(archive_context))

    elif exclude_reference == "last_record":
        record_key = get_record_key(archive_context.get("last_selected_record", {}))
        if record_key:
            record_keys.append(record_key)

    elif exclude_reference == "last_results":
        record_keys.extend(get_context_result_keys(archive_context))

    elif exclude_reference == "last_type":
        record_types.extend(get_context_result_types(archive_context))

    elif exclude_reference == "last_genre":
        terms.extend(get_context_genre_terms(archive_context))

    if exclude_scope == "record":
        record_key = get_record_key(archive_context.get("last_selected_record", {}))
        if record_key:
            record_keys.append(record_key)

    elif exclude_scope == "type":
        record_types.extend(get_context_result_types(archive_context))

    elif exclude_scope == "genre":
        terms.extend(get_context_genre_terms(archive_context))

    return {
        "terms": unique_preserve_order(terms),
        "record_keys": set(record_keys),
        "record_types": set(record_types),
    }


def get_context_keywords(archive_context: dict[str, Any]) -> list[str]:
    """최근 검색 키워드와 query_analysis 핵심어를 모은다."""
    query_analysis = archive_context.get("last_query_analysis", {})
    if not isinstance(query_analysis, dict):
        query_analysis = {}

    return unique_preserve_order([
        *archive_context.get("last_keywords", []),
        *query_analysis.get("core_keywords", []),
        *query_analysis.get("include_terms", []),
        *query_analysis.get("modifier_terms", []),
    ])


def get_context_genre_terms(archive_context: dict[str, Any]) -> list[str]:
    """최근 query_analysis의 장르성 단어를 모은다."""
    query_analysis = archive_context.get("last_query_analysis", {})
    if not isinstance(query_analysis, dict):
        return []

    return unique_preserve_order(query_analysis.get("genre_terms", []))


def get_context_result_keys(archive_context: dict[str, Any]) -> list[tuple[str, Any]]:
    """최근 결과 목록의 record key를 만든다."""
    record_keys = []
    for record in archive_context.get("last_results", []):
        record_key = get_record_key(record)
        if record_key:
            record_keys.append(record_key)

    return record_keys


def get_context_result_types(archive_context: dict[str, Any]) -> list[str]:
    """최근 결과 목록과 선택 기록의 archive type을 모은다."""
    record_types = list(archive_context.get("last_result_types", []))
    selected_record = archive_context.get("last_selected_record", {})
    selected_type = str(selected_record.get("type", "")).strip()
    if selected_type:
        record_types.append(selected_type)

    return unique_preserve_order(record_types)


def get_record_key(record: dict[str, Any]) -> tuple[Any, ...]:
    """검색 결과 dict를 비교 가능한 key로 바꾼다."""
    record_type = str(record.get("type", "")).strip()
    record_id = record.get("id")
    if record_type and record_id is not None:
        return (record_type, record_id)

    return ()


def apply_query_exclusions(
    records: list[dict[str, Any]],
    query_analysis: dict[str, Any],
    archive_context: dict[str, Any],
) -> list[dict[str, Any]]:
    """검색 결과에서 query_analysis의 제외 조건에 해당하는 기록을 제거한다."""
    if not has_query_exclusions(query_analysis):
        return records

    exclusions = build_query_exclusions(query_analysis, archive_context)
    filtered_records = []
    for record in records:
        if is_excluded_record(record, exclusions):
            continue

        filtered_records.append(record)

    return filtered_records


def is_excluded_record(record: dict[str, Any], exclusions: dict[str, Any]) -> bool:
    """단일 기록이 제외 조건에 걸리는지 판단한다."""
    record_key = get_record_key(record)
    if record_key and record_key in exclusions["record_keys"]:
        return True

    record_type = str(record.get("type", "")).strip()
    if record_type and record_type in exclusions["record_types"]:
        return True

    record_text = " ".join([
        str(record.get("name", "")),
        str(record.get("body", "")),
        " ".join(str(region) for region in record.get("regions", [])),
    ]).lower()
    for term in exclusions["terms"]:
        normalized_term = str(term).lower().strip()
        if normalized_term and normalized_term in record_text:
            return True

    return False


def recommend_node(state: ArchiveState) -> dict[str, Any]:
    """최근 맥락이나 분류 키워드 기준으로 비슷한 archive 기록을 추천한다."""
    question = state.get("question", "")
    archive_context = state.get("archive_context", {})
    query_analysis = state.get("query_analysis") or build_empty_query_analysis()
    include_keywords = get_include_keywords_from_query_analysis(query_analysis)
    keywords = state.get("keywords") or include_keywords
    if not keywords and not has_query_exclusions(query_analysis):
        keywords = extract_recent_context_keywords(
            state.get("conversation_history", []),
        )

    if not keywords:
        if has_query_exclusions(query_analysis):
            search_results = get_random_archive_records(limit=12)
            search_results = apply_query_exclusions(
                search_results,
                query_analysis,
                archive_context,
            )[:5]

            if search_results:
                return build_search_choice_response(
                    question=question,
                    search_results=search_results,
                    conversation_history=state.get("conversation_history", []),
                    keywords=[],
                    query_analysis=query_analysis,
                )

        message = "비슷한 괴담 기록을 찾지 못했습니다. 먼저 기록 하나를 열어 주십시오."
        return build_message_response(
            message=message,
            query_analysis=query_analysis,
            feedback="추천 기준이 없어 추천을 생략했습니다.",
        )

    if keywords and (
        not query_analysis.get("search_query")
        or query_analysis.get("search_query") == question
    ):
        query_analysis = {
            **query_analysis,
            "core_keywords": query_analysis.get("core_keywords") or keywords,
            "include_terms": query_analysis.get("include_terms") or keywords,
            "search_query": build_search_query_from_terms(
                query_analysis.get("core_keywords", []) or keywords,
                query_analysis.get("modifier_terms", []),
                query_analysis.get("genre_terms", []),
                question,
                keywords,
            ),
        }

    semantic_query = get_semantic_search_query(question, query_analysis, keywords)
    search_results = search_archive_records_for_question(
        question,
        keywords,
        semantic_query=semantic_query,
        limit=12,
    )
    search_results = apply_query_exclusions(
        search_results,
        query_analysis,
        archive_context,
    )[:5]
    if not search_results:
        message = "말씀하신 조건을 제외하고 추천할 만한 기록을 찾지 못했습니다."
        return build_message_response(
            message=message,
            keywords=keywords,
            query_analysis=query_analysis,
            feedback="추천 기준이 없어 추천을 생략했습니다.",
        )

    return build_search_choice_response(
        question=question,
        search_results=search_results,
        conversation_history=state.get("conversation_history", []),
        keywords=keywords,
        query_analysis=query_analysis,
    )


def extract_recent_context_keywords(
    conversation_history: list[dict[str, str]],
    limit: int = 5,
) -> list[str]:
    """최근 assistant 답변에서 추천 기준이 될 키워드를 찾는다."""
    for item in reversed(conversation_history):
        if item.get("role") != "assistant":
            continue

        content = item.get("content", "").strip()
        if not content:
            continue

        keywords = extract_keywords(content, limit=limit)
        if keywords:
            return keywords

    return []


def search_node(state: ArchiveState) -> dict[str, Any]:
    """질문에서 키워드를 뽑고 DB에서 가장 관련 있는 원본 기록을 찾는다."""
    question = state.get("question", "")
    keywords = state.get("keywords") or extract_keywords(question)
    query_analysis = state.get("query_analysis") or build_query_analysis_from_keywords(
        question,
        keywords,
    )
    query_analysis = ensure_query_analysis(
        question,
        {
            "keywords": keywords,
            "query_analysis": query_analysis,
        },
    )
    archive_context = state.get("archive_context", {})
    semantic_query = get_semantic_search_query(question, query_analysis, keywords)
    search_results = search_archive_records_for_question(
        question,
        keywords,
        semantic_query=semantic_query,
        limit=12,
    )
    search_results = apply_query_exclusions(
        search_results,
        query_analysis,
        archive_context,
    )[:5]

    if not search_results:
        message = "관련 괴담 기록을 찾지 못했습니다. 다른 키워드로 다시 물어봐 주세요."
        return build_message_response(
            message=message,
            keywords=keywords,
            query_analysis=query_analysis,
            feedback="검색 결과가 없어 생성과 평가를 생략했습니다.",
        )

    return build_search_choice_response(
        question=question,
        search_results=search_results,
        conversation_history=state.get("conversation_history", []),
        keywords=keywords,
        query_analysis=query_analysis,
    )


def get_semantic_search_query(
    question: str,
    query_analysis: dict[str, Any],
    keywords: list[str],
) -> str:
    """query_analysis에서 pgvector 검색용 문장을 고른다."""
    search_query = str(query_analysis.get("search_query", "")).strip()
    if search_query:
        return search_query

    keyword_query = " ".join(keywords).strip()
    if keyword_query:
        return keyword_query

    return question.strip()


def generate_node(state: ArchiveState) -> dict[str, Any]:
    """검색된 원본 기록과 키워드를 바탕으로 괴담 초안을 생성한다."""
    source_story = state.get("source_story", {})
    if not source_story:
        message = "관련 괴담 기록을 찾지 못했습니다. 다른 키워드로 다시 질문해 주세요."
        return {
            "generated_story": message,
            "llm_response": message,
            "skip_evaluation": True,
            "is_passed": True,
        }

    prompt = build_generation_prompt(
        question=state.get("question", ""),
        keywords=state.get("keywords", []),
        source_story=source_story,
        conversation_history=state.get("conversation_history", []),
    )
    generated_story = extract_story_from_model_response(invoke_gemma_llm(prompt))
    if not generated_story.strip():
        logging.getLogger(__name__).warning(
            "Archive generation LLM returned empty response; retrying with compact prompt",
            extra=build_story_log_extra(source_story),
        )
        retry_prompt = build_generation_retry_prompt(
            question=state.get("question", ""),
            keywords=state.get("keywords", []),
            source_story=source_story,
        )
        generated_story = extract_story_from_model_response(
            invoke_gemma_llm(retry_prompt),
        )

    if not generated_story.strip():
        logging.getLogger(__name__).warning(
            "Archive generation LLM returned empty response after retry",
            extra=build_story_log_extra(source_story),
        )
        message = get_empty_generation_message()
        return {
            "status": "error",
            "generated_story": "",
            "llm_response": message,
            "evaluation": {"feedback": "생성 LLM이 빈 응답을 반환했습니다."},
            "skip_evaluation": True,
            "is_passed": False,
        }

    return {
        "generated_story": generated_story,
        "llm_response": generated_story,
        "skip_evaluation": False,
    }


def evaluation_node(state: ArchiveState) -> dict[str, Any]:
    """생성된 괴담이 키워드, 원본 일관성, 문체, 게시글스러움 기준을 통과하는지 평가한다."""
    generated_story = state.get("generated_story", "")
    if state.get("skip_evaluation"):
        return {
            "evaluation": {"feedback": "검색 결과가 없어 평가를 건너뜁니다."},
            "is_passed": True,
            "llm_response": generated_story,
        }

    precheck_feedback = get_story_precheck_feedback(generated_story)
    if precheck_feedback:
        logging.getLogger(__name__).warning(
            "Archive generated story failed precheck",
            extra=build_story_log_extra(
                state.get("source_story", {}),
                precheck_feedback,
            ),
        )
        return {
            "evaluation": build_failed_evaluation(precheck_feedback),
            "is_passed": False,
            "llm_response": generated_story,
        }

    prompt = build_evaluation_prompt(
        keywords=state.get("keywords", []),
        source_story=state.get("source_story", {}),
        generated_story=generated_story,
    )
    try:
        evaluation = parse_evaluation_response(invoke_llm(prompt))
        evaluation = apply_automatic_penalties(evaluation, generated_story)
    except Exception:
        logging.getLogger(__name__).exception("Archive evaluation LLM failed")
        return {
            "evaluation": {
                "keyword_passed": True,
                "consistency_passed": True,
                "style_passed": True,
                "atmosphere_passed": True,
                "feedback": "평가 LLM 오류로 평가를 생략했습니다.",
            },
            "is_passed": True,
            "llm_response": generated_story,
        }

    is_passed = is_evaluation_passed(evaluation)

    return {
        "evaluation": evaluation,
        "is_passed": is_passed,
        "llm_response": generated_story,
    }


def revise_node(state: ArchiveState) -> dict[str, Any]:
    """평가 피드백과 실패한 초안을 바탕으로 괴담을 한 번 수정한다."""
    prompt = build_revision_prompt(
        question=state.get("question", ""),
        keywords=state.get("keywords", []),
        source_story=state.get("source_story", {}),
        generated_story=state.get("generated_story", ""),
        evaluation=state.get("evaluation", {}),
    )
    revised_story = extract_story_from_model_response(invoke_gemma_llm(prompt))
    if not revised_story.strip():
        generated_story = state.get("generated_story", "").strip()
        logging.getLogger(__name__).warning(
            "Archive revision LLM returned empty response",
            extra=build_story_log_extra(state.get("source_story", {})),
        )
        if not generated_story:
            message = get_empty_generation_message()
            return {
                "status": "error",
                "generated_story": "",
                "llm_response": message,
                "revise_count": state.get("revise_count", 0) + 1,
                "is_passed": False,
            }

        return {
            "generated_story": generated_story,
            "llm_response": generated_story,
            "revise_count": state.get("revise_count", 0) + 1,
            "is_passed": True,
        }

    precheck_feedback = get_story_precheck_feedback(revised_story)
    if precheck_feedback:
        logging.getLogger(__name__).warning(
            "Archive revised story failed precheck",
            extra=build_story_log_extra(
                state.get("source_story", {}),
                precheck_feedback,
            ),
        )
        message = get_empty_generation_message()
        return {
            "status": "error",
            "generated_story": "",
            "llm_response": message,
            "evaluation": {"feedback": precheck_feedback},
            "revise_count": state.get("revise_count", 0) + 1,
            "skip_evaluation": True,
            "is_passed": False,
        }

    return {
        "generated_story": revised_story,
        "llm_response": revised_story,
        "revise_count": state.get("revise_count", 0) + 1,
    }


def decide_next_node(state: ArchiveState) -> Literal["revise", "finish"]:
    """평가 결과와 수정 횟수에 따라 수정 노드로 갈지 종료할지 결정한다."""
    if state.get("is_passed"):
        return "finish"

    elif state.get("revise_count", 0) >= 1:
        return "finish"

    return "revise"


def convert_story_to_narration(story_text: str) -> str:
    """생성 괴담 본문을 ElevenLabs v3 낭독 대본으로 변환한다. 실패하면 원문을 반환한다."""
    cleaned_source = story_text.strip()
    if not cleaned_source:
        return story_text

    try:
        response = invoke_gemma_llm(build_tts_narration_prompt(cleaned_source))
    except Exception:
        logging.getLogger(__name__).exception("TTS 낭독 대본 변환 실패, 원문으로 낭독한다")
        return story_text

    narration = strip_markdown_fence(response).strip()
    if len(narration) < max(80, len(cleaned_source) // 3):
        logging.getLogger(__name__).warning(
            "TTS 낭독 대본이 너무 짧아 원문으로 낭독한다",
            extra={"narration_length": len(narration), "source_length": len(cleaned_source)},
        )
        return story_text

    return narration


def strip_markdown_fence(text: str) -> str:
    """응답 앞뒤의 마크다운 코드블록 기호를 제거한다."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1]
    if stripped.endswith("```"):
        stripped = stripped[: stripped.rfind("```")]

    return stripped.strip()


def invoke_llm(prompt: str) -> str:
    """archive 기본 Groq 모델에서 프롬프트 응답 문자열을 반환한다."""
    response = get_llm().invoke(prompt)
    log_llm_finish_reason("Archive default LLM", response)
    if hasattr(response, "content"):
        return str(response.content).strip()

    return str(response).strip()


def invoke_gemma_llm(prompt: str) -> str:
    """archive 일반 대화, 괴담 생성, 수정용 Gemma 모델 응답 문자열을 반환한다."""
    response = get_post_generation_llm().invoke(prompt)
    log_llm_finish_reason("Archive post-generation LLM", response)
    if hasattr(response, "content"):
        return str(response.content).strip()

    return str(response).strip()


def log_llm_finish_reason(context: str, response: Any) -> None:
    """LLM 응답 메타데이터의 종료 사유를 로그로 남긴다."""
    metadata = getattr(response, "response_metadata", {}) or {}
    finish_reason = metadata.get("finish_reason") or metadata.get("finishReason")
    if not finish_reason:
        return

    token_usage = metadata.get("token_usage") or metadata.get("usage")
    log_extra = {
        "finish_reason": finish_reason,
        "token_usage": token_usage,
    }
    logger = logging.getLogger(__name__)
    if finish_reason in ["stop", "eos", "complete"]:
        logger.info("%s finish reason", context, extra=log_extra)
        return

    logger.warning("%s finished unexpectedly", context, extra=log_extra)


def parse_evaluation_response(raw_response: str) -> dict[str, Any]:
    """LLM 평가 응답에서 JSON 객체를 파싱하고 실패 시 불합격 결과를 만든다."""
    parsed_response = parse_json_object(raw_response)
    if parsed_response:
        return parsed_response

    return {
        "keyword_passed": False,
        "consistency_passed": False,
        "style_passed": False,
        "atmosphere_passed": False,
        "feedback": "평가 결과를 JSON으로 해석하지 못했습니다.",
    }


def is_evaluation_passed(evaluation: dict[str, Any]) -> bool:
    """평가 JSON의 필수 통과 항목이 모두 참인지 확인한다."""
    required_keys = [
        "keyword_passed",
        "consistency_passed",
        "style_passed",
        "atmosphere_passed",
    ]
    for key in required_keys:
        if not evaluation.get(key):
            return False

    if evaluation.get("rewrite_required_by_editor"):
        return False

    if not has_required_criterion_scores(evaluation):
        return False

    return float(evaluation.get("score_total", 0.0)) >= 90.0
