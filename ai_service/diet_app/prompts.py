SYSTEM_PROMPT = """
You are a fitness nutrition assistant.
You DO NOT calculate calories or macros.
You only create meals around given targets.
Avoid allergies and diet constraints.
Do NOT give medical advice.
Return ONLY valid JSON.
"""


def build_prompt(profile, calories, macros):
    diet_mode = profile.get("diet_mode", "normal")
    medical_conditions = profile.get("medical_conditions", [])

    medical_rules = ""

    if diet_mode == "medical_safe" and medical_conditions:
        rules = []

        if "diabetes" in medical_conditions:
            rules.append(
                "No added sugar. Avoid sweets, desserts, sweetened drinks. "
                "Prefer low glycemic index foods."
            )

        if "pressure" in medical_conditions:
            rules.append(
                "Low sodium meals. Avoid pickles, processed food, packaged snacks."
            )

        if "cholesterol" in medical_conditions:
            rules.append(
                "Low saturated fat. Avoid fried food, butter-heavy items. "
                "Prefer fiber-rich foods."
            )

        medical_rules = (
            "\nMedical safety constraints (not medical advice):\n- "
            + "\n- ".join(rules)
        )

    return f"""
User constraints:
Diet constraints: {profile.get("diet_constraints")}
Allergies: {profile.get("allergies")}
{medical_rules}

Nutrition targets (fixed):
Calories: {calories}
Protein: {macros["protein_g"]} g
Carbs: {macros["carbs_g"]} g
Fat: {macros["fat_g"]} g

Create a simple daily meal plan.

Rules:
- Follow nutrition targets strictly
- Respect all constraints
- No medical advice
- Simple foods only

Return JSON only:
{{
  "meals": [
    {{
      "name": "Breakfast",
      "items": ["food item with portion"]
    }},
    {{
      "name": "Lunch",
      "items": ["food item with portion"]
    }},
    {{
      "name": "Dinner",
      "items": ["food item with portion"]
    }}
  ]
}}
"""
