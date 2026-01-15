import requests
from django.conf import settings
from django.db import transaction
from requests.exceptions import ConnectionError, Timeout
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.cache import cache
from .models import TrainerCertificate, TrainerProfile
from .permissions import IsTrainerOwner
from .serializers import (
    CertificateUploadSerializer,
    TrainerCertificateModelSerializer,
    TrainerProfileSerializer,
)
from .tasks import publish_booking_decision


class TrainerProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTrainerOwner]
    parser_classes = [MultiPartParser, FormParser]

    CACHE_TTL = 60 * 30  # 30 minutes
    CACHE_VERSION = "v1"

    def _cache_key(self, user_id):
        return f"trainer_profile:{user_id}:{self.CACHE_VERSION}"

    def get_profile(self, user):
        return TrainerProfile.objects.filter(user_id=user.id).first()

    # -------------------------
    # GET (CACHED)
    # -------------------------
    def get(self, request):
        cache_key = self._cache_key(request.user.id)

        cached = cache.get(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)

        profile = self.get_profile(request.user)
        if not profile:
            return Response(
                {"detail": "Profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = TrainerProfileSerializer(
            profile, context={"request": request}
        ).data

        cache.set(cache_key, data, self.CACHE_TTL)
        return Response(data, status=status.HTTP_200_OK)

    # -------------------------
    # PATCH (INVALIDATES CACHE)
    # -------------------------
    def patch(self, request):
        orig_profile = self.get_profile(request.user)
        if not orig_profile:
            return Response(
                {"detail": "Profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # validate early
        tmp_serializer = TrainerProfileSerializer(
            orig_profile,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        tmp_serializer.is_valid(raise_exception=True)

        files = request.FILES.getlist("files") if hasattr(request, "FILES") else []
        if files:
            upload_serializer = CertificateUploadSerializer(data={"files": files})
            upload_serializer.is_valid(raise_exception=True)
            files = upload_serializer.validated_data.get("files", files)

        created_certs = []

        with transaction.atomic():
            locked_profile = TrainerProfile.objects.select_for_update().get(
                pk=orig_profile.pk
            )

            profile_serializer = TrainerProfileSerializer(
                locked_profile,
                data=request.data,
                partial=True,
                context={"request": request},
            )
            profile_serializer.is_valid(raise_exception=True)
            profile = profile_serializer.save()

            new_is_completed = (
                bool(profile.bio)
                and bool(profile.specialties)
                and profile.experience_years > 0
            )
            if profile.is_completed != new_is_completed:
                profile.is_completed = new_is_completed
                profile.save(update_fields=["is_completed"])

            for f in files:
                created_certs.append(TrainerCertificate(trainer=profile, file=f))

            if created_certs:
                TrainerCertificate.objects.bulk_create(created_certs)
                created_certs = list(
                    TrainerCertificate.objects.filter(trainer=profile)
                    .order_by("-id")[: len(created_certs)]
                )

        # 🔥 DELETE CACHE AFTER SUCCESSFUL UPDATE
        cache.delete(self._cache_key(request.user.id))

        certs_data = TrainerCertificateModelSerializer(
            created_certs, many=True, context={"request": request}
        ).data
        profile_data = TrainerProfileSerializer(
            profile, context={"request": request}
        ).data

        status_code = (
            status.HTTP_201_CREATED if certs_data else status.HTTP_200_OK
        )
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


class DecideBookingView(APIView):
    permission_classes = [IsAuthenticated, IsTrainerOwner]

    def post(self, request, booking_id):
        action = request.data.get("action")

        if action not in ["approve", "reject"]:
            return Response({"detail": "Invalid action"}, status=400)

        auth_header = request.headers.get("Authorization")

        # 🔹 1. Ask USER SERVICE for booking details
        try:
            booking_resp = requests.get(
                f"{settings.USER_SERVICE_URL}/api/v1/user/training/bookings/{booking_id}/",
                headers={"Authorization": auth_header},
                timeout=5,
            )
        except (ConnectionError, Timeout):
            return Response(
                {"detail": "User service unavailable"},
                status=503,
            )

        if booking_resp.status_code != 200:
            return Response(
                {"detail": "Failed to fetch booking"},
                status=booking_resp.status_code,
            )

        booking = booking_resp.json()

        user_id = booking.get("user_id")
        trainer_user_id = booking.get("trainer_user_id")

        # 🔐 Safety check
        if trainer_user_id != str(request.user.id):
            return Response(
                {"detail": "Not authorized for this booking"},
                status=403,
            )

        # 🔹 2. Publish COMPLETE event
        publish_booking_decision.delay(
            {
                "event": "BOOKING_DECIDED",
                "booking_id": str(booking_id),
                "user_id": user_id,                     # ✅ REQUIRED
                "trainer_user_id": str(request.user.id),
                "action": action,
            }
        )

        return Response(
            {"detail": "Decision queued"},
            status=202,
        )


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
