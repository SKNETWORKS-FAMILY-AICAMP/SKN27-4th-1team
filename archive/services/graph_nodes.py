import json
import logging
from typing import Any, Literal, TypedDict

from archive.services.archive_search import (
    get_random_archive_suggestions,
    search_archive_records_for_question,
)
from archive.services.keyword_extractor import extract_keywords
from archive.services.prompt import (
    build_evaluation_prompt,
    build_generation_prompt,
    build_general_chat_prompt,
    build_intent_classification_prompt,
    build_revision_prompt,
    build_search_choice_prompt,
)
from archive.services.search_policy import SIMPLE_GENERAL_CHAT_MESSAGES
from common.llm_factory import get_llm, get_post_generation_llm


class ArchiveState(TypedDict, total=False):
    status: str
    question: str
    intent: str
    keywords: list[str]
    query_analysis: dict[str, Any]
    conversation_history: list[dict[str, str]]
    search_results: list[dict[str, Any]]
    source_story: dict[str, Any]
    generated_story: str
    evaluation: dict[str, Any]
    is_passed: bool
    revise_count: int
    llm_response: str
    skip_evaluation: bool


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
    prompt = build_general_chat_prompt(
        question=state.get("question", ""),
        conversation_history=state.get("conversation_history", []),
        suggestion_topics=get_random_archive_suggestions(),
    )
    response = invoke_llm(prompt)
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


def decide_after_generate_node(state: ArchiveState) -> Literal["evaluate", "finish"]:
    """검토할 원본과 생성문이 있을 때만 평가 노드를 실행한다."""
    if state.get("skip_evaluation"):
        return "finish"

    elif not state.get("source_story"):
        return "finish"

    elif not state.get("generated_story", "").strip():
        return "finish"

    return "evaluate"


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
            return {
                "intent": "tts_stop",
                "keywords": [],
                "query_analysis": build_empty_query_analysis(),
            }

    tts_markers = [
        "읽어줘",
        "읽어",
        "낭독",
        "tts",
        "들려줘",
        "재생",
    ]
    for marker in tts_markers:
        if marker in normalized_question:
            return {
                "intent": "tts_request",
                "keywords": [],
                "query_analysis": build_empty_query_analysis(),
            }

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
                return {
                    "intent": "archive_query",
                    "keywords": recommendation_keywords,
                    "query_analysis": build_query_analysis_from_keywords(
                        question,
                        recommendation_keywords,
                    ),
                }

            return {
                "intent": "recommend_request",
                "keywords": [],
                "query_analysis": build_empty_query_analysis(),
            }

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
            return {
                "intent": "archive_query",
                "keywords": keywords,
                "query_analysis": build_query_analysis_from_keywords(
                    question,
                    keywords,
                ),
            }

    if is_simple_general_chat(question):
        return {
            "intent": "general_chat",
            "keywords": [],
            "query_analysis": build_empty_query_analysis(),
        }

    keywords = extract_keywords(question)
    return {
        "intent": "archive_query",
        "keywords": keywords,
        "query_analysis": build_query_analysis_from_keywords(question, keywords),
    }


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
    search_query = str(value.get("search_query", "")).strip()
    if search_query:
        return {
            "command_terms": command_terms,
            "genre_terms": genre_terms,
            "modifier_terms": modifier_terms,
            "core_keywords": core_keywords,
            "search_query": search_query,
        }

    return {
        "command_terms": command_terms,
        "genre_terms": genre_terms,
        "modifier_terms": modifier_terms,
        "core_keywords": core_keywords,
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


def recommend_node(state: ArchiveState) -> dict[str, Any]:
    """최근 맥락이나 분류 키워드 기준으로 비슷한 archive 기록을 추천한다."""
    question = state.get("question", "")
    keywords = state.get("keywords") or extract_recent_context_keywords(
        state.get("conversation_history", []),
    )
    if not keywords:
        message = "비슷한 괴담 기록을 찾지 못했습니다. 먼저 기록 하나를 열어 주십시오."
        return {
            "keywords": [],
            "query_analysis": build_empty_query_analysis(),
            "search_results": [],
            "source_story": {},
            "generated_story": message,
            "llm_response": message,
            "skip_evaluation": True,
            "evaluation": {"feedback": "추천 기준이 없어 추천을 생략했습니다."},
            "is_passed": True,
        }

    query_analysis = state.get("query_analysis") or build_query_analysis_from_keywords(
        question,
        keywords,
    )
    if keywords and (
        not query_analysis.get("search_query")
        or query_analysis.get("search_query") == question
    ):
        query_analysis = build_query_analysis_from_keywords(question, keywords)

    semantic_query = get_semantic_search_query(question, query_analysis, keywords)
    search_results = search_archive_records_for_question(
        question,
        keywords,
        semantic_query=semantic_query,
    )
    if not search_results:
        message = "비슷한 괴담 기록을 찾지 못했습니다. 먼저 기록 하나를 열어 주십시오."
        return {
            "keywords": keywords,
            "query_analysis": query_analysis,
            "search_results": [],
            "source_story": {},
            "generated_story": message,
            "llm_response": message,
            "skip_evaluation": True,
            "evaluation": {"feedback": "추천 기준이 없어 추천을 생략했습니다."},
            "is_passed": True,
        }

    choice_prompt = build_search_choice_prompt(
        question=question,
        search_results=search_results,
        conversation_history=state.get("conversation_history", []),
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
    semantic_query = get_semantic_search_query(question, query_analysis, keywords)
    search_results = search_archive_records_for_question(
        question,
        keywords,
        semantic_query=semantic_query,
    )

    source_story = {}
    if search_results:
        source_story = search_results[0]
    elif not search_results:
        message = "관련 괴담 기록을 찾지 못했습니다. 다른 키워드로 다시 물어봐 주세요."
        return {
            "keywords": keywords,
            "query_analysis": query_analysis,
            "search_results": [],
            "source_story": {},
            "generated_story": message,
            "llm_response": message,
            "skip_evaluation": True,
            "evaluation": {"feedback": "검색 결과가 없어 생성과 평가를 생략했습니다."},
            "is_passed": True,
        }

    choice_prompt = build_search_choice_prompt(
        question=question,
        search_results=search_results,
        conversation_history=state.get("conversation_history", []),
    )
    return {
        "keywords": keywords,
        "query_analysis": query_analysis,
        "search_results": search_results,
        "source_story": source_story,
        "llm_response": invoke_llm(choice_prompt),
        "skip_evaluation": True,
        "evaluation": {},
        "is_passed": True,
    }


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
    generated_story = invoke_llm(prompt)
    return {
        "generated_story": generated_story,
        "llm_response": generated_story,
        "skip_evaluation": False,
    }


def evaluation_node(state: ArchiveState) -> dict[str, Any]:
    """생성된 괴담이 키워드, 원본 일관성, 문체, 분위기 기준을 통과하는지 평가한다."""
    generated_story = state.get("generated_story", "")
    if state.get("skip_evaluation"):
        return {
            "evaluation": {"feedback": "검색 결과가 없어 평가를 건너뜁니다."},
            "is_passed": True,
            "llm_response": generated_story,
        }

    prompt = build_evaluation_prompt(
        keywords=state.get("keywords", []),
        source_story=state.get("source_story", {}),
        generated_story=generated_story,
    )
    try:
        evaluation = parse_evaluation_response(invoke_evaluation_llm(prompt))
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
    revised_story = invoke_llm(prompt)
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


def invoke_llm(prompt: str) -> str:
    """archive 기본 생성 모델에서 프롬프트 응답 문자열을 반환한다."""
    response = get_post_generation_llm().invoke(prompt)
    if hasattr(response, "content"):
        return str(response.content).strip()

    return str(response).strip()


def invoke_evaluation_llm(prompt: str) -> str:
    """archive 평가 모델에서 프롬프트 응답 문자열을 반환한다."""
    response = get_llm().invoke(prompt)
    if hasattr(response, "content"):
        return str(response.content).strip()

    return str(response).strip()


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

    return True
