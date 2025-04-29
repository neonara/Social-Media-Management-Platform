from models import SocialPage
from django.utils import timezone
from datetime import timedelta

def store_social_page(user, page_info, platform):
    """
    Stores or updates the user's connected social media page info.
    page_info example for Facebook:
    {
        "id": "123456789",
        "name": "My Business Page",
        "access_token": "EAAG...",
        "tasks": ["MODERATE", "CREATE_CONTENT"]
    }
    """

    token_expiry = timezone.now() + timedelta(days=60)  # Or get from response if provided

    SocialPage.objects.update_or_create(
        user=user,
        page_id=page_info['id'],
        platform=platform,
        defaults={
            'page_name': page_info['name'],
            'access_token': page_info['access_token'],
            'permissions': {'tasks': page_info.get('tasks', [])},
            'token_expires_at': token_expiry,
        }
    )

