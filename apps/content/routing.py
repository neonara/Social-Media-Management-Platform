from django.urls import re_path
from apps.content.consumers import PostTableConsumer

websocket_urlpatterns = [
    re_path(r'^ws/posts/$', PostTableConsumer.as_asgi()),
]
