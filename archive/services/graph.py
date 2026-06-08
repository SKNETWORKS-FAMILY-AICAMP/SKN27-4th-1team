import json
from typing import Any, Literal, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from archive.models import HorrorStory, MythEntity, Superstition
from archive.services.keyword_extractor import extract_fallback_keywords, extract_keywords
from archive.services.prompt import (
    build_evaluation_prompt,
    build_generation_prompt,
    build_general_chat_prompt,
    build_revision_prompt,
    build_search_choice_prompt,
)
from archive.services.search_policy import (
    SIMPLE_GENERAL_CHAT_MESSAGES,
    SINGLE_KEYWORD_WEAK_MATCH_COUNTS,
)
from archive.services.search_relevance import (
    is_generic_record_name,
    is_relevant_record,
    score_record_text,
)
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


def run_archive_chatbot(
    question: str,
    conversation_history: Optional[list[dict[str, str]]] = None,
) -> dict[str, Any]:
    """사용자 질문을 받아 DB 검색 결과를 우선 보여주고, 없으면 일반 대화로 응답한다."""
    cleaned_question = question.strip()
    if not cleaned_question:
        return {
            "status": "empty",
            "query": "",
            "keywords": [],
            "results": [],
            "llm_response": "",
            "evaluation": {},
            "is_passed": False,
            "revised": False,
        }

    intent = classify_intent(cleaned_question)
    if intent == "tts_request":
        archive_graph = build_archive_graph()
        final_state = archive_graph.invoke({
            "question": cleaned_question,
            "conversation_history": conversation_history or [],
            "revise_count": 0,
        })
        return {
            "status": final_state.get("status", "tts_ready"),
            "query": cleaned_question,
            "intent": final_state.get("intent", "tts_request"),
            "keywords": [],
            "results": [],
            "source_story": {},
            "llm_response": final_state.get("llm_response", ""),
            "evaluation": final_state.get("evaluation", {}),
            "is_passed": final_state.get("is_passed", True),
            "revised": False,
        }

    if intent == "general_chat" and is_simple_general_chat(cleaned_question):
        return run_archive_graph_response(cleaned_question, conversation_history)

    keywords = extract_keywords(cleaned_question)
    search_results = search_archive_records_for_question(cleaned_question, keywords)
    if search_results:
        choice_prompt = build_search_choice_prompt(
            question=cleaned_question,
            search_results=search_results,
            conversation_history=conversation_history or [],
        )
        llm_response = invoke_llm(choice_prompt)
        return {
            "status": "success",
            "query": cleaned_question,
            "intent": "archive_query",
            "keywords": keywords,
            "results": search_results,
            "source_story": search_results[0],
            "llm_response": llm_response,
            "evaluation": {},
            "is_passed": True,
            "revised": False,
        }

    if intent == "archive_query":
        message = "관련 괴담 기록을 찾지 못했습니다. 다른 키워드로 다시 물어봐 주세요."
        return {
            "status": "success",
            "query": cleaned_question,
            "intent": "archive_query",
            "keywords": keywords,
            "results": [],
            "source_story": {},
            "llm_response": message,
            "evaluation": {"feedback": "검색 결과가 없어 생성과 평가를 생략했습니다."},
            "is_passed": True,
            "revised": False,
        }

    return run_archive_graph_response(cleaned_question, conversation_history)


def run_archive_graph_response(
    cleaned_question: str,
    conversation_history: Optional[list[dict[str, str]]] = None,
) -> dict[str, Any]:
    """검색 우선 처리 없이 LangGraph 분류 결과에 따른 응답을 만든다."""
    archive_graph = build_archive_graph()
    final_state = archive_graph.invoke({
        "question": cleaned_question,
        "conversation_history": conversation_history or [],
        "revise_count": 0,
    })
    return {
        "status": final_state.get("status", "success"),
        "query": cleaned_question,
        "intent": final_state.get("intent", ""),
        "keywords": final_state.get("keywords", []),
        "results": final_state.get("search_results", []),
        "source_story": final_state.get("source_story", {}),
        "llm_response": final_state.get("llm_response", ""),
        "evaluation": final_state.get("evaluation", {}),
        "is_passed": final_state.get("is_passed", False),
        "revised": final_state.get("revise_count", 0) > 0,
    }


def is_simple_general_chat(question: str) -> bool:
    """짧은 인사/감사처럼 검색보다 대화로 보는 입력인지 확인한다."""
    return normalize_simple_chat_message(question) in SIMPLE_GENERAL_CHAT_MESSAGES


def normalize_simple_chat_message(value: str) -> str:
    """문장부호와 공백을 제외해 짧은 일반대화 매칭을 안정화한다."""
    return "".join(char for char in value.lower().strip() if char.isalnum())


def run_archive_record_chatbot(
    question: str,
    record_type: str,
    record_id: int,
    conversation_history: Optional[list[dict[str, str]]] = None,
) -> dict[str, Any]:
    """사용자가 선택한 특정 원본 기록을 기준으로 괴담 재구성 파이프라인을 실행한다."""
    source_story = get_archive_record(record_type, record_id)
    keyword_source = f"{question} {source_story.get('name', '')}"
    state: ArchiveState = {
        "question": question.strip() or str(source_story.get("name", "")),
        "intent": "archive_query",
        "keywords": extract_keywords(keyword_source),
        "conversation_history": conversation_history or [],
        "search_results": [source_story],
        "source_story": source_story,
        "revise_count": 0,
    }
    final_state = run_generation_pipeline(state)

    return {
        "status": "success",
        "query": question,
        "intent": "archive_query",
        "keywords": final_state.get("keywords", []),
        "results": final_state.get("search_results", []),
        "source_story": final_state.get("source_story", {}),
        "llm_response": final_state.get("llm_response", ""),
        "evaluation": final_state.get("evaluation", {}),
        "is_passed": final_state.get("is_passed", False),
        "revised": final_state.get("revise_count", 0) > 0,
    }


def run_generation_pipeline(state: ArchiveState) -> ArchiveState:
    """선택된 원본 기록이 있는 상태에서 생성, 평가, 1회 수정을 순서대로 실행한다."""
    state.update(generate_node(state))
    if decide_after_generate_node(state) == "finish":
        return state

    state.update(evaluation_node(state))
    if state.get("is_passed"):
        return state

    if state.get("revise_count", 0) >= 1:
        return state

    state.update(revise_node(state))
    if decide_after_generate_node(state) == "finish":
        return state

    state.update(evaluation_node(state))
    return state


def build_archive_graph():
    """archive 챗봇용 LangGraph 노드 흐름을 구성한다."""
    builder = StateGraph(ArchiveState)
    builder.add_node("intent", intent_node)
    builder.add_node("general_chat", general_chat_node)
    builder.add_node("tts", tts_node)
    builder.add_node("search", search_node)
    builder.add_node("generate", generate_node)
    builder.add_node("evaluate", evaluation_node)
    builder.add_node("revise", revise_node)
    builder.add_edge(START, "intent")
    builder.add_conditional_edges(
        "intent",
        decide_intent_node,
        {
            "archive_query": "search",
            "general_chat": "general_chat",
            "tts_request": "tts",
        },
    )
    builder.add_edge("general_chat", END)
    builder.add_edge("tts", END)
    builder.add_conditional_edges(
        "search",
        decide_after_search_node,
        {
            "finish": END,
        },
    )
    builder.add_conditional_edges(
        "generate",
        decide_after_generate_node,
        {
            "evaluate": "evaluate",
            "finish": END,
        },
    )
    builder.add_conditional_edges(
        "evaluate",
        decide_next_node,
        {
            "revise": "revise",
            "finish": END,
        },
    )
    builder.add_conditional_edges(
        "revise",
        decide_after_generate_node,
        {
            "evaluate": "evaluate",
            "finish": END,
        },
    )
    return builder.compile()


def intent_node(state: ArchiveState) -> dict[str, Any]:
    """사용자 입력이 괴담 조회 요청인지 일반 대화인지 분류한다."""
    question = state.get("question", "")
    return {"intent": classify_intent(question)}


def general_chat_node(state: ArchiveState) -> dict[str, Any]:
    """일반 대화는 검색 없이 챗봇 기본 화자 프롬프트로 바로 응답한다."""
    prompt = build_general_chat_prompt(
        question=state.get("question", ""),
        conversation_history=state.get("conversation_history", []),
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


def decide_intent_node(state: ArchiveState) -> Literal["archive_query", "general_chat", "tts_request"]:
    """분류된 intent 값에 따라 archive 검색 흐름과 일반 대화 흐름을 나눈다."""
    if state.get("intent") == "archive_query":
        return "archive_query"

    if state.get("intent") == "tts_request":
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


def decide_after_search_node(state: ArchiveState) -> Literal["finish"]:
    """첫 검색 단계에서는 생성하지 않고 목록 반환으로 흐름을 끝낸다."""
    return "finish"


def decide_after_generate_node(state: ArchiveState) -> Literal["evaluate", "finish"]:
    """검토할 원본과 생성문이 있을 때만 평가 노드를 실행한다."""
    if state.get("skip_evaluation"):
        return "finish"

    if not state.get("source_story"):
        return "finish"

    if not state.get("generated_story", "").strip():
        return "finish"

    return "evaluate"


def classify_intent(question: str) -> Literal["archive_query", "general_chat", "tts_request"]:
    """질문 문구의 단서를 보고 괴담 조회 요청인지 일반 대화인지 판단한다."""
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
            return "tts_request"

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
            return "archive_query"

    return "general_chat"


def search_node(state: ArchiveState) -> dict[str, Any]:
    """질문에서 키워드를 뽑고 DB에서 가장 관련 있는 원본 기록을 찾는다."""
    question = state.get("question", "")
    keywords = extract_keywords(question)
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

    if state.get("revise_count", 0) >= 1:
        return "finish"

    return "revise"


def search_archive_records_for_question(
    question: str,
    keywords: list[str],
    limit: int = 5,
    body_limit: int = 1800,
) -> list[dict[str, Any]]:
    """정제 키워드 검색 후 결과가 없으면 원문 토큰으로 한 번 더 검색한다."""
    search_results = search_archive_records_by_keywords(
        keywords,
        limit=limit,
        body_limit=body_limit,
    )
    if search_results:
        return search_results

    fallback_keywords = extract_fallback_keywords(question, keywords)
    if not fallback_keywords:
        return []

    return search_archive_records_by_keywords(
        fallback_keywords,
        limit=limit,
        body_limit=body_limit,
    )


def search_archive_records_by_keywords(
    keywords: list[str],
    limit: int = 5,
    body_limit: int = 1800,
) -> list[dict[str, Any]]:
    """키워드별 명시적 필터를 합쳐 괴담, 존재, 금기 기록을 검색한다."""
    records = []
    story_queryset = HorrorStory.objects.none()
    entity_queryset = MythEntity.objects.none()
    superstition_queryset = Superstition.objects.none()

    for keyword in keywords:
        story_queryset = (
            story_queryset
            | HorrorStory.objects.filter(title__icontains=keyword)
            | HorrorStory.objects.filter(content__icontains=keyword)
            | HorrorStory.objects.filter(preview__icontains=keyword)
            | HorrorStory.objects.filter(region__icontains=keyword)
            | HorrorStory.objects.filter(category__icontains=keyword)
        )
        entity_queryset = (
            entity_queryset
            | MythEntity.objects.filter(name__icontains=keyword)
            | MythEntity.objects.filter(origin__icontains=keyword)
            | MythEntity.objects.filter(description__icontains=keyword)
            | MythEntity.objects.filter(behavior__icontains=keyword)
            | MythEntity.objects.filter(weakness__icontains=keyword)
            | MythEntity.objects.filter(history__icontains=keyword)
            | MythEntity.objects.filter(signs__icontains=keyword)
        )
        superstition_queryset = (
            superstition_queryset
            | Superstition.objects.filter(content__icontains=keyword)
            | Superstition.objects.filter(category__icontains=keyword)
            | Superstition.objects.filter(region__icontains=keyword)
        )

    for story in story_queryset.distinct()[: limit * 3]:
        body = make_preview(story.preview, story.content, limit=body_limit)
        if is_generic_record_name(story.title, keywords):
            continue

        if not is_relevant_record(
            keywords,
            strong_values=[story.title, story.region, story.category],
            weak_values=[story.content],
            single_keyword_weak_match_count=SINGLE_KEYWORD_WEAK_MATCH_COUNTS["horror_story"],
        ):
            continue

        records.append({
            "id": story.id,
            "name": story.title,
            "body": body,
            "regions": clean_regions(story.region),
            "type": "horror_story",
            "score": score_record_text(
                keywords,
                story.title,
                story.region,
                story.category,
                story.content,
            ),
        })

    for entity in entity_queryset.distinct()[: limit * 3]:
        body = make_preview(
            entity.description,
            entity.behavior,
            entity.weakness,
            entity.history,
            entity.signs,
            "\n".join(entity.survival_rules or []),
            limit=body_limit,
        )
        if not is_relevant_record(
            keywords,
            strong_values=[entity.name, entity.origin, entity.signs],
            weak_values=[
                entity.description,
                entity.behavior,
                entity.weakness,
                entity.history,
                "\n".join(entity.survival_rules or []),
            ],
            single_keyword_weak_match_count=SINGLE_KEYWORD_WEAK_MATCH_COUNTS["myth_entity"],
        ):
            continue

        records.append({
            "id": entity.id,
            "name": entity.name,
            "body": body,
            "regions": clean_regions(entity.origin),
            "type": "myth_entity",
            "score": score_record_text(
                keywords,
                entity.name,
                entity.origin,
                entity.signs,
                entity.description,
                entity.behavior,
                entity.weakness,
                entity.history,
                "\n".join(entity.survival_rules or []),
            ),
        })

    for superstition in superstition_queryset.distinct()[: limit * 3]:
        body = make_preview(superstition.content, limit=body_limit)
        if not is_relevant_record(
            keywords,
            strong_values=[superstition.region, superstition.category],
            weak_values=[superstition.content],
            single_keyword_weak_match_count=SINGLE_KEYWORD_WEAK_MATCH_COUNTS["superstition"],
        ):
            continue

        records.append({
            "id": superstition.id,
            "name": superstition.content[:50],
            "body": body,
            "regions": clean_regions(superstition.region, superstition.category),
            "type": "superstition",
            "score": score_record_text(
                keywords,
                superstition.content,
                superstition.region,
                superstition.category,
            ),
        })

    records.sort(key=lambda record: record["score"], reverse=True)
    return records[:limit]


def get_archive_record(record_type: str, record_id: int, body_limit: int = 1800) -> dict[str, Any]:
    """타입과 ID로 단일 archive 원본 기록을 조회해 생성 파이프라인 입력 형태로 변환한다."""
    if record_type == "horror_story":
        story = HorrorStory.objects.get(id=record_id)
        body = make_preview(story.preview, story.content, limit=body_limit)
        return {
            "id": story.id,
            "name": story.title,
            "body": body,
            "regions": clean_regions(story.region),
            "type": "horror_story",
            "score": 1,
        }

    if record_type == "myth_entity":
        entity = MythEntity.objects.get(id=record_id)
        body = make_preview(
            entity.description,
            entity.behavior,
            entity.weakness,
            entity.history,
            entity.signs,
            "\n".join(entity.survival_rules or []),
            limit=body_limit,
        )
        return {
            "id": entity.id,
            "name": entity.name,
            "body": body,
            "regions": clean_regions(entity.origin),
            "type": "myth_entity",
            "score": 1,
        }

    if record_type == "superstition":
        superstition = Superstition.objects.get(id=record_id)
        return {
            "id": superstition.id,
            "name": superstition.content[:50],
            "body": make_preview(superstition.content, limit=body_limit),
            "regions": clean_regions(superstition.region, superstition.category),
            "type": "superstition",
            "score": 1,
        }

    raise ValueError("지원하지 않는 archive 기록 타입입니다.")


def invoke_llm(prompt: str) -> str:
    """공통 LLM 팩토리에서 모델을 받아 프롬프트 응답 문자열을 반환한다."""
    response = get_llm().invoke(prompt)
    if hasattr(response, "content"):
        return str(response.content).strip()

    return str(response).strip()


def parse_evaluation_response(raw_response: str) -> dict[str, Any]:
    """LLM 평가 응답에서 JSON 객체를 파싱하고 실패 시 불합격 결과를 만든다."""
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


def make_preview(*parts: Any, limit: int) -> str:
    """여러 본문 조각을 합친 뒤 프롬프트에 넣을 길이로 줄인다."""
    body = "\n".join(str(part).strip() for part in parts if part)
    if len(body) <= limit:
        return body

    return f"{body[:limit].rstrip()}..."


def clean_regions(*values: Any) -> list[str]:
    """빈 지역값을 제거하고 화면 표시용 지역 목록을 만든다."""
    return [str(value).strip() for value in values if str(value).strip()]

