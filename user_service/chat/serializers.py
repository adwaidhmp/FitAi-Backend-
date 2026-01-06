# chat/serializers.py
from chat.models import Message
from rest_framework import serializers


class UserMessageCreateSerializer(serializers.Serializer):
    room_id = serializers.UUIDField()
    type = serializers.ChoiceField(choices=Message.TYPE_CHOICES)
    text = serializers.CharField(required=False, allow_blank=True)
    file = serializers.FileField(required=False)
    duration_sec = serializers.IntegerField(required=False, min_value=1)

    def validate(self, data):
        msg_type = data["type"]

        if msg_type == Message.TEXT:
            if not data.get("text"):
                raise serializers.ValidationError("Text is required")
            if data.get("file"):
                raise serializers.ValidationError("File not allowed for text")

        if msg_type == Message.IMAGE:
            if not data.get("file"):
                raise serializers.ValidationError("Image file required")

        if msg_type == Message.AUDIO:
            if not data.get("file"):
                raise serializers.ValidationError("Audio file required")
            if not data.get("duration_sec"):
                raise serializers.ValidationError("duration_sec required")

        return data


class MessageSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "room_id",
            "sender_user_id",
            "sender_role",
            "type",
            "text",
            "file",
            "duration_sec",
            "read_at",
            "created_at",
        ]

    def get_file(self, obj):
        if not obj.file:
            return None

        request = self.context.get("request")
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url

