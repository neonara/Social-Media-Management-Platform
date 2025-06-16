from channels.generic.websocket import AsyncWebsocketConsumer
import json
from asgiref.sync import async_to_sync

class MyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({"message": "WebSocket connected!"}))

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        data = json.loads(text_data)
        await self.send(text_data=json.dumps({"message": f"Received: {data}"}))

class UserActivityConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "user_activity"
        self.user_id = self.scope["user"].id if self.scope["user"].is_authenticated else None

        if self.user_id:
            # Add user to the group
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()

            # Notify group about the new user
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "user_joined",
                    "user": {
                        "id": self.user_id,
                        "name": f"{self.scope['user'].first_name} {self.scope['user'].last_name}".strip() if self.scope['user'].first_name or self.scope['user'].last_name else self.scope['user'].email,
                        "email": self.scope["user"].email,
                        "profilePicture": self.scope["user"].user_image.url if self.scope["user"].user_image else ""
                    }
                }
            )
        else:
            await self.close()

    async def disconnect(self, close_code):
        if self.user_id:
            # Remove user from the group
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

            # Notify group about the user leaving
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "user_left",
                    "userId": self.user_id
                }
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        # Broadcast the received data to the group, excluding the sender
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "user_activity_message",
                "message": data,
                "sender_channel_name": self.channel_name
            }
        )

    async def user_joined(self, event):
        # Send the user joined message to WebSocket, excluding the current user
        if self.user_id != event["user"]["id"]:
            await self.send(text_data=json.dumps({"type": "user-joined", "user": event["user"]}))

    async def user_left(self, event):
        # Send the user left message to WebSocket, excluding the current user
        if self.user_id != event["userId"]:
            await self.send(text_data=json.dumps({"type": "user-left", "userId": event["userId"]}))

    async def user_activity_message(self, event):
        # Exclude the sender from receiving their own message
        if self.channel_name != event.get("sender_channel_name"):
            await self.send(text_data=json.dumps(event["message"]))