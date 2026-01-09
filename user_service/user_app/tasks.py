# user_app/tasks.py
from celery import shared_task
from chat.models import ChatRoom

from .helper.ai_client import estimate_nutrition
from .models import MealLog, TrainerBooking


# ----------------------------
# nutrition task below(extra meal, custom meal)
# ----------------------------
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


# ----------------------------
# workout task below
# ----------------------------


import sys
from datetime import date
from decimal import Decimal

from celery import shared_task
from django.db import transaction
from requests.exceptions import ConnectionError, Timeout

from .helper.ai_client_workout import request_ai_workout
from .helper.ai_payload import build_workout_ai_payload
from .helper.calories import calculate_calories
from .helper.week_date_helper import get_week_range
from .helper.workout_validators import validate_ai_workout
from .models import UserProfile, WorkoutPlan


def normalize_durations(exercises, min_minutes, max_minutes):
    target_seconds = ((min_minutes + max_minutes) // 2) * 60
    per_exercise = target_seconds // len(exercises)

    for ex in exercises:
        ex["duration_sec"] = per_exercise


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, Timeout),
    retry_kwargs={"max_retries": 3},
)
def generate_weekly_workout_task(self, user_id, workout_type):
    profile = UserProfile.objects.get(user_id=user_id)

    if not profile.profile_completed:
        raise ValueError("Profile not completed")

    week_start, week_end = get_week_range(date.today())

    if WorkoutPlan.objects.filter(
        user_id=user_id,
        week_start=week_start,
    ).exists():
        return "already_exists"

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

    sys.stderr.write("\n🔥 WORKOUT PAYLOAD 🔥\n")
    sys.stderr.write(str(payload) + "\n")
    sys.stderr.flush()

    ai_result = request_ai_workout(payload)

    exercises = ai_result["sessions"][0]["exercises"]

    # 🔧 FIX AI MATH (THIS SOLVES YOUR ERROR)
    normalize_durations(exercises, min_duration, max_duration)

    validate_ai_workout(
        ai_result,
        exercise_count,
        min_duration,
        max_duration,
    )

    with transaction.atomic():
        total_daily = Decimal("0")

        for ex in exercises:
            calories = calculate_calories(
                ex["duration_sec"],
                profile.weight_kg,
                ex["intensity"],
            )

            ex["estimated_calories"] = int(calories)
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


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=3,
    retry_kwargs={"max_retries": 5},
)
def handle_booking_decision(self, payload):
    if payload.get("event") != "BOOKING_DECIDED":
        return

    booking_id = payload.get("booking_id")
    trainer_user_id = payload.get("trainer_user_id")
    user_id = payload.get("user_id")
    action = payload.get("action", "").lower()

    if not booking_id or not trainer_user_id or not user_id:
        raise ValueError("Invalid booking decision payload")

    with transaction.atomic():
        booking = (
            TrainerBooking.objects
            .select_for_update()
            .filter(
                id=booking_id,
                trainer_user_id=trainer_user_id,
            )
            .first()
        )

        if not booking:
            return

        # ✅ Idempotency guard
        if booking.status != TrainerBooking.STATUS_PENDING:
            return

        if action == "approve":
            booking.status = TrainerBooking.STATUS_APPROVED
            booking.save(update_fields=["status"])

            ChatRoom.objects.get_or_create(
                user_id=user_id,
                trainer_user_id=trainer_user_id,
                defaults={"is_active": True},
            )

        elif action == "reject":
            booking.status = TrainerBooking.STATUS_REJECTED
            booking.save(update_fields=["status"])



from .helper.ai_client import generate_diet_plan, AIServiceError
from .helper.ai_payload import build_payload_from_profile
from .models import DietPlan, UserProfile


@shared_task(
    bind=True,
    autoretry_for=(AIServiceError, Exception),
    retry_backoff=10,
    retry_kwargs={"max_retries": 3},
)
def generate_diet_plan_task(self, plan_id):
    plan = DietPlan.objects.select_for_update().get(id=plan_id)

    # Idempotency guard
    if plan.status != "pending":
        return

    profile = UserProfile.objects.get(user_id=plan.user_id)
    payload = build_payload_from_profile(profile)

    ai_response = generate_diet_plan(payload)

    plan.daily_calories = ai_response["daily_calories"]
    plan.macros = ai_response["macros"]
    plan.meals = ai_response["meals"]
    plan.version = ai_response.get("version", "diet_v1")
    plan.status = "ready"
    plan.save()



import json
import boto3
from celery import shared_task
from django.utils import timezone
from django.conf import settings

from .models import UserProfile


@shared_task(bind=True, max_retries=3)
def handle_expired_premium_users(self):
    now = timezone.now()

    expired_profiles = UserProfile.objects.filter(
        is_premium=True,
        premium_expires_at__lt=now,
    )

    if not expired_profiles.exists():
        return "No expired premium users"

    sqs = boto3.client(
        "sqs",
        region_name=settings.AWS_REGION,
    )

    processed = 0

    for profile in expired_profiles:
        # 1️⃣ Downgrade user (SOURCE OF TRUTH)
        profile.is_premium = False
        profile.save(update_fields=["is_premium"])

        # 2️⃣ Send email job
        sqs.send_message(
            QueueUrl=settings.AWS_PREMIUM_EXPIRED_QUEUE_URL,
            MessageBody=json.dumps({
                "email": profile.user.email,
            }),
        )

        processed += 1

    return f"{processed} users downgraded & notified"