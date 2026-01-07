import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "user_service.settings")

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# 🔥 1. Initialize Django FIRST
django_asgi_app = get_asgi_application()

# 🔥 2. Import AFTER apps are ready
from chat.middleware import JWTAuthMiddleware
from chat.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
