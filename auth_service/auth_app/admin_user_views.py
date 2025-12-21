# auth_service/admin/admin_user_views.py
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .permission import IsAdmin
from .serializers import AdminUserListSerializer, AdminUserStatusSerializer


class AdminUserListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        users = User.objects.filter(role=User.ROLE_USER)
        serializer = AdminUserListSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminUserStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def post(self, request, user_id):
        serializer = AdminUserStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = get_object_or_404(User, id=user_id)

        is_active = serializer.validated_data["is_active"]

        if user.is_active == is_active:
            return Response(
                {"detail": "User already in requested state"}, status=status.HTTP_200_OK
            )

        user.is_active = is_active
        user.save(update_fields=["is_active"])

        return Response(
            {"detail": "User status updated", "is_active": user.is_active},
            status=status.HTTP_200_OK,
        )
