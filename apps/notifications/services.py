from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from apps.notifications.models import Notification
from django.utils import timezone
from django.core.cache import cache

# Cache timeout in seconds (1 hour)
NOTIFICATION_CACHE_TIMEOUT = 3600

def notify_user(user, title, message, url="", type="general"):
    
    # Create notification record in database
    notification = Notification.objects.create(
        recipient=user,
        title=title,
        message=message,
        type=type,
        url=url,
        created_at=timezone.now(),
        is_read=False
    )

    # Handle notification cache update
    cache_key = f"user_notifications:{user.id}"
    cached_notifications = cache.get(cache_key)
    
    if cached_notifications is not None:
        # If notifications are cached, add the new one to the cache instead of invalidating
        try:
            # Add new notification to the cached queryset
            cached_notifications._result_cache.insert(0, notification)
            cache.set(cache_key, cached_notifications, NOTIFICATION_CACHE_TIMEOUT)
            print(f"Added notification to cache for user {user.id}")
        except (AttributeError, TypeError):
            # If we can't modify the cache, invalidate it
            cache.delete(cache_key)
            print(f"Failed to update cache, invalidated for user {user.id}")
    else:
        print(f"No cached notifications found for user {user.id}")
    
    # Update unread count cache
    unread_count = Notification.objects.filter(recipient=user, is_read=False).count()
    cache.set(f"user_unread_count:{user.id}", unread_count, NOTIFICATION_CACHE_TIMEOUT)
    print(f"Updated unread count cache for user {user.id}: {unread_count}")

    # Prepare notification data to send through WebSocket
    notification_data = {
        "id": notification.id,
        "title": title,
        "message": message,
        "type": type,
        "url": url,
        "is_read": False,
        "created_at": notification.created_at.isoformat()
    }

    # Send through WebSocket if the user is connected
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user.id}",
        {
            "type": "send_notification",
            "content": notification_data
        }
    )
    
    return notification

def mark_notification_read(notification_id, user=None):
    
    try:
        query = Notification.objects.filter(id=notification_id)
        if user is not None:
            query = query.filter(recipient=user)
            
        notification = query.first()
        if notification:
            notification.is_read = True
            notification.save()
            return True
        return False
    except Exception as e:
        print(f"Error marking notification as read: {str(e)}")
        return False

def mark_all_read(user):
    
    try:
        count = Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)
        return count
    except Exception as e:
        print(f"Error marking all notifications as read: {str(e)}")
        return 0

def get_unread_count(user):
    
    return Notification.objects.filter(recipient=user, is_read=False).count()

def get_recent_notifications(user, limit=20):

    return Notification.objects.filter(recipient=user).order_by('-created_at')[:limit]

def get_unread_notification_count(user_id):
    """Get the number of unread notifications for a user"""
    
    # Try to get count from cache
    cache_key = f"user_unread_count:{user_id}"
    cached_count = cache.get(cache_key)
    
    if cached_count is not None:
        return cached_count
    
    # If not in cache, get from database and cache it
    unread_count = Notification.objects.filter(recipient_id=user_id, is_read=False).count()
    cache.set(cache_key, unread_count, NOTIFICATION_CACHE_TIMEOUT)
    
    return unread_count
