import json
import pika
from django.conf import settings


def publish_event(routing_key: str, payload: dict):
    connection = pika.BlockingConnection(
        pika.URLParameters(settings.RABBIT_URL)
    )
    channel = connection.channel()

    channel.exchange_declare(
        exchange=settings.RABBIT_EXCHANGE,
        exchange_type="topic",
        durable=True,
    )

    channel.basic_publish(
        exchange=settings.RABBIT_EXCHANGE,
        routing_key=routing_key,
        body=json.dumps(payload),
        properties=pika.BasicProperties(delivery_mode=2),
    )

    connection.close()