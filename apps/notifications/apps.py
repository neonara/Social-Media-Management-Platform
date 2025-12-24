from django.apps import AppConfig
from django.db.models.signals import post_migrate


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"

    def ready(self):
        # Import function here to avoid circular imports
        from .signals import check_cache_connection

        # Connect to post_migrate signal to set up cache after migrations
        post_migrate.connect(check_cache_connection, sender=self)
