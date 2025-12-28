import json
from ai_core.llm_client import ask_ai


def generate_weekly_workout(
    profile_data,
    workout_type,
    exercise_count,
    min_duration,
    max_duration,
):
    system_prompt = """
You are a professional fitness coach.
You ONLY output valid JSON.
You NEVER include explanations or extra text.
You generate SAFE workouts only.
"""

    user_prompt = f"""
Generate ONE workout to be repeated daily for a week.

User details:
- Goal: {profile_data["goal"]}
- Experience level: {profile_data["experience"]}
- Activity level: {profile_data.get("activity_level", "moderate")}
- Workout type: {workout_type}

RULES:
- EXACTLY {exercise_count} exercises
- Total duration should be roughly {min_duration}–{max_duration} minutes
- Beginner safe if beginner
- No extreme movements
- Bodyweight only
- No equipment
- Do NOT include calories
- Output JSON ONLY

FORMAT:
{{
  "sessions": [
    {{
      "name": "Full Body Workout",
      "exercises": [
        {{
          "name": "string",
          "duration_sec": number,
          "intensity": "low | medium | high"
        }}
      ]
    }}
  ]
}}
"""

    raw = ask_ai(system_prompt, user_prompt)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("AI returned invalid JSON")

    exercises = data["sessions"][0]["exercises"]

    if len(exercises) != exercise_count:
        raise ValueError("Invalid exercise count from AI")

    for e in exercises:
        if e["intensity"] not in ["low", "medium", "high"]:
            raise ValueError("Invalid intensity")

    return data
