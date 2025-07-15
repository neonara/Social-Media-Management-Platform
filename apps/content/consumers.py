import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from .models import Post


class PostTableConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        # Anonymous users can't access post updates
        if self.user.is_anonymous:
            await self.close()
            return
            
        # Create a group for all users to receive post updates
        self.group_name = "post_table_updates"
        
        # Join the post updates group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to post updates'
        }))
    
    async def disconnect(self, close_code):
        # Leave the post updates group
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
            
            if action == 'request_posts_refresh':
                # When a user explicitly requests a refresh, 
                # we could send them the latest posts here if needed
                await self.send(text_data=json.dumps({
                    'type': 'posts_refresh_requested',
                    'message': 'Posts refresh requested'
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON received'
            }))

    async def post_updated(self, event):
        """Handle post update events sent from other parts of the app"""
        await self.send(text_data=json.dumps({
            'type': 'post_updated',
            'data': event['data'],
            'action': event.get('action', 'update'),
            'post_id': event.get('post_id'),
            'user_id': event.get('user_id', 'system')
        }))

    async def post_created(self, event):
        """Handle new post creation events"""
        await self.send(text_data=json.dumps({
            'type': 'post_created',
            'data': event['data'],
            'post_id': event.get('post_id'),
            'user_id': event.get('user_id', 'system')
        }))

    async def post_deleted(self, event):
        """Handle post deletion events"""
        await self.send(text_data=json.dumps({
            'type': 'post_deleted',
            'post_id': event['post_id'],
            'user_id': event.get('user_id', 'system')
        }))

    async def post_status_changed(self, event):
        """Handle post status change events (approve, reject, etc.)"""
        await self.send(text_data=json.dumps({
            'type': 'post_status_changed',
            'data': event['data'],
            'post_id': event['post_id'],
            'old_status': event.get('old_status'),
            'new_status': event['new_status'],
            'user_id': event.get('user_id', 'system')
        }))

    async def bulk_posts_update(self, event):
        """Handle bulk post updates (useful for initial load or mass operations)"""
        await self.send(text_data=json.dumps({
            'type': 'bulk_posts_update',
            'posts': event['posts'],
            'user_id': event.get('user_id', 'system')
        }))
