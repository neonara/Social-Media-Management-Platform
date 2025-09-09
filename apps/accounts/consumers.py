from channels.generic.websocket import AsyncWebsocketConsumer
import json

class MyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({"message": "WebSocket connected!"}))

    async def disconnect(self):
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

    async def disconnect(self):
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


class UserDataConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time user data updates including:
    - User profile changes
    - Assignment changes (moderator <-> client, CM assignments)
    - User deletions
    - User role changes
    """
    
    async def connect(self):
        self.user = self.scope["user"]
        
        # Only authenticated users can connect
        if self.user.is_anonymous:
            print(f"UserDataConsumer: Rejecting anonymous user connection from {self.scope.get('client', ['unknown'])[0]}")
            await self.close(code=1008)  # Policy Violation - authentication required
            return
        
        print(f"UserDataConsumer: Accepting connection for user {self.user.id} ({self.user.email})")
        
        # Create group for all user data updates
        self.group_name = "user_data_updates"
        
        # Join the user data updates group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to user data updates'
        }))
    
    async def disconnect(self, close_code):
        # Leave the user data updates group
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'request_user_data_refresh':
                # Client requesting fresh user data
                await self.send(text_data=json.dumps({
                    'type': 'user_data_refresh_requested',
                    'message': 'User data refresh requested'
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON received'
            }))
    
    # WebSocket event handlers
    async def user_data_updated(self, event):
        """Handle user profile/data update events"""
        await self.send(text_data=json.dumps({
            'type': 'user_data_updated',
            'data': event.get('data'),
            'user_id': event.get('user_id'),
            'updated_by': event.get('updated_by'),
            'fields_changed': event.get('fields_changed', [])
        }))
    
    async def assignment_changed(self, event):
        """Handle assignment change events (moderator-client, CM assignments)"""
        await self.send(text_data=json.dumps({
            'type': 'assignment_changed',
            'assignment_type': event.get('assignment_type'),  # 'moderator_client', 'cm_moderator', 'cm_client'
            'action': event.get('action'),  # 'assigned', 'removed'
            'user_id': event.get('user_id'),
            'target_id': event.get('target_id'),
            'updated_by': event.get('updated_by'),
            'data': event.get('data', {})
        }))
    
    async def user_deleted(self, event):
        """Handle user deletion events"""
        await self.send(text_data=json.dumps({
            'type': 'user_deleted',
            'user_id': event.get('user_id'),
            'deleted_by': event.get('deleted_by'),
            'user_data': event.get('user_data', {})
        }))
    
    async def user_created(self, event):
        """Handle new user creation events"""
        await self.send(text_data=json.dumps({
            'type': 'user_created',
            'data': event.get('data'),
            'user_id': event.get('user_id'),
            'created_by': event.get('created_by')
        }))
    
    async def role_changed(self, event):
        """Handle user role change events"""
        await self.send(text_data=json.dumps({
            'type': 'role_changed',
            'user_id': event.get('user_id'),
            'old_roles': event.get('old_roles', []),
            'new_roles': event.get('new_roles', []),
            'updated_by': event.get('updated_by'),
            'data': event.get('data', {})
        }))
    
    async def bulk_users_update(self, event):
        """Handle bulk user updates"""
        await self.send(text_data=json.dumps({
            'type': 'bulk_users_update',
            'users': event.get('users', []),
            'updated_by': event.get('updated_by')
        }))