import json
from channels.generic.websocket import AsyncWebsocketConsumer

class CollaborationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "collaboration_group"
        self.user_id = self.scope["user"].id  # Assuming user is authenticated

        # Join the collaboration group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # Add user to the list of connected users
        if not hasattr(self.channel_layer, "connected_users"):
            self.channel_layer.connected_users = {}
        self.channel_layer.connected_users[self.user_id] = self.channel_name

        await self.accept()

    async def disconnect(self, close_code):
        # Leave the collaboration group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

        # Remove user from the list of connected users
        if hasattr(self.channel_layer, "connected_users"):
            self.channel_layer.connected_users.pop(self.user_id, None)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")

        if action == "leave_calendar":
            # Handle user leaving the calendar
            if hasattr(self.channel_layer, "connected_users"):
                self.channel_layer.connected_users.pop(self.user_id, None)

    async def user_activity_event(self, event):
        # Placeholder for future Kanban board functionality
        pass
