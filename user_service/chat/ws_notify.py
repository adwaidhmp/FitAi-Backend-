from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from .serializers import MessageSerializer
from .helper.message_normalizer import normalize_for_ws

def notify_new_message(room_id, message):
    """
    message MUST be a Message ORM instance
    """

    def _send():
        channel_layer = get_channel_layer()

        payload = MessageSerializer(message).data
        payload = normalize_for_ws(payload)

        async_to_sync(channel_layer.group_send)(
            f"chat_{room_id}",
            {
                "type": "chat_message",
                "payload": payload,
            },
        )

    # send only after DB commit
    transaction.on_commit(_send)
