from uuid import UUID

import requests
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TrainerBooking, UserProfile
from .permissions import IsTrainer


class ApprovedTrainerListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return Response({"detail": "Missing Authorization"}, status=401)

        headers = {"Authorization": auth_header}

        # 1. Get approved trainers with name from auth_service
        auth_resp = requests.get(
            f"{settings.AUTH_SERVICE_URL}/api/v1/auth/internal/trainers/approved/",
            headers=headers,
            timeout=5,
        )

        if not auth_resp.ok:
            return Response({"detail": "Auth service error"}, status=502)

        # expected: [{ user_id, name }]
        approved_trainers = auth_resp.json()

        if not approved_trainers:
            return Response([])

        user_ids = [t["user_id"] for t in approved_trainers]

        # 2. Get trainer profiles from trainer_service
        trainer_resp = requests.post(
            f"{settings.TRAINER_SERVICE_URL}/api/v1/trainer/internal/trainers/by-user-ids/",
            json={"user_ids": user_ids},
            headers=headers,
            timeout=5,
        )

        if not trainer_resp.ok:
            return Response({"detail": "Trainer service error"}, status=502)

        profiles = trainer_resp.json()

        profile_map = {p["user_id"]: p for p in profiles}

        # 3. Merge response
        result = []
        for trainer in approved_trainers:
            profile = profile_map.get(trainer["user_id"])
            if not profile:
                continue

            result.append(
                {
                    "id": trainer["user_id"],
                    "name": trainer["name"],
                    "bio": profile["bio"],
                    "specialties": profile["specialties"],
                    "experience_years": profile["experience_years"],
                }
            )

        return Response(result)


class PendingClientsTrainer(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        trainer_id = UUID(str(request.user.id))

        bookings = TrainerBooking.objects.filter(
            trainer_user_id=trainer_id,
            status=TrainerBooking.STATUS_PENDING,
        ).select_related(None)

        # collect user ids
        user_ids = [b.user_id for b in bookings]

        # fetch profiles in ONE query
        profiles = UserProfile.objects.filter(user_id__in=user_ids)
        profile_map = {str(p.user_id): p for p in profiles}

        data = []
        for b in bookings:
            profile = profile_map.get(str(b.user_id))

            data.append(
                {
                    "booking_id": str(b.id),
                    "user_id": str(b.user_id),
                    # profile data (safe, nullable)
                    "gender": profile.gender if profile else None,
                    "goal": profile.goal if profile else None,
                    "notes": profile.notes if profile else None,
                    "created_at": b.created_at,
                }
            )

        return Response(data, status=200)


class DecideBookingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        trainer_id = request.user.id
        action = request.data.get("action")

        if action not in ["approve", "reject"]:
            return Response(
                {"detail": "Invalid action"},
                status=400,
            )

        booking = TrainerBooking.objects.filter(
            id=booking_id,
            trainer_user_id=trainer_id,
            status=TrainerBooking.STATUS_PENDING,
        ).first()

        if not booking:
            return Response(
                {"detail": "Booking not found or not pending"},
                status=404,
            )

        if action == "approve":
            booking.status = TrainerBooking.STATUS_APPROVED
        else:
            booking.status = TrainerBooking.STATUS_REJECTED

        booking.save(update_fields=["status"])

        return Response(
            {
                "detail": f"Booking {action}d",
                "status": booking.status,
            },
            status=200,
        )


class ApprovedUsersForTrainerView(APIView):
    permission_classes = [IsAuthenticated, IsTrainer]

    def get(self, request):
        bookings = TrainerBooking.objects.filter(
            trainer_user_id=request.user.id,
            status=TrainerBooking.STATUS_APPROVED,
        ).order_by("-created_at")

        data = [
            {
                "booking_id": str(b.id),
                "user_id": str(b.user_id),
                "approved_at": b.created_at,
            }
            for b in bookings
        ]

        return Response(data, status=200)
