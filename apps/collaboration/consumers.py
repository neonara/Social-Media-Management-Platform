from channels.generic.websocket import AsyncJsonWebsocketConsumer

class CollaborationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.content_id = self.scope["url_route"]["kwargs"]["content_id"]
        self.room_group_name = f"content_{self.content_id}"
        user = self.scope["user"]

        if user.is_authenticated:
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
            await self.channel_layer.group_send(self.room_group_name, {
                "type": "user.joined",
                "user_id": user.id,
                "username": user.get_full_name()
            })
        else:
            await self.close()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, content):
        await self.channel_layer.group_send(self.room_group_name, {
            "type": "broadcast.edit",
            "user_id": self.scope["user"].id,
            "content": content["content"]
        })

    async def broadcast_edit(self, event):
        await self.send_json({
            "type": "edit",
            "user_id": event["user_id"],
            "content": event["content"]
        })

    async def user_joined(self, event):
        await self.send_json({
            "type": "user_joined",
            "user_id": event["user_id"],
            "username": event["username"]
        })
