from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


@shared_task
def send_otp_email_task(email: str, otp: str, purpose: str = "register"):
    subject = "Your verification code"
    body = (
        f"Your OTP for {purpose} is: {otp}\n\n"
        f"This code expires in {getattr(settings, 'OTP_TTL_SECONDS', 300)//60} minutes.\n"
        "If you did not request this, ignore this email."
    )
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)


from django.utils import timezone

from .models import RefreshTokenRecord


@shared_task
def cleanup_expired_refresh_tokens():
    now = timezone.now()
    # delete expired rows, or archive them instead if needed
    qs = RefreshTokenRecord.objects.filter(expires_at__lt=now)
    count = qs.delete()[0]
    return {"deleted": count}
