# user_service/profiles/serializers.py
from rest_framework import serializers

from .models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):

    REQUIRED_FIELDS = [
        "dob",
        "gender",
        "height_cm",
        "weight_kg",
        "goal",
        "activity_level",
        "exercise_experience",
    ]

    # Show the linked auth user id, never allow clients to write it
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
        Enforce required fields (works for create and partial update).
        Uses existing instance values for missing fields on update.
        """
        missing = []
        instance = getattr(self, "instance", None)

        for field in self.REQUIRED_FIELDS:
            value = (
                attrs.get(field) if field in attrs else getattr(instance, field, None)
            )
            if value in (None, "", []):
                missing.append(field)

        if missing:
            raise serializers.ValidationError(
                {
                    "detail": "Profile incomplete. Fill all required fields.",
                    "missing_fields": missing,
                }
            )

        return attrs

    def _set_user_and_completion(self, instance):
        """
        Attach user_id (from verified token) and compute completion status.
        """
        request = self.context.get("request")
        if (
            not request
            or not getattr(request, "user", None)
            or not getattr(request.user, "id", None)
        ):
            raise serializers.ValidationError("User must be authenticated.")

        # request.user.id comes from your SimpleJWTAuth and should be a UUID string or uuid.UUID
        instance.user_id = request.user.id

        # auto calculate profile completion
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
        # ignore any client-provided user_id
        validated_data.pop("user_id", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance = self._set_user_and_completion(instance)
        instance.save()
        return instance
