from celery import shared_task
from django.core.mail import send_mail
from social_media_management import settings

@shared_task
def send_celery_email(subject, message, recipient_email):
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [recipient_email],
        fail_silently=False,
    )

