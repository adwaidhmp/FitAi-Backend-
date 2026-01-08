import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import ChatRoom


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.group_name = f"chat_{self.room_id}"
        user = self.scope.get("user")

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
            text_data=json.dumps(
                {
                    "type": "message",
                    "payload": event["payload"],
                }
            )
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



from channels.generic.websocket import AsyncJsonWebsocketConsumer
import logging

logger = logging.getLogger("django")


class UserCallConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")

        logger.error(
            f"🔌 USER WS CONNECT ATTEMPT → user={user} id={getattr(user, 'id', None)}"
        )

        if not user or not user.is_authenticated:
            logger.error("❌ USER WS REJECTED (unauthenticated)")
            await self.close()
            return

        self.group_name = f"user_{user.id}"

        logger.error(f"➕ ADD TO GROUP → {self.group_name}")

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        await self.accept()

        logger.error(f"✅ USER WS CONNECTED → {self.group_name}")

    async def disconnect(self, close_code):
        logger.error(
            f"🔌 USER WS DISCONNECT → {getattr(self, 'group_name', None)} code={close_code}"
        )

        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )

            logger.error(f"➖ REMOVED FROM GROUP → {self.group_name}")

    async def user_call_event(self, event):
        logger.error(f"📥 USER WS EVENT RECEIVED → {event}")

        payload = event.get("payload")

        logger.error(f"📤 USER WS SEND TO CLIENT → {payload}")

        await self.send_json(payload)


from channels.generic.websocket import AsyncJsonWebsocketConsumer
import logging

logger = logging.getLogger("django")


class CallConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        self.call_id = str(self.scope["url_route"]["kwargs"]["call_id"])

        logger.error(
            f"🔌 CALL WS CONNECT ATTEMPT → call={self.call_id} user={user}"
        )

        if not user or not user.is_authenticated:
            logger.error("❌ CALL WS REJECTED (unauthenticated)")
            await self.close()
            return

        self.group_name = f"call_{self.call_id}"

        logger.error(f"➕ ADD TO CALL GROUP → {self.group_name}")

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        await self.accept()

        logger.error(f"✅ CALL WS CONNECTED → {self.group_name}")

    async def disconnect(self, close_code):
        logger.error(
            f"🔌 CALL WS DISCONNECT → {self.group_name} code={close_code}"
        )

        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name,
        )

        logger.error(f"➖ REMOVED FROM CALL GROUP → {self.group_name}")

    async def receive_json(self, content):
        logger.error(
            f"📥 CALL WS RECEIVE_JSON → from={self.channel_name} content={content}"
        )

        if not isinstance(content, dict):
            logger.error("⚠️ INVALID WS PAYLOAD (not dict)")
            return

        if "type" not in content:
            logger.error("⚠️ INVALID WS PAYLOAD (missing type)")
            return

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "call_event",
                "payload": content,
                "sender": self.channel_name,
            },
        )

        logger.error("📡 CALL WS RELAYED TO GROUP")

    async def call_event(self, event):
        logger.error(f"📥 CALL WS EVENT RECEIVED → {event}")

        if event.get("sender") == self.channel_name:
            logger.error("↩️ SKIP ECHO TO SENDER")
            return

        payload = event.get("payload")

        logger.error(f"📤 CALL WS SEND TO CLIENT → {payload}")

        await self.send_json(payload)