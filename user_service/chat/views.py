from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from chat.models import ChatRoom, Message
from chat.serializers import UserMessageCreateSerializer, MessageSerializer
from chat.pagination import ChatMessageCursorPagination
from chat.ws_notify import notify_new_message
import uuid

from user_app.tasks import emit_webhook
from .helper.message_normalizer import normalize_for_ws
from django.db.models import Q
from django.db import transaction
from user_app.tasks import send_user_notification

# -------------------------------------------------
# USER CHAT ROOM LIST (with has_unread)
# -------------------------------------------------
class UserChatRoomListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = str(request.user.id)

        rooms = ChatRoom.objects.filter(
            Q(user_id=user_id) | Q(trainer_user_id=user_id),
            is_active=True,
        ).order_by("-last_message_at", "-created_at")

        data = []

        for room in rooms:
            has_unread = Message.objects.filter(
                room=room,
                read_at__isnull=True,
            ).exclude(
                sender_user_id=user_id
            ).exists()

            data.append(
                {
                    "id": room.id,
                    "user_id": room.user_id,
                    "trainer_user_id": room.trainer_user_id,
                    "last_message_at": room.last_message_at,
                    "created_at": room.created_at,
                    "has_unread": has_unread,
                }
            )

        return Response(data)


# -------------------------------------------------
# CHAT HISTORY (AUTO MARK AS READ)
# -------------------------------------------------
class ChatHistoryView(ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ChatMessageCursorPagination

    def get_queryset(self):
        room = get_object_or_404(
            ChatRoom,
            id=self.kwargs["room_id"],
        )

        user_id = str(self.request.user.id)

        # 🔐 UUID-safe authorization
        if user_id not in (str(room.user_id), str(room.trainer_user_id)):
            return Message.objects.none()

        # ✅ AUTO MARK AS READ
        Message.objects.filter(
            room=room,
            read_at__isnull=True,
        ).exclude(
            sender_user_id=user_id
        ).update(read_at=now())

        return Message.objects.filter(
            room=room,
            is_deleted=False,
        ).order_by("created_at")


# -------------------------------------------------
# SEND TEXT MESSAGE (REST → WS)
# -------------------------------------------------
class SendTextMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        room_id = request.data.get("room_id")
        text = request.data.get("text", "").strip()

        if not room_id:
            return Response(
                {"detail": "room_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not text:
            return Response(
                {"detail": "Text is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        room = get_object_or_404(ChatRoom, id=room_id, is_active=True)

        try:
            user_uuid = uuid.UUID(str(request.user.id))
        except ValueError:
            return Response(
                {"detail": "Invalid user id in token"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if user_uuid not in (room.user_id, room.trainer_user_id):
            return Response(
                {"detail": "Forbidden"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # ✅ CREATE ORM MESSAGE
        msg = Message.objects.create(
            room=room,
            sender_user_id=user_uuid,
            sender_role=(
                Message.SENDER_USER
                if user_uuid == room.user_id
                else Message.SENDER_TRAINER
            ),
            type=Message.TEXT,
            text=text,
        )

        room.last_message_at = msg.created_at
        room.save(update_fields=["last_message_at"])

        def on_commit_actions():
            # WS notify
            notify_new_message(room.id, msg)

            # 🔔 Notify trainer ONLY when user sends message
            if msg.sender_role == Message.SENDER_USER:
                emit_webhook.delay(
                    event="NEW_CHAT_MESSAGE",
                    payload={
                        "trainer_user_id": str(room.trainer_user_id),
                        "chat_room_id": str(room.id),
                    },
                )
            else:
                # 🔔 Trainer → User (user push)
                send_user_notification.delay(
                    user_id=str(room.user_id),
                    title="New Message 💬",
                    body="Your trainer sent you a message",
                    data={
                        "type": "NEW_CHAT_MESSAGE",
                        "room_id": str(room.id),
                    },
                )

        # ✅ Fire only after DB commit
        transaction.on_commit(on_commit_actions)

        # ✅ HTTP RESPONSE
        return Response(
            MessageSerializer(msg).data,
            status=status.HTTP_201_CREATED,
        )



# -------------------------------------------------
# SEND MEDIA / UNIFIED MESSAGE ENDPOINT
# -------------------------------------------------
class SendMediaMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UserMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        room = get_object_or_404(
            ChatRoom,
            id=serializer.validated_data["room_id"],
            is_active=True,
        )

        try:
            user_uuid = uuid.UUID(str(request.user.id))
        except ValueError:
            return Response(
                {"detail": "Invalid user id in token"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if user_uuid not in (room.user_id, room.trainer_user_id):
            return Response(
                {"detail": "Forbidden"},
                status=status.HTTP_403_FORBIDDEN,
            )

        file = serializer.validated_data.get("file")
        msg_type = serializer.validated_data["type"]

        msg = Message.objects.create(
            room=room,
            sender_user_id=user_uuid,
            sender_role=(
                Message.SENDER_USER
                if user_uuid == room.user_id
                else Message.SENDER_TRAINER
            ),
            type=msg_type,
            text=serializer.validated_data.get("text", ""),
            file=file,
            duration_sec=serializer.validated_data.get("duration_sec"),
            file_size=file.size if file else None,
            mime_type=file.content_type if file else "",
        )

        room.last_message_at = msg.created_at
        room.save(update_fields=["last_message_at"])

        # ✅ CRITICAL FIX: notify AFTER commit, send ORM instance
        def on_commit_actions():
            # WS notify
            notify_new_message(room.id, msg)

            # 🔔 Notify trainer ONLY when user sends message
            if msg.sender_role == Message.SENDER_USER:
                emit_webhook.delay(
                    event="NEW_CHAT_MESSAGE",
                    payload={
                        "trainer_user_id": str(room.trainer_user_id),
                        "chat_room_id": str(room.id),
                    },
                )
            else:
                # 🔔 Trainer → User (user push)
                send_user_notification.delay(
                    user_id=str(room.user_id),
                    title="New Message 💬",
                    body="Your trainer sent you a message",
                    data={
                        "type": "NEW_CHAT_MESSAGE",
                        "room_id": str(room.id),
                    },
                )


        # ✅ Fire only after DB commit
        transaction.on_commit(on_commit_actions)

        # ✅ HTTP response is serialized normally
        return Response(
            MessageSerializer(msg).data,
            status=status.HTTP_201_CREATED,
        )