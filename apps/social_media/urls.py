from django.urls import path

from apps.social_media.views.views import SocialPagesView, ClientSocialPagesView

from .views import (
    FacebookConnectView,
    FacebookCallbackView,
    FacebookDisconnectView,
    PublishToFacebookView,
    InstagramConnectView,
    InstagramCallbackView,
    InstagramDisconnectView,
    PublishToInstagramView,
    LinkedInConnectView,
    LinkedInCallbackView,
    LinkedInDisconnectView,
    PublishToLinkedInView,
    FacebookPageView,
    InstagramPageView,
    LinkedInPageView,
)

urlpatterns = [
    path(
        "facebook/<int:post_id>/publish/",
        PublishToFacebookView.as_view(),
        name="publish_facebook",
    ),
    path(
        "instagram/<int:post_id>/publish/",
        PublishToInstagramView.as_view(),
        name="publish_instagram",
    ),
    path(
        "linkedin/<int:post_id>/publish/",
        PublishToLinkedInView.as_view(),
        name="publish_linkedin",
    ),
    path("facebook/connect/", FacebookConnectView.as_view(), name="facebook_connect"),
    path(
        "facebook/callback/", FacebookCallbackView.as_view(), name="facebook_callback"
    ),
    path(
        "facebook/disconnect/",
        FacebookDisconnectView.as_view(),
        name="facebook_disconnect",
    ),
    path("instagram/connect/", InstagramConnectView.as_view(), name="ig_connect"),
    path("instagram/callback/", InstagramCallbackView.as_view(), name="ig_callback"),
    path(
        "instagram/disconnect/", InstagramDisconnectView.as_view(), name="ig_disconnect"
    ),
    path("linkedin/connect/", LinkedInConnectView.as_view(), name="linkedin_connect"),
    path(
        "linkedin/callback/", LinkedInCallbackView.as_view(), name="linkedin_callback"
    ),
    path(
        "linkedin/disconnect/",
        LinkedInDisconnectView.as_view(),
        name="linkedin_disconnect",
    ),
    # Endpoint to get current client's connected social pages
    path("social/pages/", SocialPagesView.as_view(), name="social_pages"),
    # Endpoint for moderators and community managers to get a specific client's pages
    path(
        "social/pages/client/<int:client_id>/",
        ClientSocialPagesView.as_view(),
        name="client_social_pages",
    ),
    # Optional: Platform-specific page info endpoints
    path("facebook/page/", FacebookPageView.as_view(), name="facebook_page"),
    path("instagram/page/", InstagramPageView.as_view(), name="instagram_page"),
    path("linkedin/page/", LinkedInPageView.as_view(), name="linkedin_page"),
]
