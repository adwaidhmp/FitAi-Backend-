from datetime import date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from .models import MealLog

from .helper.diet_analytics_helper import (
    get_daily_analytics,
    get_weekly_analytics,
    get_monthly_analytics,
)


class DailyDietAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        date_str = request.query_params.get("date")

        try:
            target_date = (
                date.fromisoformat(date_str)
                if date_str
                else date.today()
            )
        except ValueError:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        analytics = get_daily_analytics(
            user_id=request.user.id,
            target_date=target_date,
        )

        return Response(analytics, status=status.HTTP_200_OK)


class WeeklyDietAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        analytics = get_weekly_analytics(
            user_id=request.user.id
        )

        if not analytics:
            return Response(
                {"detail": "Not enough data for weekly analytics"},
                status=status.HTTP_200_OK,
            )

        return Response(analytics, status=status.HTTP_200_OK)



class MonthlyDietAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        year = request.query_params.get("year")
        month = request.query_params.get("month")

        if not year or not month:
            return Response(
                {"detail": "year and month are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            year = int(year)
            month = int(month)
            if month < 1 or month > 12:
                raise ValueError
        except ValueError:
            return Response(
                {"detail": "Invalid year or month"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        analytics = get_monthly_analytics(
            user_id=request.user.id,
            year=year,
            month=month,
        )

        return Response(analytics, status=status.HTTP_200_OK)


#daily meal status view for frontend rendering 

class TodayMealStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

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