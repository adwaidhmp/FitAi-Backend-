import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load .env file ONCE
load_dotenv()

def get_llm():
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not found in environment")

    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2,
        api_key=api_key,
        timeout=30,
        max_retries=2,
        max_tokens=300,   
    )
