# user_app/tasks.py
from celery import shared_task
from .models import MealLog
from .helper.ai_client import estimate_nutrition


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=10,
    retry_kwargs={"max_retries": 3},
)
def estimate_nutrition_task(self, meal_log_id):
    meal = MealLog.objects.get(id=meal_log_id)

    # idempotent
    if meal.calories > 0:
        return

    result = estimate_nutrition(", ".join(meal.items))
    total = result["total"]

    meal.calories = total.get("calories", 0)
    meal.protein = total.get("protein", 0)
    meal.carbs = total.get("carbs", 0)
    meal.fat = total.get("fat", 0)
    meal.save()


from datetime import date

from .models import UserProfile
from .models import WorkoutPlan  # adjust if model lives elsewhere

from .helper.week_date_helper import get_week_range
from .helper.ai_client_workout import request_ai_workout
from .helper.ai_payload import build_workout_ai_payload
from .helper.calories import calculate_calories
from .helper.workout_validators import validate_ai_workout
from django.db import transaction
from decimal import Decimal

@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_kwargs={"max_retries": 3},
)
def generate_weekly_workout_task(self, user_id, workout_type):
    profile = UserProfile.objects.get(user_id=user_id)

    if not profile.profile_completed:
        raise ValueError("Profile not completed")

    week_start, week_end = get_week_range(date.today())

    # Hard guard: never generate duplicate weekly plans
    if WorkoutPlan.objects.filter(
        user_id=user_id,
        week_start=week_start,
    ).exists():
        return "already_exists"

    # Rules by experience
    if profile.exercise_experience == "beginner":
        exercise_count = 5
        min_duration, max_duration = 30, 40
    elif profile.exercise_experience == "intermediate":
        exercise_count = 6
        min_duration, max_duration = 35, 50
    else:
        exercise_count = 7
        min_duration, max_duration = 45, 60

    payload = build_workout_ai_payload(
        profile=profile,
        workout_type=workout_type,
        exercise_count=exercise_count,
        min_duration=min_duration,
        max_duration=max_duration,
    )

    ai_result = request_ai_workout(payload)

    validate_ai_workout(
        ai_result,
        exercise_count,
        min_duration,
        max_duration,
    )

    # From here on, everything must succeed or nothing is saved
    with transaction.atomic():
        total_daily = Decimal("0")

        for ex in ai_result["sessions"][0]["exercises"]:
            calories = calculate_calories(
                ex["duration_sec"],
                profile.weight_kg,
                ex["intensity"],
            )

            ex["estimated_calories"] = int(calories)  # JSON-safe
            total_daily += calories

        WorkoutPlan.objects.create(
            user_id=user_id,
            week_start=week_start,
            week_end=week_end,
            goal=profile.goal,
            workout_type=workout_type,
            sessions=ai_result,
            estimated_weekly_calories=total_daily * Decimal("7"),
        )

    return "created"

