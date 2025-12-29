# chat/ws_notify.py
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .serializers import MessageSerializer


def notify_new_message(room_id, message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"chat_{room_id}",
        {
            "type": "chat.message",
            "payload": MessageSerializer(message).data,
        },
    )
