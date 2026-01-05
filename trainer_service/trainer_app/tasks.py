from celery import current_app, shared_task


@shared_task
def publish_booking_decision(payload):
    current_app.send_task(
        "user_app.tasks.handle_booking_decision",
        args=[payload],
        queue="user_tasks",
    )
