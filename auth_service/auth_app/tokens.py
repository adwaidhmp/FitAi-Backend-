# auth_service/tokens.py
from datetime import datetime, timezone

from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

from .models import RefreshTokenRecord


def _save_refresh_record(refresh_token_obj, user):
    jti = refresh_token_obj["jti"]
    exp_ts = refresh_token_obj["exp"]
    expires_at = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
    RefreshTokenRecord.objects.create(jti=jti, user=user, expires_at=expires_at)


def get_token_pair(user, audience="user_service", issuer="https://auth.internal"):
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token

    # canonical user id claims (store as strings)
    user_id_str = str(user.id)
    access["sub"] = user_id_str  # standard subject claim
    access["user_id"] = user_id_str  # explicit, for libraries that expect user_id

    # additional useful claims
    access["iss"] = issuer
    access["aud"] = audience
    access["roles"] = [user.role] if hasattr(user, "role") else ["user"]
    access["token_type"] = "access"

    # persist refresh jti for revocation
    try:
        _save_refresh_record(refresh, user)
    except Exception:
        # log in prod, but don't block login
        pass

    return {
        "access": str(access),
        "refresh": str(refresh),
    }
