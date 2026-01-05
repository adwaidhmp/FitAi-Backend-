import json
import logging
from datetime import date

from ai_core.ai_nutrition import estimate_nutrition
from ai_core.calculations import (
    activity_multiplier,
    calculate_age,
    calculate_bmr,
    calculate_macros,
    target_calories,
)
from ai_core.guardrails import GuardrailError, validate_profile_for_diet
from ai_core.llm_client import ask_ai
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .prompts import SYSTEM_PROMPT, build_prompt

logger = logging.getLogger(__name__)


class GenerateDietView(APIView):
    def post(self, request):
        profile = request.data

        try:
            # --- DOB → AGE ---
            if isinstance(profile["dob"], str):
                profile["dob"] = date.fromisoformat(profile["dob"])

            profile["age"] = calculate_age(profile["dob"])

            # --- MODE ---
            diet_mode = profile.get("diet_mode", "normal")

            # --- VALIDATION ---
            validate_profile_for_diet(
                profile,
                allow_medical=(diet_mode == "medical_safe"),
            )

            # --- BMR + TDEE ---
            bmr = calculate_bmr(
                profile["weight_kg"],
                profile["height_cm"],
                profile["age"],
                profile["gender"],
            )

            tdee = bmr * activity_multiplier(profile["activity_level"])

            # --- CALORIES ---
            if diet_mode == "medical_safe":
                calories = round(tdee * 0.9)
            else:
                calories = target_calories(
                    tdee=tdee,
                    current_weight=profile["weight_kg"],
                    target_weight=profile["target_weight_kg"],
                    goal=profile["goal"],
                )

            # --- MACROS ---
            macros = calculate_macros(
                calories,
                profile["weight_kg"],
                profile["goal"],
            )

            # --- AI ---
            prompt = build_prompt(profile, calories, macros)
            ai_text = ask_ai(SYSTEM_PROMPT, prompt)
            meals = json.loads(ai_text)

            # --- RESPONSE ---
            return Response(
                {
                    "version": (
                        "medical_safe_v1" if diet_mode == "medical_safe" else "diet_v1"
                    ),
                    "daily_calories": calories,
                    "macros": macros,
                    "meals": meals["meals"],
                    "disclaimer": (
                        (
                            "This plan is AI-generated for general guidance only. "
                            "Not a medical prescription."
                        )
                        if diet_mode == "medical_safe"
                        else ""
                    ),
                }
            )

        except GuardrailError as e:
            return Response({"error": str(e)}, status=400)

        except Exception as e:
            import traceback

            traceback.print_exc()
            return Response(
                {"error": str(e)},
                status=500,
            )


class NutritionEstimateView(APIView):
    def post(self, request):
        logger.info("NutritionEstimateView called")

        food_text = request.data.get("food_text")

        if not food_text or not food_text.strip():
            logger.info("NutritionEstimateView called")
            return Response(
                {"detail": "food_text required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = estimate_nutrition(food_text)
            logger.info("NutritionEstimateView returning response")
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(result, status=status.HTTP_200_OK)
