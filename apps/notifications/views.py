from requests import Response
from rest_framework.generics import UpdateAPIView, ListAPIView, DestroyAPIView
from .models import Notification
from .serializers import NotificationSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

class UserNotificationsView(ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)
    
class MarkNotificationAsReadView(UpdateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Notification.objects.all()

    def update(self, request, *args, **kwargs):
        notification_id = kwargs.get('pk')
        try:
            notification = self.queryset.get(id=notification_id, recipient=request.user)
            notification.is_read = True
            notification.save()
            return Response({'marked_as_read': True}, status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

class MarkAllAsReadView(UpdateAPIView):
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        count = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({'marked_as_read': count})
    
class DeleteNotificationView(DestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Notification.objects.all()

    def delete(self, request, *args, **kwargs):
        notification_id = kwargs.get('pk')
        try:
            notification = self.queryset.get(id=notification_id, recipient=request.user)
            notification.delete()
            return Response({'deleted': True}, status=status.HTTP_204_NO_CONTENT)
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

