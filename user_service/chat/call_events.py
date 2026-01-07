from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import logging

logger = logging.getLogger("django")


def emit_user_call_event(user_id, payload):
    try:
        channel_layer = get_channel_layer()

        if channel_layer is None:
            logger.error("❌ Channel layer is None")
            return

        group = f"user_{user_id}"

        logger.info(f"🔥 EMIT CALL EVENT → {group} {payload}")

        async_to_sync(channel_layer.group_send)(
            group,
            {
                "type": "user_call_event",
                "payload": payload,
            },
        )

    except Exception as e:
        logger.exception("❌ FAILED TO EMIT USER CALL EVENT")


def emit_call_event(call_id, payload):
    try:
        channel_layer = get_channel_layer()

        if channel_layer is None:
            logger.error("❌ Channel layer is None")
            return

        async_to_sync(channel_layer.group_send)(
            f"call_{call_id}",
            {
                "type": "call_event",
                "payload": payload,
            },
        )

    except Exception:
        logger.exception("❌ FAILED TO EMIT CALL EVENT")
