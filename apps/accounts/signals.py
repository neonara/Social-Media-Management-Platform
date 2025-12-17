# apps/accounts/signals.py
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.accounts.models import User

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def user_created_handler(sender, instance, created, **kwargs):
    if created:
        logger.info(f"New user created: {instance.email}")
    # Add your custom logic here
