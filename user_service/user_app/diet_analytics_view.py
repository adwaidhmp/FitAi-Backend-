from datetime import date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

from .helper.diet_analytics_helper import (
    get_daily_analytics,
    get_weekly_analytics,
    get_monthly_analytics,
)


class DailyDietAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        date_str = request.query_params.get("date")

        if date_str:
            try:
                target_date = date.fromisoformat(date_str)
            except ValueError:
                return Response(
                    {"detail": "Invalid date format (YYYY-MM-DD)"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            target_date = date.today()

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
        except ValueError:
            return Response(
                {"detail": "year and month must be integers"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        analytics = get_monthly_analytics(
            user_id=request.user.id,
            year=year,
            month=month,
        )

        return Response(analytics, status=status.HTTP_200_OK)
