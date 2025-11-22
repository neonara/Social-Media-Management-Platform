from django.db import models
from .models import Post


class PostAnalytics(models.Model):
    """
    Store analytics/performance metrics for published posts.
    This data can be synced from social media platforms' APIs.
    """

    post = models.OneToOneField(
        Post,
        on_delete=models.CASCADE,
        related_name="analytics",
        help_text="The post these analytics belong to",
    )

    # Engagement metrics
    likes = models.IntegerField(default=0, help_text="Total likes/reactions")
    comments = models.IntegerField(default=0, help_text="Total comments")
    shares = models.IntegerField(default=0, help_text="Total shares/retweets")

    # Reach and impressions
    reach = models.IntegerField(default=0, help_text="Unique users who saw the post")
    impressions = models.IntegerField(
        default=0, help_text="Total times the post was displayed"
    )

    # Engagement rate (calculated field but stored for query efficiency)
    engagement_rate = models.FloatField(
        default=0.0, help_text="Engagement rate percentage (engagement/reach * 100)"
    )

    # Click tracking (if applicable)
    clicks = models.IntegerField(default=0, help_text="Total clicks on post links")

    # Video-specific metrics (optional)
    video_views = models.IntegerField(
        default=0,
        null=True,
        blank=True,
        help_text="Video views (if post contains video)",
    )
    video_watch_time = models.IntegerField(
        default=0, null=True, blank=True, help_text="Total watch time in seconds"
    )

    # Timestamps
    last_synced_at = models.DateTimeField(
        auto_now=True, help_text="Last time analytics were synced from platform"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Post Analytics"
        verbose_name_plural = "Post Analytics"
        ordering = ["-last_synced_at"]
        indexes = [
            models.Index(fields=["post"]),
            models.Index(fields=["-last_synced_at"]),
        ]

    def __str__(self):
        return f"Analytics for {self.post.title}"

    @property
    def total_engagement(self):
        """Calculate total engagement (likes + comments + shares)"""
        return self.likes + self.comments + self.shares

    def calculate_engagement_rate(self):
        """Calculate and update engagement rate"""
        if self.reach > 0:
            self.engagement_rate = (self.total_engagement / self.reach) * 100
        else:
            self.engagement_rate = 0.0
        return self.engagement_rate

    def save(self, *args, **kwargs):
        """Auto-calculate engagement rate before saving"""
        self.calculate_engagement_rate()
        super().save(*args, **kwargs)
