from datetime import date, timedelta

from django.db import transaction
from django.utils.timezone import now
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from user_app.helper.ai_client import AIServiceError

from .helper.ai_client import estimate_nutrition, generate_diet_plan
from .helper.ai_payload import build_payload_from_profile
from .helper.meals import meal_already_logged
from .models import DietPlan, MealLog, UserProfile, WeightLog
from .tasks import estimate_nutrition_task, generate_diet_plan_task


def get_week_start(today):
    return today - timedelta(days=today.weekday())


class GenerateDietPlanView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        today = now().date()

        # 1️⃣ Load profile
        profile = UserProfile.objects.filter(user_id=request.user.id).first()
        if not profile:
            return Response(
                {"detail": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 2️⃣ Block regeneration
        if DietPlan.objects.filter(user_id=request.user.id).exists():
            return Response(
                {
                    "detail": (
                        "Diet plans are generated automatically after "
                        "weekly weight updates."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3️⃣ Stop if target achieved
        if (
            profile.goal == "cutting"
            and profile.target_weight_kg
            and profile.weight_kg <= profile.target_weight_kg
        ) or (
            profile.goal == "bulking"
            and profile.target_weight_kg
            and profile.weight_kg >= profile.target_weight_kg
        ):
            return Response(
                {
                    "status": "completed",
                    "detail": "Target weight achieved. Diet plan generation stopped.",
                },
                status=status.HTTP_200_OK,
            )

        # 4️⃣ Create week window
        week_start = get_week_start(today)
        week_end = week_start + timedelta(days=6)

        # 5️⃣ Create placeholder plan
        plan = DietPlan.objects.create(
            user_id=request.user.id,
            week_start=week_start,
            week_end=week_end,
            status="pending",
        )

        # 6️⃣ Enqueue async generation
        generate_diet_plan_task.delay(plan.id)

        # 7️⃣ Immediate response
        return Response(
            {
                "has_plan": False,
                "status": "processing",
                "detail": "Diet plan is being generated",
            },
            status=status.HTTP_202_ACCEPTED,
        )


class CurrentDietPlanView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = now().date()

        # 1️⃣ Try ACTIVE plan
        plan = DietPlan.objects.filter(
            user_id=request.user.id,
            week_start__lte=today,
            week_end__gte=today,
        ).first()

        # 2️⃣ If active plan exists
        if plan:
            return Response(
                {
                    "has_plan": True,
                    "status": plan.status,
                    "daily_calories": plan.daily_calories,
                    "macros": plan.macros,
                    "meals": plan.meals,
                    "version": plan.version,
                    "week_start": plan.week_start,
                    "week_end": plan.week_end,
                    "can_generate": False,
                    "can_update_weight": False,
                },
                status=status.HTTP_200_OK,
            )

        # 3️⃣ No active plan → check if user EVER had a plan
        has_any_plan = DietPlan.objects.filter(
            user_id=request.user.id
        ).exists()

        # 🆕 Brand-new user → allow manual generation
        if not has_any_plan:
            return Response(
                {
                    "has_plan": False,
                    "can_generate": True,
                    "can_update_weight": False,
                },
                status=status.HTTP_200_OK,
            )

        # 🔁 Existing user → must update weight
        return Response(
            {
                "has_plan": False,
                "can_generate": False,
                "can_update_weight": True,
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

        # 🔒 block multiple actions
        if MealLog.objects.filter(
            user_id=request.user.id,
            date=today,
            meal_type=meal_type,
        ).exists():
            return Response(
                {"detail": f"{meal_type} already logged"},
                status=400,
            )

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
            return Response({"detail": "Meal not found"}, status=400)

        # ✅ READ CORRECT MACRO KEYS
        macros = plan.macros or {}

        protein_total = macros.get("protein_g", 0)
        carbs_total = macros.get("carbs_g", 0)
        fat_total = macros.get("fat_g", 0)

        meals_count = 3  # breakfast, lunch, dinner

        MealLog.objects.create(
            user_id=request.user.id,
            date=today,
            meal_type=meal_type,
            source="planned",
            items=meal["items"],
            calories=round(plan.daily_calories / meals_count),
            protein=round(protein_total / meals_count, 1),
            carbs=round(carbs_total / meals_count, 1),
            fat=round(fat_total / meals_count, 1),
        )

        return Response(
            {"detail": f"{meal_type} logged from plan"},
            status=status.HTTP_200_OK,
        )



class LogCustomMealWithAIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        meal_type = request.data.get("meal_type")
        food_text = request.data.get("food_text")
        today = date.today()

        if meal_type not in ["breakfast", "lunch", "dinner"]:
            return Response({"detail": "Invalid meal_type"}, status=400)

        if not food_text or not food_text.strip():
            return Response({"detail": "food_text required"}, status=400)

        if meal_already_logged(request.user.id, today, meal_type):
            return Response(
                {"detail": f"{meal_type} already logged"},
                status=400,
            )

        meal = MealLog.objects.create(
            user_id=request.user.id,
            date=today,
            meal_type=meal_type,
            source="custom",
            items=[x.strip() for x in food_text.split(",")],
            calories=0,
            protein=0,
            carbs=0,
            fat=0,
        )

        # 🔥 ASYNC
        estimate_nutrition_task.delay(meal.id)

        return Response(
            {"detail": "Custom meal logged. Nutrition estimation in progress."},
            status=200,
        )


class SkipMealView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        meal_type = request.data.get("meal_type")
        today = date.today()

        if meal_type not in ["breakfast", "lunch", "dinner"]:
            return Response({"detail": "Invalid meal_type"}, status=400)

        if meal_already_logged(request.user.id, today, meal_type):
            return Response(
                {"detail": f"{meal_type} already logged"},
                status=400,
            )

        MealLog.objects.create(
            user_id=request.user.id,
            date=today,
            meal_type=meal_type,
            source="skipped",
            items=None,
            calories=0,
            protein=0,
            carbs=0,
            fat=0,
        )

        return Response({"detail": f"{meal_type} skipped"})


class LogExtraMealView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        food_text = request.data.get("food_text")

        if not food_text or not food_text.strip():
            return Response({"detail": "food_text required"}, status=400)

        meal = MealLog.objects.create(
            user_id=request.user.id,
            date=date.today(),
            meal_type="other",
            source="extra",
            items=[x.strip() for x in food_text.split(",")],
            calories=0,
            protein=0,
            carbs=0,
            fat=0,
        )

        # 🔥 ASYNC
        estimate_nutrition_task.delay(meal.id)

        return Response(
            {"detail": "Extra meal logged. Nutrition estimation in progress."},
            status=200,
        )


class UpdateWeightView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        weight = request.data.get("weight_kg")

        # ---------------------------
        # 1️⃣ Validate input
        # ---------------------------
        try:
            weight = float(weight)
            if weight <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid weight value"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        today = now().date()

        # ---------------------------
        # 2️⃣ Load profile
        # ---------------------------
        profile = UserProfile.objects.filter(user_id=request.user.id).first()
        if not profile:
            return Response(
                {"detail": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ---------------------------
        # 3️⃣ Ensure at least one completed week exists
        # ---------------------------
        last_completed_plan = (
            DietPlan.objects.filter(
                user_id=request.user.id,
                week_end__lt=today,
            )
            .order_by("-week_end")
            .first()
        )

        if not last_completed_plan:
            return Response(
                {
                    "detail": (
                        "You can update weight only after completing "
                        "at least one diet week"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ---------------------------
        # 4️⃣ Enforce once-per-week weight update
        # ---------------------------
        last_log = (
            WeightLog.objects.filter(user_id=request.user.id)
            .order_by("-logged_at")
            .first()
        )

        if last_log and (today - last_log.logged_at).days < 7:
            return Response(
                {"detail": "Weight can be updated only once per week"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ---------------------------
        # 5️⃣ Update profile + log weight (atomic)
        # ---------------------------
        with transaction.atomic():
            profile.weight_kg = weight
            profile.save(update_fields=["weight_kg"])

            WeightLog.objects.create(
                user_id=request.user.id,
                weight_kg=weight,
                logged_at=today,
            )

        # ---------------------------
        # 6️⃣ Stop if target achieved
        # ---------------------------
        if (
            profile.goal == "cutting"
            and profile.target_weight_kg
            and weight <= profile.target_weight_kg
        ) or (
            profile.goal == "bulking"
            and profile.target_weight_kg
            and weight >= profile.target_weight_kg
        ):
            return Response(
                {
                    "detail": (
                        "Target weight achieved. "
                        "Diet plan generation stopped."
                    )
                },
                status=status.HTTP_200_OK,
            )

        # ---------------------------
        # 7️⃣ Calculate NEXT week
        # ---------------------------
        week_start = today
        week_end = today + timedelta(days=6)

        # ---------------------------
        # 8️⃣ SAFE diet plan creation (FIXED)
        # ---------------------------
        plan, created = DietPlan.objects.update_or_create(
            user_id=request.user.id,
            week_start=week_start,
            defaults={
                "week_end": week_end,
                "status": "pending",
            },
        )

        # Trigger AI only when needed
        if created or plan.status != "pending":
            plan.status = "pending"
            plan.save(update_fields=["status"])
            generate_diet_plan_task.delay(plan.id)

        # ---------------------------
        # 9️⃣ Response
        # ---------------------------
        return Response(
            {
                "detail": "Weight updated. New diet plan is being generated.",
                "new_plan": {
                    "week_start": plan.week_start,
                    "week_end": plan.week_end,
                    "status": plan.status,
                },
            },
            status=status.HTTP_200_OK,
        )