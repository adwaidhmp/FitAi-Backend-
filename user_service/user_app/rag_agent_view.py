import requests
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings


class AskAIAgentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        question = request.data.get("question", "").strip()

        if not question:
            return Response({"detail": "Question is required"}, status=400)

        payload = {"question": question}

        url = f"{settings.AI_KNOWLEDGE_SERVICE_URL}/api/v1/ai/ask"
        print("✅ Calling AI URL:", url)

        try:
            ai_response = requests.post(
                url,
                json=payload,
                timeout=60,
            )
        except requests.RequestException as e:
            print("🔥 AI REQUEST FAILED:", repr(e))
            return Response(
                {"detail": str(e)},
                status=503,
            )

        print("✅ AI responded:", ai_response.status_code)

        # Safe JSON handling
        try:
            data = ai_response.json()
        except Exception:
            data = {"raw": ai_response.text}

        return Response(data, status=ai_response.status_code)
