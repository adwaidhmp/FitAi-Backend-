from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TrainerProfile
from .permissions import IsAdmin
from .serializers import TrainerProfileSerializer


class AdminTrainerProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request, user_id):
        profile = get_object_or_404(TrainerProfile, user_id=user_id)

        serializer = TrainerProfileSerializer(profile, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
