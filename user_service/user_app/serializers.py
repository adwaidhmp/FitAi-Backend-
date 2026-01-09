from rest_framework import serializers

from .models import UserProfile, WorkoutLog, WorkoutPlan


class UserProfileSerializer(serializers.ModelSerializer):
    REQUIRED_FIELDS = [
        "dob",
        "gender",
        "height_cm",
        "weight_kg",
        "target_weight_kg",
        "goal",
        "activity_level",
        "exercise_experience",
    ]

    # Expose auth user id, never writable
    user_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "user_id",
            "dob",
            "gender",
            "height_cm",
            "weight_kg",
            "target_weight_kg",
            "goal",
            "body_type",
            "activity_level",
            "exercise_experience",
            "diet_constraints",
            "allergies",
            "medical_conditions",
            "supplements",
            "preferred_equipment",
            "notes",
            "is_premium",
            "premium_expires_at",
            "profile_completed",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "is_premium",
            "profile_completed",
            "created_at",
            "updated_at",
            "deleted_at",
        ]

    def validate(self, attrs):
        """
        Enforce required fields for both create and partial update.
        Uses instance values when fields are not present in attrs.
        """
        instance = getattr(self, "instance", None)
        missing = []

        for field in self.REQUIRED_FIELDS:
            if field in attrs:
                value = attrs.get(field)
            elif instance is not None:
                value = getattr(instance, field, None)
            else:
                value = None

            if value in (None, "", []):
                missing.append(field)

        if missing:
            raise serializers.ValidationError(
                {
                    "detail": "Profile incomplete. Fill all required fields.",
                    "missing_fields": missing,
                }
            )

        # ---- semantic validation ----
        weight = (
            attrs.get("weight_kg")
            if "weight_kg" in attrs
            else getattr(instance, "weight_kg", None)
        )

        target = (
            attrs.get("target_weight_kg")
            if "target_weight_kg" in attrs
            else getattr(instance, "target_weight_kg", None)
        )

        if target is not None:
            if target <= 0:
                raise serializers.ValidationError(
                    {"target_weight_kg": "Target weight must be greater than zero."}
                )

            if weight is not None and abs(weight - target) > 100:
                raise serializers.ValidationError(
                    {
                        "target_weight_kg": (
                            "Target weight difference from current weight is unrealistic."
                        )
                    }
                )

        return attrs

    def _set_user_and_completion(self, instance):
        """
        Attach authenticated user_id and compute profile completion.
        """
        request = self.context.get("request")
        if not request or not getattr(request.user, "id", None):
            raise serializers.ValidationError("User must be authenticated.")

        instance.user_id = request.user.id

        # Compute completion only if not already completed
        if not instance.profile_completed:
            instance.profile_completed = all(
                getattr(instance, field) not in (None, "", [])
                for field in self.REQUIRED_FIELDS
            )

        return instance

    def create(self, validated_data):
        instance = UserProfile(**validated_data)
        instance = self._set_user_and_completion(instance)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        # Ignore any client-provided user_id
        validated_data.pop("user_id", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance = self._set_user_and_completion(instance)
        instance.save()
        return instance


# workout serializer
class WorkoutPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkoutPlan
        fields = [
            "week_start",
            "week_end",
            "goal",
            "workout_type",
            "sessions",
            "estimated_weekly_calories",
            "created_at",
        ]


class WorkoutLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkoutLog
        fields = "__all__"
