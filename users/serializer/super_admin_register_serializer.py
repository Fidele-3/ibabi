from rest_framework import serializers
from users.models import CustomUser, UserProfile

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        exclude = ['user']  # We'll attach user in view

class SuperAdminCreateSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)  # nested profile

    class Meta:
        model = CustomUser
        fields = ['email', 'full_names', 'phone_number', 'national_id', 'password', 'profile']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate(self, attrs):
        if CustomUser.objects.filter(user_level='super_admin').exists():
            raise serializers.ValidationError("Superadmin already exists.")
        return attrs

    def create(self, validated_data):
        profile_data = validated_data.pop('profile', None)
        validated_data['user_level'] = 'super_admin'
        password = validated_data.pop('password')
        user = CustomUser.objects.create(**validated_data)
        user.set_password(password)
        user.save()

        if profile_data:
            UserProfile.objects.create(user=user, **profile_data)

        return user
