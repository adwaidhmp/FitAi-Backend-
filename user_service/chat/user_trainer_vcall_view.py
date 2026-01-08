from django.db import transaction
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from chat.models import ChatRoom, Call
from .call_events import emit_user_call_event, emit_call_event


# ===========================
# START CALL
# ===========================
class StartCallView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, room_id):
        user_id = request.user.id

        room = get_object_or_404(ChatRoom, id=room_id, is_active=True)

        target_user_id = room.other_participant_id(user_id)

        # 🚫 prevent self-call
        if target_user_id == user_id:
            return Response(
                {"detail": "Invalid call target"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 🔥 cleanup stale ringing calls
        Call.objects.filter(
            room=room,
            status=Call.STATUS_RINGING,
        ).update(status=Call.STATUS_ENDED)

        # create new call
        call = Call.objects.create(
            room=room,
            started_by=user_id,
            status=Call.STATUS_RINGING,
        )

        print("START CALL:", call.id, "FROM:", user_id, "TO:", target_user_id)

        # 🔔 notify callee
        emit_user_call_event(
            target_user_id,
            {
                "type": "INCOMING_CALL",
                "call_id": str(call.id),
                "room_id": str(room.id),
                "from_user": str(user_id),
            },
        )

        return Response(
            {
                "call_id": str(call.id),
                "status": call.status,
            },
            status=status.HTTP_201_CREATED,
        )


# ===========================
# ACCEPT CALL
# ===========================

import logging

logger = logging.getLogger(__name__)

class AcceptCallView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, call_id):
        call = get_object_or_404(Call, id=call_id)

        user_id = str(request.user.id)
        caller_id = str(call.started_by)
        room = call.room

        if str(room.user_id) == caller_id:
            receiver_id = str(room.trainer_user_id)
        else:
            receiver_id = str(room.user_id)

        logger.warning("🔍 ACCEPT CALL DEBUG")
        logger.warning(" - request.user.id = %s", user_id)
        logger.warning(" - caller_id = %s", caller_id)
        logger.warning(" - receiver_id = %s", receiver_id)

        if user_id != receiver_id:
            return Response(
                {"detail": "Only the called user can accept this call"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if call.status != Call.STATUS_RINGING:
            return Response(
                {"detail": "Call not ringing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        call.status = Call.STATUS_ACTIVE
        call.save(update_fields=["status"])

        emit_user_call_event(caller_id, {
            "type": "CALL_ACCEPTED",
            "call_id": str(call.id),
        })
        emit_user_call_event(receiver_id, {
            "type": "CALL_ACCEPTED",
            "call_id": str(call.id),
        })
        emit_call_event(call.id, {
            "type": "CALL_ACCEPTED",
            "call_id": str(call.id),
        })

        return Response({"status": "active"})

# ===========================
# END CALL
# ===========================
class EndCallView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, call_id):
        call = get_object_or_404(Call, id=call_id)

        logger.warning("🔍 END CALL DEBUG")
        logger.warning(" - request.user.id = %s", request.user.id)
        logger.warning(" - call.started_by = %s", call.started_by)
        logger.warning(" - room.user_id = %s", call.room.user_id)
        logger.warning(" - room.trainer_user_id = %s", call.room.trainer_user_id)

        participants = {
            str(call.started_by),
            str(call.room.user_id),
            str(call.room.trainer_user_id),
        }

        if str(request.user.id) not in participants:
            return Response(
                {"detail": "Not allowed"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if call.status == Call.STATUS_ENDED:
            return Response({"status": "already ended"}, status=200)

        call.status = Call.STATUS_ENDED
        call.save(update_fields=["status"])

        for uid in participants:
            emit_user_call_event(uid, {
                "type": "CALL_ENDED",
                "call_id": str(call.id),
            })

        emit_call_event(call.id, {
            "type": "CALL_ENDED",
            "call_id": str(call.id),
        })

        return Response({"status": "ended"}, status=200)