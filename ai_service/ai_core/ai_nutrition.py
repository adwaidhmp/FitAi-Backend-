import json
from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = """
You are a nutrition estimation engine.
Estimate calories, protein, carbs, and fat.
Assume Indian portion sizes if not specified.
Return ONLY valid JSON.
Do not explain anything.
"""

def estimate_nutrition(food_text: str):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Estimate nutrition for: {food_text}"
            },
        ],
        temperature=0,
    )

    content = response.choices[0].message.content
    return json.loads(content)
