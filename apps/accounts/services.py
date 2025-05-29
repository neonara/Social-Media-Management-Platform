from django.core.cache import cache
from django.core.cache.backends.base import InvalidCacheBackendError
from redis.exceptions import ConnectionError
from .serializers import GetUserSerializer

# Cache timeout in seconds (1 hour)
USER_CACHE_TIMEOUT = 3600

def build_user_data(user):
    return {
        "id": user.id,
        "full_name": user.full_name,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone_number": user.phone_number,
        "email": user.email,
        "image": user.user_image.url if user.user_image else None,
        "is_administrator": user.is_administrator,
        "is_superadministrator": user.is_superadministrator,
        "is_moderator": user.is_moderator,
        "is_community_manager": user.is_community_manager,
        "is_client": user.is_client,
        "is_verified": user.is_verified,
    }

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
    
    # If not in cache, serialize and cache the data
    serializer = GetUserSerializer(user)
    user_data = serializer.data
    
    # Cache the serialized data
    cache.set(cache_key, user_data, USER_CACHE_TIMEOUT)
    
    return user_data

def clear_user_cache(user_id):
    """
    Clear all cached data related to a user
    
    Args:
        user_id: ID of the user to clear cache for
    """
    # Clear Django cache
    cache.delete(f"user_data:{user_id}")
    cache.delete(f"user_meta:{user_id}")
    cache.delete(f"user_fullname:{user_id}")
    cache.delete(f"user_profile:{user_id}")
    cache.delete(f"user_stats:{user_id}")
    cache.delete(f"user_notifications:{user_id}")
    cache.delete(f"user_unread_count:{user_id}")
    
    # Also clear Redis cache if available
    try:
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        
        # Clear cache patterns related to the user
        cache_patterns = [
            f"*:user:{user_id}:*",
            f"*:user_data:{user_id}*",
            f"*:views.decorators.cache.cache_page.*user*{user_id}*",
            f"*:current-user*"
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
