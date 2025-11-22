from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
from .models import Post
from .serializers import PostSerializer


# Get channel layer for WebSocket communication
channel_layer = get_channel_layer()


def send_post_websocket_update(
    action, post_data=None, post_id=None, old_status=None, new_status=None, user_id=None
):
    """
    Send WebSocket update to all clients in the post_table_updates group
    """
    if not channel_layer:
        print("Error: Channel layer not available")
        return

    # Determine the correct WebSocket message type based on action
    if action == "created":
        message_type = "post_created"
    elif action == "deleted":
        message_type = "post_deleted"
    elif action == "status_changed":
        message_type = "post_status_changed"
    else:
        message_type = "post_updated"

    message = {
        "type": message_type,
        "action": action,
        "post_id": post_id,
        "user_id": user_id,
    }

    if post_data:
        message["data"] = post_data

    if old_status and new_status:
        message["old_status"] = old_status
        message["new_status"] = new_status

    print(f"Sending WebSocket message: {message}")

    # Send message to the WebSocket group
    async_to_sync(channel_layer.group_send)("post_table_updates", message)


@receiver(post_save, sender=Post)
def handle_post_saved(sender, instance, created, **kwargs):
    """
    Handle post creation and updates
    """
    try:
        # Clear cache when post is created or updated
        from django.core.cache import cache
        from django_redis import get_redis_connection

        try:
            redis_conn = get_redis_connection("default")
            # Clear user-specific caches for all users since the post affects multiple users
            patterns = [
                "user_posts:*",
                "cm_posts:*",
                "pending_posts:*",
                "scheduled_posts_*",
                "draft_posts_*",
            ]

            for pattern in patterns:
                keys = redis_conn.keys(pattern)
                if keys:
                    redis_conn.delete(*keys)

            print(
                f"Cache cleared for post {instance.id} ({'created' if created else 'updated'})"
            )
        except Exception as cache_error:
            print(f"Cache invalidation error: {cache_error}")
            cache.clear()  # Fallback

        # Get the post data
        post_data = PostSerializer(instance).data

        if created:
            # Post was created
            send_post_websocket_update(
                action="created",
                post_data=post_data,
                post_id=instance.id,
                user_id=instance.creator.id if instance.creator else None,
            )
        else:
            # Post was updated - check if status changed
            if (
                hasattr(instance, "_old_status")
                and instance._old_status != instance.status
            ):
                send_post_websocket_update(
                    action="status_changed",
                    post_data=post_data,
                    post_id=instance.id,
                    old_status=instance._old_status,
                    new_status=instance.status,
                    user_id=instance.creator.id if instance.creator else None,
                )
            else:
                # Regular update
                send_post_websocket_update(
                    action="updated",
                    post_data=post_data,
                    post_id=instance.id,
                    user_id=instance.creator.id if instance.creator else None,
                )
    except Exception as e:
        # Log error but don't break the save operation
        print(f"Error sending WebSocket update for post {instance.id}: {e}")


@receiver(pre_save, sender=Post)
def store_old_status(sender, instance, **kwargs):
    """
    Store the old status before saving to detect status changes
    """
    if instance.pk:
        try:
            old_instance = Post.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Post.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_delete, sender=Post)
def handle_post_deleted(sender, instance, **kwargs):
    """
    Handle post deletion
    """
    try:
        send_post_websocket_update(
            action="deleted",
            post_id=instance.id,
            user_id=instance.creator.id if instance.creator else None,
        )
    except Exception as e:
        # Log error but don't break the delete operation
        print(f"Error sending WebSocket update for deleted post {instance.id}: {e}")
