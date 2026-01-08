from rest_framework import permissions
from rest_framework.permissions import BasePermission


class IsTrainerOwner(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, "is_authenticated", False)

    def has_object_permission(self, request, view, obj):
        return str(obj.user_id) == str(request.user.id)


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and getattr(user, "role", None) == "admin"
        )


class IsTrainer(BasePermission):
    message = "Trainer access required"

    def has_permission(self, request, view):
        return getattr(request.user, "role", None) == "trainer"