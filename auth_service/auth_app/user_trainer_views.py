from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User


class ApprovedTrainerListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        trainers = User.objects.filter(
            role=User.ROLE_TRAINER,
            is_approved=True,
            is_active=True,
        )

        return Response(
            [
                {
                    "user_id": str(t.id),
                    "name": t.name if t.name else t.email,
                }
                for t in trainers
            ]
        )


# to see name in booking details
class UsersByIdsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_ids = request.data.get("user_ids", [])

        users = User.objects.filter(id__in=user_ids)

        return Response(
            [
                {
                    "user_id": str(u.id),
                    "name": u.name if u.name else u.email,
                }
                for u in users
            ]
        )


# to se user name in trainer pending clients view
class BulkUserInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_ids = request.data.get("user_ids")

        if not isinstance(user_ids, list) or not user_ids:
            return Response(
                {"detail": "user_ids must be a non-empty list"},
                status=400,
            )

        users = User.objects.filter(id__in=user_ids).only("id", "name")

        data = [
            {
                "id": str(user.id),
                "name": user.name,
            }
            for user in users
        ]

        return Response(data, status=200)
