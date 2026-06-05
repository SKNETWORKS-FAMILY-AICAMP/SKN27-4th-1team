"""LangGraph pipeline for horror archive search."""
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END, START
from .services import search_horror_records, call_groq_llm_structured, rewrite_query


class SearchState(TypedDict):
    query: str
    search_query: str
    conversation_history: List[dict]
    search_results: List[dict]
    is_certain: bool
    picked_index: Optional[int]
    llm_response: str


def query_rewrite_node(state: SearchState) -> dict:
    """Node 1: Rewrites follow-up queries into proper search keywords using conversation history."""
    rewritten = rewrite_query(state["query"], state["conversation_history"])
    return {"search_query": rewritten}


def search_node(state: SearchState) -> dict:
    """Node 2: Hybrid search (keyword + vector) against Neo4j using rewritten query."""
    results = search_horror_records(state["search_query"])
    return {"search_results": results}


def llm_node(state: SearchState) -> dict:
    """Node 3: Groq LLM ranks results and generates terminal response."""
    structured = call_groq_llm_structured(
        state["query"],
        state["search_results"],
        state["conversation_history"]
    )
    return {
        "is_certain": structured.get("is_certain", False),
        "picked_index": structured.get("picked_index"),
        "llm_response": structured.get("response", "")
    }


workflow = StateGraph(SearchState)
workflow.add_node("query_rewrite", query_rewrite_node)
workflow.add_node("search", search_node)
workflow.add_node("llm_rank", llm_node)
workflow.add_edge(START, "query_rewrite")
workflow.add_edge("query_rewrite", "search")
workflow.add_edge("search", "llm_rank")
workflow.add_edge("llm_rank", END)

search_graph = workflow.compile()
