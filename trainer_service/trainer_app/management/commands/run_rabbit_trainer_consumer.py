# user_service/trainers/management/commands/run_rabbit_trainer_consumer.py
import json
import logging
import os
import signal
import time
import uuid

import django
from django.core.management.base import BaseCommand
from django.db import DatabaseError, transaction

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "user_service.settings")
django.setup()

try:
    import pika
    from pika.exceptions import AMQPConnectionError, StreamLostError
except Exception:
    pika = None

from trainer_app.models import TrainerProfile

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@rabbitmq:5672/")
EXCHANGE = os.getenv("RABBIT_EXCHANGE", "user_events")
ROUTING_KEY = os.getenv("RABBIT_ROUTING_KEY_TRAINER", "trainer.registered")
QUEUE = os.getenv("RABBIT_QUEUE_TRAINER", "trainer.registered")
PREFETCH = int(os.getenv("PREFETCH_COUNT", "1"))

stop_requested = False


def handle_signal(signum, frame):
    global stop_requested
    logger.info("Signal %s received, shutting down trainer consumer...", signum)
    stop_requested = True


def create_trainer_if_missing(user_id_str):
    try:
        user_uuid = uuid.UUID(str(user_id_str))
    except Exception:
        raise ValueError("Invalid user_id")

    defaults = {
        "bio": "",
        "specialties": [],
        "experience_years": 0,
        "is_completed": False,
    }

    profile, created = TrainerProfile.objects.get_or_create(
        user_id=user_uuid, defaults=defaults
    )
    return created


class Command(BaseCommand):
    help = "Simple RabbitMQ consumer that creates trainer profiles for trainer.registered events"

    def handle(self, *args, **options):
        if pika is None:
            logger.error(
                "pika is not installed in this image. Install pika and try again."
            )
            return

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        attempt = 0
        while not stop_requested:
            try:
                params = pika.URLParameters(RABBIT_URL)
                logger.info("Connecting to RabbitMQ at %s", RABBIT_URL)
                conn = pika.BlockingConnection(params)
                ch = conn.channel()

                # ensure exchange and queue exist
                ch.exchange_declare(
                    exchange=EXCHANGE, exchange_type="topic", durable=True
                )
                ch.queue_declare(queue=QUEUE, durable=True)
                ch.queue_bind(queue=QUEUE, exchange=EXCHANGE, routing_key=ROUTING_KEY)
                ch.basic_qos(prefetch_count=PREFETCH)

                logger.info(
                    "Connected to RabbitMQ, waiting for messages on queue '%s'", QUEUE
                )

                def callback(channel, method, properties, body):
                    try:
                        data = json.loads(body.decode("utf-8"))
                    except Exception as e:
                        logger.error(
                            "Invalid JSON, acking and dropping. err=%s body=%s", e, body
                        )
                        channel.basic_ack(method.delivery_tag)
                        return

                    user_id = data.get("user_id")
                    if not user_id:
                        logger.warning(
                            "Missing user_id in message, acking and dropping. body=%s",
                            data,
                        )
                        channel.basic_ack(method.delivery_tag)
                        return

                    try:
                        with transaction.atomic():
                            created = create_trainer_if_missing(user_id)
                            if created:
                                logger.info(
                                    "Created TrainerProfile for user_id=%s", user_id
                                )
                            else:
                                logger.debug(
                                    "TrainerProfile already exists for user_id=%s",
                                    user_id,
                                )
                    except DatabaseError as db_exc:
                        logger.exception(
                            "DB error for user_id=%s, will requeue: %s", user_id, db_exc
                        )
                        # Requeue message so it can be retried later
                        try:
                            channel.basic_nack(
                                delivery_tag=method.delivery_tag, requeue=True
                            )
                        except Exception:
                            logger.exception(
                                "basic_nack failed; acknowledging to avoid duplicate loop"
                            )
                            channel.basic_ack(delivery_tag=method.delivery_tag)
                        return
                    except Exception as exc:
                        logger.exception(
                            "Unexpected error for user_id=%s, acking to drop: %s",
                            user_id,
                            exc,
                        )
                        channel.basic_ack(delivery_tag=method.delivery_tag)
                        return

                    # success -> ack
                    try:
                        channel.basic_ack(delivery_tag=method.delivery_tag)
                    except Exception as e:
                        logger.exception(
                            "Failed to ack message for user_id=%s: %s", user_id, e
                        )

                ch.basic_consume(queue=QUEUE, on_message_callback=callback)

                # consume loop: use process_data_events in small increments so we can handle stop_requested
                try:
                    while not stop_requested:
                        ch.connection.process_data_events(time_limit=1)
                    logger.info("Stop requested, stopping consumer loop")
                    try:
                        ch.stop_consuming()
                    except Exception:
                        pass
                finally:
                    try:
                        if ch.is_open:
                            ch.close()
                    except Exception:
                        pass
                    try:
                        if conn.is_open:
                            conn.close()
                    except Exception:
                        pass

            except (AMQPConnectionError, StreamLostError) as conn_exc:
                attempt += 1
                delay = min(1 * (2 ** (attempt - 1)), 30)
                logger.warning(
                    "RabbitMQ connection failed (attempt %s). Retrying in %.1fs: %s",
                    attempt,
                    delay,
                    conn_exc,
                )
                time.sleep(delay)
                continue
            except Exception as exc:
                logger.exception("Consumer error, sleeping 5s then retrying: %s", exc)
                time.sleep(5)
                continue

        logger.info("Trainer consumer shut down cleanly")
