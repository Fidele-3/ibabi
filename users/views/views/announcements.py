# permissions.py
from rest_framework import permissions

class IsSuperAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission:
    - Superadmins: all actions
    - Others: read-only
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.user_level == "super_admin"
# views.py
from rest_framework import viewsets
from report.models.notifications import Announcement
from users.serializer.announcements import AnnouncementSerializer


class AnnouncementViewSet(viewsets.ModelViewSet):
    """
    API endpoint for announcements
    """
    queryset = Announcement.objects.all().order_by('-created_at')
    serializer_class = AnnouncementSerializer
    permission_classes = [IsSuperAdminOrReadOnly]

    def perform_create(self, serializer):
        # Automatically set created_by as the logged-in superadmin
        serializer.save(created_by=self.request.user)
