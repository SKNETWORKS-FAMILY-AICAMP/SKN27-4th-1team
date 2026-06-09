
from langchain_groq import ChatGroq
from langchain_ollama import OllamaLLM

def get_post_generation_llm():
    return ChatGroq(
        model="openai/gpt-oss-20b",
        temperature=0.5
    )

def get_llm(): # archive intent, search, evaluation
    return ChatGroq(model="openai/gpt-oss-120b")

def generator_llm():
    return OllamaLLM(model="gemma4:e4b")

