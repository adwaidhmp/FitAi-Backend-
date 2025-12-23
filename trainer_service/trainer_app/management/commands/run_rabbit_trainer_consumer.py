import json
import logging
import os
import signal
import time
import uuid

import django
from django.core.management.base import BaseCommand
from django.db import DatabaseError, transaction

# ✅ MUST point to trainer_service
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "trainer_service.settings",
)
django.setup()

try:
    import pika
    from pika.exceptions import AMQPConnectionError, StreamLostError
except Exception:
    pika = None
    AMQPConnectionError = Exception
    StreamLostError = Exception

from trainer_app.models import TrainerProfile

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# RabbitMQ config
RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@rabbitmq:5672/")
EXCHANGE = os.getenv("RABBIT_EXCHANGE", "user_events")
ROUTING_KEY = os.getenv("RABBIT_ROUTING_KEY_TRAINER", "trainer.registered")

# ✅ Queue must be service-specific, NOT routing key
QUEUE = os.getenv(
    "RABBIT_QUEUE_TRAINER",
    "trainer_service.trainer_registered",
)

PREFETCH = int(os.getenv("PREFETCH_COUNT", "1"))

stop_requested = False


def handle_signal(signum, frame):
    global stop_requested
    logger.info("Signal %s received, shutting down trainer consumer...", signum)
    stop_requested = True


def create_trainer_if_missing(user_id):
    try:
        user_uuid = uuid.UUID(str(user_id))
    except Exception:
        raise ValueError("Invalid user_id, expected UUID")

    defaults = {
        "bio": "",
        "specialties": [],
        "experience_years": 0,
        "is_completed": False,
    }

    _, created = TrainerProfile.objects.get_or_create(
        user_id=user_uuid,
        defaults=defaults,
    )
    return created


class Command(BaseCommand):
    help = "RabbitMQ consumer for trainer.registered events"

    def handle(self, *args, **options):
        if pika is None:
            logger.error("pika not installed, cannot start trainer consumer")
            return

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        attempt = 0

        while not stop_requested:
            conn = None
            ch = None
            try:
                logger.info("Connecting to RabbitMQ at %s", RABBIT_URL)
                params = pika.URLParameters(RABBIT_URL)
                conn = pika.BlockingConnection(params)
                ch = conn.channel()

                # Idempotent declarations
                ch.exchange_declare(
                    exchange=EXCHANGE,
                    exchange_type="topic",
                    durable=True,
                )
                ch.queue_declare(queue=QUEUE, durable=True)
                ch.queue_bind(
                    queue=QUEUE,
                    exchange=EXCHANGE,
                    routing_key=ROUTING_KEY,
                )
                ch.basic_qos(prefetch_count=PREFETCH)

                logger.info(
                    "Trainer consumer listening on queue=%s routing_key=%s",
                    QUEUE,
                    ROUTING_KEY,
                )

                def callback(channel, method, properties, body):
                    try:
                        payload = json.loads(body.decode("utf-8"))
                    except Exception as e:
                        logger.error(
                            "Invalid JSON, acking and dropping. err=%s body=%s",
                            e,
                            body,
                        )
                        channel.basic_ack(method.delivery_tag)
                        return

                    user_id = payload.get("user_id")
                    if not user_id:
                        logger.warning(
                            "Missing user_id, acking and dropping. payload=%s",
                            payload,
                        )
                        channel.basic_ack(method.delivery_tag)
                        return

                    try:
                        with transaction.atomic():
                            created = create_trainer_if_missing(user_id)
                            if created:
                                logger.info(
                                    "Created TrainerProfile for user_id=%s",
                                    user_id,
                                )
                            else:
                                logger.debug(
                                    "TrainerProfile already exists for user_id=%s",
                                    user_id,
                                )
                    except DatabaseError as db_exc:
                        logger.exception(
                            "DB error, requeueing message user_id=%s: %s",
                            user_id,
                            db_exc,
                        )
                        channel.basic_nack(
                            delivery_tag=method.delivery_tag,
                            requeue=True,
                        )
                        return
                    except Exception as exc:
                        logger.exception(
                            "Unexpected error, acking to drop user_id=%s: %s",
                            user_id,
                            exc,
                        )
                        channel.basic_ack(method.delivery_tag)
                        return

                    channel.basic_ack(method.delivery_tag)

                ch.basic_consume(
                    queue=QUEUE,
                    on_message_callback=callback,
                    auto_ack=False,
                )

                attempt = 0

                while not stop_requested:
                    conn.process_data_events(time_limit=1)

                logger.info("Stop requested, stopping trainer consumer")
                try:
                    ch.stop_consuming()
                except Exception:
                    pass

            except (AMQPConnectionError, StreamLostError) as exc:
                attempt += 1
                delay = min(2 ** attempt, 30)
                logger.warning(
                    "RabbitMQ connection failed (attempt %d), retrying in %ds: %s",
                    attempt,
                    delay,
                    exc,
                )
                time.sleep(delay)

            except Exception as exc:
                logger.exception(
                    "Trainer consumer crashed, retrying in 5s: %s",
                    exc,
                )
                time.sleep(5)

            finally:
                try:
                    if ch and ch.is_open:
                        ch.close()
                except Exception:
                    pass
                try:
                    if conn and conn.is_open:
                        conn.close()
                except Exception:
                    pass

        logger.info("Trainer consumer shut down cleanly")
