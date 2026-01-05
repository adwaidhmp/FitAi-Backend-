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
from .helper.message_normalizer import normalize_for_ws
from django.db.models import Q

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
        ).order_by("-created_at")



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
            user_uuid = uuid.UUID(request.user.id)
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

        msg = Message.objects.create(
            room=room,
            sender_user_id=user_uuid,
            sender_role=Message.SENDER_USER,
            type=Message.TEXT,
            text=text,
        )

        room.last_message_at = msg.created_at
        room.save(update_fields=["last_message_at"])

        data = MessageSerializer(msg).data

        # 🔥 normalize ONLY for WS
        ws_payload = normalize_for_ws(data)
        notify_new_message(room.id, ws_payload)

        return Response(data, status=status.HTTP_201_CREATED)



# -------------------------------------------------
# SEND MEDIA / UNIFIED MESSAGE ENDPOINT
# -------------------------------------------------
class SendMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UserMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        room = get_object_or_404(
            ChatRoom,
            id=serializer.validated_data["room_id"],
            is_active=True,
        )

        if request.user.id not in (room.user_id, room.trainer_user_id):
            return Response({"detail": "Forbidden"}, status=403)

        file = serializer.validated_data.get("file")

        msg = Message.objects.create(
            room=room,
            sender_user_id=request.user.id,
            sender_role=Message.SENDER_USER,
            type=serializer.validated_data["type"],
            text=serializer.validated_data.get("text", ""),
            file=file,
            duration_sec=serializer.validated_data.get("duration_sec"),
            file_size=file.size if file else None,
            mime_type=file.content_type if file else "",
        )

        room.last_message_at = msg.created_at
        room.save(update_fields=["last_message_at"])

        notify_new_message(room.id, msg)

        return Response(
            MessageSerializer(msg).data,
            status=status.HTTP_201_CREATED,
        )
