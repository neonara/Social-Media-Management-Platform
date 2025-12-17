from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.content.models import Post, Media
from django.utils import timezone

User = get_user_model()


class PostModelTestCase(TestCase):
    """Test cases for Post model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="creator@example.com",
            password="testpass123",
            first_name="Content",
            last_name="Creator",
        )

    def test_create_post(self):
        """Test creating a post"""
        post = Post.objects.create(
            title="Test Post",
            description="This is a test post",
            creator=self.user,
            status="draft",
        )
        self.assertEqual(post.title, "Test Post")
        self.assertEqual(post.status, "draft")
        self.assertEqual(post.creator, self.user)

    def test_post_status_choices(self):
        """Test post status transitions"""
        post = Post.objects.create(
            title="Status Test",
            creator=self.user,
            status="draft",
        )
        # Test status change
        post.status = "scheduled"
        post.save()
        self.assertEqual(post.status, "scheduled")

    def test_post_scheduled_for(self):
        """Test scheduling a post"""
        scheduled_time = timezone.now() + timezone.timedelta(days=1)
        post = Post.objects.create(
            title="Scheduled Post",
            creator=self.user,
            status="scheduled",
            scheduled_for=scheduled_time,
        )
        self.assertIsNotNone(post.scheduled_for)
        self.assertEqual(post.status, "scheduled")

    def test_post_platforms_field(self):
        """Test platforms JSON field"""
        post = Post.objects.create(
            title="Multi-platform Post",
            creator=self.user,
            platforms=["instagram", "facebook", "linkedin"],
        )
        self.assertEqual(len(post.platforms), 3)
        self.assertIn("instagram", post.platforms)


class MediaModelTestCase(TestCase):
    """Test cases for Media model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="media@example.com",
            password="testpass123",
        )

    def test_create_media(self):
        """Test creating a media object"""
        media = Media.objects.create(
            name="Test Image",
            type="image",
            creator=self.user,
        )
        self.assertEqual(media.type, "image")
        self.assertEqual(media.creator, self.user)

    def test_media_types(self):
        """Test different media types"""
        image = Media.objects.create(name="Image", type="image", creator=self.user)
        video = Media.objects.create(name="Video", type="video", creator=self.user)
        doc = Media.objects.create(name="Doc", type="document", creator=self.user)
        
        self.assertEqual(image.type, "image")
        self.assertEqual(video.type, "video")
        self.assertEqual(doc.type, "document")
