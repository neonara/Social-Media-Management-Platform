from django.core.cache import cache
from django.core.cache.backends.base import InvalidCacheBackendError
from redis.exceptions import ConnectionError
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .serializers import GetUserSerializer

# Cache timeout in seconds (1 hour)
USER_CACHE_TIMEOUT = 3600
USERS_LIST_CACHE_TIMEOUT = 1800  # 30 minutes for user list cache

def build_user_data(user):
    """Build user data dictionary with all relevant information"""
    # Determine the primary role based on priority
    role = "user"  # default
    if user.is_superadministrator:
        role = "superadministrator"
    elif user.is_administrator:
        role = "administrator"
    elif user.is_moderator:
        role = "moderator"
    elif user.is_community_manager:
        role = "community_manager"
    elif user.is_client:
        role = "client"

    data = {
        "id": user.id,
        "full_name": user.full_name,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone_number": user.phone_number,
        "email": user.email,
        "image": user.user_image.url if user.user_image else None,
        "user_image": user.user_image.url if user.user_image else None,
        "is_administrator": user.is_administrator,
        "is_superadministrator": user.is_superadministrator,
        "is_moderator": user.is_moderator,
        "is_community_manager": user.is_community_manager,
        "is_client": user.is_client,
        "is_verified": user.is_verified,
        "is_active": user.is_active,
        "is_staff": user.is_staff,
        "role": role,
    }

    # Add assignment information
    if user.is_client and hasattr(user, 'assigned_moderator') and user.assigned_moderator:
        data["assigned_moderator"] = user.assigned_moderator.full_name
        data["assigned_moderator_id"] = user.assigned_moderator.id
    else:
        data["assigned_moderator"] = None
        data["assigned_moderator_id"] = None

    if user.is_moderator:
        assigned_cms = user.assigned_communitymanagers.all()
        data["assigned_communitymanagers"] = ", ".join([cm.full_name for cm in assigned_cms]) if assigned_cms else None
        data["assigned_communitymanagers_list"] = [
            {"id": cm.id, "full_name": cm.full_name} for cm in assigned_cms
        ] if assigned_cms else []
    else:
        data["assigned_communitymanagers"] = None
        data["assigned_communitymanagers_list"] = []

    return data

def get_cached_user_data(user, force_refresh=False):
    """
    Get user data with caching to improve performance
    
    Args:
        user: The user object to retrieve data for
        force_refresh: If True, bypass the cache and get fresh data
        
    Returns:
        dict: Serialized user data
    """
    # Check if data is in cache and we're not forcing a refresh
    cache_key = f"user_data:{user.id}"
    cached_data = None if force_refresh else cache.get(cache_key)
    
    if cached_data is not None:
        return cached_data
    
    # If not in cache, build user data and cache it
    user_data = build_user_data(user)
    
    # Cache the serialized data
    cache.set(cache_key, user_data, USER_CACHE_TIMEOUT)
    
    return user_data

def get_cached_users_list(force_refresh=False, bypass_cache=False):
    """
    Get all users list with caching
    
    Args:
        force_refresh: If True, bypass the cache and get fresh data
        bypass_cache: Alternative parameter name for consistency with frontend
        
    Returns:
        list: List of user data dictionaries
    """
    should_refresh = force_refresh or bypass_cache
    cache_key = "all_users_list"
    cached_data = None if should_refresh else cache.get(cache_key)
    
    if cached_data is not None:
        return cached_data
    
    # Import here to avoid circular imports
    from .models import User
    
    # Get all users and build data
    users = User.objects.all()
    users_data = []
    
    for user in users:
        users_data.append(build_user_data(user))
    
    # Cache the data
    cache.set(cache_key, users_data, USERS_LIST_CACHE_TIMEOUT)
    
    return users_data

def get_cached_user_by_id(user_id, force_refresh=False, bypass_cache=False):
    """
    Get user by ID with caching
    
    Args:
        user_id: ID of user to retrieve
        force_refresh: If True, bypass the cache and get fresh data
        bypass_cache: Alternative parameter name for consistency with frontend
        
    Returns:
        dict: User data dictionary or None if not found
    """
    should_refresh = force_refresh or bypass_cache
    cache_key = f"user_by_id:{user_id}"
    cached_data = None if should_refresh else cache.get(cache_key)
    
    if cached_data is not None:
        return cached_data
    
    # Import here to avoid circular imports
    from .models import User
    
    try:
        user = User.objects.get(pk=user_id)
        user_data = build_user_data(user)
        
        # Cache the data
        cache.set(cache_key, user_data, USER_CACHE_TIMEOUT)
        
        return user_data
    except User.DoesNotExist:
        return None

def clear_user_cache(user_id):
    """
    Clear all cached data related to a user
    
    Args:
        user_id: ID of the user to clear cache for
    """
    # Clear individual user cache
    cache.delete(f"user_data:{user_id}")
    cache.delete(f"user_by_id:{user_id}")
    cache.delete(f"user_meta:{user_id}")
    cache.delete(f"user_fullname:{user_id}")
    cache.delete(f"user_profile:{user_id}")
    cache.delete(f"user_stats:{user_id}")
    cache.delete(f"user_notifications:{user_id}")
    cache.delete(f"user_unread_count:{user_id}")
    
    # Clear users list cache since it contains this user
    cache.delete("all_users_list")
    
    # Also clear Redis cache if available
    try:
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        
        # Clear cache patterns related to the user
        cache_patterns = [
            f"*:user:{user_id}:*",
            f"*:user_data:{user_id}*",
            f"*:user_by_id:{user_id}*",
            f"*:views.decorators.cache.cache_page.*user*{user_id}*",
            f"*:current-user*",
            f"*:all_users_list*"
        ]
        
        for pattern in cache_patterns:
            keys = redis_conn.keys(pattern)
            if keys:
                for key in keys:
                    redis_conn.delete(key)
    except Exception as e:
        # Log the error but continue
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error clearing Redis cache: {str(e)}")

def clear_all_users_cache():
    """
    Clear all user-related cache entries
    """
    try:
        # Clear main lists cache
        cache.delete("all_users_list")
        
        # Clear Redis cache patterns
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        
        cache_patterns = [
            "*:user_data:*",
            "*:user_by_id:*", 
            "*:all_users_list*",
            "*:user:*"
        ]
        
        for pattern in cache_patterns:
            keys = redis_conn.keys(pattern)
            if keys:
                for key in keys:
                    redis_conn.delete(key)
                    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error clearing all users cache: {str(e)}")

# WebSocket notification functions
def notify_user_data_updated(user_id, updated_by_id, fields_changed=None, user_data=None):
    """
    Send WebSocket notification for user data updates
    
    Args:
        user_id: ID of the user that was updated
        updated_by_id: ID of the user who made the update
        fields_changed: List of field names that were changed
        user_data: Optional updated user data to include
    """
    channel_layer = get_channel_layer()
    
    if channel_layer is None:
        return
    
    # Clear cache for the updated user
    clear_user_cache(user_id)
    
    # Send notification to WebSocket group
    async_to_sync(channel_layer.group_send)(
        "user_data_updates",
        {
            "type": "user_data_updated",
            "user_id": user_id,
            "updated_by": updated_by_id,
            "fields_changed": fields_changed or [],
            "data": user_data
        }
    )

def notify_assignment_changed(user_id, target_id, assignment_type, action, updated_by_id, data=None):
    """
    Send WebSocket notification for assignment changes
    
    Args:
        user_id: ID of the primary user in the assignment
        target_id: ID of the target user in the assignment
        assignment_type: Type of assignment ('moderator_client', 'cm_moderator', 'cm_client')
        action: Action taken ('assigned', 'removed')
        updated_by_id: ID of the user who made the change
        data: Optional additional data
    """
    channel_layer = get_channel_layer()
    
    if channel_layer is None:
        return
    
    # Clear cache for both users involved
    clear_user_cache(user_id)
    clear_user_cache(target_id)
    clear_all_users_cache()  # Since assignments affect the users list view
    
    # Send notification to WebSocket group
    async_to_sync(channel_layer.group_send)(
        "user_data_updates",
        {
            "type": "assignment_changed",
            "user_id": user_id,
            "target_id": target_id,
            "assignment_type": assignment_type,
            "action": action,
            "updated_by": updated_by_id,
            "data": data or {}
        }
    )

def notify_user_deleted(user_id, deleted_by_id, user_data=None):
    """
    Send WebSocket notification for user deletion
    
    Args:
        user_id: ID of the deleted user
        deleted_by_id: ID of the user who deleted the user
        user_data: Optional user data before deletion
    """
    channel_layer = get_channel_layer()
    
    if channel_layer is None:
        return
    
    # Clear all caches since user is deleted
    clear_user_cache(user_id)
    clear_all_users_cache()
    
    # Send notification to WebSocket group
    async_to_sync(channel_layer.group_send)(
        "user_data_updates",
        {
            "type": "user_deleted",
            "user_id": user_id,
            "deleted_by": deleted_by_id,
            "user_data": user_data or {}
        }
    )

def notify_user_created(user_id, created_by_id, user_data=None):
    """
    Send WebSocket notification for user creation
    
    Args:
        user_id: ID of the created user
        created_by_id: ID of the user who created the user
        user_data: Optional new user data
    """
    channel_layer = get_channel_layer()
    
    if channel_layer is None:
        return
    
    # Clear users list cache since new user was added
    clear_all_users_cache()
    
    # Send notification to WebSocket group
    async_to_sync(channel_layer.group_send)(
        "user_data_updates",
        {
            "type": "user_created",
            "user_id": user_id,
            "created_by": created_by_id,
            "data": user_data
        }
    )

def notify_role_changed(user_id, old_roles, new_roles, updated_by_id, user_data=None):
    """
    Send WebSocket notification for role changes
    
    Args:
        user_id: ID of the user whose role changed
        old_roles: List of old role names
        new_roles: List of new role names
        updated_by_id: ID of the user who made the change
        user_data: Optional updated user data
    """
    channel_layer = get_channel_layer()
    
    if channel_layer is None:
        return
    
    # Clear cache for the user whose role changed
    clear_user_cache(user_id)
    clear_all_users_cache()
    
    # Send notification to WebSocket group
    async_to_sync(channel_layer.group_send)(
        "user_data_updates",
        {
            "type": "role_changed",
            "user_id": user_id,
            "old_roles": old_roles,
            "new_roles": new_roles,
            "updated_by": updated_by_id,
            "data": user_data or {}
        }
    )
