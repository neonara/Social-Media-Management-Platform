from django.core.management.base import BaseCommand
from django.core.cache import cache
from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.accounts.services import get_cached_user_data
from apps.accounts.serializers import GetUserSerializer

class Command(BaseCommand):
    help = 'Manually initialize cache for a specific user or all users'

    def add_arguments(self, parser):
        parser.add_argument('user_id', type=int, nargs='?', default=None, help='Optional user ID to initialize')

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        
        if user_id:
            # Initialize specific user
            self.initialize_user_cache(user_id)
        else:
            # Initialize all users
            users = User.objects.all()
            for user in users:
                self.initialize_user_cache(user.id)
                
    def initialize_user_cache(self, user_id):
        """Initialize all cache entries for a specific user"""
        try:
            user = User.objects.get(id=user_id)
            self.stdout.write(f"Initializing cache for user: {user.email}")
            
            # Cache user data
            serializer = GetUserSerializer(user)
            user_data = serializer.data
            cache.set(f"user_data:{user_id}", user_data, 3600)
            self.stdout.write(self.style.SUCCESS(f"✓ Cached user data"))
            
            # Cache user meta
            meta_data = user.get_meta_data()
            cache.set(f"user_meta:{user_id}", meta_data, 3600)
            self.stdout.write(self.style.SUCCESS(f"✓ Cached user meta data"))
            
            # Cache full name
            full_name = user.get_full_name()
            cache.set(f"user_fullname:{user_id}", full_name, 3600)
            self.stdout.write(self.style.SUCCESS(f"✓ Cached user full name"))
            
            # Cache notifications
            notifications = Notification.objects.filter(recipient=user).order_by('-created_at')
            cache.set(f"user_notifications:{user_id}", notifications, 3600)
            self.stdout.write(self.style.SUCCESS(f"✓ Cached {notifications.count()} notifications"))
            
            # Cache unread count
            unread_count = notifications.filter(is_read=False).count()
            cache.set(f"user_unread_count:{user_id}", unread_count, 3600)
            self.stdout.write(self.style.SUCCESS(f"✓ Cached unread count: {unread_count}"))
            
            self.stdout.write(self.style.SUCCESS(f"Successfully initialized cache for user ID {user_id}"))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User with ID {user_id} does not exist"))