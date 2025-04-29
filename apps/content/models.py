# your_app_name/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Media(models.Model):
    FILE_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('document', 'Document'),
    ]

    file = models.FileField(upload_to='media/')
    name = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default='image')
    creator = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.type} - {self.file.name}"

class Post(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('published', 'Published'),
        ('failed', 'Failed'),
    ]

    PLATFORM_CHOICES = [
        ('linkedin', 'LinkedIn'),
        ('instagram', 'Instagram'),
        ('facebook', 'Facebook'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    media = models.ManyToManyField(Media, blank=True, related_name='posts')
    platforms = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='client_posts',
        limit_choices_to={'is_client': True}
    )

    def __str__(self):
        return self.title

    @property
    def is_past_due(self):
        if self.scheduled_for:
            return timezone.now() > self.scheduled_for
        return False