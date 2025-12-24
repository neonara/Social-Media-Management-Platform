# Import all views from platform-specific files
from apps.social_media.views.facebook import (
    FacebookConnectView,
    FacebookCallbackView,
    FacebookDisconnectView,
    FacebookPageView,
    PublishToFacebookView,
)

from apps.social_media.views.instagram import (
    InstagramConnectView,
    InstagramCallbackView,
    InstagramDisconnectView,
    InstagramPageView,
    PublishToInstagramView,
)

from apps.social_media.views.linkedin import (
    LinkedInConnectView,
    LinkedInCallbackView,
    LinkedInDisconnectView,
    LinkedInPageView,
    PublishToLinkedInView,
)

# Expose all views
__all__ = [
    "FacebookConnectView",
    "FacebookCallbackView",
    "FacebookDisconnectView",
    "FacebookPageView",
    "PublishToFacebookView",
    "InstagramConnectView",
    "InstagramCallbackView",
    "InstagramDisconnectView",
    "InstagramPageView",
    "PublishToInstagramView",
    "LinkedInConnectView",
    "LinkedInCallbackView",
    "LinkedInDisconnectView",
    "LinkedInPageView",
    "PublishToLinkedInView",
]
