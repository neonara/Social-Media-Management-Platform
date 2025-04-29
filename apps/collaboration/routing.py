from django.urls import re_path
from .consumers import CollaborationConsumer

websocket_urlpatterns = [
    re_path(r'ws/collaboration/(?P<content_id>\d+)/$', CollaborationConsumer.as_asgi()),
]
