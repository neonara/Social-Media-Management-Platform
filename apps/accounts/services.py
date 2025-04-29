from django.core.cache import cache
from django.core.cache.backends.base import InvalidCacheBackendError
from redis.exceptions import ConnectionError

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
        "is_moderator": user.is_moderator,
        "is_community_manager": user.is_community_manager,
        "is_client": user.is_client,
        "is_verified": user.is_verified,
    }

def get_cached_user_data(user):
    key = f"user_meta:{user.id}"
    try:
        data = cache.get(key)
    except (InvalidCacheBackendError, ConnectionError):
        data = None

    if data is None:
        data = build_user_data(user)
        try:
            cache.set(key, data, timeout=60 * 5)  # 5 minutes
        except (InvalidCacheBackendError, ConnectionError):
            pass  # Fail silently — we already have the data

    return data
