from langchain_groq import ChatGroq
#from langchain_ollama import OllamaLLM

def get_post_generation_llm():
    return ChatGroq(
        model="openai/gpt-oss-120b",
        temperature=0.5
    )

def get_llm(): # evaluation, rag
    return ChatGroq(model="openai/gpt-oss-120b")