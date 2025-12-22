from datetime import date
from calendar import monthrange
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from datetime import date, timedelta
from .models import MealLog, DietPlan, WeightLog


# 1️⃣ DAILY CALORIE GRAPH API
class DailyCaloriesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = date.today()

        meals = MealLog.objects.filter(
            user_id=request.user.id,
            date=today,
        )

        total = meals.aggregate(
            calories=Sum("calories")
        )["calories"] or 0

        return Response({
            "date": today,
            "calories": total,
        })
    
# 2️⃣ WEEKLY PROGRESS API
class WeeklyProgressView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = date.today()
        start = today - timedelta(days=6)

        meals = MealLog.objects.filter(
            user_id=request.user.id,
            date__range=[start, today],
        )

        # if not meals.exists():
        #     return Response(
        #         {"detail": "No meals logged this week"},
        #         status=404,
        #     )

        plan = DietPlan.objects.filter(
            user_id=request.user.id
        ).order_by("-created_at").first()

        weekly_target = plan.daily_calories * 7 if plan else None

        daily_stats = {}

        for m in meals:
            day = m.date.isoformat()
            if day not in daily_stats:
                daily_stats[day] = {
                    "calories": 0,
                    "followed": 0,
                }

            daily_stats[day]["calories"] += m.calories
            if m.source == "plan":
                daily_stats[day]["followed"] += 1

        return Response({
            "range": {
                "from": start,
                "to": today,
            },
            "weekly_target_calories": weekly_target,
            "days": daily_stats,
        })
    
# 2️⃣ MONTHLY CALORIE AGGREGATION API
class MonthlyCaloriesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = date.today()
        year = int(request.query_params.get("year", today.year))
        month = int(request.query_params.get("month", today.month))

        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])

        meals = MealLog.objects.filter(
            user_id=request.user.id,
            date__range=[start, end],
        )

        daily = {}
        for m in meals:
            key = m.date.isoformat()
            daily[key] = daily.get(key, 0) + m.calories

        plan = DietPlan.objects.filter(
            user_id=request.user.id,
            created_at__date__lte=end
        ).order_by("-created_at").first()

        monthly_target = plan.daily_calories * len(daily) if plan else None
        monthly_actual = sum(daily.values())

        return Response({
            "month": f"{year}-{month}",
            "daily_calories": daily,
            "monthly_target": monthly_target,
            "monthly_actual": monthly_actual,
        })


# 3️⃣ MONTHLY WEIGHT GRAPH API
class MonthlyWeightView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = date.today()
        year = int(request.query_params.get("year", today.year))
        month = int(request.query_params.get("month", today.month))

        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])

        weights = WeightLog.objects.filter(
            user_id=request.user.id,
            logged_at__range=[start, end],
        ).order_by("logged_at")

        data = [
            {
                "date": w.logged_at,
                "weight": w.weight_kg,
            }
            for w in weights
        ]

        return Response({
            "month": f"{year}-{month}",
            "weights": data,
        })


# 4️⃣ MONTHLY CAUSE ANALYSIS (CUSTOM MEALS)
class MonthlyCauseAnalysisView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = date.today()
        year = int(request.query_params.get("year", today.year))
        month = int(request.query_params.get("month", today.month))

        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])

        custom_meals = MealLog.objects.filter(
            user_id=request.user.id,
            source="custom",
            date__range=[start, end],
        )

        daily_custom = {}
        for m in custom_meals:
            key = m.date.isoformat()
            daily_custom[key] = daily_custom.get(key, 0) + m.calories

        top_days = sorted(
            daily_custom.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        return Response({
            "month": f"{year}-{month}",
            "total_custom_calories": sum(daily_custom.values()),
            "top_custom_days": top_days,
        })