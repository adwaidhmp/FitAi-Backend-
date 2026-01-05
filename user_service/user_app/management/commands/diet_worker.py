import pika
from django.conf import settings
from django.core.management.base import BaseCommand
from user_app.events.consumers import handle_weight_updated


class Command(BaseCommand):
    help = "Diet regeneration worker"

    def handle(self, *args, **options):
        connection = pika.BlockingConnection(pika.URLParameters(settings.RABBIT_URL))
        channel = connection.channel()

        channel.exchange_declare(
            exchange=settings.RABBIT_EXCHANGE,
            exchange_type="topic",
            durable=True,
        )

        channel.queue_declare(
            queue=settings.RABBIT_QUEUE_DIET_REGEN,
            durable=True,
        )

        channel.queue_bind(
            exchange=settings.RABBIT_EXCHANGE,
            queue=settings.RABBIT_QUEUE_DIET_REGEN,
            routing_key=settings.RABBIT_ROUTING_KEY_WEIGHT_UPDATED,
        )

        channel.basic_consume(
            queue=settings.RABBIT_QUEUE_DIET_REGEN,
            on_message_callback=handle_weight_updated,
            auto_ack=False,
        )

        self.stdout.write("Diet worker listening for weight.updated")
        channel.start_consuming()
