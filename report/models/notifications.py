import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings

class Notifications(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="app_notifications"
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, null=True)  # Optional: direct link in dashboard
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    is_announcement = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification to {self.recipient} - {self.title}"


class Announcement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    message = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="announcements"
    )
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title
