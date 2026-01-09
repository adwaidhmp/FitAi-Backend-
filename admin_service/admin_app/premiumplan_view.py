import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings

class AdminPremiumPlanProxyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Proxy: Get all premium plans (admin)
        """
        url = f"{settings.USER_SERVICE_URL}/api/v1/user/admin/premium/plan/"

        response = requests.get(
            url,
            headers={
                "Authorization": request.headers.get("Authorization"),
            },
            timeout=10,
        )

        return Response(response.json(), status=response.status_code)

    def post(self, request):
        """
        Proxy: Create / Update premium plan
        """
        url = f"{settings.USER_SERVICE_URL}/api/v1/user/admin/premium/plan/"

        response = requests.post(
            url,
            json=request.data,
            headers={
                "Authorization": request.headers.get("Authorization"),
            },
            timeout=10,
        )

        return Response(response.json(), status=response.status_code)