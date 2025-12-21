import requests
from django.conf import settings
from django.db import transaction
from requests.exceptions import ConnectionError, Timeout
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TrainerCertificate, TrainerProfile
from .permissions import IsTrainerOwner
from .serializers import (CertificateUploadSerializer,
                          TrainerCertificateModelSerializer,
                          TrainerProfileSerializer)


class TrainerProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTrainerOwner]
    parser_classes = [MultiPartParser, FormParser]

    def get_profile(self, user):
        return TrainerProfile.objects.filter(user_id=user.id).first()

    def get(self, request):
        profile = self.get_profile(request.user)
        if not profile:
            return Response(
                {"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = TrainerProfileSerializer(profile, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        orig_profile = self.get_profile(request.user)
        if not orig_profile:
            return Response(
                {"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # validate incoming profile data up front (keeps early errors)
        tmp_serializer = TrainerProfileSerializer(
            orig_profile, data=request.data, partial=True, context={"request": request}
        )
        tmp_serializer.is_valid(raise_exception=True)

        files = request.FILES.getlist("files") if hasattr(request, "FILES") else []
        if files:
            upload_serializer = CertificateUploadSerializer(data={"files": files})
            upload_serializer.is_valid(raise_exception=True)
            files = upload_serializer.validated_data.get("files", files)

        created_certs = []
        with transaction.atomic():
            # lock the row and use the locked instance for saving
            locked_profile = TrainerProfile.objects.select_for_update().get(
                pk=orig_profile.pk
            )

            # re-create serializer bound to the locked instance, validate, then save
            profile_serializer = TrainerProfileSerializer(
                locked_profile,
                data=request.data,
                partial=True,
                context={"request": request},
            )
            profile_serializer.is_valid(raise_exception=True)
            profile = profile_serializer.save()

            # recompute is_completed only when needed and save minimally
            new_is_completed = (
                bool(profile.bio)
                and bool(profile.specialties)
                and profile.experience_years > 0
            )
            if profile.is_completed != new_is_completed:
                profile.is_completed = new_is_completed
                profile.save(update_fields=["is_completed"])

            # create cert records
            for f in files:
                created_certs.append(TrainerCertificate(trainer=profile, file=f))
            if created_certs:
                TrainerCertificate.objects.bulk_create(created_certs)
                # reload created certs for serialization
                created_certs = list(
                    TrainerCertificate.objects.filter(trainer=profile).order_by("-id")[
                        : len(created_certs)
                    ]
                )

        certs_data = TrainerCertificateModelSerializer(
            created_certs, many=True, context={"request": request}
        ).data
        profile_data = TrainerProfileSerializer(
            profile, context={"request": request}
        ).data

        status_code = status.HTTP_201_CREATED if certs_data else status.HTTP_200_OK
        return Response(
            {"profile": profile_data, "created_certificates": certs_data},
            status=status_code,
        )


class PendingClientsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        auth_header = request.headers.get("Authorization")
        headers = {"Authorization": auth_header}

        try:
            resp = requests.get(
                f"{settings.USER_SERVICE_URL}/api/v1/user/training/pending/",
                headers=headers,
                timeout=3,
            )
        except (ConnectionError, Timeout):
            return Response(
                {"detail": "User service temporarily unavailable. Try again."},
                status=503,
            )

        if resp.status_code != 200:
            return Response(
                {"detail": "Failed to fetch pending clients"},
                status=resp.status_code,
            )

        bookings = resp.json()

        if not bookings:
            return Response([], status=200)

        # collect user_ids
        user_ids = list({b["user_id"] for b in bookings})

        # bulk fetch user names
        users_resp = requests.post(
            f"{settings.AUTH_SERVICE_URL}/api/v1/auth/internal/users/bulk/",
            json={"user_ids": user_ids},
            headers=headers,
            timeout=5,
        )

        users = users_resp.json() if users_resp.status_code == 200 else []
        user_map = {u.get("id"): u.get("name") for u in users}

        # merge
        result = []
        for b in bookings:
            result.append(
                {
                    **b,
                    "user_name": user_map.get(b["user_id"]),
                }
            )

        return Response(result, status=200)


class DecideUserBookingView(APIView):
    permission_classes = [IsAuthenticated, IsTrainerOwner]

    def post(self, request, booking_id):
        auth_header = request.headers.get("Authorization")

        action = request.data.get("action")
        if action not in ["approve", "reject"]:
            return Response(
                {"detail": "Invalid action"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            resp = requests.post(
                f"{settings.USER_SERVICE_URL}/api/v1/user/training/booking/{booking_id}/",
                json={"action": action},   # ✅ SEND BODY
                headers={"Authorization": auth_header},
                timeout=5,
            )
        except requests.RequestException:
            return Response(
                {"detail": "User service unreachable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            data = resp.json()
        except ValueError:
            return Response(
                {
                    "detail": "Invalid response from user service",
                    "raw": resp.text, 
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(data, status=resp.status_code)


class ApprovedUsersView(APIView):
    permission_classes = [IsAuthenticated, IsTrainerOwner]

    def get(self, request):
        auth_header = request.headers.get("Authorization")

        # 1. Get approved bookings from user service
        bookings_resp = requests.get(
            f"{settings.USER_SERVICE_URL}/api/v1/user/training/bookings/approved/",
            headers={"Authorization": auth_header},
            timeout=5,
        )

        if bookings_resp.status_code != 200:
            return Response(
                {"detail": "Failed to fetch approved users"},
                status=bookings_resp.status_code,
            )

        bookings = bookings_resp.json()

        if not bookings:
            return Response([], status=200)

        # 2. Extract user_ids
        user_ids = list({b["user_id"] for b in bookings})

        # 3. Fetch user names from auth service (BULK)
        users_resp = requests.post(
            f"{settings.AUTH_SERVICE_URL}/api/v1/auth/internal/users/bulk/",
            json={"user_ids": user_ids},
            headers={"Authorization": auth_header},
            timeout=5,
        )

        if users_resp.status_code != 200:
            return Response(
                {"detail": "Failed to fetch user details"},
                status=users_resp.status_code,
            )

        users = users_resp.json()
        user_map = {u["id"]: u["name"] for u in users}

        # 4. Merge data
        result = []
        for b in bookings:
            result.append(
                {
                    "booking_id": b["booking_id"],
                    "user_id": b["user_id"],
                    "user_name": user_map.get(b["user_id"]),
                    "approved_at": b["approved_at"],
                }
            )

        return Response(result, status=200)
