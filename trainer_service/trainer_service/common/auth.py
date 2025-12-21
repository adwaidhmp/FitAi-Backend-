# trainer_service/common/auth.py

from types import SimpleNamespace

from django.conf import settings
from rest_framework import authentication, exceptions
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.exceptions import TokenError


class SimpleJWTAuth(authentication.BaseAuthentication):
    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Bearer "):
            return None

        token = header.split(" ", 1)[1].strip()

        try:
            backend = TokenBackend(
                algorithm=settings.SIMPLE_JWT.get("ALGORITHM", "HS256"),
                signing_key=settings.SIMPLE_JWT.get("SIGNING_KEY"),
            )
            payload = backend.decode(token, verify=True)
        except TokenError as e:
            raise exceptions.AuthenticationFailed(str(e))

        user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")
        if not user_id:
            raise exceptions.AuthenticationFailed("Token missing user id")

        roles = payload.get("roles", [])

        user = SimpleNamespace(
            id=user_id,
            role=roles[0] if roles else None,  # ✅ THIS FIXES EVERYTHING
            is_authenticated=True,
        )

        return (user, None)
