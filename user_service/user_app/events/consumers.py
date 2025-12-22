import json
import requests
from django.conf import settings
from user_app.models import UserProfile, DietPlan
from user_app.helper.ai_payload import build_payload_from_profile


def handle_weight_updated(ch, method, properties, body):
    data = json.loads(body)
    user_id = data["user_id"]

    try:
        profile = UserProfile.objects.get(user_id=user_id)
        payload = build_payload_from_profile(profile)

        resp = requests.post(
            f"{settings.AI_SERVICE_BASE_URL}/api/v1/diet/generate/",
            json=payload,
            timeout=20,
        )
        resp.raise_for_status()

        ai = resp.json()

        DietPlan.objects.create(
            user_id=user_id,
            daily_calories=ai["daily_calories"],
            macros=ai["macros"],
            meals=ai["meals"],
            version=ai["version"],
        )

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print("Diet regeneration failed:", e)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
