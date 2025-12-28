from datetime import date, timedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import MealLog
from .helper.diet_workout_progress_helpers import (
    daily_progress,
    weekly_progress,
    monthly_progress,
)
from .helper.week_date_helper import get_week_range

class DailyProgressView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.user.id

        date_str = request.query_params.get("date")
        try:
            day = date.fromisoformat(date_str) if date_str else date.today()
        except ValueError:
            return Response(
                {"detail": "Invalid date format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data = daily_progress(user_id, day)
        except Exception:
            return Response(
                {"detail": "Failed to generate daily progress"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"data": data}, status=status.HTTP_200_OK)


class WeeklyProgressView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.user.id

        week_start_str = request.query_params.get("week_start")
        try:
            if week_start_str:
                raw_date = date.fromisoformat(week_start_str)
            else:
                raw_date = date.today()

            week_start, _ = get_week_range(raw_date)

        except ValueError:
            return Response(
                {"detail": "Invalid week_start format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data = weekly_progress(user_id, week_start)
        except Exception:
            return Response(
                {"detail": "Failed to generate weekly progress"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"data": data}, status=status.HTTP_200_OK)


class MonthlyProgressView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.user.id

        try:
            year = int(request.query_params.get("year", date.today().year))
            month = int(request.query_params.get("month", date.today().month))
        except ValueError:
            return Response(
                {"detail": "Invalid year or month"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if month < 1 or month > 12:
            return Response(
                {"detail": "Month must be between 1 and 12"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data = monthly_progress(user_id, year, month)
        except Exception:
            return Response(
                {"detail": "Failed to generate monthly progress"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"data": data}, status=status.HTTP_200_OK)



#daily meal status view for frontend rendering 

class TodayMealStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = date.today()

        logs = MealLog.objects.filter(
            user_id=request.user.id,
            date=today,
        ).exclude(meal_type="other")

        status = {
            "breakfast": None,
            "lunch": None,
            "dinner": None,
        }

        for log in logs:
            status[log.meal_type] = log.source

        return Response({
            "date": today,
            "meals": status,
        })