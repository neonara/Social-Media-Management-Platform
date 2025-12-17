from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.social_media.models import SocialPage

User = get_user_model()


class SocialPageModelTestCase(TestCase):
    """Test cases for SocialPage model"""

    def setUp(self):
        self.client_user = User.objects.create_user(
            email="client@example.com",
            password="testpass123",
        )
        self.client_user.is_client = True
        self.client_user.save()

    def test_create_facebook_page(self):
        """Test creating a Facebook social page"""
        page = SocialPage.objects.create(
            client=self.client_user,
            platform="facebook",
            page_id="123456789",
            page_name="My Facebook Page",
            access_token="test_fb_token",
        )
        self.assertEqual(page.platform, "facebook")
        self.assertEqual(page.page_name, "My Facebook Page")
        self.assertEqual(page.client, self.client_user)

    def test_create_instagram_page(self):
        """Test creating an Instagram social page"""
        page = SocialPage.objects.create(
            client=self.client_user,
            platform="instagram",
            page_id="987654321",
            page_name="My Instagram Account",
            access_token="test_ig_token",
        )
        self.assertEqual(page.platform, "instagram")
        self.assertEqual(page.page_name, "My Instagram Account")

    def test_create_linkedin_page(self):
        """Test creating a LinkedIn social page"""
        page = SocialPage.objects.create(
            client=self.client_user,
            platform="linkedin",
            page_id="linkedin123",
            page_name="My LinkedIn Company",
            access_token="test_linkedin_token",
            permissions={"expires_in": 5184000},  # 60 days in seconds
        )
        self.assertEqual(page.platform, "linkedin")
        self.assertEqual(page.page_name, "My LinkedIn Company")

    def test_social_page_string_representation(self):
        """Test social page string representation"""
        page = SocialPage.objects.create(
            client=self.client_user,
            platform="facebook",
            page_id="123456",
            page_name="Test Page",
            access_token="token",
        )
        self.assertEqual(str(page), "Test Page (facebook)")

    def test_token_validation_with_expires_at(self):
        """Test token validation with token_expires_at"""
        # Token expires in the future - should be valid
        future_time = timezone.now() + timedelta(days=30)
        page = SocialPage.objects.create(
            client=self.client_user,
            platform="facebook",
            page_id="123",
            page_name="Valid Token Page",
            access_token="token",
            token_expires_at=future_time,
        )
        self.assertTrue(page.is_token_valid())

    def test_token_validation_expired(self):
        """Test token validation with expired token"""
        # Token expired in the past - should be invalid
        past_time = timezone.now() - timedelta(days=1)
        page = SocialPage.objects.create(
            client=self.client_user,
            platform="facebook",
            page_id="456",
            page_name="Expired Token Page",
            access_token="token",
            token_expires_at=past_time,
        )
        self.assertFalse(page.is_token_valid())

    def test_linkedin_token_validation(self):
        """Test LinkedIn token validation with expires_in"""
        page = SocialPage.objects.create(
            client=self.client_user,
            platform="linkedin",
            page_id="linkedin456",
            page_name="LinkedIn Page",
            access_token="linkedin_token",
            permissions={"expires_in": 5184000},  # 60 days
        )
        # Since the page was just created, token should be valid
        self.assertTrue(page.is_token_valid())

    def test_unique_together_constraint(self):
        """Test unique_together constraint on client, page_id, platform"""
        SocialPage.objects.create(
            client=self.client_user,
            platform="facebook",
            page_id="unique123",
            page_name="First Page",
            access_token="token1",
        )
        
        # Creating another page with same client, page_id, and platform should fail
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            SocialPage.objects.create(
                client=self.client_user,
                platform="facebook",
                page_id="unique123",
                page_name="Duplicate Page",
                access_token="token2",
            )

    def test_permissions_json_field(self):
        """Test permissions JSON field"""
        page = SocialPage.objects.create(
            client=self.client_user,
            platform="facebook",
            page_id="789",
            page_name="Permissions Test",
            access_token="token",
            permissions={
                "scope": ["pages_manage_posts", "pages_read_engagement"],
                "expires_in": 3600
            },
        )
        self.assertIsInstance(page.permissions, dict)
        self.assertIn("scope", page.permissions)
        self.assertEqual(page.permissions["expires_in"], 3600)
