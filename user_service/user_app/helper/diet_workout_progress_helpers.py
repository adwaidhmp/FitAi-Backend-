from calendar import monthrange
from datetime import date, timedelta

from django.db.models import Sum
from user_app.models import DietPlan, MealLog, WeightLog, WorkoutLog, WorkoutPlan

# =====================================================
# CORE UTILITIES
# =====================================================


def _daterange(start, end):
    for i in range((end - start).days + 1):
        yield start + timedelta(days=i)


def _meal_aggregate(user_id, start, end):
    agg = MealLog.objects.filter(
        user_id=user_id,
        date__range=(start, end),
    ).aggregate(
        calories=Sum("calories"),
        protein=Sum("protein"),
        carbs=Sum("carbs"),
        fat=Sum("fat"),
    )

    return {
        "calories": agg["calories"] or 0,
        "protein": round(agg["protein"] or 0, 1),
        "carbs": round(agg["carbs"] or 0, 1),
        "fat": round(agg["fat"] or 0, 1),
    }


def _workout_calories(user_id, start, end):
    return (
        WorkoutLog.objects.filter(
            user_id=user_id,
            date__range=(start, end),
            status="completed",
        ).aggregate(total=Sum("calories_burnt"))["total"]
        or 0
    )


def _skipped_meals(user_id, start, end):
    return MealLog.objects.filter(
        user_id=user_id,
        date__range=(start, end),
        source="skipped",
    ).count()


# =====================================================
# WEIGHT HELPERS (WEEKLY AUTHORITATIVE)
# =====================================================


def _weekly_weight_change(user_id, week_start, week_end):
    prev_log = (
        WeightLog.objects.filter(
            user_id=user_id,
            logged_at__lt=week_start,
        )
        .order_by("-logged_at")
        .first()
    )

    curr_log = (
        WeightLog.objects.filter(
            user_id=user_id,
            logged_at__gte=week_start,
            logged_at__lte=week_end,
        )
        .order_by("-logged_at")
        .last()
    )

    if not prev_log or not curr_log:
        return None, None, None

    return (
        prev_log.weight_kg,
        curr_log.weight_kg,
        round(curr_log.weight_kg - prev_log.weight_kg, 2),
    )


# =====================================================
# REASON LOGIC (HONEST + DATA BACKED)
# =====================================================


def _diet_reason(actual, target, skipped):
    if target is None:
        return "no diet plan available"

    if skipped > 0:
        return "one or more meals skipped"

    if actual > target + 200:
        return "calorie intake exceeded target"

    if actual < target - 200:
        return "calorie intake below target"

    return "calorie intake within target"


def _workout_reason(actual, expected):
    if expected is None:
        return "no workout plan available"

    if actual == 0:
        return "no workouts completed"

    if actual < expected * 0.7:
        return "workout volume lower than planned"

    return "workout target mostly met"


def _weekly_weight_reason(delta, net_calories):
    if delta is None:
        return "no weight logged this week"

    if delta > 0 and net_calories > 0:
        return "weight increased due to calorie surplus"

    if delta < 0 and net_calories < 0:
        return "weight decreased due to calorie deficit"

    if delta > 0 and net_calories <= 0:
        return "weight increased despite calorie control"

    if delta < 0 and net_calories >= 0:
        return "weight decreased despite calorie surplus"

    return "weight stable this week"


# =====================================================
# DAILY PROGRESS
# =====================================================


def daily_progress(user_id, day: date):
    meals = _meal_aggregate(user_id, day, day)
    burn = _workout_calories(user_id, day, day)
    skipped = _skipped_meals(user_id, day, day)

    diet = DietPlan.objects.filter(
        user_id=user_id,
        week_start__lte=day,
        week_end__gte=day,
    ).first()

    expected = diet.daily_calories if diet else None
    net = meals["calories"] - burn

    return {
        "date": day,
        "diet": {
            "calories": meals["calories"],
            "protein": meals["protein"],
            "carbs": meals["carbs"],
            "fat": meals["fat"],
            "target_calories": expected,
            "skipped_meals": skipped,
            "reason": _diet_reason(meals["calories"], expected, skipped),
        },
        "workout": {
            "calories_burnt": burn,
        },
        "net_calories": net,
    }


# =====================================================
# WEEKLY PROGRESS (WEIGHT ANALYSIS HERE)
# =====================================================


def weekly_progress(user_id, week_start: date):
    week_end = week_start + timedelta(days=6)

    meals = _meal_aggregate(user_id, week_start, week_end)
    burn = _workout_calories(user_id, week_start, week_end)
    skipped = _skipped_meals(user_id, week_start, week_end)

    diet = DietPlan.objects.filter(user_id=user_id, week_start=week_start).first()
    workout = WorkoutPlan.objects.filter(user_id=user_id, week_start=week_start).first()

    expected_intake = diet.daily_calories * 7 if diet else None
    expected_burn = workout.estimated_weekly_calories if workout else None

    prev_wt, curr_wt, delta = _weekly_weight_change(user_id, week_start, week_end)

    net = meals["calories"] - burn

    return {
        "week_start": week_start,
        "week_end": week_end,
        "diet": {
            "calories": meals["calories"],
            "protein": meals["protein"],
            "carbs": meals["carbs"],
            "fat": meals["fat"],
            "target_calories": expected_intake,
            "skipped_meals": skipped,
            "reason": _diet_reason(meals["calories"], expected_intake, skipped),
        },
        "workout": {
            "calories_burnt": burn,
            "target_burn": expected_burn,
            "reason": _workout_reason(burn, expected_burn),
        },
        "weight": {
            "previous": prev_wt,
            "current": curr_wt,
            "change_kg": delta,
            "reason": _weekly_weight_reason(delta, net),
        },
        "net_calories": net,
    }


# =====================================================
# MONTHLY PROGRESS (SUMMARY)
# =====================================================


def monthly_progress(user_id, year: int, month: int):
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])

    meals = _meal_aggregate(user_id, start, end)
    burn = _workout_calories(user_id, start, end)
    net = meals["calories"] - burn

    return {
        "month": f"{year}-{month:02d}",
        "diet": {
            "calories": meals["calories"],
            "protein": meals["protein"],
            "carbs": meals["carbs"],
            "fat": meals["fat"],
        },
        "workout": {
            "calories_burnt": burn,
        },
        "net_calories": net,
    }
