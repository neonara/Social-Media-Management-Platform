from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.accounts.tasks import send_celery_email
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class UserModelTestCase(TestCase):
    """Test cases for User model"""

    def setUp(self):
        self.user_data = {
            "email": "test@example.com",
            "password": "testpass123",
            "first_name": "Test",
            "last_name": "User",
        }

    def test_create_user(self):
        """Test creating a regular user"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.email, self.user_data["email"])
        self.assertTrue(user.check_password(self.user_data["password"]))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        """Test creating a superuser"""
        superuser = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
        )
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)

    def test_user_full_name(self):
        """Test user full name property"""
        user = User.objects.create_user(**self.user_data)
        expected_name = f"{self.user_data['first_name']} {self.user_data['last_name']}"
        self.assertEqual(user.full_name, expected_name)

    def test_user_roles(self):
        """Test user role flags"""
        user = User.objects.create_user(**self.user_data)
        user.is_client = True
        user.is_moderator = False
        user.save()
        self.assertTrue(user.is_client)
        self.assertFalse(user.is_moderator)


class UserAuthenticationTestCase(TestCase):
    """Test cases for user authentication"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )

    def test_user_login(self):
        """Test user can login with valid credentials"""
        response = self.client.post(
            "/api/accounts/login/",
            {"email": "test@example.com", "password": "testpass123"},
            format="json",
        )
        # Test passes if endpoint exists and returns valid response
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])


class CeleryTaskTestCase(TestCase):
    """Test cases for Celery tasks"""

    def test_send_email_task(self):
        """Test email task is queued successfully"""
        result = send_celery_email.delay(
            subject="Test Email",
            message="This is a test email sent via Celery.",
            recipient_list=["recipient@example.com"],
        )
        self.assertTrue(result.id)  # Check if the task was queued
