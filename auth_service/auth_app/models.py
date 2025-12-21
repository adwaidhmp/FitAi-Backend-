import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from .managers import UserManager

phone_validator = RegexValidator(
    regex=r"^\+?[0-9]{7,15}$",
    message="Enter phone number in format: +999999999. Up to 15 digits allowed.",
)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_USER = "user"
    ROLE_TRAINER = "trainer"
    ROLE_ADMIN = "admin"

    ROLE_CHOICES = [
        (ROLE_USER, "User"),
        (ROLE_TRAINER, "Trainer"),
        (ROLE_ADMIN, "Admin"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    oauth_uid = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(unique=True, null=False, max_length=254)
    phone = models.CharField(
        max_length=20, validators=[phone_validator], blank=True, null=True
    )
    name = models.CharField(max_length=150, blank=True)

    # auth and operational fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # required for admin site
    is_verified = models.BooleanField(default=False)
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(blank=True, null=True)
    password_changed_at = models.DateTimeField(blank=True, null=True)
    is_approved = models.BooleanField(default=True)  # for trainers
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_USER)
    oauth_provider = models.CharField(max_length=50, blank=True, null=True)
    date_joined = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["role"]),
            models.Index(fields=["is_verified"]),
        ]
        ordering = ("-date_joined",)

    def __str__(self):
        return self.email


class RefreshTokenRecord(models.Model):
    jti = models.UUIDField(primary_key=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    revoked = models.BooleanField(default=False, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["expires_at"]),
            models.Index(fields=["revoked"]),
        ]

    def is_active(self):
        return (not self.revoked) and (self.expires_at > timezone.now())
