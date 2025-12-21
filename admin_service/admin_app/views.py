import requests
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permission import IsAdmin


def get_auth_header(request):
    auth = request.headers.get("Authorization")
    if not auth:
        return None
    return {"Authorization": auth}


class AdminUserListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        headers = get_auth_header(request)
        if not headers:
            return Response({"detail": "Missing Authorization header"}, status=401)

        try:
            resp = requests.get(
                f"{settings.AUTH_SERVICE_URL}/api/v1/auth/internal/admin/users/",
                headers=headers,
                timeout=5,
            )
        except requests.RequestException:
            return Response({"detail": "Auth service unreachable"}, status=503)

        if not resp.ok:
            return Response(
                {
                    "detail": "Auth service error",
                    "status_code": resp.status_code,
                    "auth_response": resp.text,
                },
                status=resp.status_code,
            )

        return Response(resp.json())


class AdminUserStatusView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, user_id):
        headers = get_auth_header(request)
        if not headers:
            return Response({"detail": "Missing Authorization header"}, status=401)

        is_active = request.data.get("is_active")

        if isinstance(is_active, str):
            is_active = is_active.lower() == "true"

        if not isinstance(is_active, bool):
            return Response(
                {"detail": "is_active must be true or false"},
                status=400,
            )

        try:
            resp = requests.post(
                f"{settings.AUTH_SERVICE_URL}/api/v1/auth/internal/admin/users/{user_id}/status/",
                headers=headers,
                json={"is_active": is_active},
                timeout=5,
            )
        except requests.RequestException:
            return Response({"detail": "Auth service unreachable"}, status=503)

        if not resp.ok:
            return Response(
                {"detail": "User status update failed"},
                status=resp.status_code,
            )

        return Response(
            {
                "user_id": str(user_id),
                "is_active": is_active,
                "detail": "User status updated successfully",
            },
            status=200,
        )


class AdminTrainerListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        headers = get_auth_header(request)
        if not headers:
            return Response({"detail": "Missing Authorization header"}, status=401)

        try:
            resp = requests.get(
                f"{settings.AUTH_SERVICE_URL}/api/v1/auth/internal/admin/trainers/",
                headers=headers,
                timeout=5,
            )
        except requests.RequestException:
            return Response({"detail": "Auth service unreachable"}, status=503)

        if not resp.ok:
            return Response(
                {"detail": "Failed to fetch trainers"},
                status=resp.status_code,
            )

        return Response(resp.json())


class AdminTrainerDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, user_id):
        headers = get_auth_header(request)
        if not headers:
            return Response(
                {"detail": "Missing Authorization header"},
                status=401,
            )

        try:
            trainer_resp = requests.get(
                f"{settings.TRAINER_SERVICE_URL}/api/v1/trainer/internal/admin/trainers/{user_id}/profile/",
                headers=headers,
                timeout=5,
            )
        except requests.RequestException:
            return Response(
                {"detail": "Trainer service unreachable"},
                status=503,
            )

        if trainer_resp.status_code == 404:
            return Response(
                {"detail": "Trainer profile not found"},
                status=404,
            )

        if not trainer_resp.ok:
            return Response(
                {
                    "detail": "Trainer service error",
                    "status_code": trainer_resp.status_code,
                    "body": trainer_resp.text,
                },
                status=trainer_resp.status_code,
            )

        # ✅ SAFE JSON PARSE
        try:
            profile_data = trainer_resp.json()
        except ValueError:
            return Response(
                {
                    "detail": "Invalid JSON from trainer service",
                    "raw_response": trainer_resp.text,
                },
                status=502,
            )

        return Response(
            {"profile": profile_data},
            status=200,
        )


class AdminApproveTrainerView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, user_id):
        headers = get_auth_header(request)
        if not headers:
            return Response({"detail": "Missing Authorization header"}, status=401)

        try:
            resp = requests.post(
                f"{settings.AUTH_SERVICE_URL}/api/v1/auth/internal/admin/trainers/{user_id}/approve/",
                headers=headers,
                timeout=5,
            )
        except requests.RequestException:
            return Response({"detail": "Auth service unreachable"}, status=503)

        if not resp.ok:
            return Response(
                {"detail": "Approval failed"},
                status=resp.status_code,
            )

        return Response({"detail": "Trainer approved"})
