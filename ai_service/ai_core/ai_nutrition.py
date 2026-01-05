import json
import logging

from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)


def get_client():
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=settings.OPENAI_API_KEY)


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
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": food_text},
            ],
            temperature=0,
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        logger.info("Nutrition estimation success")

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
