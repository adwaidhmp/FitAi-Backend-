import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import ChatRoom


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.group_name = f"chat_{self.room_id}"
        user = self.scope["user"]

        if not user or not user.is_authenticated:
            await self.close()
            return

        allowed = await self._is_user_allowed(user.id)
        if not allowed:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # WS is receive-only. No receive().

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps({
                "type": "message",
                "payload": event["payload"],
            })
        )

    @database_sync_to_async
    def _is_user_allowed(self, user_id):
        return (
            ChatRoom.objects.filter(
                id=self.room_id,
                is_active=True,
                user_id=user_id,
            ).exists()
            or ChatRoom.objects.filter(
                id=self.room_id,
                is_active=True,
                trainer_user_id=user_id,
            ).exists()
        )
