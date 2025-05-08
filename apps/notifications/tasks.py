from datetime import timedelta
from celery import shared_task
from django.utils.timezone import now
from apps.notifications.models import Notification

@shared_task
def clean_old_notifications():
    Notification.objects.filter(is_read=True, created_at__lt=now() - timedelta(days=30)).delete()



@shared_task
def test_celery_task():
    print("✅ Celery task executed!")
    return "Hello from Celery"

