from rest_framework import serializers

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()  # email or phone
    password = serializers.CharField(write_only=True)

class OTPVerifySerializer(serializers.Serializer):
    identifier = serializers.CharField()  # email or phone
    otp_code = serializers.CharField(max_length=6)
