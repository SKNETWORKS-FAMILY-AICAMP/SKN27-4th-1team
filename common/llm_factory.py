from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()


def get_post_generation_llm():
    return ChatOpenAI(
        model="gpt-5.4-mini",
        temperature=0.5,
    )

def get_llm():
    return ChatOpenAI(
        model="gpt-5.4-mini",
        temperature=0,
    )








# GROQ_ARCHIVE_MODEL = "openai/gpt-oss-20b"
# # gpt-oss는 추론 토큰이 출력에 포함되므로 2048 기본 한도면 JSON 본문이 잘릴 수 있다.
# GROQ_MAX_OUTPUT_TOKENS = 8192
# # 추론 토큰을 줄여 응답 잘림과 분당 토큰 한도(429) 소진을 함께 완화한다.
# GROQ_REASONING_EFFORT = "low"
#
#
# def get_post_generation_llm():
#     from langchain_groq import ChatGroq
#
#     return ChatGroq(
#         model=GROQ_ARCHIVE_MODEL,
#         temperature=0.5,
#         max_tokens=GROQ_MAX_OUTPUT_TOKENS,
#         reasoning_effort=GROQ_REASONING_EFFORT,
#     )
#
#
# def get_llm():  # archive intent, search, evaluation
#     from langchain_groq import ChatGroq
#
#     return ChatGroq(
#         model=GROQ_ARCHIVE_MODEL,
#         max_tokens=GROQ_MAX_OUTPUT_TOKENS,
#         reasoning_effort=GROQ_REASONING_EFFORT,
#     )
#
#
# def generator_llm():
#     from langchain_ollama import OllamaLLM
#
#     return OllamaLLM(model="gemma4:e4b")

