# chat/serializers.py
from rest_framework import serializers
from .models import Message


class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.IntegerField(source="sender.id", read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "room",
            "sender",
            "type",
            "text",
            "file_url",
            "duration_sec",
            "created_at",
        ]

    def get_file_url(self, obj):
        return obj.file.url if obj.file else None
