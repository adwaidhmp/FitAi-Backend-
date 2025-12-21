from rest_framework.permissions import BasePermission


class IsTrainer(BasePermission):
    message = "Trainer access required"

    def has_permission(self, request, view):
        user = request.user
        return bool(user and getattr(user, "role", None) == "trainer")
