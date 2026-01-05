# auth_service/messaging/publish.py
import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime

try:
    import pika
    from pika.exceptions import AMQPConnectionError
except Exception:
    pika = None
    AMQPConnectionError = None

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@rabbitmq:5672/")
EXCHANGE = os.getenv("RABBIT_EXCHANGE", "user_events")
ROUTING_KEY = os.getenv("RABBIT_ROUTING_KEY", "user.created")
TRAINER_ROUTING_KEY = os.getenv("RABBIT_ROUTING_KEY_TRAINER", "trainer.registered")

CONN_PARAMS = {
    "heartbeat": int(os.getenv("RABBIT_HEARTBEAT", "60")),
    "blocked_connection_timeout": float(os.getenv("RABBIT_BLOCKED_TIMEOUT", "30")),
    "socket_timeout": float(os.getenv("RABBIT_SOCKET_TIMEOUT", "10")),
}


def _make_properties(message_id=None):
    return pika.BasicProperties(
        delivery_mode=2,
        message_id=message_id or str(uuid.uuid4()),
        timestamp=int(datetime.utcnow().timestamp()),
        content_type="application/json",
    )


def _connect(url):
    params = pika.URLParameters(url)
    try:
        params.heartbeat = CONN_PARAMS["heartbeat"]
        params.blocked_connection_timeout = CONN_PARAMS["blocked_connection_timeout"]
        params.socket_timeout = CONN_PARAMS["socket_timeout"]
    except Exception:
        pass
    return pika.BlockingConnection(params)


def _publish_with_retry(routing_key, payload, max_retries=3, base_delay=0.5):
    attempt = 0

    while attempt < max_retries:
        attempt += 1
        conn = None
        try:
            conn = _connect(RABBIT_URL)
            ch = conn.channel()

            ch.exchange_declare(
                exchange=EXCHANGE,
                exchange_type="topic",
                durable=True,
            )

            props = _make_properties()

            ch.basic_publish(
                exchange=EXCHANGE,
                routing_key=routing_key,
                body=json.dumps(payload, ensure_ascii=False),
                properties=props,
            )

            logger.info(
                "Published %s user_id=%s message_id=%s",
                routing_key,
                payload.get("user_id"),
                props.message_id,
            )
            return True

        except AMQPConnectionError as e:
            backoff = base_delay * (2 ** (attempt - 1))
            jitter = backoff * 0.1
            sleep_for = backoff + jitter
            logger.warning(
                "Publish attempt %d failed: %s. Retrying in %.2fs",
                attempt,
                e,
                sleep_for,
            )
            time.sleep(sleep_for)

        except Exception as e:
            logger.exception("Unexpected publish error: %s", e)
            break

        finally:
            try:
                if conn and conn.is_open:
                    conn.close()
            except Exception:
                logger.exception("Error closing RabbitMQ connection")

    logger.error("Failed to publish %s after %d attempts", routing_key, max_retries)
    return False


# ===========================
# USER CREATED
# ===========================


def publish_sync(user_id, email, max_retries=3, base_delay=0.5):
    if pika is None:
        logger.error("pika not installed, skipping publish")
        return False

    payload = {
        "user_id": str(user_id),
        "email": email,
    }

    return _publish_with_retry(
        ROUTING_KEY,
        payload,
        max_retries=max_retries,
        base_delay=base_delay,
    )


def publish_user_created(user_id, email, background=True):
    if pika is None:
        logger.error("pika not available, skipping publish for user_id=%s", user_id)
        return False

    if background:
        t = threading.Thread(
            target=publish_sync,
            args=(user_id, email),
        )
        t.daemon = True
        t.start()
        logger.debug("Spawned background user publisher for user_id=%s", user_id)
        return True

    return publish_sync(user_id, email)


# ===========================
# TRAINER REGISTERED
# ===========================


def publish_trainer_sync(user_id, email, extra=None, max_retries=3, base_delay=0.5):
    if pika is None:
        logger.error("pika missing, skipping trainer publish")
        return False

    payload = {
        "user_id": str(user_id),
        "email": email,
    }

    if extra and isinstance(extra, dict):
        payload.update(extra)

    return _publish_with_retry(
        TRAINER_ROUTING_KEY,
        payload,
        max_retries=max_retries,
        base_delay=base_delay,
    )


def publish_trainer_registered(user_id, email, extra=None, background=True):
    if pika is None:
        logger.error(
            "pika not available, skipping trainer publish for user_id=%s", user_id
        )
        return False

    if background:
        t = threading.Thread(
            target=publish_trainer_sync,
            args=(user_id, email, extra),
        )
        t.daemon = True
        t.start()
        logger.debug("Spawned background trainer publisher for user_id=%s", user_id)
        return True

    return publish_trainer_sync(user_id, email, extra)
