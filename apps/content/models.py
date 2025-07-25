from django.db import models
from apps.accounts.models import User
from apps.social_media.models import SocialPage  # Assuming User is in accounts
from django.utils import timezone

class Media(models.Model):
    FILE_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('document', 'Document'),
    ]
    

    file = models.FileField(upload_to='media/')
    name = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default='image')
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.type} - {self.file.name}"

class Post(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('rejected', 'Rejected'),
        ('scheduled', 'Scheduled'),
        ('published', 'Published'),
        ('failed', 'Failed'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='posts', null=True)
    media = models.ManyToManyField(Media, blank=True, related_name='posts')
    platforms = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_edited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='last_edited_posts',
        help_text="The user who last edited this post"
    )
    client = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='client_posts',
        limit_choices_to={'is_client': True}
    )
    platform_page = models.ForeignKey(
        SocialPage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posts',
        help_text="The exact Page or Account where this post is scheduled"
    )
    feedback = models.TextField(
        blank=True,
        null=True,
        help_text="Feedback provided when approving or rejecting the post"
    )
    feedback_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feedback_posts',
        help_text="The user who provided the feedback"
    )
    feedback_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the feedback was provided"
    )

    def __str__(self):
        return f"{self.title} by {self.creator.email}"

    @property
    def is_past_due(self):
        if self.scheduled_for:
            return timezone.now() > self.scheduled_for
        return False
    
    class Meta:
        ordering = ["-created_at"]
        
    def is_user_assigned(self, user):
        """
        Check if the given user is assigned to the post creator.
        """
        if self.creator == user:
            return True
        if user in self.creator.assigned_communitymanagers.all():
            return True
        if user == self.creator.assigned_moderator:
            return True
        return False
    
    def has_feedback(self):
        """
        Check if the post has feedback.
        """
        return bool(self.feedback and self.feedback.strip())
