from datetime import date, timedelta

from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    UserProfile,
    DietPlan,
    MealLog,
    WorkoutPlan,
    WorkoutLog,
    WeightLog,
)
from .permissions import IsTrainer
from .trainer_user_data_serializer import TrainerUserOverviewSerializer


class TrainerUserOverviewView(APIView):
    """
    Weekly read-only overview of a user's fitness data for trainers.
    """

    permission_classes = [IsAuthenticated, IsTrainer]

    def get(self, request, user_id):
        # ----------------------------
        # Week boundaries (Mon–Sun)
        # ----------------------------
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        # ----------------------------
        # Profile (must exist)
        # ----------------------------
        profile = get_object_or_404(UserProfile, user_id=user_id)

        # ----------------------------
        # Diet plan (this week)
        # ----------------------------
        diet_plan = DietPlan.objects.filter(
            user_id=user_id,
            week_start=week_start,
        ).first()

        # ----------------------------
        # Meal logs (this week)
        # ----------------------------
        diet_logs = MealLog.objects.filter(
            user_id=user_id,
            date__range=(week_start, week_end),
        ).order_by("date")

        total_calories_in = (
            diet_logs.aggregate(total=Sum("calories"))["total"] or 0
        )

        # ----------------------------
        # Workout plan (this week)
        # ----------------------------
        workout_plan = WorkoutPlan.objects.filter(
            user_id=user_id,
            week_start=week_start,
        ).first()

        # ----------------------------
        # Workout logs (this week)
        # ----------------------------
        workout_logs = WorkoutLog.objects.filter(
            user_id=user_id,
            date__range=(week_start, week_end),
        ).order_by("date")

        total_calories_burned = (
            workout_logs.aggregate(total=Sum("calories_burnt"))["total"] or 0
        )

        # ----------------------------
        # Weight logs (this week)
        # ----------------------------
        weight_logs = WeightLog.objects.filter(
            user_id=user_id,
            logged_at__range=(week_start, week_end),
        ).order_by("logged_at")

        # ----------------------------
        # Serialize
        # ----------------------------
        serializer = TrainerUserOverviewSerializer(
            {
                "profile": profile,
                "diet_plan": diet_plan,
                "diet_logs": diet_logs,
                "workout_plan": workout_plan,
                "workout_logs": workout_logs,
                "weight_logs": weight_logs,
                "weekly_stats": {
                    "calories_in": total_calories_in,
                    "calories_burned": total_calories_burned,
                },
            }
        )

        return Response(serializer.data)
