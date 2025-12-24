from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.notifications.models import Notification

User = get_user_model()


class NotificationModelTestCase(TestCase):
    """Test cases for Notification model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="notify@example.com",
            password="testpass123",
        )

    def test_create_notification(self):
        """Test creating a notification"""
        notification = Notification.objects.create(
            recipient=self.user,
            title="Test Notification",
            message="This is a test notification",
            type="post_approved",
        )
        self.assertEqual(notification.title, "Test Notification")
        self.assertEqual(notification.recipient, self.user)
        self.assertFalse(notification.is_read)

    def test_notification_ordering(self):
        """Test notifications are ordered by created_at desc"""
        notif1 = Notification.objects.create(
            recipient=self.user,
            title="First",
            message="First notification",
        )
        notif2 = Notification.objects.create(
            recipient=self.user,
            title="Second",
            message="Second notification",
        )
        notifications = Notification.objects.all()
        self.assertEqual(notifications[0], notif2)
        self.assertEqual(notifications[1], notif1)

    def test_notification_type_field(self):
        """Test notification type field"""
        notification = Notification.objects.create(
            recipient=self.user,
            title="Post Approved",
            message="Your post has been approved",
            type="post_approved",
        )
        self.assertEqual(notification.type, "post_approved")

    def test_notification_is_read_default(self):
        """Test notification is_read defaults to False"""
        notification = Notification.objects.create(
            recipient=self.user,
            title="Test",
            message="Test message",
        )
        self.assertFalse(notification.is_read)

    def test_mark_notification_as_read(self):
        """Test marking notification as read"""
        notification = Notification.objects.create(
            recipient=self.user,
            title="Test",
            message="Test message",
        )
        notification.is_read = True
        notification.save()
        self.assertTrue(notification.is_read)
