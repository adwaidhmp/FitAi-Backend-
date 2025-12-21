# user_app/management/commands/run_rabbit_consumer.py
import json
import logging
import os
import signal
import time
import uuid
from typing import Optional

import django
from django.core.management.base import BaseCommand
from django.db import DatabaseError, IntegrityError, transaction

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "user_service.settings")
django.setup()

# import pika optionally (deployment images might not have it at build time)
try:
    import pika
    from pika.exceptions import AMQPConnectionError, StreamLostError
except Exception:
    pika = None
    AMQPConnectionError = Exception
    StreamLostError = Exception

from user_app.models import UserProfile

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Rabbit config (tune via env)
RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@rabbitmq:5672/")
EXCHANGE = os.getenv("RABBIT_EXCHANGE", "user_events")
ROUTING_KEY = os.getenv("RABBIT_ROUTING_KEY", "user.created")
QUEUE = os.getenv("RABBIT_QUEUE", "user.created")
PREFETCH = int(os.getenv("PREFETCH_COUNT", "1"))

# Connection tuning (optional)
HEARTBEAT = int(os.getenv("RABBIT_HEARTBEAT", "60"))
BLOCKED_CONNECTION_TIMEOUT = float(os.getenv("RABBIT_BLOCKED_TIMEOUT", "30"))
SOCKET_TIMEOUT = float(os.getenv("RABBIT_SOCKET_TIMEOUT", "10"))

stop_requested = False


def handle_signal(signum, frame):
    global stop_requested
    logger.info("Signal %s received, requesting stop...", signum)
    stop_requested = True


def _make_urlparams(url: str) -> Optional["{pika} .URLParameters"]:
    if pika is None:
        return None
    params = pika.URLParameters(url)
    # apply tunables if supported by pika version
    try:
        params.heartbeat = HEARTBEAT
    except Exception:
        pass
    try:
        params.blocked_connection_timeout = BLOCKED_CONNECTION_TIMEOUT
    except Exception:
        pass
    try:
        params.socket_timeout = SOCKET_TIMEOUT
    except Exception:
        pass
    return params


def create_profile_if_missing(user_id_str: str) -> bool:
    """
    Create a UserProfile for the given user_id if it does not exist.
    Returns True if created, False if existed.
    Raises ValueError for invalid UUID format only if you expect UUID.
    """
    # If your UserProfile expects a UUID foreign key, convert. If it uses integer PK,
    # you can pass the string id directly — adjust here as needed.
    try:
        user_uuid = uuid.UUID(str(user_id_str))
    except Exception:
        # Not a UUID — caller may pass numeric id as string; raise if you require UUID
        # Here we raise ValueError to indicate invalid UUID; adjust if your model uses ints.
        raise ValueError("Invalid user_id format; expected UUID")

    defaults = {
        "profile_completed": False,
        "diet_constraints": {},
        "allergies": [],
        "medical_conditions": [],
        "supplements": [],
        "preferred_equipment": [],
    }

    # IMPORTANT: do NOT merge incoming payload into defaults.
    profile, created = UserProfile.objects.get_or_create(
        user_id=user_uuid, defaults=defaults
    )
    return created


class Command(BaseCommand):
    help = "RabbitMQ consumer: creates UserProfile rows for user.created events"

    def handle(self, *args, **options):
        global stop_requested

        if pika is None:
            logger.error(
                "pika is not installed in the image. Install pika and try again."
            )
            return

        # register signals early
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        params = _make_urlparams(RABBIT_URL)
        attempt = 0
        max_retries = 10

        while not stop_requested:
            conn = None
            ch = None
            try:
                logger.info("Connecting to RabbitMQ at %s", RABBIT_URL)
                conn = pika.BlockingConnection(params)
                ch = conn.channel()

                # idempotent declarations
                ch.exchange_declare(
                    exchange=EXCHANGE, exchange_type="topic", durable=True
                )
                ch.queue_declare(queue=QUEUE, durable=True)
                ch.queue_bind(queue=QUEUE, exchange=EXCHANGE, routing_key=ROUTING_KEY)
                ch.basic_qos(prefetch_count=PREFETCH)

                logger.info(
                    "Connected. Listening on queue '%s' (routing_key=%s)",
                    QUEUE,
                    ROUTING_KEY,
                )

                def callback(channel, method, properties, body):
                    # decode body
                    try:
                        raw = body.decode("utf-8")
                    except Exception as e:
                        logger.exception(
                            "Failed to decode body, acking and dropping. err=%s", e
                        )
                        try:
                            channel.basic_ack(delivery_tag=method.delivery_tag)
                        except Exception:
                            logger.exception("Failed to ack undecodable message")
                        return

                    logger.info(
                        "Received message delivery_tag=%s properties=%s raw=%s",
                        getattr(method, "delivery_tag", None),
                        properties,
                        raw,
                    )

                    # parse JSON
                    try:
                        payload = json.loads(raw)
                    except Exception as e:
                        logger.exception(
                            "Invalid JSON, acking and dropping. err=%s raw=%s", e, raw
                        )
                        try:
                            channel.basic_ack(delivery_tag=method.delivery_tag)
                        except Exception:
                            logger.exception("Failed to ack invalid JSON message")
                        return

                    # flexible keys: try a few common names
                    user_id = (
                        payload.get("user_id")
                        or payload.get("id")
                        or payload.get("user")
                        or payload.get("userId")
                    )
                    if not user_id:
                        logger.warning(
                            "Missing user_id (tried user_id/id/user/userId). Acking and dropping. payload=%s",
                            payload,
                        )
                        try:
                            channel.basic_ack(delivery_tag=method.delivery_tag)
                        except Exception:
                            logger.exception("Failed to ack missing-user-id message")
                        return

                    # normalize/validate user_id: expect UUID here; if you use ints, adjust this block
                    try:
                        user_uuid = uuid.UUID(str(user_id))
                        user_id_str = str(user_uuid)
                    except Exception:
                        logger.warning(
                            "user_id is not a valid UUID: %s. Acking and dropping.",
                            user_id,
                        )
                        try:
                            channel.basic_ack(delivery_tag=method.delivery_tag)
                        except Exception:
                            logger.exception("Failed to ack invalid-uuid message")
                        return

                    # Ensure we never pass unexpected payload keys into defaults
                    try:
                        with transaction.atomic():
                            created = create_profile_if_missing(user_id_str)
                            if created:
                                logger.info(
                                    "Created UserProfile for user_id=%s", user_id_str
                                )
                            else:
                                logger.debug(
                                    "UserProfile already exists for user_id=%s",
                                    user_id_str,
                                )
                    except IntegrityError as integ_exc:
                        # likely foreign key or constraint failure; requeue to retry later
                        logger.exception(
                            "IntegrityError creating profile for user_id=%s, requeuing: %s",
                            user_id_str,
                            integ_exc,
                        )
                        try:
                            channel.basic_nack(
                                delivery_tag=method.delivery_tag, requeue=True
                            )
                        except Exception:
                            logger.exception(
                                "basic_nack failed; acknowledging to avoid duplicate loop"
                            )
                            try:
                                channel.basic_ack(delivery_tag=method.delivery_tag)
                            except Exception:
                                logger.exception("Failed to ack after nack failure")
                        return
                    except DatabaseError as db_exc:
                        # transient DB error, requeue
                        logger.exception(
                            "DatabaseError creating profile for user_id=%s, requeuing: %s",
                            user_id_str,
                            db_exc,
                        )
                        try:
                            channel.basic_nack(
                                delivery_tag=method.delivery_tag, requeue=True
                            )
                        except Exception:
                            logger.exception(
                                "basic_nack failed; acknowledging to avoid duplicate loop"
                            )
                            try:
                                channel.basic_ack(delivery_tag=method.delivery_tag)
                            except Exception:
                                logger.exception("Failed to ack after nack failure")
                        return
                    except ValueError as ve:
                        # invalid ID format or other validation
                        logger.warning(
                            "Invalid payload for user_id=%s: %s. Acking and dropping.",
                            user_id,
                            ve,
                        )
                        try:
                            channel.basic_ack(delivery_tag=method.delivery_tag)
                        except Exception:
                            logger.exception("Failed to ack invalid-payload message")
                        return
                    except Exception as exc:
                        logger.exception(
                            "Unexpected error creating profile for user_id=%s. Acking and dropping: %s",
                            user_id_str,
                            exc,
                        )
                        try:
                            channel.basic_ack(delivery_tag=method.delivery_tag)
                        except Exception:
                            logger.exception("Failed to ack after unexpected error")
                        return

                    # success -> ack
                    try:
                        channel.basic_ack(delivery_tag=method.delivery_tag)
                    except Exception as e:
                        logger.exception(
                            "Failed to ack message for user_id=%s: %s", user_id_str, e
                        )

                # Use manual event loop to allow graceful shutdown
                ch.basic_consume(
                    queue=QUEUE, on_message_callback=callback, auto_ack=False
                )
                attempt = 0  # reset attempts on successful connect

                while not stop_requested:
                    # short time_limit so we can break quickly on stop_requested
                    conn.process_data_events(time_limit=1)

                logger.info("Stop requested, stopping consumer loop")
                try:
                    ch.stop_consuming()
                except Exception:
                    pass

            except (AMQPConnectionError, StreamLostError) as conn_exc:
                attempt += 1
                backoff = min(1 * (2 ** (attempt - 1)), 30)
                jitter = backoff * 0.1 * (1 + (time.time() % 1 - 0.5))
                delay = max(0.5, backoff + jitter)
                logger.warning(
                    "RabbitMQ connection failed (attempt %d), retrying in %.1fs: %s",
                    attempt,
                    delay,
                    conn_exc,
                )
                time.sleep(delay)
                if attempt >= max_retries:
                    logger.error(
                        "Reached max connection attempts (%d). Sleeping longer before retry.",
                        max_retries,
                    )
                    time.sleep(30)
                continue
            except Exception as exc:
                logger.exception(
                    "Unexpected consumer error, sleeping 5s then retrying: %s", exc
                )
                time.sleep(5)
                continue
            finally:
                # ensure resources closed
                try:
                    if ch is not None and getattr(ch, "is_open", False):
                        ch.close()
                except Exception:
                    logger.exception("Error closing channel")
                try:
                    if conn is not None and getattr(conn, "is_open", False):
                        conn.close()
                except Exception:
                    logger.exception("Error closing connection")

        logger.info("Consumer shut down cleanly")
