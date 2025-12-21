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
    AMQPConnectionError = None  # keep the name defined for linters

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@rabbitmq:5672/")
EXCHANGE = os.getenv("RABBIT_EXCHANGE", "user_events")
ROUTING_KEY = os.getenv("RABBIT_ROUTING_KEY", "user.created")

# connection tuning (optional)
CONN_PARAMS = {
    "heartbeat": int(os.getenv("RABBIT_HEARTBEAT", "60")),
    "blocked_connection_timeout": float(os.getenv("RABBIT_BLOCKED_TIMEOUT", "30")),
    "socket_timeout": float(os.getenv("RABBIT_SOCKET_TIMEOUT", "10")),
}


def _make_properties(message_id=None):
    # timestamp must be int
    return pika.BasicProperties(
        delivery_mode=2,  # persistent
        message_id=message_id or str(uuid.uuid4()),
        timestamp=int(datetime.utcnow().timestamp()),
        content_type="application/json",
    )


def _connect(params):
    # helper to create a connection, applying timeouts if URLParameters supports them
    urlp = pika.URLParameters(params)
    # apply optional tuning if supported
    try:
        # some versions allow attributes assignment
        if hasattr(urlp, "heartbeat") and CONN_PARAMS.get("heartbeat"):
            urlp.heartbeat = CONN_PARAMS["heartbeat"]
    except Exception:
        pass
    return pika.BlockingConnection(urlp)


def publish_sync(user_id, email, max_retries=3, base_delay=0.5):
    """
    Blocking publish with retries and safe connection cleanup.
    Returns True on success, False on failure.
    """
    if pika is None:
        logger.error("pika is not installed. Skipping publish.")
        return False

    payload = {"user_id": str(user_id), "email": email}
    attempt = 0
    while attempt < max_retries:
        attempt += 1
        conn = None
        try:
            conn = _connect(RABBIT_URL)
            ch = conn.channel()
            # declare exchange (idempotent)
            ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
            props = _make_properties()
            ch.basic_publish(
                exchange=EXCHANGE,
                routing_key=ROUTING_KEY,
                body=json.dumps(payload, ensure_ascii=False),
                properties=props,
            )
            logger.info(
                "Published %s for user_id=%s message_id=%s",
                ROUTING_KEY,
                user_id,
                props.message_id,
            )
            return True
        except AMQPConnectionError as e:
            # transient connection errors: retry with jittered exponential backoff
            backoff = base_delay * (2 ** (attempt - 1))
            jitter = backoff * 0.1 * (1 + (0.5 - (time.time() % 1)))
            sleep_for = backoff + jitter
            logger.warning(
                "Publish attempt %d failed (AMQPConnectionError): %s. retrying in %.2fs",
                attempt,
                e,
                sleep_for,
            )
            time.sleep(sleep_for)
        except Exception as e:
            logger.exception("Unexpected publish error on attempt %d: %s", attempt, e)
            # on non-transient error, break and return False
            break
        finally:
            try:
                if conn is not None and getattr(conn, "is_open", False):
                    conn.close()
            except Exception:
                logger.exception("Error closing RabbitMQ connection")

    logger.error(
        "Failed to publish %s for user_id=%s after %d attempts",
        ROUTING_KEY,
        user_id,
        max_retries,
    )
    return False


def publish_user_created(user_id, email, background=True):
    if pika is None:
        logger.error("pika not available, skipping publish for user_id=%s", user_id)
        return False

    if background:
        # spawn non-daemon if you want guaranteed delivery on shutdown,
        # keep daemon=True if you prefer fast shutdown and best-effort delivery
        t = threading.Thread(target=publish_sync, args=(user_id, email))
        t.daemon = True
        t.start()
        logger.debug("Spawned background publisher thread for user_id=%s", user_id)
        return True

    return publish_sync(user_id, email)


# trainer publisher (same pattern)
TRAINER_ROUTING_KEY = os.getenv("RABBIT_ROUTING_KEY_TRAINER", "trainer.registered")


def publish_trainer_sync(user_id, email, extra=None, max_retries=3, base_delay=0.5):
    if pika is None:
        logger.error("pika missing, skipping trainer publish")
        return False

    payload = {"user_id": str(user_id), "email": email}
    if extra and isinstance(extra, dict):
        payload.update(extra)

    attempt = 0
    while attempt < max_retries:
        attempt += 1
        conn = None
        try:
            conn = _connect(RABBIT_URL)
            ch = conn.channel()
            ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
            props = _make_properties()
            ch.basic_publish(
                exchange=EXCHANGE,
                routing_key=TRAINER_ROUTING_KEY,
                body=json.dumps(payload, ensure_ascii=False),
                properties=props,
            )
            logger.info(
                "Published %s for user_id=%s message_id=%s",
                TRAINER_ROUTING_KEY,
                user_id,
                props.message_id,
            )
            return True
        except AMQPConnectionError as e:
            backoff = base_delay * (2 ** (attempt - 1))
            jitter = backoff * 0.1 * (1 + (0.5 - (time.time() % 1)))
            sleep_for = backoff + jitter
            logger.warning(
                "Trainer publish attempt %d failed (AMQPConnectionError): %s. retrying in %.2fs",
                attempt,
                e,
                sleep_for,
            )
            time.sleep(sleep_for)
        except Exception as e:
            logger.exception(
                "Unexpected trainer publish error on attempt %d: %s", attempt, e
            )
            break
        finally:
            try:
                if conn is not None and getattr(conn, "is_open", False):
                    conn.close()
            except Exception:
                logger.exception("Error closing RabbitMQ connection")

    logger.error(
        "Failed to publish %s for user_id=%s after %d attempts",
        TRAINER_ROUTING_KEY,
        user_id,
        max_retries,
    )
    return False


def publish_trainer_registered(user_id, email, extra=None, background=True):
    if pika is None:
        logger.error(
            "pika not available, skipping trainer publish for user_id=%s", user_id
        )
        return False
    if background:
        t = threading.Thread(target=publish_trainer_sync, args=(user_id, email, extra))
        t.daemon = True
        t.start()
        logger.debug(
            "Spawned background trainer-publisher thread for user_id=%s", user_id
        )
        return True
    return publish_trainer_sync(user_id, email, extra)
