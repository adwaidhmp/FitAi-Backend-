import requests
from django.conf import settings


def request_ai_workout(payload: dict) -> dict:
    url = f"{settings.AI_SERVICE_BASE_URL}/api/v1/workout/generate/"
    """
    Calls AI Service to generate weekly workout.
    """
    response = requests.post(
        url,
        json=payload,
        timeout=60,
    )

    response.raise_for_status()
    return response.json()