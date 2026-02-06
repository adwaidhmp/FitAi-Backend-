import json
import logging
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a nutrition estimation engine.

Return ONLY valid JSON in EXACTLY this format:

{
  "items": ["food item 1", "food item 2"],
  "total": {
    "calories": number,
    "protein": number,
    "carbs": number,
    "fat": number
  }
}

Rules:
- Assume Indian portion sizes if not specified
- Do NOT explain anything
- Do NOT include markdown
- Do NOT include text outside JSON
"""


def estimate_nutrition(food_text: str) -> dict:
    logger.info("Estimating nutrition", extra={"food_text": food_text})

    try:
        # ✅ Groq Key Check
        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not set")

        # ✅ Groq Client (OpenAI-compatible)
        client = OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )

        # ✅ Prompt
        prompt = f"""
Food Input:
{food_text}

Return ONLY JSON.
"""

        # ✅ Call Groq Chat Model
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # fast + free tier
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=300,
        )

        content = response.choices[0].message.content.strip()

        # ✅ Parse JSON strictly
        data = json.loads(content)

        return data

    except Exception:
        logger.exception("Nutrition estimation FAILED")

        return {
            "items": [food_text],
            "total": {
                "calories": 0,
                "protein": 0,
                "carbs": 0,
                "fat": 0,
            },
            "error": "AI nutrition failed",
        }
