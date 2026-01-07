import uuid
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from chat.models import ChatRoom, Call
from .call_events import emit_user_call_event, emit_call_event


class StartCallView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, room_id):
        user_id = request.user.id

        room = get_object_or_404(ChatRoom, id=room_id, is_active=True)

        # prevent parallel ringing calls
        if Call.objects.filter(
            room=room,
            status=Call.STATUS_RINGING
        ).exists():
            return Response(
                {"detail": "Call already ringing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        call = Call.objects.create(
            room=room,
            started_by=user_id,
            status=Call.STATUS_RINGING,
        )

        # 🔔 notify the OTHER participant (FIXED)
        target_user_id = room.other_participant_id(user_id)

        emit_user_call_event(
            target_user_id,
            {
                "type": "INCOMING_CALL",
                "call_id": str(call.id),
                "room_id": str(room.id),
                "from_user": str(user_id),
            },
        )

        # 🔔 notify the CALLER to navigate to call page
        emit_user_call_event(
            user_id,
            {
                "type": "CALL_STARTED",
                "call_id": str(call.id),
                "room_id": str(room.id),
            },
        )

        return Response(
            {
                "call_id": str(call.id),
                "status": call.status,
            },
            status=status.HTTP_201_CREATED,
        )



class AcceptCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, call_id):
        call = get_object_or_404(Call, id=call_id)

        if call.status != Call.STATUS_RINGING:
            return Response(
                {"detail": "Call not ringing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        call.status = Call.STATUS_ACTIVE
        call.save(update_fields=["status"])

        # notify both sides
        emit_call_event(
            call.id,
            {
                "type": "CALL_ACCEPTED",
                "call_id": str(call.id),
            },
        )

        emit_user_call_event(
            call.started_by,
            {
                "type": "CALL_ACCEPTED",
                "call_id": str(call.id),
            },
        )

        # notify the accepter as well
        accepter_id = call.room.other_participant_id(call.started_by)
        emit_user_call_event(
            accepter_id,
            {
                "type": "CALL_ACCEPTED",
                "call_id": str(call.id),
            },
        )

        return Response({"status": "active"})



class EndCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, call_id):
        call = get_object_or_404(Call, id=call_id)

        if call.status == Call.STATUS_ENDED:
            return Response({"status": "already ended"})

        call.status = Call.STATUS_ENDED
        call.save(update_fields=["status"])

        emit_call_event(
            call.id,
            {
                "type": "CALL_ENDED",
                "call_id": str(call.id),
            },
        )

        emit_user_call_event(
            call.started_by,
            {
                "type": "CALL_ENDED",
                "call_id": str(call.id),
            },
        )

        # notify the other participant as well
        other_id = call.room.other_participant_id(call.started_by)
        emit_user_call_event(
            other_id,
            {
                "type": "CALL_ENDED",
                "call_id": str(call.id),
            },
        )

        return Response({"status": "ended"})