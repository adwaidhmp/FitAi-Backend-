from datetime import date

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .helper.calories import calculate_calories
from .helper.week_date_helper import get_week_range
from .models import UserProfile, WorkoutLog, WorkoutPlan
from .serializers import WorkoutPlanSerializer
from .tasks import generate_weekly_workout_task


class GenerateWorkoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        workout_type = request.data.get("workout_type")

        if workout_type not in ["cardio", "strength", "mixed"]:
            return Response(
                {"error": "Invalid workout_type"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        week_start, week_end = get_week_range(date.today())

        plan = WorkoutPlan.objects.filter(
            user_id=request.user.id,
            week_start=week_start,
        ).first()

        # 🚫 Block if pending
        if plan and plan.status == "pending":
            return Response(
                {"status": "pending"},
                status=status.HTTP_409_CONFLICT,
            )

        # 🚫 Block if already ready
        if plan and plan.status == "ready":
            return Response(
                {"status": "ready"},
                status=status.HTTP_409_CONFLICT,
            )

        # ✅ First click OR retry after failure
        if not plan:
            WorkoutPlan.objects.create(
                user_id=request.user.id,
                week_start=week_start,
                week_end=week_end,
                goal="",
                workout_type=workout_type,
                sessions={},
                estimated_weekly_calories=0,
                status="pending",
            )
        else:
            plan.status = "pending"
            plan.save(update_fields=["status"])

        generate_weekly_workout_task.delay(
            str(request.user.id),
            workout_type,
        )

        return Response(
            {"status": "queued"},
            status=status.HTTP_202_ACCEPTED,
        )


class GetCurrentWorkoutView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        week_start, _ = get_week_range(date.today())

        plan = WorkoutPlan.objects.filter(
            user_id=request.user.id,
            week_start=week_start,
        ).first()

        if not plan:
            return Response(
                {"status": "idle"},
                status=status.HTTP_200_OK,
            )

        if plan.status == "pending":
            return Response(
                {"status": "pending"},
                status=status.HTTP_200_OK,
            )

        if plan.status == "failed":
            return Response(
                {"status": "failed"},
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "status": "ready",
                "plan": WorkoutPlanSerializer(plan).data,
            },
            status=status.HTTP_200_OK,
        )


class LogWorkoutExerciseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.user.id
        today = date.today()

        exercise_name = request.data.get("exercise_name")
        duration_sec = int(request.data.get("duration_sec", 0))
        intensity = request.data.get("intensity")
        status_value = request.data.get("status")  # completed | skipped

        if not exercise_name:
            return Response(
                {"error": "exercise_name required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if status_value not in ["completed", "skipped"]:
            return Response(
                {"error": "Invalid status"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        week_start, _ = get_week_range(today)

        plan = WorkoutPlan.objects.filter(
            user_id=user_id,
            week_start=week_start,
        ).first()

        if not plan:
            return Response(
                {"error": "No workout plan for this week"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 🚫 Block repeated logging for same exercise/day
        if WorkoutLog.objects.filter(
            user_id=user_id,
            date=today,
            exercise_name=exercise_name,
        ).exists():
            return Response(
                {"error": "Exercise already logged for today"},
                status=status.HTTP_409_CONFLICT,
            )

        calories = 0

        if status_value == "completed":
            profile = UserProfile.objects.get(user_id=user_id)

            calories = calculate_calories(
                duration_sec=duration_sec,
                weight_kg=profile.weight_kg,
                intensity=intensity,
            )

        WorkoutLog.objects.create(
            user_id=user_id,
            date=today,
            exercise_name=exercise_name,
            duration_sec=duration_sec if status_value == "completed" else 0,
            calories_burnt=calories,
            status=status_value,
        )

        return Response(
            {
                "status": "logged",
                "exercise": exercise_name,
                "calories_burnt": calories,
            },
            status=status.HTTP_201_CREATED,
        )


class GetTodayWorkoutLogsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        today = date.today()

        logs = WorkoutLog.objects.filter(
            user_id=user_id,
            date=today,
        ).values("exercise_name", "status")

        # Map: { exercise_name: status }
        result = {log["exercise_name"]: log["status"] for log in logs}

        return Response(result, status=status.HTTP_200_OK)
