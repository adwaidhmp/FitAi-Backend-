import uuid
from django.db import models


class ChatRoom(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user_id = models.UUIDField(db_index=True)
    trainer_user_id = models.UUIDField(db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "trainer_user_id"],
                name="unique_user_trainer_chatroom"
            )
        ]


class Message(models.Model):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"

    TYPE_CHOICES = [
        (TEXT, "Text"),
        (IMAGE, "Image"),
        (AUDIO, "Audio"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    room = models.ForeignKey(
        "ChatRoom",
        on_delete=models.CASCADE,
        related_name="messages",
    )

    sender_user_id = models.UUIDField(db_index=True)

    type = models.CharField(max_length=10, choices=TYPE_CHOICES)

    text = models.TextField(blank=True)

    file = models.FileField(
        upload_to="chat_media/",
        null=True,
        blank=True,
    )

    duration_sec = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    