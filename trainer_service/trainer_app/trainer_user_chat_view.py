from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .helper.proxy_helper import forward_request



class TrainerChatRoomListProxyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return forward_request(
            request,
            method="GET",
            path="/api/chat/rooms/",
        )



class TrainerChatHistoryProxyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_id):
        return forward_request(
            request,
            method="GET",
            path=f"/api/chat/rooms/{room_id}/messages/",
            params=request.query_params,
        )
    


class TrainerSendTextMessageProxyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return forward_request(
            request,
            method="POST",
            path="/api/chat/send/text/",
            data=request.data,
        )
    


class TrainerSendMediaProxyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Copy data safely
        data = request.data.copy()

        # IMPORTANT: remove file fields from data
        # Adjust key names if different
        data.pop("file", None)

        return forward_request(
            request,
            method="POST",
            path="/api/chat/send/media/",
            data=data,
            files=request.FILES,
        )