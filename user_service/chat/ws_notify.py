from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from .serializers import MessageSerializer


def notify_new_message(room_id, message):
    def _send():
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{room_id}",
            {
                "type": "chat_message",
                "payload": MessageSerializer(message).data,
            },
        )

    # ✅ send only after DB commit
    transaction.on_commit(_send)
