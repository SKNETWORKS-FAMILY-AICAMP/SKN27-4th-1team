from typing import Any, Optional

from langgraph.graph import END, START, StateGraph

from archive.services import graph_nodes
from archive.services.archive_search import get_archive_record
from archive.services.keyword_extractor import extract_keywords


def run_archive_chatbot(
    question: str,
    conversation_history: Optional[list[dict[str, str]]] = None,
    archive_context: Optional[dict[str, Any]] = None,
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

    archive_graph = build_archive_graph()
    final_state = archive_graph.invoke({
        "question": cleaned_question,
        "conversation_history": conversation_history or [],
        "archive_context": archive_context or {},
        "revise_count": 0,
    })
    return {
        "status": final_state.get("status", "success"),
        "query": cleaned_question,
        "intent": final_state.get("intent", ""),
        "keywords": final_state.get("keywords", []),
        "query_analysis": final_state.get("query_analysis", {}),
        "results": final_state.get("search_results", []),
        "source_story": final_state.get("source_story", {}),
        "llm_response": final_state.get("llm_response", ""),
        "evaluation": final_state.get("evaluation", {}),
        "is_passed": final_state.get("is_passed", False),
        "revised": final_state.get("revise_count", 0) > 0,
    }


def run_archive_record_chatbot(
    question: str,
    record_type: str,
    record_id: int,
    conversation_history: Optional[list[dict[str, str]]] = None,
    archive_context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """사용자가 선택한 특정 원본 기록을 기준으로 괴담 재구성 파이프라인을 실행한다."""
    source_story = get_archive_record(record_type, record_id)
    keyword_source = f"{question} {source_story.get('name', '')}"
    state: graph_nodes.ArchiveState = {
        "question": question.strip() or str(source_story.get("name", "")),
        "intent": "archive_query",
        "keywords": extract_keywords(keyword_source),
        "archive_context": archive_context or {},
        "conversation_history": conversation_history or [],
        "search_results": [source_story],
        "source_story": source_story,
        "revise_count": 0,
    }
    final_state = build_archive_graph().invoke(state)

    return {
        "status": final_state.get("status", "success"),
        "query": question,
        "intent": "archive_query",
        "keywords": final_state.get("keywords", []),
        "query_analysis": final_state.get("query_analysis", {}),
        "results": final_state.get("search_results", []),
        "source_story": final_state.get("source_story", {}),
        "llm_response": final_state.get("llm_response", ""),
        "evaluation": final_state.get("evaluation", {}),
        "is_passed": final_state.get("is_passed", False),
        "revised": final_state.get("revise_count", 0) > 0,
    }


def build_archive_graph():
    """archive 챗봇용 LangGraph 노드 흐름을 구성한다."""
    builder = StateGraph(graph_nodes.ArchiveState)
    builder.add_node("intent", graph_nodes.intent_node)
    builder.add_node("general_chat", graph_nodes.general_chat_node)
    builder.add_node("recommend", graph_nodes.recommend_node)
    builder.add_node("tts", graph_nodes.tts_node)
    builder.add_node("tts_stop", graph_nodes.tts_stop_node)
    builder.add_node("search", graph_nodes.search_node)
    builder.add_node("generate", graph_nodes.generate_node)
    builder.add_node("evaluate", graph_nodes.evaluation_node)
    builder.add_node("revise", graph_nodes.revise_node)
    builder.add_edge(START, "intent")
    builder.add_conditional_edges(
        "intent",
        graph_nodes.decide_intent_node,
        {
            "archive_query": "search",
            "generate": "generate",
            "general_chat": "general_chat",
            "recommend_request": "recommend",
            "tts_request": "tts",
            "tts_stop": "tts_stop",
        },
    )
    builder.add_edge("general_chat", END)
    builder.add_edge("recommend", END)
    builder.add_edge("tts", END)
    builder.add_edge("tts_stop", END)
    builder.add_edge("search", END)
    builder.add_conditional_edges(
        "generate",
        graph_nodes.decide_after_generate_node,
        {
            "evaluate": "evaluate",
            "finish": END,
        },
    )
    builder.add_conditional_edges(
        "evaluate",
        graph_nodes.decide_next_node,
        {
            "revise": "revise",
            "finish": END,
        },
    )
    builder.add_conditional_edges(
        "revise",
        graph_nodes.decide_after_generate_node,
        {
            "evaluate": "evaluate",
            "finish": END,
        },
    )
    return builder.compile()
