from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .helper.proxy_helper import forward_request


class TrainerStartCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_id):
        return forward_request(
            request=request,
            method="POST",
            path=f"/api/chat/calls/start/{room_id}/",
        )



class TrainerAcceptCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, call_id):
        return forward_request(
            request=request,
            method="POST",
            path=f"/api/chat/calls/{call_id}/accept/",
        )
    


class TrainerEndCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, call_id):
        return forward_request(
            request=request,
            method="POST",
            path=f"/api/chat/calls/{call_id}/end/",
        )
