from django.db import models
from django.utils import timezone
from apps.content.models import Post


class HashtagPerformance(models.Model):
    """Hashtag performance data (synthetic or scraped)"""

    INDUSTRY_CHOICES = [
        ("fitness", "Fitness 💪"),
        ("fashion", "Fashion 👗"),
        ("tech", "Technology 💻"),
        ("food", "Food & Beverage 🍕"),
        ("travel", "Travel ✈️"),
        ("lifestyle", "Lifestyle 🌟"),
        ("business", "Business 💼"),
        ("marketing", "Marketing 📊"),
    ]

    PLATFORM_CHOICES = [
        ("instagram", "Instagram"),
        ("facebook", "Facebook"),
        ("linkedin", "LinkedIn"),
    ]

    # Hashtag info
    hashtag = models.CharField(max_length=100, unique=True, db_index=True)
    industry = models.CharField(max_length=20, choices=INDUSTRY_CHOICES)
    platform = models.CharField(
        max_length=20, choices=PLATFORM_CHOICES, default="instagram"
    )

    # Performance metrics (synthetic data)
    avg_engagement_rate = models.FloatField(
        help_text="Average engagement rate (0-100%)"
    )
    usage_frequency = models.IntegerField(
        default=0, help_text="Times used in sample data"
    )
    reach_estimate = models.IntegerField(
        default=0, help_text="Estimated reach (synthetic)"
    )

    # Metadata
    trending = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-avg_engagement_rate", "-usage_frequency"]
        indexes = [
            models.Index(fields=["industry", "platform"]),
            models.Index(fields=["avg_engagement_rate"]),
        ]

    def __str__(self):
        return f"#{self.hashtag} ({self.industry})"


class OptimalPostingTime(models.Model):
    """Optimal times to post (synthetic data)"""

    PLATFORM_CHOICES = [
        ("instagram", "Instagram"),
        ("facebook", "Facebook"),
        ("linkedin", "LinkedIn"),
    ]

    DAY_CHOICES = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    day_of_week = models.IntegerField(choices=DAY_CHOICES)  # 0-6
    hour = models.IntegerField()  # 0-23
    engagement_score = models.FloatField(
        help_text="Engagement score for this time (0-100)"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["platform", "day_of_week", "hour"]
        ordering = ["-engagement_score"]

    def __str__(self):
        day_name = dict(self.DAY_CHOICES)[self.day_of_week]
        return f"{self.platform} - {day_name} {self.hour:02d}:00 (score: {self.engagement_score})"


class EngagementForecast(models.Model):
    """
    Stores engagement forecast predictions for posts before publication.
    Allows tracking of actual vs predicted engagement after publishing.
    """

    ENGAGEMENT_LEVEL_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]

    post = models.OneToOneField(
        Post,
        on_delete=models.CASCADE,
        related_name="engagement_forecast",
        help_text="The post for which engagement is being forecasted",
    )

    # Prediction inputs
    caption_length = models.IntegerField(
        help_text="Length of the post caption in characters"
    )
    hashtag_count = models.IntegerField(help_text="Number of hashtags in the post")
    time_of_day = models.IntegerField(
        help_text="Hour of day when post is scheduled (0-23)"
    )
    day_of_week = models.IntegerField(
        help_text="Day of week when post is scheduled (0=Monday, 6=Sunday)"
    )
    platform = models.CharField(
        max_length=20,
        choices=[
            ("facebook", "Facebook"),
            ("instagram", "Instagram"),
            ("linkedin", "LinkedIn"),
        ],
    )
    media_type = models.CharField(
        max_length=20,
        choices=[
            ("image", "Image"),
            ("video", "Video"),
            ("carousel", "Carousel"),
            ("text", "Text Only"),
        ],
    )
    brand_sentiment = models.FloatField(
        default=0.5, help_text="Sentiment score of the post content (0-1)"
    )

    # Prediction outputs
    predicted_engagement_score = models.FloatField(
        help_text="Predicted engagement score (0-100)"
    )
    engagement_level = models.CharField(
        max_length=10,
        choices=ENGAGEMENT_LEVEL_CHOICES,
        help_text="Engagement level category",
    )
    confidence_score = models.FloatField(
        help_text="Model confidence in prediction (0-1)"
    )

    # Actual engagement (populated after publishing)
    actual_engagement_score = models.FloatField(
        null=True, blank=True, help_text="Actual engagement after publishing"
    )
    actual_engagement_level = models.CharField(
        max_length=10,
        choices=ENGAGEMENT_LEVEL_CHOICES,
        null=True,
        blank=True,
        help_text="Actual engagement level after publishing",
    )

    # Timestamps
    predicted_at = models.DateTimeField(
        auto_now_add=True, help_text="When the prediction was made"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-predicted_at"]
        verbose_name_plural = "Engagement Forecasts"

    def __str__(self):
        return f"Forecast for Post {self.post.id}: {self.engagement_level} ({self.predicted_engagement_score:.1f}/100)"

    def get_prediction_accuracy(self):
        """
        Calculate accuracy if actual engagement has been recorded.
        """
        if self.actual_engagement_score is None:
            return None

        # Calculate percentage difference
        difference = abs(self.actual_engagement_score - self.predicted_engagement_score)
        accuracy = max(0, 100 - (difference / 100 * 100))
        return accuracy


class TrainingData(models.Model):
    """
    Stores training data points used for ML model training.
    Allows model retraining with real data when it becomes available.
    """

    DATA_TYPE_CHOICES = [
        ("synthetic", "Synthetic"),
        ("real", "Real"),
        ("combined", "Combined"),
    ]

    caption_length = models.IntegerField()
    hashtag_count = models.IntegerField()
    time_of_day = models.IntegerField()
    day_of_week = models.IntegerField()
    platform = models.CharField(max_length=20)
    media_type = models.CharField(max_length=20)
    brand_sentiment = models.FloatField()
    engagement_score = models.FloatField(help_text="Target engagement score (0-100)")

    data_type = models.CharField(
        max_length=20, choices=DATA_TYPE_CHOICES, default="synthetic"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Training Data"

    def __str__(self):
        return f"Training Data: {self.platform} - Score {self.engagement_score:.1f}"


class ModelMetrics(models.Model):
    """
    Stores metrics for the trained engagement forecast model.
    Allows tracking of model performance over time.
    """

    version = models.CharField(
        max_length=50, unique=True, help_text="Model version identifier"
    )
    model_type = models.CharField(
        max_length=50, help_text="Type of model (e.g., RandomForest, LinearRegression)"
    )
    training_samples = models.IntegerField(
        help_text="Number of samples used for training"
    )
    r2_score = models.FloatField(help_text="R² score on training data")
    mae = models.FloatField(help_text="Mean Absolute Error")
    rmse = models.FloatField(help_text="Root Mean Squared Error")
    training_data_type = models.CharField(
        max_length=20, choices=TrainingData.DATA_TYPE_CHOICES, default="synthetic"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this model version is actively used for predictions",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Model {self.version} ({self.model_type})"

    def save(self, *args, **kwargs):
        # Only one model should be active at a time
        if self.is_active:
            ModelMetrics.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)
