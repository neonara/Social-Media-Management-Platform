from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    DeleteNotificationView,
    MarkNotificationAsReadView,
    UserNotificationsView,
    MarkAllAsReadView,
    NotificationViewSet,
)

# Create a router for ViewSets
router = DefaultRouter()
router.register(
    r"api/notifications", NotificationViewSet, basename="notification-viewset"
)

# Standard URL patterns for class-based views
urlpatterns = [
    # Include ViewSet URLs
    path("", include(router.urls)),
    # Existing URLs
    path("notifications/", UserNotificationsView.as_view(), name="notifications_list"),
    path(
        "notifications/read-all/",
        MarkAllAsReadView.as_view(),
        name="notifications_mark_all_read",
    ),
    path(
        "notifications/<int:pk>/read/",
        MarkNotificationAsReadView.as_view(),
        name="notifications_mark_read",
    ),
    path(
        "notifications/<int:pk>/delete/",
        DeleteNotificationView.as_view(),
        name="notifications_delete",
    ),
]
