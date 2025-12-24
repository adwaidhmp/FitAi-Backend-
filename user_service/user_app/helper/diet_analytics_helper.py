from datetime import date
from calendar import monthrange
from django.db.models import Sum

from user_app.models import DietPlan, MealLog, WeightLog


# =====================================================
# DAILY ANALYTICS
# =====================================================

def get_daily_calorie_summary(user_id, target_date: date):
    meals = MealLog.objects.filter(
        user_id=user_id,
        date=target_date,
    )

    consumed = meals.aggregate(
        total=Sum("calories")
    )["total"] or 0

    plan = DietPlan.objects.filter(
        user_id=user_id,
        week_start__lte=target_date,
        week_end__gte=target_date,
    ).first()

    planned = plan.daily_calories if plan else 0
    difference = consumed - planned

    return {
        "planned_calories": planned,
        "consumed_calories": consumed,
        "difference": difference,
        "meals": meals,
    }


def get_daily_reason(meals, difference):
    extra_meals = meals.filter(source="extra").count()
    skipped_meals = meals.filter(source="skipped").count()
    custom_meals = meals.filter(source="custom").count()

    if difference > 200:
        if extra_meals > 0:
            return "High calories due to extra meals"
        if custom_meals > 0:
            return "High calories due to custom meals"
        return "High calorie intake"

    if difference < -200:
        if skipped_meals > 0:
            return "Low calories due to skipped meals"
        return "Low calorie intake"

    return "Calories within target range"


def get_daily_analytics(user_id, target_date: date):
    data = get_daily_calorie_summary(user_id, target_date)
    reason = get_daily_reason(data["meals"], data["difference"])

    status = "normal"
    if data["difference"] > 200:
        status = "high"
    elif data["difference"] < -200:
        status = "low"

    return {
        "date": target_date,
        "planned_calories": data["planned_calories"],
        "consumed_calories": data["consumed_calories"],
        "difference": data["difference"],
        "status": status,
        "reason": reason,
    }


# =====================================================
# WEEKLY ANALYTICS
# =====================================================

def get_weekly_calorie_average(user_id, week_start, week_end):
    meals = MealLog.objects.filter(
        user_id=user_id,
        date__range=(week_start, week_end),
    )

    daily_totals = (
        meals.values("date")
        .annotate(total=Sum("calories"))
    )

    if not daily_totals:
        return 0

    return sum(d["total"] for d in daily_totals) / len(daily_totals)


def get_weekly_weight_change(user_id):
    logs = (
        WeightLog.objects
        .filter(user_id=user_id)
        .order_by("-logged_at")[:2]
    )

    if len(logs) < 2:
        return None

    return logs[0].weight_kg - logs[1].weight_kg


def get_weekly_reason(weight_change, avg_calories, planned_calories):
    if weight_change is None:
        return "Not enough weight data"

    if weight_change > 0:
        if avg_calories > planned_calories:
            return "Weight increased due to calorie surplus"
        return "Weight increased possibly due to water retention"

    if weight_change < 0:
        if avg_calories < planned_calories:
            return "Weight decreased due to calorie deficit"
        return "Weight decreased despite calorie intake"

    return "No significant weight change"


def get_weekly_analytics(user_id):
    latest_plan = (
        DietPlan.objects
        .filter(user_id=user_id)
        .order_by("-week_start")
        .first()
    )

    if not latest_plan:
        return None

    avg_calories = get_weekly_calorie_average(
        user_id,
        latest_plan.week_start,
        latest_plan.week_end,
    )

    weight_change = get_weekly_weight_change(user_id)
    reason = get_weekly_reason(
        weight_change,
        avg_calories,
        latest_plan.daily_calories,
    )

    return {
        "week_start": latest_plan.week_start,
        "week_end": latest_plan.week_end,
        "planned_daily_calories": latest_plan.daily_calories,
        "avg_daily_calories": round(avg_calories),
        "weight_change": weight_change,
        "reason": reason,
    }


# =====================================================
# MONTHLY ANALYTICS
# =====================================================

def get_monthly_progress(user_id, year: int, month: int):
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])

    meals = MealLog.objects.filter(
        user_id=user_id,
        date__range=(start, end),
    )

    total_calories = meals.aggregate(
        total=Sum("calories")
    )["total"] or 0

    days_logged = meals.values("date").distinct().count()
    avg_daily_calories = (
        total_calories / days_logged if days_logged else 0
    )

    weights = (
        WeightLog.objects
        .filter(user_id=user_id, logged_at__range=(start, end))
        .order_by("logged_at")
    )

    if weights.count() >= 2:
        weight_change = weights.last().weight_kg - weights.first().weight_kg
    else:
        weight_change = 0

    return avg_daily_calories, weight_change


def get_monthly_reason(weight_change, avg_calories, planned_calories):
    if weight_change < 0:
        return "Consistent calorie deficit resulted in fat loss"
    if weight_change > 0:
        return "Consistent calorie surplus resulted in weight gain"
    return "Weight maintained throughout the month"


def get_monthly_analytics(user_id, year: int, month: int):
    avg_calories, weight_change = get_monthly_progress(
        user_id, year, month
    )

    plan = (
        DietPlan.objects
        .filter(user_id=user_id, week_start__year=year, week_start__month=month)
        .first()
    )

    planned_calories = plan.daily_calories if plan else 0
    reason = get_monthly_reason(
        weight_change, avg_calories, planned_calories
    )

    return {
        "year": year,
        "month": month,
        "avg_daily_calories": round(avg_calories),
        "planned_daily_calories": planned_calories,
        "weight_change": weight_change,
        "reason": reason,
    }
