from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import json
from datetime import date
from ai_core.llm_client import ask_ai
from ai_core.calculations import (
    calculate_age,
    calculate_bmr,
    activity_multiplier,
    target_calories,
    calculate_macros,
)
from ai_core.guardrails import validate_profile_for_diet, GuardrailError
from .prompts import SYSTEM_PROMPT, build_prompt
from ai_core.ai_nutrition import estimate_nutrition

class GenerateDietView(APIView):
    def post(self, request):
        profile = request.data

        try:
            if isinstance(profile["dob"], str):
                profile["dob"] = date.fromisoformat(profile["dob"])

            profile["age"] = calculate_age(profile["dob"])

            diet_mode = profile.get("diet_mode", "normal")

            validate_profile_for_diet(
                profile,
                allow_medical=(diet_mode == "medical_safe"),
            )

            bmr = calculate_bmr(
                profile["weight_kg"],
                profile["height_cm"],
                profile["age"],
                profile["gender"],
            )

            tdee = bmr * activity_multiplier(profile["activity_level"])

            if diet_mode == "medical_safe":
                calories = round(tdee * 0.9)  # safe deficit
            else:
                calories = round(target_calories(tdee, profile["goal"]))

            macros = calculate_macros(
                calories,
                profile["weight_kg"],
                profile["goal"],
            )

            prompt = build_prompt(profile, calories, macros)

            ai_text = ask_ai(SYSTEM_PROMPT, prompt)
            meals = json.loads(ai_text)

            return Response(
                {
                    "version": "medical_safe_v1"
                    if diet_mode == "medical_safe"
                    else "diet_v1",
                    "daily_calories": calories,
                    "macros": macros,
                    "meals": meals["meals"],
                    "disclaimer": (
                        "This plan is AI-generated for general guidance only. "
                        "Not a medical prescription."
                    )
                    if diet_mode == "medical_safe"
                    else "",
                }
            )

        except GuardrailError as e:
            return Response({"error": str(e)}, status=400)



class NutritionEstimateView(APIView):

    def post(self, request):
        food_text = request.data.get("food_text")

        if not food_text:
            return Response({"detail": "food_text required"}, status=400)

        result = estimate_nutrition(food_text)
        return Response(result)