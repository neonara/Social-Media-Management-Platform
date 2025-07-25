#!/usr/bin/env python
"""
Script to check cached user data in Django cache and Redis
Usage: python check_cache.py [user_id]
"""

import os
import sys
import django
from django.conf import settings

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'planit.settings')
django.setup()

from django.core.cache import cache
from django.contrib.auth import get_user_model
from apps.accounts.services import get_cached_user_data, clear_user_cache
import json

User = get_user_model()

def check_django_cache(user_id=None):
    """Check Django cache for user data"""
    print("=" * 60)
    print("DJANGO CACHE INSPECTION")
    print("=" * 60)
    
    if user_id:
        users = [User.objects.get(id=user_id)]
        print(f"Checking cache for user ID: {user_id}")
    else:
        users = User.objects.all()[:10]  # Check first 10 users
        print("Checking cache for all users (first 10)...")
    
    print()
    
    cache_keys = [
        'user_data',
        'user_meta',
        'user_fullname',
        'user_profile',
        'user_stats',
        'user_notifications',
        'user_unread_count'
    ]
    
    for user in users:
        print(f"User: {user.email} (ID: {user.id})")
        print(f"Name: {user.first_name} {user.last_name}")
        print(f"Profile Image: {'Yes' if user.user_image else 'No'}")
        print("-" * 40)
        
        has_cache = False
        for key_type in cache_keys:
            cache_key = f"{key_type}:{user.id}"
            cached_data = cache.get(cache_key)
            
            if cached_data is not None:
                has_cache = True
                print(f"✓ {key_type}: CACHED")
                if key_type == 'user_data':
                    # Show user_data details
                    if isinstance(cached_data, dict):
                        print(f"  - Name: {cached_data.get('first_name', 'N/A')} {cached_data.get('last_name', 'N/A')}")
                        print(f"  - Email: {cached_data.get('email', 'N/A')}")
                        print(f"  - Image: {'Yes' if cached_data.get('image') else 'No'}")
                    else:
                        print(f"  - Data: {str(cached_data)[:100]}...")
            else:
                print(f"✗ {key_type}: NOT CACHED")
        
        if not has_cache:
            print("⚠️  No cache data found for this user")
        
        print()

def check_redis_cache(user_id=None):
    """Check Redis cache for user data"""
    try:
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        
        print("=" * 60)
        print("REDIS CACHE INSPECTION")
        print("=" * 60)
        
        if user_id:
            patterns = [
                f"*:user:{user_id}:*",
                f"*:user_data:{user_id}*",
                f"*:views.decorators.cache.cache_page.*user*{user_id}*"
            ]
            print(f"Checking Redis cache for user ID: {user_id}")
        else:
            patterns = [
                "*:user:*",
                "*:user_data:*",
                "*:views.decorators.cache.cache_page.*user*",
                "*:current-user*"
            ]
            print("Checking Redis cache for user-related keys...")
        
        print()
        
        total_keys = 0
        for pattern in patterns:
            keys = redis_conn.keys(pattern)
            if keys:
                print(f"Pattern: {pattern}")
                print(f"Found {len(keys)} keys:")
                for key in keys[:10]:  # Show first 10 keys
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else str(key)
                    print(f"  - {key_str}")
                if len(keys) > 10:
                    print(f"  ... and {len(keys) - 10} more")
                print()
                total_keys += len(keys)
        
        if total_keys == 0:
            print("⚠️  No user-related keys found in Redis cache")
        else:
            print(f"Total user-related keys in Redis: {total_keys}")
            
    except Exception as e:
        print("❌ Error accessing Redis cache:")
        print(f"   {str(e)}")
        print("   Make sure Redis is running and django-redis is configured")

def test_cache_operations(user_id):
    """Test cache operations for a specific user"""
    try:
        user = User.objects.get(id=user_id)
        
        print("=" * 60)
        print(f"CACHE OPERATIONS TEST - User: {user.email}")
        print("=" * 60)
        
        # 1. Get cached data (should create cache if not exists)
        print("1. Getting cached user data...")
        cached_data = get_cached_user_data(user)
        print(f"✓ Retrieved data for: {cached_data.get('email', 'N/A')}")
        print(f"   Name: {cached_data.get('first_name', 'N/A')} {cached_data.get('last_name', 'N/A')}")
        print(f"   Image: {'Yes' if cached_data.get('image') else 'No'}")
        
        # 2. Check if cache exists
        print("\n2. Checking if cache exists...")
        cache_key = f"user_data:{user.id}"
        cache_exists = cache.get(cache_key) is not None
        print(f"✓ Cache exists: {cache_exists}")
        
        # 3. Clear cache
        print("\n3. Clearing user cache...")
        clear_user_cache(user.id)
        print("✓ Cache cleared")
        
        # 4. Check if cache was cleared
        print("\n4. Verifying cache was cleared...")
        cache_exists_after = cache.get(cache_key) is not None
        print(f"✓ Cache exists after clear: {cache_exists_after}")
        
        # 5. Force refresh
        print("\n5. Testing force refresh...")
        refreshed_data = get_cached_user_data(user, force_refresh=True)
        print(f"✓ Force refreshed data for: {refreshed_data.get('email', 'N/A')}")
        
        print("\n✅ All cache operations completed successfully!")
        
    except User.DoesNotExist:
        print(f"❌ User with ID {user_id} not found")
    except Exception as e:
        print(f"❌ Error during cache operations test: {str(e)}")

def clear_all_user_cache():
    """Clear all user-related cache"""
    print("=" * 60)
    print("CLEARING ALL USER CACHE")
    print("=" * 60)
    
    # Clear Django cache
    print("Clearing Django cache...")
    users = User.objects.all()
    cleared_count = 0
    
    for user in users:
        clear_user_cache(user.id)
        cleared_count += 1
    
    print(f"✓ Cleared Django cache for {cleared_count} users")
    
    # Clear Redis cache
    try:
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        
        print("Clearing Redis cache...")
        patterns = [
            "*:user:*",
            "*:user_data:*",
            "*:views.decorators.cache.cache_page.*user*",
            "*:current-user*"
        ]
        
        total_deleted = 0
        for pattern in patterns:
            keys = redis_conn.keys(pattern)
            if keys:
                for key in keys:
                    redis_conn.delete(key)
                    total_deleted += 1
        
        print(f"✓ Deleted {total_deleted} Redis keys")
        
    except Exception as e:
        print(f"⚠️  Error clearing Redis cache: {str(e)}")
    
    print("\n✅ All user cache cleared!")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Check cached user data')
    parser.add_argument('--user-id', '-u', type=int, help='Specific user ID to check')
    parser.add_argument('--test', '-t', action='store_true', help='Run cache operations test')
    parser.add_argument('--clear-all', '-c', action='store_true', help='Clear all user cache')
    parser.add_argument('--redis-only', '-r', action='store_true', help='Check Redis cache only')
    parser.add_argument('--django-only', '-d', action='store_true', help='Check Django cache only')
    
    args = parser.parse_args()
    
    if args.clear_all:
        clear_all_user_cache()
        return
    
    if args.test:
        if not args.user_id:
            print("❌ --test requires --user-id")
            return
        test_cache_operations(args.user_id)
        return
    
    # Default: check both caches
    if not args.redis_only:
        check_django_cache(args.user_id)
    
    if not args.django_only:
        check_redis_cache(args.user_id)

if __name__ == '__main__':
    main()
