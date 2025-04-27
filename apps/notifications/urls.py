from django.urls import path

from .views import DeleteNotificationView, MarkNotificationAsReadView, UserNotificationsView, MarkAllAsReadView

urlpatterns = [
    path('notifications/', UserNotificationsView.as_view(), name='notifications_list'),
    path('notifications/read-all/', MarkAllAsReadView.as_view(), name='notifications_mark_all_read'),
    path('notifications/<int:pk>/read/', MarkNotificationAsReadView.as_view(), name='notifications_mark_read'),
    path('notifications/<int:pk>/delete/', DeleteNotificationView.as_view(), name='notifications_delete'),
]