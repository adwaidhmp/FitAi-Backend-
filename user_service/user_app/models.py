import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

# ---------- choices ----------
GENDER_CHOICES = [
    ("male", "Male"),
    ("female", "Female"),
    ("other", "Other"),
]

GOAL_CHOICES = [
    ("maintenance", "Maintenance"),
    ("bulking", "Bulking"),
    ("cutting", "Cutting / Fat loss"),
    ("recomposition", "Body Recomposition"),
]

BODY_TYPE_CHOICES = [
    ("ectomorph", "Ectomorph"),
    ("mesomorph", "Mesomorph"),
    ("endomorph", "Endomorph"),
]

ACTIVITY_LEVEL_CHOICES = [
    ("sedentary", "Sedentary"),
    ("light", "Lightly active"),
    ("moderate", "Moderately active"),
    ("active", "Active"),
    ("very_active", "Very active"),
]

EXERCISE_EXPERIENCE_CHOICES = [
    ("none", "None"),
    ("beginner", "Beginner"),
    ("intermediate", "Intermediate"),
    ("advanced", "Advanced"),
]


# ---------- Profile & long-term user info ----------
class UserProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(
        unique=True,
        help_text="UUID from auth_service User",
    )

    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=16, choices=GENDER_CHOICES, blank=True)
    height_cm = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(30), MaxValueValidator(300)],
    )
    weight_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(2), MaxValueValidator(500)],
    )
    target_weight_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(2), MaxValueValidator(500)],
    )
    goal = models.CharField(max_length=32, choices=GOAL_CHOICES, blank=True)
    body_type = models.CharField(max_length=32, choices=BODY_TYPE_CHOICES, blank=True)
    activity_level = models.CharField(
        max_length=32, choices=ACTIVITY_LEVEL_CHOICES, blank=True
    )
    exercise_experience = models.CharField(
        max_length=32, choices=EXERCISE_EXPERIENCE_CHOICES, blank=True
    )

    diet_constraints = models.JSONField(default=dict, blank=True)
    allergies = models.JSONField(default=list, blank=True)
    medical_conditions = models.JSONField(default=list, blank=True)
    supplements = models.JSONField(default=list, blank=True)
    preferred_equipment = models.JSONField(default=list, blank=True)

    notes = models.TextField(blank=True)

    is_premium = models.BooleanField(default=False)
    premium_expires_at = models.DateTimeField(null=True, blank=True)
    profile_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "user_profile"
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["goal"]),
            models.Index(fields=["is_premium"]),
        ]

    def __str__(self):
        return f"Profile {self.user_id}"


#premium model
class PremiumPlan(models.Model):
    PLAN_CHOICES = [
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
    ]

    plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        unique=True,
    )
    price = models.PositiveIntegerField(help_text="Price in INR")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "premium_plan"

    def __str__(self):
        return f"{self.plan} - ₹{self.price}"

    @property
    def duration_days(self):
        return {
            "weekly": 7,
            "monthly": 30,
        }.get(self.plan, 0)



# Trainer booking model

class TrainerBooking(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user_id = models.UUIDField()
    trainer_user_id = models.UUIDField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["trainer_user_id"]),
            models.Index(fields=["user_id"]),
        ]

    def __str__(self):
        return f"{self.user_id} → {self.trainer_user_id} ({self.status})"


# Ai deit generation model


class DietPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()

    week_start = models.DateField()
    week_end = models.DateField()

    # ⬇️ Filled asynchronously
    daily_calories = models.IntegerField(null=True, blank=True)
    macros = models.JSONField(null=True, blank=True)
    meals = models.JSONField(null=True, blank=True)

    # ⬇️ Async state
    status = models.CharField(
        max_length=10,
        choices=(
            ("pending", "Pending"),
            ("ready", "Ready"),
            ("failed", "Failed"),
        ),
        default="pending",
    )

    version = models.CharField(max_length=20, default="diet_v1")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "week_start"],
                name="unique_user_week_plan",
            )
        ]


class MealLog(models.Model):
    MEAL_TYPES = (
        ("breakfast", "Breakfast"),
        ("lunch", "Lunch"),
        ("dinner", "Dinner"),
        ("other", "Other"),
    )

    SOURCE_TYPES = (
        ("planned", "Planned"),
        ("custom", "Custom"),
        ("skipped", "Skipped"),
        ("extra", "Extra"),
    )

    user_id = models.UUIDField()
    date = models.DateField()
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPES)
    source = models.CharField(max_length=20, choices=SOURCE_TYPES)

    items = models.JSONField(null=True, blank=True)

    calories = models.PositiveIntegerField(default=0)
    protein = models.FloatField(default=0)
    carbs = models.FloatField(default=0)
    fat = models.FloatField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "date", "meal_type"],
                condition=~Q(meal_type="other"),
                name="unique_main_meal_per_user_per_day",
            )
        ]


class WeightLog(models.Model):
    user_id = models.UUIDField()
    weight_kg = models.FloatField()
    logged_at = models.DateField()

    class Meta:
        indexes = [
            models.Index(fields=["user_id", "logged_at"]),
        ]


# Ai workout model


class WorkoutPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user_id = models.UUIDField(db_index=True)

    week_start = models.DateField(db_index=True)
    week_end = models.DateField(db_index=True)
    
    goal = models.CharField(max_length=32)
    workout_type = models.CharField(
        max_length=16,
        choices=[("cardio", "Cardio"), ("strength", "Strength"), ("mixed", "Mixed")],
    )

    sessions = models.JSONField()
    estimated_weekly_calories = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=10,
        choices=[
            ("pending", "Pending"),
            ("ready", "Ready"),
            ("failed", "Failed"),
        ],
        default="pending",
    )

    class Meta:
        db_table = "workout_plan"
        unique_together = ("user_id", "week_start")

    def __str__(self):
        return f"WorkoutPlan {self.user_id} {self.week_start}"


class WorkoutLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user_id = models.UUIDField(db_index=True)
    date = models.DateField(db_index=True)

    exercise_name = models.CharField(max_length=128)
    duration_sec = models.PositiveIntegerField(default=0)
    calories_burnt = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=16,
        choices=[("completed", "Completed"), ("skipped", "Skipped")],
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user_id", "date", "exercise_name")
        db_table = "workout_log"
