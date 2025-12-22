from datetime import date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from .models import DietPlan, MealLog
from .models import UserProfile, DietPlan,WeightLog
from .helper.ai_client import generate_diet_plan,estimate_nutrition
from datetime import date
from .helper.ai_payload import build_payload_from_profile
from .events.publisher import publish_event
from django.conf import settings
from rest_framework import permissions, status
from user_app.helper.ai_client import AIServiceError



class GenerateDietPlanView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile = UserProfile.objects.filter(
            user_id=request.user.id
        ).first()

        if not profile:
            return Response(
                {"detail": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        payload = build_payload_from_profile(profile)

        try:
            ai_response = generate_diet_plan(payload)
        except AIServiceError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        DietPlan.objects.create(
            user_id=request.user.id,
            daily_calories=ai_response["daily_calories"],
            macros=ai_response["macros"],
            meals=ai_response["meals"],
            version=ai_response["version"],
        )

        return Response(ai_response, status=status.HTTP_200_OK)


class FollowMealFromPlanView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        meal_type = request.data["meal_type"]  # breakfast / lunch / dinner
        today = date.today()

        plan = DietPlan.objects.filter(
            user_id=request.user.id
        ).order_by("-created_at").first()

        if not plan:
            return Response({"detail": "No diet plan found"}, status=404)
        
        meal = next(
            m for m in plan.meals if m["type"] == meal_type
        )

        MealLog.objects.update_or_create(
            user_id=request.user.id,
            date=today,
            meal_type=meal_type,
            defaults={
                "source": "plan",
                "items": meal["items"],
                "calories": meal["calories"],
                "protein": meal["protein"],
                "carbs": meal["carbs"],
                "fat": meal["fat"],
            },
        )

        return Response({"detail": f"{meal_type} logged from plan"})


class LogCustomMealWithAIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):

        meal_type = request.data["meal_type"]  # breakfast/lunch/dinner
        food_text = request.data["food_text"]

        if meal_type not in ["breakfast", "lunch", "dinner"]:
            return Response({"detail": "Invalid meal_type"}, status=400)

        ai_result = estimate_nutrition(food_text)

        total = ai_result["total"]

        if total["calories"] <= 0 or total["calories"] > 3000:
            return Response(
                {"detail": "Invalid nutrition estimate"},
                status=400,
            )

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
                "nutrition_source": "ai",
                "nutrition_confidence": ai_result.get("confidence", "estimated"),
            },
        )

        return Response({
            "detail": "Meal logged using AI estimate",
            "nutrition": total,
        })
    

class SkipMealView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        meal_type = request.data.get("meal_type")

        if meal_type not in ["breakfast", "lunch", "dinner"]:
            return Response({"detail": "Invalid meal_type"}, status=400)

        MealLog.objects.update_or_create(
            user_id=request.user.id,
            date=request.data.get("date"),
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

        return Response({"detail": "Meal skipped"})




    
class UpdateWeightView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        weight = request.data.get("weight_kg")

        if not weight or float(weight) <= 0:
            return Response({"detail": "Invalid weight"}, status=400)

        profile = UserProfile.objects.get(user_id=request.user.id)
        profile.weight_kg = float(weight)
        profile.save(update_fields=["weight_kg"])

        WeightLog.objects.create(
            user_id=request.user.id,
            weight_kg=weight,
            logged_at=request.data.get("date", date.today()),
        )

        # 🔥 Publish event (NO AI CALL HERE)
        publish_event(
            routing_key=settings.RABBIT_ROUTING_KEY_WEIGHT_UPDATED,
            payload={
                "user_id": str(request.user.id),
                "weight_kg": float(weight),
            },
        )

        return Response(
            {"detail": "Weight updated. Diet will regenerate shortly."},
            status=200,
        )