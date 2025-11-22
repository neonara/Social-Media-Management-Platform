from django.utils import timezone
from django.db import models
from apps.accounts.models import User


# Create your models here.
class SocialPage(models.Model):
    PLATFORM_CHOICES = [
        ("facebook", "Facebook"),
        ("instagram", "Instagram"),
        ("linkedin", "LinkedIn"),
    ]

    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="social_pages",
        limit_choices_to={"is_client": True},
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
        unique_together = ("client", "page_id", "platform")

    def __str__(self):
        return f"{self.page_name} ({self.platform})"

    def is_token_valid(self):
        # First check if token_expires_at is set and valid
        if self.token_expires_at and timezone.now() < self.token_expires_at:
            return True

        # If no token_expires_at but we have expires_in in permissions
        if self.permissions and "expires_in" in self.permissions:
            # For LinkedIn, we only have expires_in (seconds) in the permissions field
            # We need to check if the token is still valid based on when it was created/updated
            if self.platform == "linkedin":
                # Calculate expiration time based on updated_at + expires_in
                expires_in_seconds = int(self.permissions.get("expires_in", 0))
                if expires_in_seconds > 0:
                    # Calculate the expiration time
                    expiration_time = self.updated_at + timezone.timedelta(
                        seconds=expires_in_seconds
                    )
                    return timezone.now() < expiration_time

        return False
