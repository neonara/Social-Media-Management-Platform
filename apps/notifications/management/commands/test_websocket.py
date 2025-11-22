from django.core.management.base import BaseCommand
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import time


class Command(BaseCommand):
    help = "Tests WebSocket functionality by sending test messages"

    def add_arguments(self, parser):
        parser.add_argument(
            "user_id", type=int, help="User ID to send test notification to"
        )

    def handle(self, *args, **options):
        user_id = options["user_id"]
        self.stdout.write(
            self.style.SUCCESS(f"Sending test notification to user {user_id}")
        )

        channel_layer = get_channel_layer()

        # Test 1: Send a simple message
        self.stdout.write("Test 1: Sending simple test message...")
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",
            {
                "type": "new_notification",
                "content": {
                    "type": "test_notification",
                    "message": "This is a test notification",
                    "timestamp": time.time(),
                },
            },
        )
        self.stdout.write(self.style.SUCCESS("Test message sent!"))

        # Test 2: Send a notification-like message
        self.stdout.write("Test 2: Sending test notification object...")
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",
            {
                "type": "new_notification",
                "content": {
                    "type": "new_notification",
                    "notification": {
                        "id": 0,  # Test ID
                        "title": "Test Notification",
                        "message": "This is a test notification sent from management command",
                        "type": "test",
                        "is_read": False,
                        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "url": None,
                    },
                },
            },
        )
        self.stdout.write(self.style.SUCCESS("Test notification sent!"))

        self.stdout.write(self.style.SUCCESS("WebSocket tests completed!"))
