from django.conf import settings
from kombu import Connection, Exchange, Queue
from user_app.tasks import handle_booking_decision

exchange = Exchange("booking_events", type="fanout")
queue = Queue("user_booking_events", exchange)


def start_consumer():
    with Connection(settings.CELERY_BROKER_URL) as conn:
        with conn.Consumer(
            queues=[queue],
            callbacks=[on_message],
            accept=["json"],
        ):
            while True:
                conn.drain_events()


def on_message(body, message):
    try:
        handle_booking_decision.delay(body)
        message.ack()
    except Exception:
        # do NOT ack on failure
        message.reject()
