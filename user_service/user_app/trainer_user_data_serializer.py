from rest_framework import serializers

from .models import (
    UserProfile,
    DietPlan,
    MealLog,
    WorkoutPlan,
    WorkoutLog,
    WeightLog,
)

# -------------------------------
# Profile (safe fields only)
# -------------------------------

class TrainerUserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "dob",
            "gender",
            "height_cm",
            "weight_kg",
            "target_weight_kg",
            "goal",
            "activity_level",
            "exercise_experience",
            "body_type",
            "diet_constraints",
            "allergies",
            "preferred_equipment",
            "notes",
        ]


# -------------------------------
# Diet Plan (this week)
# -------------------------------

class TrainerDietPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = DietPlan
        fields = [
            "week_start",
            "week_end",
            "daily_calories",
            "macros",
            "meals",
            "version",
        ]


# -------------------------------
# Meal Logs (this week)
# -------------------------------

class TrainerMealLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealLog
        fields = [
            "date",
            "meal_type",
            "source",
            "calories",
            "protein",
            "carbs",
            "fat",
        ]


# -------------------------------
# Workout Plan (this week)
# -------------------------------

class TrainerWorkoutPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkoutPlan
        fields = [
            "week_start",
            "week_end",
            "goal",
            "workout_type",
            "sessions",
            "estimated_weekly_calories",
        ]


# -------------------------------
# Workout Logs (this week)
# -------------------------------

class TrainerWorkoutLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkoutLog
        fields = [
            "date",
            "exercise_name",
            "duration_sec",
            "calories_burnt",
            "status",
        ]


# -------------------------------
# Weight Logs (this week)
# -------------------------------

class TrainerWeightLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeightLog
        fields = [
            "logged_at",
            "weight_kg",
        ]


# -------------------------------
# Weekly Aggregates
# -------------------------------

class WeeklyStatsSerializer(serializers.Serializer):
    calories_in = serializers.IntegerField()
    calories_burned = serializers.IntegerField()


# -------------------------------
# Aggregated Trainer Overview
# -------------------------------

class TrainerUserOverviewSerializer(serializers.Serializer):
    profile = TrainerUserProfileSerializer()
    diet_plan = TrainerDietPlanSerializer(allow_null=True)
    diet_logs = TrainerMealLogSerializer(many=True)
    workout_plan = TrainerWorkoutPlanSerializer(allow_null=True)
    workout_logs = TrainerWorkoutLogSerializer(many=True)
    weight_logs = TrainerWeightLogSerializer(many=True)
    weekly_stats = WeeklyStatsSerializer()
