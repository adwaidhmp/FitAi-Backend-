# call_events.py
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import logging

logger = logging.getLogger("django")


def _serialize(payload: dict) -> dict:
    safe = {}
    for k, v in payload.items():
        try:
            safe[k] = str(v)
        except Exception:
            safe[k] = v
    return safe


def emit_user_call_event(user_id, payload):
    logger.error(f"📤 EMIT USER EVENT REQUEST → user={user_id} payload={payload}")

    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            logger.error("❌ Channel layer is NONE (Redis down?)")
            return False

        payload = _serialize(payload)
        group = f"user_{user_id}"

        logger.error(f"📡 GROUP_SEND → {group}")

        async_to_sync(channel_layer.group_send)(
            group,
            {
                "type": "user_call_event",
                "payload": payload,
            },
        )

        logger.error(f"✅ USER EVENT SENT → {group}")
        return True

    except Exception as e:
        logger.exception("❌ USER EVENT FAILED")
        return False


def emit_call_event(call_id, payload):
    logger.error(f"📤 EMIT CALL EVENT REQUEST → call={call_id} payload={payload}")

    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            logger.error("❌ Channel layer is NONE (Redis down?)")
            return False

        payload = _serialize(payload)
        group = f"call_{call_id}"

        logger.error(f"📡 GROUP_SEND → {group}")

        async_to_sync(channel_layer.group_send)(
            group,
            {
                "type": "call_event",
                "payload": payload,
            },
        )

        logger.error(f"✅ CALL EVENT SENT → {group}")
        return True

    except Exception:
        logger.exception("❌ CALL EVENT FAILED")
        return False
