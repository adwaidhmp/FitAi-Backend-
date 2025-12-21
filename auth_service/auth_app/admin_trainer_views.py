# auth_service/admin/admin_trainer_views.py
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .permission import IsAdmin
from .serializers import AdminTrainerListSerializer


class AdminTrainerListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        trainers = User.objects.filter(role=User.ROLE_TRAINER)
        serializer = AdminTrainerListSerializer(trainers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminApproveTrainerView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def post(self, request, user_id):
        trainer = get_object_or_404(
            User,
            id=user_id,
            role=User.ROLE_TRAINER,
        )

        if trainer.is_approved:
            return Response(
                {"detail": "Trainer already approved"}, status=status.HTTP_200_OK
            )

        trainer.is_approved = True
        trainer.save(update_fields=["is_approved"])

        return Response(
            {"detail": "Trainer approved successfully"}, status=status.HTTP_200_OK
        )
