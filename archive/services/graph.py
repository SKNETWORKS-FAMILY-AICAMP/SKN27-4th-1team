from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import PromptTemplate
from typing import TypedDict, List, Optional

class ArchiveState(TypedDict):
    question: str
    search_query: str
    conversation_history: List[dict]
    search_results: List[dict]
    is_certain: bool
    picked_index: Optional[int]
    llm_response: str



def search_node(state: ArchiveState) -> dict:
    pass

def rewrite_node(state: ArchiveState) -> dict:
    pass

def evaluation_node(state: ArchiveState) -> dict:
    pass

graph = StateGraph(ArchiveState)


