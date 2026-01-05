import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "user_service.settings")

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

# 🔥 1. Initialize Django FIRST
django_asgi_app = get_asgi_application()

# 🔥 2. Import anything that touches models/auth AFTER
from chat.middleware import JWTAuthMiddleware
import chat.routing

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JWTAuthMiddleware(
            URLRouter(chat.routing.websocket_urlpatterns)
        ),
    }
)
