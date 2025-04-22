from django.urls import path

from .views import publish_to_facebook, publish_to_instagram, publish_to_linkedin, FacebookConnectView, FacebookCallbackView,FacebookDisconnectView

urlpatterns = [
    path('social/facebook/<int:post_id>/publish/', publish_to_facebook.as_view(), name='publish_facebook'),
    path('social/instagram/<int:post_id>/publish/', publish_to_instagram.as_view(), name='publish_instagram'),
    path('social/linkedin/<int:post_id>/publish/', publish_to_linkedin.as_view(), name='publish_linkedin'),

    path('social/facebook/connect/', FacebookConnectView.as_view(), name='facebook_connect'),
    path('social/facebook/callback/', FacebookCallbackView.as_view(), name='facebook_callback'),
    path('social/facebook/disconnect/', FacebookDisconnectView.as_view(), name='facebook_disconnect'),
]