from django.test import TestCase
from apps.accounts.tasks import send_email_task


class CeleryTaskTestCase(TestCase):
    def test_send_email_task(self):
        result = send_email_task.delay(
            subject="Test Email",
            message="This is a test email sent via Celery.",
            from_email="your_email@example.com",
            recipient_list=["recipient@example.com"],
        )
        self.assertTrue(result.id)  # Check if the task was queued
