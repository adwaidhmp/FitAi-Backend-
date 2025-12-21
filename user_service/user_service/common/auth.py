from types import SimpleNamespace

from django.conf import settings
from rest_framework import authentication, exceptions
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.exceptions import TokenError


class SimpleJWTAuth(authentication.BaseAuthentication):
    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")

        if not header or not header.startswith("Bearer "):
            return None

        token = header.split(" ", 1)[1].strip()

        try:
            backend = TokenBackend(
                algorithm=settings.SIMPLE_JWT.get("ALGORITHM", "HS256"),
                signing_key=settings.SIMPLE_JWT.get("SIGNING_KEY"),
            )
            payload = backend.decode(token, verify=True)

        except TokenError as e:
            raise exceptions.AuthenticationFailed(f"Invalid token: {str(e)}")
        except Exception:
            raise exceptions.AuthenticationFailed("Invalid token")

        # ----- extract user id -----
        user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")
        if not user_id:
            raise exceptions.AuthenticationFailed("Token missing user id")

        # ----- extract role (support both formats) -----
        role = payload.get("role")
        roles = payload.get("roles")

        if not role and isinstance(roles, list) and roles:
            role = roles[0]

        # ----- create lightweight user object -----
        user = SimpleNamespace(
            id=user_id,
            role=role,
            token_payload=payload,
        )

        # DRF expects this
        user.is_authenticated = True

        return (user, token)
