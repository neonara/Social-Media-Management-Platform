import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import ChatRoom, Message

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

class GeneralChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.current_room_id = None
        self.room_group_name = None

        await self.accept()

    async def disconnect(self, close_code):
        # Leave current room if connected
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'join_room':
            room_id = data.get('room_id')
            if room_id:
                await self.join_room(room_id)

        elif action == 'leave_room':
            room_id = data.get('room_id')
            if room_id:
                await self.leave_room(room_id)

        elif action == 'send_message':
            message_content = data.get('message')
            if message_content and self.current_room_id:
                await self.send_message(message_content)

    async def join_room(self, room_id):
        # Leave current room if connected to another
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

        # Check if user is member of the room
        if await self.is_room_member(room_id, self.user.id):
            self.current_room_id = room_id
            self.room_group_name = f'chat_{room_id}'

            # Join new room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            # Send confirmation
            await self.send(text_data=json.dumps({
                'type': 'room_joined',
                'room_id': room_id
            }))
        else:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Not authorized to join this room'
            }))

    async def leave_room(self, room_id):
        if self.current_room_id == room_id and self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            self.current_room_id = None
            self.room_group_name = None

            await self.send(text_data=json.dumps({
                'type': 'room_left',
                'room_id': room_id
            }))

    async def send_message(self, message_content):
        # Save message to database
        message = await self.save_message(self.current_room_id, self.user.id, message_content)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': {
                    'id': message.id,
                    'content': message.content,
                    'sender': {
                        'id': self.user.id,
                        'name': self.user.get_full_name() or self.user.email,
                        'email': self.user.email
                    },
                    'created_at': message.created_at.isoformat(),
                }
            }
        )

    async def chat_message(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': message
        }))

    @database_sync_to_async
    def is_room_member(self, room_id, user_id):
        try:
            room = ChatRoom.objects.get(id=room_id, is_active=True)
            return room.members.filter(id=user_id).exists()
        except ChatRoom.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, room_id, user_id, content):
        room = ChatRoom.objects.get(id=room_id)
        message = Message.objects.create(
            room=room,
            sender_id=user_id,
            content=content
        )
        return message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope["user"]

        # Check if user is member of the room
        if await self.is_room_member(self.room_id, self.user.id):
            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
        else:
            await self.close(code=4001)  # Unauthorized

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'send_message':
            message_content = data.get('message')
            if message_content:
                # Save message to database
                message = await self.save_message(self.room_id, self.user.id, message_content)

                # Send message to room group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': {
                            'id': message.id,
                            'content': message.content,
                            'sender': {
                                'id': self.user.id,
                                'name': self.user.get_full_name() or self.user.email,
                                'email': self.user.email
                            },
                            'created_at': message.created_at.isoformat(),
                        }
                    }
                )

    async def chat_message(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': message
        }))

    @database_sync_to_async
    def is_room_member(self, room_id, user_id):
        try:
            room = ChatRoom.objects.get(id=room_id, is_active=True)
            return room.members.filter(id=user_id).exists()
        except ChatRoom.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, room_id, user_id, content):
        room = ChatRoom.objects.get(id=room_id)
        message = Message.objects.create(
            room=room,
            sender_id=user_id,
            content=content
        )
        return message
