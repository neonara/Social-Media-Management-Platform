from django.urls import path

from .views import InstagramCallbackView, InstagramConnectView, InstagramDisconnectView, publish_to_facebook, publish_to_instagram, publish_to_linkedin, FacebookConnectView, FacebookCallbackView, FacebookDisconnectView

urlpatterns = [
    path('facebook/<int:post_id>/publish/', publish_to_facebook, name='publish_facebook'),
    path('instagram/<int:post_id>/publish/', publish_to_instagram, name='publish_instagram'),
    path('linkedin/<int:post_id>/publish/', publish_to_linkedin, name='publish_linkedin'),

    path('facebook/connect/', FacebookConnectView.as_view(), name='facebook_connect'),
    path('facebook/callback/', FacebookCallbackView.as_view(), name='facebook_callback'),
    path('facebook/disconnect/', FacebookDisconnectView.as_view(), name='facebook_disconnect'),

    path('instagram/connect/', InstagramConnectView.as_view(), name='ig_connect'),
    path('instagram/callback/', InstagramCallbackView.as_view(), name='ig_callback'),
    path('instagram/disconnect/', InstagramDisconnectView.as_view(), name='ig_callback'),
]