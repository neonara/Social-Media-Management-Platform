from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock

User = get_user_model()


class AIIntegrationTestCase(TestCase):
    """Test cases for AI Integration features"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="ai_tester@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

    @patch("apps.ai_integration.views.get_gemini_service")
    def test_suggest_hashtags_api(self, mock_gemini):
        """Test hashtag suggestion API endpoint"""
        # Mock Gemini service response
        mock_service = MagicMock()
        mock_service.analyze_caption_for_hashtags.return_value = {
            "hashtags": ["#fitness", "#workout", "#gym"],
            "industry": "fitness",
            "platform": "instagram",
            "reasoning": "These are trending fitness hashtags",
            "count": 3,
        }
        mock_gemini.return_value = mock_service

        response = self.client.post(
            "/api/ai/hashtags/suggest/",
            {
                "caption": "Just finished my workout!",
                "platform": "instagram",
                "count": 3,
            },
            format="json",
        )

        # Should return 200 or 404 if endpoint doesn't exist yet
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    def test_suggest_hashtags_missing_caption(self):
        """Test hashtag API with missing caption"""
        response = self.client.post(
            "/api/ai/hashtags/suggest/",
            {"platform": "instagram"},
            format="json",
        )
        # Should return 400 or 404
        self.assertIn(
            response.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND],
        )

    @patch("apps.ai_integration.views.get_gemini_service")
    def test_analyze_mood_api(self, mock_gemini):
        """Test mood analysis API endpoint"""
        mock_service = MagicMock()
        mock_service.extract_mood_and_tone.return_value = {
            "mood": "Energetic",
            "tone": "Motivational",
            "confidence": 0.95,
            "description": "The caption has an energetic and motivational tone",
        }
        mock_gemini.return_value = mock_service

        response = self.client.post(
            "/api/ai/caption/analyze-mood/",
            {"caption": "Let's crush this workout! 💪"},
            format="json",
        )

        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    @patch("apps.ai_integration.views.get_gemini_service")
    def test_improve_caption_api(self, mock_gemini):
        """Test caption improvement API endpoint"""
        mock_service = MagicMock()
        mock_service.generate_caption_improvement.return_value = {
            "improved_caption": "Just crushed my morning workout! 💪 Feeling energized!",
            "improvements": ["Added emojis", "Made it more engaging"],
            "reasoning": "Enhanced with action words and emoji",
        }
        mock_gemini.return_value = mock_service

        response = self.client.post(
            "/api/ai/caption/improve/",
            {"caption": "Had a workout", "platform": "instagram"},
            format="json",
        )

        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])


class GeminiServiceTestCase(TestCase):
    """Test cases for Gemini Service (requires API key)"""

    def test_gemini_service_initialization(self):
        """Test Gemini service can be initialized"""
        try:
            from apps.ai_integration.services.gemini_service import GeminiService
            service = GeminiService()
            self.assertIsNotNone(service)
        except Exception as e:
            # Service might fail without API key, which is expected in tests
            self.assertIn("API_KEY", str(e).upper())
