from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.core.exceptions import ObjectDoesNotExist

from .models import TrainerProfile


class SaveFCMTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get("fcm_token")

        if not token or not token.strip():
            return Response(
                {"error": "fcm_token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            profile = TrainerProfile.objects.get(
                user_id=request.user.id
            )
        except ObjectDoesNotExist:
            # This should NEVER happen if your system is correct
            return Response(
                {
                    "error": "TrainerProfile missing for authenticated user",
                    "detail": "This indicates a system invariant violation"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Idempotent save
        if profile.fcm_token != token:
            profile.fcm_token = token
            profile.save(update_fields=["fcm_token"])

        return Response(
            {"status": "FCM token saved"},
            status=status.HTTP_200_OK,
        )
