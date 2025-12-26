from datetime import date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from .models import UserProfile, DietPlan,WeightLog,MealLog
from .helper.ai_client import generate_diet_plan,estimate_nutrition
from datetime import date, timedelta
from .helper.ai_payload import build_payload_from_profile
from rest_framework import permissions, status
from user_app.helper.ai_client import AIServiceError
from django.utils.timezone import now
from datetime import timedelta
from django.db import transaction
from .helper.meals import meal_already_logged
from .tasks import estimate_nutrition_task


def get_week_start():
    today = now().date()
    return today - timedelta(days=today.weekday())


class GenerateDietPlanView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # 1️⃣ Load profile
        profile = UserProfile.objects.filter(
            user_id=request.user.id
        ).first()

        if not profile:
            return Response(
                {"detail": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        today = now().date()

        # 2️⃣ Block if active plan already exists
        active_plan = DietPlan.objects.filter(
            user_id=request.user.id,
            week_start__lte=today,
            week_end__gte=today,
        ).first()

        if active_plan:
            return Response(
                {
                    "has_plan": True,
                    "detail": "You already have an active diet plan",
                    "daily_calories": active_plan.daily_calories,
                    "macros": active_plan.macros,
                    "meals": active_plan.meals,
                    "version": active_plan.version,
                },
                status=status.HTTP_200_OK,
            )

        # 3️⃣ Stop if target already achieved
        if profile.goal == "cutting" and profile.weight_kg <= profile.target_weight_kg:
            return Response(
                {
                    "status": "completed",
                    "detail": "Target weight achieved. Diet plan generation stopped.",
                },
                status=status.HTTP_200_OK,
            )

        if profile.goal == "bulking" and profile.weight_kg >= profile.target_weight_kg:
            return Response(
                {
                    "status": "completed",
                    "detail": "Target weight achieved. Diet plan generation stopped.",
                },
                status=status.HTTP_200_OK,
            )

        # 4️⃣ Create new week window
        week_start = get_week_start()
        week_end = week_start + timedelta(days=6)

        # 5️⃣ Build AI payload
        payload = build_payload_from_profile(profile)

        # 6️⃣ Call AI
        try:
            ai_response = generate_diet_plan(payload)
        except AIServiceError:
            return Response(
                {"detail": "AI service unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # 7️⃣ Save plan
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

        # 8️⃣ Response
        return Response(
            {
                "has_plan": True,
                "detail": "New diet plan generated",
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
        profile = UserProfile.objects.filter(
            user_id=request.user.id
        ).first()

        if not profile:
            return Response(
                {"detail": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ---------------------------
        # 3️⃣ Get active diet plan
        # ---------------------------
        current_plan = DietPlan.objects.filter(
            user_id=request.user.id,
            week_start__lte=today,
            week_end__gte=today,
        ).first()

        if not current_plan:
            return Response(
                {"detail": "No active diet plan found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ---------------------------
        # 4️⃣ Enforce FULL WEEK completion
        # ---------------------------
        if today < current_plan.week_end:
            return Response(
                {
                    "detail": (
                        "You can update weight only after completing "
                        "the current diet week"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ---------------------------
        # 5️⃣ Enforce once-per-week weight update
        # ---------------------------
        last_log = (
            WeightLog.objects
            .filter(user_id=request.user.id)
            .order_by("-logged_at")
            .first()
        )

        if last_log and (today - last_log.logged_at).days < 7:
            return Response(
                {"detail": "Weight can be updated only once per week"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ---------------------------
        # 6️⃣ Generate next plan window
        # ---------------------------
        new_week_start = today + timedelta(days=1)
        new_week_end = new_week_start + timedelta(days=6)

        # ---------------------------
        # 7️⃣ Atomic update + regeneration
        # ---------------------------
        with transaction.atomic():
            # update profile weight
            profile.weight_kg = weight
            profile.save(update_fields=["weight_kg"])

            # log weight
            WeightLog.objects.create(
                user_id=request.user.id,
                weight_kg=weight,
                logged_at=today,
            )

            # generate new plan
            payload = build_payload_from_profile(profile)

            try:
                ai_response = generate_diet_plan(payload)
            except AIServiceError:
                raise  # rollback transaction

            new_plan = DietPlan.objects.create(
                user_id=request.user.id,
                week_start=new_week_start,
                week_end=new_week_end,
                daily_calories=ai_response["daily_calories"],
                macros=ai_response["macros"],
                meals=ai_response["meals"],
                version=ai_response.get("version", "diet_v1"),
            )

        # ---------------------------
        # 8️⃣ Return response
        # ---------------------------
        return Response(
            {
                "detail": "Weight updated and new diet plan generated",
                "new_plan": {
                    "week_start": new_plan.week_start,
                    "week_end": new_plan.week_end,
                    "daily_calories": new_plan.daily_calories,
                    "macros": new_plan.macros,
                    "meals": new_plan.meals,
                },
            },
            status=status.HTTP_200_OK,
        )