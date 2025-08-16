# views.py
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from report.models.notifications import Notifications
from users.serializer.notifications import NotificationSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user notifications
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only return notifications for the logged-in user
        return Notifications.objects.filter(recipient=self.request.user).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """
        Mark a single notification as read
        """
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({"status": "marked as is_read"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'])
    def delete_notification(self, request, pk=None):
        """
        Delete a notification
        """
        notification = self.get_object()
        notification.delete()
        return Response({"status": "deleted"}, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """
        Return unread notifications
        """
        unread_notifications = self.get_queryset().filter(is_read=False)
        serializer = self.get_serializer(unread_notifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
