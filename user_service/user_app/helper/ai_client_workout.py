import sys
import requests
from django.conf import settings

def request_ai_workout(payload: dict) -> dict:
    url = f"{settings.AI_SERVICE_BASE_URL}/api/v1/workout/generate/"

    sys.stderr.write("\n🔥🔥🔥 WORKOUT AI PAYLOAD SENT 🔥🔥🔥\n")
    sys.stderr.write(str(payload) + "\n")
    sys.stderr.flush()

    response = requests.post(
        url,
        json=payload,
        timeout=60,
    )

    if response.status_code != 200:
        sys.stderr.write("\n❌❌❌ WORKOUT AI ERROR ❌❌❌\n")
        sys.stderr.write(f"STATUS: {response.status_code}\n")
        sys.stderr.write(f"BODY: {response.text}\n")
        sys.stderr.flush()
        response.raise_for_status()

    return response.json()