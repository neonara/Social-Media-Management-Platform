import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from .models import Notification

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        # Anonymous users can't receive notifications
        if self.user.is_anonymous:
            await self.close()
            return
            
        self.user_group_name = f"user_{self.user.id}"
        
        # Join user group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial unread count
        unread_count = await self.get_unread_count(self.user.id)
        await self.send(text_data=json.dumps({
            'type': 'notification_count',
            'count': unread_count
        }))
    
    async def disconnect(self, close_code):
        pass
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')
        
        if action == 'mark_read':
            notification_id = data.get('notification_id')
            if notification_id:
                success = await self.mark_notification_read(notification_id)
                if success:
                    # Update unread count
                    unread_count = await self.get_unread_count(self.user.id)
                    await self.send(text_data=json.dumps({
                        'type': 'notification_count', 
                        'count': unread_count
                    }))
        
        elif action == 'mark_all_read':
            count = await self.mark_all_read()
            if count > 0:
                await self.send(text_data=json.dumps({
                    'type': 'notification_count',
                    'count': 0
                }))
    
    async def send_notification(self, event):
        # Send notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification': event['content']
        }))
        
        # Update and send the new unread count
        unread_count = await self.get_unread_count(self.user.id)
        await self.send(text_data=json.dumps({
            'type': 'notification_count',
            'count': unread_count
        }))
    
    @database_sync_to_async
    def get_unread_count(self, user_id):
        # Try to get count from cache
        cache_key = f"user_unread_count:{user_id}"
        cached_count = cache.get(cache_key)
        
        if cached_count is not None:
            return cached_count
        
        # If not in cache, get from database and cache it
        unread_count = Notification.objects.filter(recipient_id=user_id, is_read=False).count()
        cache.set(cache_key, unread_count, 3600)  # Cache for 1 hour
        
        return unread_count
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        try:
            notification = Notification.objects.get(id=notification_id, recipient=self.user)
            if not notification.is_read:
                notification.is_read = True
                notification.save()
                
                # Invalidate user notifications cache
                cache_key = f"user_notifications:{self.user.id}"
                cache.delete(cache_key)
                
                # Update unread count cache
                unread_count = Notification.objects.filter(recipient=self.user, is_read=False).count()
                cache.set(f"user_unread_count:{self.user.id}", unread_count, 3600)
                
                return True
            return False
        except Notification.DoesNotExist:
            return False
    
    @database_sync_to_async
    def mark_all_read(self):
        count = Notification.objects.filter(recipient=self.user, is_read=False).update(is_read=True)
        
        if count > 0:
            # Invalidate user notifications cache
            cache_key = f"user_notifications:{self.user.id}"
            cache.delete(cache_key)
            
            # Update unread count cache
            cache.set(f"user_unread_count:{self.user.id}", 0, 3600)
            
        return count
