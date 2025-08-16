# serializers.py
from rest_framework import serializers
from report.models.notifications import Announcement

class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ['id', 'title', 'message', 'created_by', 'created_at']
        read_only_fields = ['id', 'created_by', 'created_at']
