from django.core.management.base import BaseCommand
from django.core.cache import cache
from apps.accounts.models import User
from apps.notifications.models import Notification
import json

class Command(BaseCommand):
    help = 'Check if users and notifications are properly stored in cache'

    def add_arguments(self, parser):
        parser.add_argument('user_id', type=int, nargs='?', default=None, help='Optional user ID to check')

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        
        if user_id:
            # Check specific user
            self.check_user_cache(user_id)
        else:
            # Check all users with notifications
            users_with_notifications = User.objects.filter(notifications__isnull=False).distinct()
            if not users_with_notifications:
                self.stdout.write(self.style.WARNING('No users with notifications found'))
                return
                
            self.stdout.write(f"Found {users_with_notifications.count()} users with notifications")
            for user in users_with_notifications:
                self.check_user_cache(user.id)
                
    def check_user_cache(self, user_id):
        """Check cache status for a specific user"""
        self.stdout.write(f"\n{'=' * 40}")
        self.stdout.write(f"Checking cache for user ID: {user_id}")
        self.stdout.write(f"{'=' * 40}")
        
        # Check if the user exists
        try:
            user = User.objects.get(id=user_id)
            self.stdout.write(f"User found: {user.email}")
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User with ID {user_id} does not exist"))
            return
            
        # Check notification cache
        cache_key = f"user_notifications:{user_id}"
        cached_notifications = cache.get(cache_key)
        
        db_notifications = Notification.objects.filter(recipient_id=user_id).order_by('-created_at')
        
        if cached_notifications is not None:
            try:
                num_cached = len(cached_notifications)
                self.stdout.write(self.style.SUCCESS(f"Notification cache exists! Contains {num_cached} notifications"))
                
                # Compare with DB
                num_db = db_notifications.count()
                if num_cached == num_db:
                    self.stdout.write(self.style.SUCCESS(f"Cache count matches database count: {num_db}"))
                else:
                    self.stdout.write(self.style.WARNING(
                        f"Cache count ({num_cached}) doesn't match database ({num_db})"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error accessing cached notifications: {str(e)}"))
        else:
            self.stdout.write(self.style.WARNING("Notification cache does not exist"))
            
        # Check unread count cache
        unread_key = f"user_unread_count:{user_id}"
        cached_unread = cache.get(unread_key)
        db_unread = db_notifications.filter(is_read=False).count()
        
        if cached_unread is not None:
            self.stdout.write(self.style.SUCCESS(f"Unread count is cached: {cached_unread}"))
            if cached_unread == db_unread:
                self.stdout.write(self.style.SUCCESS(f"Cached unread count matches database: {db_unread}"))
            else:
                self.stdout.write(self.style.WARNING(
                    f"Cached unread count ({cached_unread}) doesn't match database ({db_unread})"))
        else:
            self.stdout.write(self.style.WARNING("Unread count is not cached"))
            
        # Check user data cache
        user_data_key = f"user_data:{user_id}"
        cached_user_data = cache.get(user_data_key)
        
        if cached_user_data is not None:
            self.stdout.write(self.style.SUCCESS("User data is cached"))
        else:
            self.stdout.write(self.style.WARNING("User data is not cached"))