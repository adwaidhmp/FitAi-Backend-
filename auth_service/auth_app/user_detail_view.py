from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import User


class UserEmailByIdView(APIView):

    def post(self, request):
        user_id = request.data.get("user_id")

        if not user_id:
            return Response(
                {"error": "user_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "user_id": str(user.id),
                "email": user.email,
            }
        )