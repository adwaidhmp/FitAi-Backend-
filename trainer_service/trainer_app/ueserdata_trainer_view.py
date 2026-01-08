import requests

from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .permissions import IsTrainer


class TrainerUserOverviewProxyView(APIView):
    """
    Proxy view to fetch user overview data from user_service for trainers.
    """

    permission_classes = [IsAuthenticated, IsTrainer]

    def get(self, request, user_id):
        # 🔗 user_service endpoint
        url = f"{settings.USER_SERVICE_URL}/api/v1/user/trainer/users/{user_id}/overview/"

        # 🔐 Forward auth header
        headers = {
            "Authorization": request.headers.get("Authorization"),
        }

        try:
            response = requests.get(url, headers=headers, timeout=5)
        except requests.RequestException:
            return Response(
                {"detail": "User service unavailable"},
                status=503,
            )

        # 🔁 Pass-through response
        return Response(
            response.json(),
            status=response.status_code,
        )