from django.core.management.base import BaseCommand
from django.core.cache import cache
from apps.accounts.models import User
from apps.accounts.services import get_cached_user_data, clear_user_cache
import json


class Command(BaseCommand):
    help = "Check and manage user cache data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id",
            type=int,
            help="Specific user ID to check",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear cache for the specified user or all users",
        )
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Force refresh cache for the specified user",
        )
        parser.add_argument(
            "--stats",
            action="store_true",
            help="Show cache statistics",
        )

    def handle(self, *args, **options):
        user_id = options.get("user_id")

        if options.get("clear"):
            self.clear_cache(user_id)
        elif options.get("refresh"):
            self.refresh_cache(user_id)
        elif options.get("stats"):
            self.show_stats()
        else:
            self.check_cache(user_id)

    def check_cache(self, user_id=None):
        """Check cache for specific user or all users"""
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                self.check_user_cache(user)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User with ID {user_id} not found"))
        else:
            users = User.objects.all()[:10]  # First 10 users
            self.stdout.write(f"Checking cache for {len(users)} users...\n")

            for user in users:
                self.check_user_cache(user)
                self.stdout.write("-" * 50)

    def check_user_cache(self, user):
        """Check cache for a single user"""
        self.stdout.write(f"User: {user.email} (ID: {user.id})")
        self.stdout.write(f"Name: {user.first_name} {user.last_name}")

        # Check user_data cache
        cache_key = f"user_data:{user.id}"
        cached_data = cache.get(cache_key)

        if cached_data:
            self.stdout.write(self.style.SUCCESS("✓ Cache exists"))
            if isinstance(cached_data, dict):
                self.stdout.write(
                    f"  Cached name: {cached_data.get('first_name', 'N/A')} {cached_data.get('last_name', 'N/A')}"
                )
                self.stdout.write(f"  Cached email: {cached_data.get('email', 'N/A')}")
                self.stdout.write(
                    f"  Cached image: {'Yes' if cached_data.get('image') else 'No'}"
                )
        else:
            self.stdout.write(self.style.WARNING("✗ No cache found"))

    def clear_cache(self, user_id=None):
        """Clear cache for specific user or all users"""
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                clear_user_cache(user.id)
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Cleared cache for user {user.email}")
                )
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User with ID {user_id} not found"))
        else:
            users = User.objects.all()
            count = 0
            for user in users:
                clear_user_cache(user.id)
                count += 1

            self.stdout.write(self.style.SUCCESS(f"✓ Cleared cache for {count} users"))

    def refresh_cache(self, user_id):
        """Force refresh cache for a specific user"""
        if not user_id:
            self.stdout.write(
                self.style.ERROR("User ID is required for refresh operation")
            )
            return

        try:
            user = User.objects.get(id=user_id)

            # Clear existing cache
            clear_user_cache(user.id)

            # Force refresh
            cached_data = get_cached_user_data(user, force_refresh=True)

            self.stdout.write(
                self.style.SUCCESS(f"✓ Refreshed cache for user {user.email}")
            )
            self.stdout.write(
                f"  Name: {cached_data.get('first_name', 'N/A')} {cached_data.get('last_name', 'N/A')}"
            )
            self.stdout.write(f"  Email: {cached_data.get('email', 'N/A')}")
            self.stdout.write(f"  Image: {'Yes' if cached_data.get('image') else 'No'}")

        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User with ID {user_id} not found"))

    def show_stats(self):
        """Show cache statistics"""
        users = User.objects.all()
        total_users = len(users)
        cached_users = 0

        for user in users:
            cache_key = f"user_data:{user.id}"
            if cache.get(cache_key):
                cached_users += 1

        self.stdout.write("=" * 50)
        self.stdout.write("CACHE STATISTICS")
        self.stdout.write("=" * 50)
        self.stdout.write(f"Total users: {total_users}")
        self.stdout.write(f"Cached users: {cached_users}")
        self.stdout.write(
            f"Cache hit rate: {(cached_users/total_users*100):.1f}%"
            if total_users > 0
            else "0%"
        )

        # Check Redis if available
        try:
            from django_redis import get_redis_connection

            redis_conn = get_redis_connection("default")

            patterns = ["*:user_data:*", "*:user:*", "*:current-user*"]

            total_redis_keys = 0
            for pattern in patterns:
                keys = redis_conn.keys(pattern)
                total_redis_keys += len(keys)

            self.stdout.write(f"Redis user keys: {total_redis_keys}")

        except Exception:
            self.stdout.write("Redis: Not available")
