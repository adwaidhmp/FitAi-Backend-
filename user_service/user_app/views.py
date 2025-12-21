# user_app/views.py
import requests
from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TrainerBooking, UserProfile
from .serializers import UserProfileSerializer


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_profile(self, user):
        # user is the SimpleNamespace created by SimpleJWTAuth
        return UserProfile.objects.filter(user_id=user.id).first()

    def get(self, request):
        profile = self.get_profile(request.user)
        if not profile:
            return Response(
                {"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = UserProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        profile = self.get_profile(request.user)
        if not profile:
            return Response(
                {"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = UserProfileSerializer(
            profile, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProfileChoicesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Returns choices as { field_name: [{value,label}, ...], ... }
        def choices_for(field_name):
            field = UserProfile._meta.get_field(field_name)
            return [{"value": v, "label": l} for v, l in field.choices]

        data = {
            "gender": choices_for("gender"),
            "goal": choices_for("goal"),
            "body_type": choices_for("body_type"),
            "activity_level": choices_for("activity_level"),
            "exercise_experience": choices_for("exercise_experience"),
        }
        return Response(data)


class BookTrainerView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, trainer_user_id):
        user_id = request.user.id

        if TrainerBooking.objects.filter(
            user_id=user_id,
            status__in=["pending", "approved"],
        ).exists():
            return Response(
                {"detail": "You already have an active trainer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking = TrainerBooking.objects.create(
            user_id=user_id,
            trainer_user_id=trainer_user_id,
        )

        return Response(
            {
                "id": booking.id,
                "status": booking.status,
            },
            status=status.HTTP_201_CREATED,
        )


class MyTrainersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return Response({"detail": "Missing Authorization"}, status=401)

        headers = {"Authorization": auth_header}

        bookings = TrainerBooking.objects.filter(user_id=user_id).order_by(
            "-created_at"
        )

        if not bookings.exists():
            return Response([])

        trainer_user_ids = list({str(b.trainer_user_id) for b in bookings})

        # 🔹 Call auth service ONCE
        auth_resp = requests.post(
            f"{settings.AUTH_SERVICE_URL}/api/v1/auth/internal/users/by-ids/",
            json={"user_ids": trainer_user_ids},
            headers=headers,
            timeout=5,
        )

        if not auth_resp.ok:
            return Response({"detail": "Auth service error"}, status=502)

        users = auth_resp.json()
        user_map = {u["user_id"]: u for u in users}

        data = []
        for b in bookings:
            trainer = user_map.get(str(b.trainer_user_id))

            data.append(
                {
                    "booking_id": str(b.id),
                    "trainer_user_id": str(b.trainer_user_id),
                    "trainer_name": trainer["name"] if trainer else None,
                    "status": b.status,
                    "created_at": b.created_at,
                    "is_active": b.status == TrainerBooking.STATUS_APPROVED,
                }
            )

        return Response(data)


class RemoveTrainerView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        booking = TrainerBooking.objects.filter(
            user_id=request.user.id,
            status__in=["pending", "approved"],
        ).first()

        if not booking:
            return Response(
                {"detail": "No active trainer found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        booking.status = TrainerBooking.STATUS_CANCELLED
        booking.save()

        return Response(
            {"detail": "Trainer removed"},
            status=status.HTTP_200_OK,
        )
