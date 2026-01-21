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
            return Response(
                {"detail": "Question is required"},
                status=400,
            )

        payload = {
            "question": question,
            # chat_history will be added later
        }

        try:
            ai_response = requests.post(
                f"{settings.AI_KNOWLEDGE_SERVICE_URL}/api/v1/ai/ask",
                json=payload,
                timeout=60,
            )
        except requests.RequestException:
            return Response(
                {"detail": "AI service unavailable"},
                status=503,
            )

        # Pass-through response
        return Response(
            ai_response.json(),
            status=ai_response.status_code,
        )
