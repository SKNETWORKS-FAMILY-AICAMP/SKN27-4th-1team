import json
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
from common.llm_factory import get_llm


class ArchiveState(TypedDict, total=False):
    status: str
    question: str
    intent: str
    keywords: list[str]
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
        return {
            "intent": state.get("intent", "archive_query"),
            "keywords": state.get("keywords", []),
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
) -> Literal["archive_query", "generate", "general_chat", "tts_request"]:
    """분류된 intent 값에 따라 archive 검색 흐름과 일반 대화 흐름을 나눈다."""
    if state.get("source_story"):
        return "generate"

    elif state.get("intent") == "archive_query":
        return "archive_query"

    elif state.get("intent") == "tts_request":
        return "tts_request"

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

            return classification
    except Exception:
        pass

    return classify_intent_and_keywords_by_rule(question)


def classify_intent_and_keywords_by_rule(question: str) -> dict[str, Any]:
    """LLM 분류 실패 시 기존 규칙으로 intent와 키워드를 만든다."""
    normalized_question = question.lower().strip()
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
            return {
                "intent": "archive_query",
                "keywords": extract_keywords(question),
            }

    if is_simple_general_chat(question):
        return {
            "intent": "general_chat",
            "keywords": [],
        }

    return {
        "intent": "archive_query",
        "keywords": extract_keywords(question),
    }


def parse_intent_classification_response(raw_response: str) -> dict[str, Any]:
    """LLM 라우팅 응답에서 intent와 keywords를 읽는다."""
    parsed_response = parse_json_object(raw_response)
    if not parsed_response:
        return {}

    intent = str(parsed_response.get("intent", "")).strip()
    if intent not in ["archive_query", "general_chat", "tts_request"]:
        return {}

    keywords = clean_classified_keywords(parsed_response.get("keywords", []))
    if intent != "archive_query":
        keywords = []

    return {
        "intent": intent,
        "keywords": keywords,
    }


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


def search_node(state: ArchiveState) -> dict[str, Any]:
    """질문에서 키워드를 뽑고 DB에서 가장 관련 있는 원본 기록을 찾는다."""
    question = state.get("question", "")
    keywords = state.get("keywords") or extract_keywords(question)
    search_results = search_archive_records_for_question(question, keywords)

    source_story = {}
    if search_results:
        source_story = search_results[0]
    elif not search_results:
        message = "관련 괴담 기록을 찾지 못했습니다. 다른 키워드로 다시 물어봐 주세요."
        return {
            "keywords": keywords,
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
        "search_results": search_results,
        "source_story": source_story,
        "llm_response": invoke_llm(choice_prompt),
        "skip_evaluation": True,
        "evaluation": {},
        "is_passed": True,
    }


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
    evaluation = parse_evaluation_response(invoke_llm(prompt))
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
    """공통 LLM 팩토리에서 모델을 받아 프롬프트 응답 문자열을 반환한다."""
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
