import requests
from django.conf import settings


class AIServiceError(Exception):
    pass


def generate_diet_plan(profile_data: dict):
    url = f"{settings.AI_SERVICE_BASE_URL}/api/v1/diet/generate/"

    try:
        response = requests.post(
            url,
            json=profile_data,
            timeout=20,
        )
    except requests.RequestException:
        raise AIServiceError("AI service unreachable")

    if response.status_code != 200:
        raise AIServiceError(response.text)

    return response.json()



def estimate_nutrition(food_text: str) -> dict:
    """
    Calls ai_service to estimate nutrition for given food text.
    This function does NOT do any AI logic itself.
    """

    if not food_text or not food_text.strip():
        raise ValueError("food_text cannot be empty")

    url = f"{settings.AI_SERVICE_BASE_URL}/api/v1/diet/estimate-nutrition/"

    try:
        response = requests.post(
            url,
            json={"food_text": food_text},
            timeout=10,  # never block user service
        )
    except requests.RequestException as e:
        raise AIServiceError("AI service not reachable") from e

    if response.status_code != 200:
        raise AIServiceError(
            f"AI service error: {response.status_code}"
        )

    data = response.json()

    # minimal validation (DO NOT trust blindly)
    if "total" not in data:
        raise AIServiceError("Invalid AI response format")

    return data