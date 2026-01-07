from types import SimpleNamespace
from urllib.parse import parse_qs
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.exceptions import TokenError
import uuid

class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner
        self.backend = TokenBackend(
            algorithm=settings.SIMPLE_JWT.get("ALGORITHM", "HS256"),
            signing_key=settings.SIMPLE_JWT.get("SIGNING_KEY"),
        )

    async def __call__(self, scope, receive, send):
        scope["user"] = AnonymousUser()

        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token_list = params.get("token")

        if token_list:
            user = await self._get_user_from_token(token_list[0])
            if user:
                scope["user"] = user

        return await self.inner(scope, receive, send)

    @database_sync_to_async
    def _get_user_from_token(self, token):
        try:
            payload = self.backend.decode(token, verify=True)

            raw_user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")
            if not raw_user_id:
                return None

            try:
                user_id = uuid.UUID(str(raw_user_id))
            except Exception:
                return None

            role = payload.get("role")
            roles = payload.get("roles")
            if not role and isinstance(roles, list) and roles:
                role = roles[0]

            user = SimpleNamespace(
                id=user_id,
                role=role,
                token_payload=payload,
            )
            user.is_authenticated = True
            return user

        except TokenError:
            return None
        except Exception:
            return None