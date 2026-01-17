# user_app/tasks.py
from celery import shared_task
from chat.models import ChatRoom

from .helper.ai_client import estimate_nutrition
from .models import MealLog, TrainerBooking
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

import requests
from celery import shared_task


from user_service.firebase.push import send_push
from .models import UserProfile


from .helper.ai_client import generate_diet_plan, AIServiceError
from .helper.ai_payload import build_payload_from_profile
from .models import DietPlan, UserProfile


import json
import boto3
from celery import shared_task
from django.utils import timezone
from django.conf import settings

from .models import UserProfile

import requests
from django.conf import settings

from django.core.cache import cache
#webhook event with celery for notifications to trainer side


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=5,
    retry_kwargs={"max_retries": 5},
)
def emit_webhook(self, *,event, payload):
    """
    General webhook emitter for all cross-service events
    """
    requests.post(
        f"{settings.TRAINER_SERVICE_URL}/api/v1/trainer/internal/notification/",
        json={
            "event": event,
            "payload": payload,
        },
        timeout=3,
    )

    
# user side notification using webhook


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=5,
    retry_kwargs={"max_retries": 3},
)
def send_user_notification(
    self,
    *,
    user_id,
    title,
    body,
    data=None,
):
    profile = UserProfile.objects.filter(user_id=user_id).first()

    if not profile or not profile.fcm_token:
        return

    send_push(
        token=profile.fcm_token,
        title=title,
        body=body,
        data=data,
    )



# nutrition task below(extra meal, custom meal)

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

    # 🔔 USER NOTIFICATION (PROGRESS UPDATED)
    send_user_notification.delay(
        user_id=str(meal.user_id),
        title="Progress Updated 🍽️",
        body="Check your progress!",
        data={
            "type": "MEAL_NUTRITION_UPDATED & PROGRESS_UPDATED",
            "meal_log_id": str(meal.id),
        },
    )



# workout task below

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
    week_start, week_end = get_week_range(date.today())

    plan = WorkoutPlan.objects.get(
        user_id=user_id,
        week_start=week_start,
    )

    try:
        # -------------------------
        # SAFE ZONE START
        # -------------------------
        profile = UserProfile.objects.get(user_id=user_id)

        if not profile.profile_completed:
            raise ValueError("Profile not completed")

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
        normalize_durations(exercises, min_duration, max_duration)

        validate_ai_workout(
            ai_result,
            exercise_count,
            min_duration,
            max_duration,
        )

        total_daily = Decimal("0")
        for ex in exercises:
            calories = calculate_calories(
                ex["duration_sec"],
                profile.weight_kg,
                ex["intensity"],
            )
            ex["estimated_calories"] = int(calories)
            total_daily += calories

        # -------------------------
        # SAVE SUCCESS
        # -------------------------
        WorkoutPlan.objects.filter(
            user_id=user_id,
            week_start=week_start,
        ).update(
            week_end=week_end,
            goal=profile.goal,
            workout_type=workout_type,
            sessions=ai_result,
            estimated_weekly_calories=int(total_daily * Decimal("7")),
            status="ready",
        )
        send_user_notification.delay(
            user_id=str(user_id),
            title="Workout Plan Ready 💪",
            body="Your new workout plan has been generated. Time to train!",
            data={
                "type": "WORKOUT_PLAN_READY",
                "week_start": str(week_start),
            },
        )

        return "created"

    except Exception as e:
        # -------------------------
        # SAVE FAILURE
        # -------------------------
        WorkoutPlan.objects.filter(
            user_id=user_id,
            week_start=week_start,
        ).update(status="failed")

        raise e



# diet plan task below

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

    send_user_notification.delay(
        user_id=str(plan.user_id),
        title="Diet Plan Ready 🥗",
        body="Your personalized diet plan is ready to follow.",
        data={
            "type": "DIET_PLAN_READY",
            "plan_id": str(plan.id),
        },
    )



# premium handling tasks below



def fetch_email_from_auth(user_id):
    response = requests.post(
        f"{settings.AUTH_SERVICE_URL}/api/v1/auth/internal/users/email/",
        json={"user_id": str(user_id)},
        timeout=10,
    )

    response.raise_for_status()
    return response.json()["email"]



@shared_task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=5,
)
def handle_expired_premium_users(self):
    now = timezone.now()

    expired_profiles = list(
        UserProfile.objects.filter(
            is_premium=True,
            premium_expires_at__lt=now,
        )
    )

    if not expired_profiles:
        return "No expired premium users"

    #  Bulk update DB (FAST)
    for profile in expired_profiles:
        profile.is_premium = False
        profile.premium_expires_at = None

    UserProfile.objects.bulk_update(
        expired_profiles,
        fields=["is_premium", "premium_expires_at"],
    )

    for profile in expired_profiles:
        cache_key = f"profile:{profile.user_id}:v1"
        cache.delete(cache_key)

    for profile in expired_profiles:
        send_user_notification.delay(
            user_id=str(profile.user_id),
            title="Premium Expired ⏳",
            body="Your premium subscription has expired. Renew to continue premium features.",
            data={
                "type": "PREMIUM_EXPIRED",
            },
        )

    #  External calls
    sqs = boto3.client("sqs", region_name=settings.AWS_REGION)

    processed = 0
    for profile in expired_profiles:
        email = fetch_email_from_auth(profile.user_id)

        sqs.send_message(
            QueueUrl=settings.AWS_PREMIUM_EXPIRED_QUEUE_URL,
            MessageBody=json.dumps({"email": email}),
        )

        processed += 1

    return f"{processed} users downgraded & notified"





#celery task to handle booking decision from trainer
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

    if action not in ("approve", "reject"):
        return

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

        if booking.status != TrainerBooking.STATUS_PENDING:
            return

        # -------------------------
        # APPLY STATE CHANGE
        # -------------------------
        if action == "approve":
            booking.status = TrainerBooking.STATUS_APPROVED
            booking.save(update_fields=["status"])

            # Ensure only one active room
            ChatRoom.objects.filter(
                user_id=user_id,
                trainer_user_id=trainer_user_id,
                is_active=True,
            ).update(is_active=False)

            room = ChatRoom.objects.filter(
                user_id=user_id,
                trainer_user_id=trainer_user_id,
                is_active=False,
            ).first()

            if room:
                room.is_active = True
                room.save(update_fields=["is_active"])
            else:
                ChatRoom.objects.create(
                    user_id=user_id,
                    trainer_user_id=trainer_user_id,
                    is_active=True,
                )

        elif action == "reject":
            booking.status = TrainerBooking.STATUS_REJECTED
            booking.save(update_fields=["status"])

        # -------------------------
        # 🔔 NOTIFY USER (AFTER COMMIT)
        # -------------------------
        def notify_user():
            if action == "approve":
                send_user_notification.delay(
                    user_id=str(user_id),
                    title="Trainer Approved 🎉",
                    body="Your trainer has approved your booking. You can now chat or call.",
                    data={
                        "type": "BOOKING_APPROVED",
                        "booking_id": str(booking_id),
                    },
                )

            elif action == "reject":
                send_user_notification.delay(
                    user_id=str(user_id),
                    title="Booking Rejected ❌",
                    body="Your trainer has rejected the booking.",
                    data={
                        "type": "BOOKING_REJECTED",
                        "booking_id": str(booking_id),
                    },
                )

        transaction.on_commit(notify_user)