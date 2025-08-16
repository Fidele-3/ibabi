from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.utils import timezone
from django.db.models import Q
import random
from datetime import timedelta
from users.models import CustomUser, LoginOTP
from users.serializer.login import LoginSerializer, OTPVerifySerializer
from rest_framework_simplejwt.tokens import RefreshToken

# All users go to the same dashboard frontend route
def get_redirect_url(user_level):
    return '/dashboard/'  # Single frontend route for all roles

class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data['identifier']
        password = serializer.validated_data['password']

        # Find user by email or phone
        try:
            user = CustomUser.objects.get(Q(email=identifier) | Q(phone_number=identifier))
        except CustomUser.DoesNotExist:
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(password):
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.is_active:
            return Response({'detail': 'User account is inactive.'}, status=status.HTTP_403_FORBIDDEN)

        # Generate OTP
        otp_code = f"{random.randint(100000, 999999)}"
        expires_at = timezone.now() + timedelta(minutes=15)
        LoginOTP.objects.create(user=user, otp_code=otp_code, expires_at=expires_at)

        return Response({'detail': 'OTP sent to your email and phone.'})


class OTPVerifyAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        identifier = serializer.validated_data['identifier']
        otp_code = serializer.validated_data['otp_code']

        # Find user
        try:
            user = CustomUser.objects.get(Q(email=identifier) | Q(phone_number=identifier))
        except CustomUser.DoesNotExist:
            return Response({'detail': 'Invalid OTP or identifier.'}, status=status.HTTP_400_BAD_REQUEST)

        # Find latest OTP that is not used and matches code
        otp_qs = LoginOTP.objects.filter(
            user=user,
            otp_code=otp_code,
            is_used=False,
            expires_at__gt=timezone.now()
        ).order_by('-created_at')

        if not otp_qs.exists():
            return Response({'detail': 'Invalid or expired OTP.'}, status=status.HTTP_400_BAD_REQUEST)

        otp = otp_qs.first()
        otp.is_used = True
        otp.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user_level': user.user_level,
            'redirect_url': get_redirect_url(user.user_level),  # now always /dashboard/
        })
