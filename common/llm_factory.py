from langchain_ollama import OllamaLLM

def get_post_generation_llm():
    return OllamaLLM(
        model="gemma4:e4b",
        temperature=0.5
    )

def get_llm(): # evaluation, rag
    return OllamaLLM(model="gemma4:e4b")