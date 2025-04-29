from django.utils import timezone
from django.db import models
from apps.accounts.models import User

# Create your models here.
class SocialPage(models.Model):
    PLATFORM_CHOICES = [
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('linkedin', 'LinkedIn'),
    ]

    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='social_pages',
        limit_choices_to={'is_client': True}
    )
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    page_id = models.CharField(max_length=255)
    page_name = models.CharField(max_length=255)
    access_token = models.TextField()
    token_expires_at = models.DateTimeField(null=True, blank=True)
    permissions = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('client', 'page_id', 'platform')

    def __str__(self):
        return f"{self.page_name} ({self.platform})"

    def is_token_valid(self):
        return self.token_expires_at and timezone.now() < self.token_expires_at
