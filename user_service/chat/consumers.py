import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import ChatRoom, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.group_name = f"chat_{self.room_id}"

        user = self.scope["user"]
        if not user or not user.is_authenticated:
            await self.close()
            return

        if not ChatRoom.objects.filter(id=self.room_id).exists():
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_text = data.get("text", "").strip()

        if not message_text:
            return

        msg = Message.objects.create(
            room_id=self.room_id,
            sender=self.scope["user"],
            type=Message.TEXT,
            text=message_text,
        )

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat.message",
                "payload": {
                    "id": str(msg.id),
                    "sender": msg.sender.id,
                    "type": msg.type,
                    "text": msg.text,
                    "created_at": msg.created_at.isoformat(),
                },
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["payload"]))
