from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TrainerProfile
from .serializers import TrainerProfileSerializer


class TrainerProfilesByUserIdsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_ids = request.data.get("user_ids")

        if not user_ids or not isinstance(user_ids, list):
            return Response(
                {"detail": "user_ids list required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profiles = TrainerProfile.objects.filter(user_id__in=user_ids)

        serializer = TrainerProfileSerializer(profiles, many=True)
        return Response(serializer.data)
