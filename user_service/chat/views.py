# chat/views.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import ChatRoom, Message
from .serializers import MessageSerializer
from .ws_notify import notify_new_message
from rest_framework.generics import ListAPIView


class UploadMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        room_id = request.data.get("room_id")
        msg_type = request.data.get("type")

        room = get_object_or_404(ChatRoom, id=room_id)

        if request.user not in (room.user, room.trainer):
            return Response(status=403)

        msg = Message.objects.create(
            room=room,
            sender=request.user,
            type=msg_type,
            text=request.data.get("text", ""),
            file=request.FILES.get("file"),
            duration_sec=request.data.get("duration_sec"),
        )

        notify_new_message(room.id, msg)

        return Response(MessageSerializer(msg).data, status=201)


class ChatHistoryView(ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        room_id = self.kwargs["room_id"]
        room = get_object_or_404(ChatRoom, id=room_id)

        if self.request.user not in (room.user, room.trainer):
            return Message.objects.none()

        return Message.objects.filter(room=room).order_by("created_at")