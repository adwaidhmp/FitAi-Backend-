import hmac
import logging
import secrets
import time

import redis
from django.conf import settings

logger = logging.getLogger(__name__)

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

OTP_TTL = getattr(settings, "OTP_TTL_SECONDS", 300)
OTP_RATE_LIMIT_TTL = getattr(settings, "OTP_RATE_LIMIT_TTL", 60)
OTP_LENGTH = getattr(settings, "OTP_LENGTH", 6)
MAX_FAILED_ATTEMPTS = getattr(settings, "OTP_MAX_FAILED_ATTEMPTS", 5)
FAILED_ATTEMPT_TTL = getattr(settings, "OTP_FAILED_ATTEMPT_TTL", 600)


def _norm(email: str) -> str:
    return email.lower().strip()


def _otp_key(email: str, purpose: str = "register"):
    return f"otp:{purpose}:{_norm(email)}"


def _rl_key(email: str, purpose: str = "register"):
    return f"otp_rl:{purpose}:{_norm(email)}"


def _fail_key(email: str, purpose: str = "register"):
    return f"otp_fail:{purpose}:{_norm(email)}"


def generate_otp(length: int = None) -> str:
    length = length or OTP_LENGTH
    # generate a secure numeric OTP with leading digits allowed
    otp = "".join(str(secrets.randbelow(10)) for _ in range(length))
    return otp


def store_otp(email: str, otp: str, purpose: str = "register", ttl: int = None):
    key = _otp_key(email, purpose)
    try:
        redis_client.setex(key, ttl or OTP_TTL, otp)
    except redis.exceptions.RedisError as e:
        logger.exception("Redis error storing OTP for %s: %s", email, e)
        raise


def get_otp(email: str, purpose: str = "register"):
    try:
        return redis_client.get(_otp_key(email, purpose))
    except redis.exceptions.RedisError as e:
        logger.exception("Redis error get_otp: %s", e)
        return None


def delete_otp(email: str, purpose: str = "register"):
    try:
        redis_client.delete(_otp_key(email, purpose))
    except redis.exceptions.RedisError:
        logger.exception("Redis error delete_otp for %s", email)


def can_request_otp(email: str, purpose: str = "register") -> bool:
    """
    Atomic rate-limit check: returns False if caller must wait.
    Uses SET NX EX to avoid exists->set race.
    """
    rl = _rl_key(email, purpose)
    try:
        # set with NX and EX returns True if set, None/False if existed
        ok = redis_client.set(rl, int(time.time()), nx=True, ex=OTP_RATE_LIMIT_TTL)
        return bool(ok)
    except redis.exceptions.RedisError as e:
        # on Redis failure, be conservative and allow request (or choose otherwise)
        logger.exception("Redis error in can_request_otp: %s", e)
        return True


def record_failed_attempt(email: str, purpose: str = "register"):
    fk = _fail_key(email, purpose)
    try:
        pipe = redis_client.pipeline()
        pipe.incr(fk)
        pipe.expire(fk, FAILED_ATTEMPT_TTL)
        count, _ = pipe.execute()
        return int(count)
    except redis.exceptions.RedisError as e:
        logger.exception("Redis error record_failed_attempt: %s", e)
        # return a large number as conservative measure? return 1 to avoid blocking legit users
        return 1


def get_failed_attempts(email: str, purpose: str = "register") -> int:
    try:
        val = redis_client.get(_fail_key(email, purpose))
        return int(val) if val else 0
    except redis.exceptions.RedisError as e:
        logger.exception("Redis error get_failed_attempts: %s", e)
        return 0


def reset_failed_attempts(email: str, purpose: str = "register"):
    try:
        redis_client.delete(_fail_key(email, purpose))
    except redis.exceptions.RedisError:
        logger.exception("Redis error reset_failed_attempts for %s", email)


def verify_otp(email: str, otp_candidate: str, purpose: str = "register") -> bool:
    """
    Constant-time comparison, deletes on success, increments fail counter on failure.
    """
    key = _otp_key(email, purpose)
    try:
        stored = redis_client.get(key)
    except redis.exceptions.RedisError as e:
        logger.exception("Redis error verify_otp get: %s", e)
        return False

    if not stored:
        # no OTP or expired
        return False

    # use constant-time compare
    if hmac.compare_digest(stored, otp_candidate):
        try:
            redis_client.delete(key)
            reset_failed_attempts(email, purpose)
        except redis.exceptions.RedisError:
            logger.exception("Redis error cleaning up OTP for %s", email)
        return True

    # wrong OTP -> increment fail count
    count = record_failed_attempt(email, purpose)
    logger.debug("OTP verify failed for %s, count=%s", email, count)
    return False
