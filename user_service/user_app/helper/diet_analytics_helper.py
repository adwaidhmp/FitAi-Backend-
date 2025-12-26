from datetime import date, timedelta
from calendar import monthrange
from django.db.models import Sum

from user_app.models import DietPlan, MealLog, WeightLog


# =====================================================
# DAILY ANALYTICS
# =====================================================

def get_daily_analytics(user_id, target_date: date):
    meals = MealLog.objects.filter(
        user_id=user_id,
        date=target_date,
    )

    totals = meals.aggregate(
        calories=Sum("calories"),
        protein=Sum("protein"),
        carbs=Sum("carbs"),
        fat=Sum("fat"),
    )

    consumed_calories = totals["calories"] or 0

    plan = DietPlan.objects.filter(
        user_id=user_id,
        week_start__lte=target_date,
        week_end__gte=target_date,
    ).first()

    planned_calories = plan.daily_calories if plan else 0
    difference = consumed_calories - planned_calories

    by_meal = (
        meals.values("meal_type")
        .annotate(calories=Sum("calories"))
    )

    by_source = (
        meals.values("source")
        .annotate(calories=Sum("calories"))
    )

    if difference > 200:
        status = "high"
    elif difference < -200:
        status = "low"
    else:
        status = "normal"

    if status == "high":
        reason = "Calorie intake exceeded target"
        if any(m["source"] == "extra" for m in by_source):
            reason = "Excess calories due to extra meals"
        elif any(m["source"] == "custom" for m in by_source):
            reason = "Excess calories due to custom meals"
    elif status == "low":
        reason = "Calorie intake below target"
        if meals.filter(source="skipped").exists():
            reason = "Low calories due to skipped meals"
    else:
        reason = "Calories within target range"

    return {
        "date": target_date,
        "planned_calories": planned_calories,
        "consumed_calories": consumed_calories,
        "difference": difference,
        "status": status,
        "macros": {
            "protein": totals["protein"] or 0,
            "carbs": totals["carbs"] or 0,
            "fat": totals["fat"] or 0,
        },
        "by_meal": {m["meal_type"]: m["calories"] for m in by_meal},
        "by_source": {s["source"]: s["calories"] for s in by_source},
        "reason": reason,
    }


# =====================================================
# WEEKLY ANALYTICS
# =====================================================

def get_weekly_analytics(user_id):
    plan = (
        DietPlan.objects
        .filter(user_id=user_id)
        .order_by("-week_start")
        .first()
    )

    if not plan:
        return None

    meals = MealLog.objects.filter(
        user_id=user_id,
        date__range=(plan.week_start, plan.week_end),
    )

    daily_totals = (
        meals.values("date")
        .annotate(calories=Sum("calories"))
    )

    total_week_calories = sum(d["calories"] for d in daily_totals)
    avg_daily_calories = round(total_week_calories / 7)

    by_source = (
        meals.values("source")
        .annotate(calories=Sum("calories"))
    )

    weight_logs = (
        WeightLog.objects
        .filter(user_id=user_id)
        .order_by("-logged_at")[:2]
    )

    weight_change = None
    if len(weight_logs) == 2:
        weight_change = weight_logs[0].weight_kg - weight_logs[1].weight_kg

    if weight_change is None:
        reason = "Not enough weight data"
    elif weight_change > 0 and avg_daily_calories > plan.daily_calories:
        reason = "Weight increased due to calorie surplus"
    elif weight_change < 0 and avg_daily_calories < plan.daily_calories:
        reason = "Weight decreased due to calorie deficit"
    else:
        reason = "Weight change not clearly linked to calories"

    return {
        "week_start": plan.week_start,
        "week_end": plan.week_end,
        "planned_daily_calories": plan.daily_calories,
        "avg_daily_calories": avg_daily_calories,
        "weight_change": weight_change,
        "by_source": {s["source"]: s["calories"] for s in by_source},
        "reason": reason,
    }


# =====================================================
# MONTHLY ANALYTICS
# =====================================================

def get_monthly_analytics(user_id, year: int, month: int):
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])

    meals = MealLog.objects.filter(
        user_id=user_id,
        date__range=(start, end),
    )

    totals = meals.aggregate(
        calories=Sum("calories"),
        protein=Sum("protein"),
        carbs=Sum("carbs"),
        fat=Sum("fat"),
    )

    days_logged = meals.values("date").distinct().count()
    avg_daily_calories = (
        round((totals["calories"] or 0) / days_logged)
        if days_logged else 0
    )

    plans = DietPlan.objects.filter(
        user_id=user_id,
        week_start__lte=end,
        week_end__gte=start,
    )

    planned_daily_calories = (
        round(sum(p.daily_calories for p in plans) / plans.count())
        if plans.exists() else 0
    )

    weights = (
        WeightLog.objects
        .filter(user_id=user_id, logged_at__range=(start, end))
        .order_by("logged_at")
    )

    weight_change = 0
    if weights.count() >= 2:
        weight_change = weights.last().weight_kg - weights.first().weight_kg

    if weight_change > 0 and avg_daily_calories > planned_daily_calories:
        reason = "Monthly calorie surplus led to weight gain"
    elif weight_change < 0 and avg_daily_calories < planned_daily_calories:
        reason = "Monthly calorie deficit led to weight loss"
    else:
        reason = "Weight remained stable this month"

    return {
        "year": year,
        "month": month,
        "avg_daily_calories": avg_daily_calories,
        "planned_daily_calories": planned_daily_calories,
        "weight_change": weight_change,
        "macros": {
            "protein": totals["protein"] or 0,
            "carbs": totals["carbs"] or 0,
            "fat": totals["fat"] or 0,
        },
        "reason": reason,
    }
