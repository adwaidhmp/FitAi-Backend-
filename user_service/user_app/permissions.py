from rest_framework.permissions import BasePermission


class IsTrainer(BasePermission):
    message = "Trainer access required"

    def has_permission(self, request, view):
        user = request.user
        return bool(user and getattr(user, "role", None) == "trainer")


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


from rest_framework.permissions import BasePermission
from django.utils import timezone
from .models import UserProfile


class IsPremiumUser(BasePermission):
    message = "Premium subscription required"

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return UserProfile.objects.filter(
            user_id=request.user.id,
            is_premium=True,
            premium_expires_at__gt=timezone.now(),
        ).exists()