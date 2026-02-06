from openai import OpenAI
from django.conf import settings


def get_client():
    """
    Returns Groq OpenAI-compatible client.
    """

    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set")

    return OpenAI(
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )


def ask_ai(system_prompt: str, user_prompt: str):
    """
    Calls Groq LLM and returns raw response text.
    Expected output: JSON string.
    """

    client = get_client()

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",  # fast + free tier
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=400,
    )

    return response.choices[0].message.content.strip()
