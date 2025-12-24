from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ChatRoomViewSet,
    GetDirectMessageView,
    GetRoomMessagesView,
    MessageViewSet,
    SendMessageView,
)

router = DefaultRouter()
router.register(r"chat-rooms", ChatRoomViewSet)
router.register(r"messages", MessageViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("send-message/", SendMessageView.as_view(), name="send-message"),
    path(
        "room-messages/<int:room_id>/",
        GetRoomMessagesView.as_view(),
        name="room-messages",
    ),
    path("direct-message/", GetDirectMessageView.as_view(), name="direct-message"),
]
