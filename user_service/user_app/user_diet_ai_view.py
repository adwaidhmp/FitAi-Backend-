from datetime import date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from .models import DietPlan, MealLog
from .models import UserProfile, DietPlan,WeightLog
from .helper.ai_client import generate_diet_plan,estimate_nutrition
from datetime import date, timedelta
from .helper.ai_payload import build_payload_from_profile
from .events.publisher import publish_event
from django.conf import settings
from rest_framework import permissions, status
from user_app.helper.ai_client import AIServiceError
from django.utils.timezone import now
from datetime import timedelta
from django.db import transaction


def get_week_start():
    today = now().date()
    return today - timedelta(days=today.weekday())


class GenerateDietPlanView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # 1️⃣ Load profile (SOURCE OF TRUTH)
        profile = UserProfile.objects.filter(
            user_id=request.user.id
        ).first()

        if not profile:
            return Response(
                {"detail": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 2️⃣ Check if target weight already achieved
        current_weight = profile.weight_kg
        target_weight = profile.target_weight_kg
        goal = profile.goal

        if goal == "cutting" and current_weight <= target_weight:
            return Response(
                {
                    "status": "completed",
                    "detail": "Target weight achieved. Diet plan generation stopped.",
                },
                status=status.HTTP_200_OK,
            )

        if goal == "bulking" and current_weight >= target_weight:
            return Response(
                {
                    "status": "completed",
                    "detail": "Target weight achieved. Diet plan generation stopped.",
                },
                status=status.HTTP_200_OK,
            )

        # 3️⃣ Weekly window
        week_start = get_week_start()
        week_end = week_start + timedelta(days=6)

        # 4️⃣ Return existing plan if already generated this week
        existing_plan = DietPlan.objects.filter(
            user_id=request.user.id,
            week_start=week_start,
        ).first()

        if existing_plan:
            return Response(
                {
                    "has_plan": True,
                    "daily_calories": existing_plan.daily_calories,
                    "macros": existing_plan.macros,
                    "meals": existing_plan.meals,
                    "version": existing_plan.version,
                },
                status=status.HTTP_200_OK,
            )

        # 5️⃣ Build payload (profile → AI-safe dict)
        payload = build_payload_from_profile(profile)

        # 6️⃣ Call AI service
        try:
            ai_response = generate_diet_plan(payload)
        except AIServiceError:
            return Response(
                {"detail": "AI service unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # 7️⃣ Persist plan atomically
        with transaction.atomic():
            plan = DietPlan.objects.create(
                user_id=request.user.id,
                week_start=week_start,
                week_end=week_end,
                daily_calories=ai_response["daily_calories"],
                macros=ai_response["macros"],
                meals=ai_response["meals"],
                version=ai_response.get("version", "diet_v1"),
            )

        # 8️⃣ Return response
        return Response(
            {
                "has_plan": True,
                "daily_calories": plan.daily_calories,
                "macros": plan.macros,
                "meals": plan.meals,
                "version": plan.version,
            },
            status=status.HTTP_201_CREATED,
        )

    

class CurrentDietPlanView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        week_start = get_week_start()

        plan = DietPlan.objects.filter(
            user_id=request.user.id,
            week_start=week_start,
        ).first()

        if not plan:
            return Response(
                {"has_plan": False},
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "has_plan": True,
                "daily_calories": plan.daily_calories,
                "macros": plan.macros,
                "meals": plan.meals,
                "version": plan.version,
            },
            status=status.HTTP_200_OK,
        )



class FollowMealFromPlanView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        meal_type = request.data.get("meal_type")
        today = date.today()

        if meal_type not in ["breakfast", "lunch", "dinner"]:
            return Response({"detail": "Invalid meal_type"}, status=400)

        plan = DietPlan.objects.filter(
            user_id=request.user.id,
            week_start__lte=today,
            week_end__gte=today,
        ).first()

        if not plan:
            return Response({"detail": "No active diet plan"}, status=404)

        meal = next(
            (m for m in plan.meals if m["name"].lower() == meal_type),
            None,
        )

        if not meal:
            return Response({"detail": "Meal not found in plan"}, status=400)

        MealLog.objects.update_or_create(
            user_id=request.user.id,
            date=today,
            meal_type=meal_type,
            defaults={
                "source": "planned",
                "items": meal["items"],
                "calories": meal.get("calories", 0),
                "protein": meal.get("protein", 0),
                "carbs": meal.get("carbs", 0),
                "fat": meal.get("fat", 0),
            },
        )

        return Response({"detail": f"{meal_type} logged from plan"})

class LogCustomMealWithAIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        meal_type = request.data.get("meal_type")
        food_text = request.data.get("food_text")

        if meal_type not in ["breakfast", "lunch", "dinner"]:
            return Response({"detail": "Invalid meal_type"}, status=400)

        if not food_text or not food_text.strip():
            return Response({"detail": "food_text required"}, status=400)

        ai_result = estimate_nutrition(food_text)
        total = ai_result["total"]

        if total["calories"] <= 0 or total["calories"] > 3000:
            return Response({"detail": "Invalid nutrition estimate"}, status=400)

        MealLog.objects.update_or_create(
            user_id=request.user.id,
            date=date.today(),
            meal_type=meal_type,
            defaults={
                "source": "custom",
                "items": ai_result["items"],
                "calories": total["calories"],
                "protein": total["protein"],
                "carbs": total["carbs"],
                "fat": total["fat"],
            },
        )

        return Response(
            {
                "detail": "Custom meal logged",
                "nutrition": total,
            }
        )

class SkipMealView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        meal_type = request.data.get("meal_type")

        if meal_type not in ["breakfast", "lunch", "dinner"]:
            return Response({"detail": "Invalid meal_type"}, status=400)

        MealLog.objects.update_or_create(
            user_id=request.user.id,
            date=date.today(),
            meal_type=meal_type,
            defaults={
                "source": "skipped",
                "items": None,
                "calories": 0,
                "protein": 0,
                "carbs": 0,
                "fat": 0,
            },
        )

        return Response({"detail": f"{meal_type} skipped"})


class LogExtraMealView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        food_text = request.data.get("food_text")

        if not food_text or not food_text.strip():
            return Response({"detail": "food_text required"}, status=400)

        ai_result = estimate_nutrition(food_text)
        total = ai_result["total"]

        if total["calories"] <= 0 or total["calories"] > 3000:
            return Response({"detail": "Invalid nutrition estimate"}, status=400)

        MealLog.objects.create(
            user_id=request.user.id,
            date=date.today(),
            meal_type="other",
            source="extra",
            items=ai_result["items"],
            calories=total["calories"],
            protein=total["protein"],
            carbs=total["carbs"],
            fat=total["fat"],
        )

        return Response(
            {
                "detail": "Extra meal logged",
                "nutrition": total,
            }
        )



class UpdateWeightView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        weight = request.data.get("weight_kg")

        if not weight or float(weight) <= 0:
            return Response({"detail": "Invalid weight"}, status=400)

        today = now().date()

        # 1️⃣ Enforce weekly update rule
        last_log = (
            WeightLog.objects
            .filter(user_id=request.user.id)
            .order_by("-logged_at")
            .first()
        )

        if last_log and (today - last_log.logged_at).days < 7:
            return Response(
                {"detail": "Weight can be updated only once per week"},
                status=400,
            )

        profile = UserProfile.objects.filter(
            user_id=request.user.id
        ).first()

        if not profile:
            return Response({"detail": "Profile not found"}, status=404)

        # 2️⃣ Close current diet plan (if any)
        current_plan = DietPlan.objects.filter(
            user_id=request.user.id,
            week_start__lte=today,
            week_end__gte=today,
        ).first()

        if not current_plan:
            return Response(
                {"detail": "No active diet plan to update"},
                status=400,
            )

        with transaction.atomic():
            # update profile weight
            profile.weight_kg = float(weight)
            profile.save(update_fields=["weight_kg"])

            # log weight
            WeightLog.objects.create(
                user_id=request.user.id,
                weight_kg=float(weight),
                logged_at=today,
            )

            # close current plan early
            current_plan.week_end = today
            current_plan.save(update_fields=["week_end"])

            # 3️⃣ Generate NEW plan for next week
            new_week_start = today
            new_week_end = today + timedelta(days=6)

            payload = build_payload_from_profile(profile)

            try:
                ai_response = generate_diet_plan(payload)
            except AIServiceError:
                return Response(
                    {"detail": "AI service unavailable"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            DietPlan.objects.create(
                user_id=request.user.id,
                week_start=new_week_start,
                week_end=new_week_end,
                daily_calories=ai_response["daily_calories"],
                macros=ai_response["macros"],
                meals=ai_response["meals"],
                version=ai_response.get("version", "diet_v1"),
            )

        return Response(
            {
                "detail": "Weight updated and new diet plan generated",
                "new_plan": {
                    "daily_calories": ai_response["daily_calories"],
                    "macros": ai_response["macros"],
                    "meals": ai_response["meals"],
                },
            },
            status=200,
        )