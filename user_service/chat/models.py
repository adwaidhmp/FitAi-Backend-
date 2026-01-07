import uuid

from django.db import models


class ChatRoom(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user_id = models.UUIDField(db_index=True)
    trainer_user_id = models.UUIDField(db_index=True)

    is_active = models.BooleanField(default=True)

    # helps chat list ordering without heavy queries
    last_message_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "trainer_user_id"],
                name="unique_user_trainer_chatroom",
            )
        ]

    def __str__(self):
        return f"ChatRoom({self.user_id} ↔ {self.trainer_user_id})"

    def other_participant_id(self, current_user_id):
        """
        Return the other participant's user_id in this chat room.
        """
        if str(current_user_id) == str(self.user_id):
            return self.trainer_user_id

        if str(current_user_id) == str(self.trainer_user_id):
            return self.user_id

        raise ValueError("User is not a participant of this room")


class Message(models.Model):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO ="video"

    TYPE_CHOICES = [
        (TEXT, "Text"),
        (IMAGE, "Image"),
        (AUDIO, "Audio"),
        (VIDEO, "Video"),
    ]

    SENDER_USER = "user"
    SENDER_TRAINER = "trainer"

    SENDER_CHOICES = [
        (SENDER_USER, "User"),
        (SENDER_TRAINER, "Trainer"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    sender_user_id = models.UUIDField(db_index=True)
    sender_role = models.CharField(
        max_length=10,
        choices=SENDER_CHOICES,
    )

    type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
    )

    text = models.TextField(blank=True)

    file = models.FileField(
        upload_to="chat_media/",
        null=True,
        blank=True,
    )

    # media metadata (cheap, useful)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=50, blank=True)

    # for audio messages
    duration_sec = models.PositiveIntegerField(null=True, blank=True)

    # read / delete control
    read_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["room", "created_at"]),
        ]

    def __str__(self):
        return f"Message({self.type}) in {self.room_id}"



class Call(models.Model):
    STATUS_RINGING = "ringing"
    STATUS_ACTIVE = "active"
    STATUS_ENDED = "ended"

    STATUS_CHOICES = [
        (STATUS_RINGING, "Ringing"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_ENDED, "Ended"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    room = models.ForeignKey(
        "chat.ChatRoom",
        on_delete=models.CASCADE,
        related_name="calls",
    )

    started_by = models.UUIDField()  # user_id or trainer_user_id

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_RINGING,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["room", "status"]),
        ]