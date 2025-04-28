from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from apps.notifications.models import Notification

def notify_user(user, title, message, url="", type="general"):
    Notification.objects.create(
        recipient=user,
        title=title,
        message=message,
        type=type,
        url=url
    )

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user.id}",
        {
            "type": "send.notification",
            "content": {
                "title": title,
                "message": message,
                "url": url,
                "type": type
            }
        }
    )
