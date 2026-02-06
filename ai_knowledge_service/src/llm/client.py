import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_llm():
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY not found")

    return ChatOpenAI(
        model="llama-3.1-8b-instant",   # Best quality free model
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.2,
        max_tokens=300,
    )
