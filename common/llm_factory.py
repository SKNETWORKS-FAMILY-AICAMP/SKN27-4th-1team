from langchain_ollama import OllamaLLM

def get_llm():
    return OllamaLLM(model="gemma4:e4b")

