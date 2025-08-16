# serializers.py
from rest_framework import serializers
from report.models.notifications import Notifications

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notifications
        fields = ['id', 'title', 'message', 'link', 'created_at', 'is_read']
