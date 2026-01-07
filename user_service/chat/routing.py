from django.urls import re_path
from .consumers import ChatConsumer, CallConsumer, UserCallConsumer

websocket_urlpatterns = [
    # Chat
    re_path(
        r"^ws/chat/(?P<room_id>[0-9a-f-]+)/$",
        ChatConsumer.as_asgi(),
    ),

    # 🔥 GLOBAL USER CALL SOCKET
    re_path(
        r"^ws/user/call/$",
        UserCallConsumer.as_asgi(),
    ),

    # Call signaling (per call)
    re_path(
        r"^ws/calls/(?P<call_id>[0-9a-f-]+)/$",
        CallConsumer.as_asgi(),
    ),
]
