# users/serializers/profile.py
from rest_framework import serializers
from users.models import CustomUser

class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'address']  # adjust fields

    def validate_email(self, value):
        if CustomUser.objects.exclude(pk=self.instance.pk).filter(email=value).exists():
            raise serializers.ValidationError("Email is already in use.")
        return value

    def validate_phone_number(self, value):
        if CustomUser.objects.exclude(pk=self.instance.pk).filter(phone_number=value).exists():
            raise serializers.ValidationError("Phone number is already in use.")
        return value
