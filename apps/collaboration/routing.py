from django.urls import re_path
from .consumers import CollaborationConsumer, ChatConsumer, GeneralChatConsumer

websocket_urlpatterns = [
    re_path(r"ws/collaboration/(?P<content_id>\d+)/$", CollaborationConsumer.as_asgi()),
    re_path(r"ws/chat/$", GeneralChatConsumer.as_asgi()),
    re_path(r"ws/chat/(?P<room_id>\d+)/$", ChatConsumer.as_asgi()),
]
