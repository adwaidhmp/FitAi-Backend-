from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import TrainerProfile
from trainer_service.firebase.push import send_push


class TrainerEventsWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        event = request.data.get("event")
        payload = request.data.get("payload", {})

        trainer_user_id = payload.get("trainer_user_id")

        if not event or not trainer_user_id:
            return Response(
                {"detail": "Invalid payload"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1️⃣ Fetch trainer + FCM token ONCE
        try:
            trainer = TrainerProfile.objects.get(user_id=trainer_user_id)
        except TrainerProfile.DoesNotExist:
            return Response(
                {"detail": "Trainer not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not trainer.fcm_token:
            # No token → nothing to send, but webhook succeeded
            return Response(status=status.HTTP_200_OK)

        # 2️⃣ Dispatch by event
        self.handle_event(
            event=event,
            payload=payload,
            fcm_token=trainer.fcm_token,
        )

        return Response(status=status.HTTP_200_OK)

    # ----------------------------------------------------
    # EVENT DISPATCHER
    # ----------------------------------------------------
    def handle_event(self, *, event, payload, fcm_token):
        if event == "TRAINER_BOOKED":
            self.on_trainer_booked(fcm_token, payload)

        elif event == "NEW_CHAT_MESSAGE":
            self.on_new_chat_message(fcm_token, payload)

        elif event == "INCOMING_CALL":
            self.on_incoming_call(fcm_token, payload)

        # else:
        #     unknown events are safely ignored

    # ----------------------------------------------------
    # EVENT HANDLERS
    # ----------------------------------------------------
    def on_trainer_booked(self, token, payload):
        send_push(
            token=token,
            title="New Booking 👨‍🏫",
            body="A user booked a session with you",
            data={
                "type": "TRAINER_BOOKED",
                "booking_id": payload.get("booking_id"),
            },
        )

    def on_new_chat_message(self, token, payload):
        send_push(
            token=token,
            title="New Message 💬",
            body="You received a new chat message",
            data={
                "type": "NEW_CHAT_MESSAGE",
                "chat_room_id": payload.get("chat_room_id"),
            },
        )

    def on_incoming_call(self, token, payload):
        send_push(
            token=token,
            title="Incoming Call 📞",
            body="You have an incoming call",
            data={
                "type": "INCOMING_CALL",
                "call_id": payload.get("call_id"),
            },
        )

