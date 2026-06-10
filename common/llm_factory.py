
def get_post_generation_llm():
    from langchain_groq import ChatGroq

    return ChatGroq(
        model="openai/gpt-oss-20b",
        temperature=0.5
    )

def get_llm(): # archive intent, search, evaluation
    from langchain_groq import ChatGroq

    return ChatGroq(model="openai/gpt-oss-20b")

def generator_llm():
    from langchain_ollama import OllamaLLM

    return OllamaLLM(model="gemma4:e4b")

