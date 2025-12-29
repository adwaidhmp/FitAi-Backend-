from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db import close_old_connections


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        close_old_connections()

        query_string = parse_qs(scope["query_string"].decode())
        token = query_string.get("token")

        if token:
            try:
                jwt_auth = JWTAuthentication()
                validated = jwt_auth.get_validated_token(token[0])
                user = jwt_auth.get_user(validated)
                scope["user"] = user
            except Exception:
                scope["user"] = AnonymousUser()
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)
