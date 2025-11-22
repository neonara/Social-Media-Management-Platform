from rest_framework.response import Response
from rest_framework.generics import ListAPIView, DestroyAPIView
from rest_framework.views import APIView
from .models import Notification
from .serializers import NotificationSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, viewsets
from django.core.cache import cache
from django.conf import settings
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

# Cache timeout in seconds (1 hour)
NOTIFICATION_CACHE_TIMEOUT = getattr(settings, "NOTIFICATION_CACHE_TIMEOUT", 3600)


# New ViewSet for Notifications with caching
class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    # Apply cache for GET methods
    @method_decorator(cache_page(300))  # Cache for 5 minutes
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(recipient=self.request.user)

    def perform_update(self, serializer):
        instance = self.get_object()
        # If marking as read, update the unread count cache
        if (
            "is_read" in serializer.validated_data
            and serializer.validated_data["is_read"]
        ):
            cache_key = f"user_notifications:{self.request.user.id}"
            cache.delete(cache_key)
            self._update_unread_count_cache(self.request.user.id)
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()
        # Invalidate user notifications cache
        cache_key = f"user_notifications:{self.request.user.id}"
        cache.delete(cache_key)
        # Update unread count cache
        self._update_unread_count_cache(self.request.user.id)

    def _update_unread_count_cache(self, user_id):
        """Update the cached unread notification count"""
        unread_count = Notification.objects.filter(
            recipient_id=user_id, is_read=False
        ).count()
        cache.set(
            f"user_unread_count:{user_id}", unread_count, NOTIFICATION_CACHE_TIMEOUT
        )


# Keep your existing views below
class UserNotificationsView(ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Check if user notifications are cached
        cache_key = f"user_notifications:{self.request.user.id}"
        cached_notifications = cache.get(cache_key)

        if cached_notifications is not None:
            return cached_notifications

        # If not cached, fetch from database
        queryset = Notification.objects.filter(recipient=self.request.user)

        # Cache the queryset
        cache.set(cache_key, queryset, NOTIFICATION_CACHE_TIMEOUT)

        return queryset


class MarkNotificationAsReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        notification_id = kwargs.get("pk")
        try:
            notification = Notification.objects.get(
                id=notification_id, recipient=request.user
            )
            notification.is_read = True
            notification.save()

            # Invalidate user notifications cache
            cache_key = f"user_notifications:{request.user.id}"
            cache.delete(cache_key)

            # Update unread count cache
            self._update_unread_count_cache(request.user.id)

            return Response({"marked_as_read": True}, status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response(
                {"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND
            )

    def _update_unread_count_cache(self, user_id):
        """Update the cached unread notification count"""
        unread_count = Notification.objects.filter(
            recipient_id=user_id, is_read=False
        ).count()
        cache.set(
            f"user_unread_count:{user_id}", unread_count, NOTIFICATION_CACHE_TIMEOUT
        )

    def _update_unread_count_cache(self, user_id):
        """Update the cached unread notification count"""
        unread_count = Notification.objects.filter(
            recipient_id=user_id, is_read=False
        ).count()
        cache.set(
            f"user_unread_count:{user_id}", unread_count, NOTIFICATION_CACHE_TIMEOUT
        )


class MarkAllAsReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True)

        # Invalidate user notifications cache
        cache_key = f"user_notifications:{request.user.id}"
        cache.delete(cache_key)

        # Update unread count cache
        cache.set(f"user_unread_count:{request.user.id}", 0, NOTIFICATION_CACHE_TIMEOUT)

        return Response({"marked_as_read": count})


class DeleteNotificationView(DestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Notification.objects.all()

    def delete(self, request, *args, **kwargs):
        notification_id = kwargs.get("pk")
        try:
            notification = self.queryset.get(id=notification_id, recipient=request.user)
            notification.delete()

            # Invalidate user notifications cache
            cache_key = f"user_notifications:{request.user.id}"
            cache.delete(cache_key)

            # Update unread count cache
            unread_count = Notification.objects.filter(
                recipient=request.user, is_read=False
            ).count()
            cache.set(
                f"user_unread_count:{request.user.id}",
                unread_count,
                NOTIFICATION_CACHE_TIMEOUT,
            )

            return Response({"deleted": True}, status=status.HTTP_204_NO_CONTENT)
        except Notification.DoesNotExist:
            return Response(
                {"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND
            )
