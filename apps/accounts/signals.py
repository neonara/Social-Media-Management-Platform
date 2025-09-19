# apps/accounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.accounts.models import User

@receiver(post_save, sender=User)
def user_created_handler(sender, instance, created, **kwargs):
    if created:
        print(f"New user created: {instance.email}")
    # Add your custom logic here