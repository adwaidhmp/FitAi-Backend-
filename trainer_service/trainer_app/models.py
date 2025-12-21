import uuid

from django.core.validators import MinValueValidator
from django.db import models


class TrainerProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(unique=True, help_text="UUID from auth_service User")
    bio = models.TextField(blank=True)
    specialties = models.JSONField(default=list, blank=True)
    experience_years = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user_id"]),
        ]

    def __str__(self):
        return f"TrainerProfile({self.user_id})"

    @property
    def latest_certificate(self):
        # relies on TrainerCertificate.Meta.ordering = ["-uploaded_at"]
        return self.certificates.first()


class TrainerCertificate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trainer = models.ForeignKey(
        "TrainerProfile", on_delete=models.CASCADE, related_name="certificates"
    )
    file = models.FileField(upload_to="trainer_certificates/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"Certificate({self.trainer.user_id}, {self.id})"
