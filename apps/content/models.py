from django.db import models

from apps.accounts.models import User
from apps.social_media.models import SocialPage  # Assuming User is in accounts

class Post(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    media = models.JSONField(blank=True, null=True)  # Store media URLs as a list
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    scheduled_time = models.DateTimeField(blank=True, null=True)
    is_published = models.BooleanField(default=True)
    status = models.CharField(max_length=50, default="draft")  # Example status field
    facebook_post_id = models.CharField(max_length=100, blank=True)  # Track FB post ID
    instagram_post_id = models.CharField(max_length=100, blank=True)  # Track IG post ID
    linkedin_post_id = models.CharField(max_length=100, blank=True)  # Track LI post ID
    creator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, 
        null=True, 
        related_name="created_posts", 
        limit_choices_to={'is_community_manager': True}
        )
    platform_page = models.ForeignKey(
        SocialPage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posts',
        help_text="The exact Page or Account where this post is scheduled"
    )

    def __str__(self):
        return f"{self.title} by {self.creator.email}"

    class Meta:
        ordering = ["-created_at"]
