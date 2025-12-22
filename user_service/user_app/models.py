import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

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


class DietPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    
    daily_calories = models.IntegerField()
    macros = models.JSONField()
    meals = models.JSONField()
    
    version = models.CharField(max_length=20, default="diet_v1")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user_id"]),
        ]



class MealLog(models.Model):
    MEAL_CHOICES = (
        ("breakfast", "Breakfast"),
        ("lunch", "Lunch"),
        ("dinner", "Dinner"),
    )

    SOURCE_CHOICES = (
        ("plan", "AI Plan"),
        ("custom", "Custom"),
        ("skipped", "Skipped"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    date = models.DateField()

    meal_type = models.CharField(max_length=10, choices=MEAL_CHOICES)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)

    items = models.JSONField(blank=True, null=True)
    calories = models.IntegerField(default=0)
    protein = models.IntegerField(default=0)
    carbs = models.IntegerField(default=0)
    fat = models.IntegerField(default=0)

    class Meta:
        unique_together = ("user_id", "date", "meal_type")
        indexes = [
            models.Index(fields=["user_id", "date"]),
        ]


class WeightLog(models.Model):
    user_id = models.UUIDField()
    weight_kg = models.FloatField()
    logged_at = models.DateField()


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
