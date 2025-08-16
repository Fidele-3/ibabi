# views/user/reset_password.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from users.models import CustomUser, PasswordResetOTP
from django.utils import timezone
from datetime import timedelta
from ibabi.utils.generate_otp import generate_otp
from users.tasks.otp_notification import send_email_password_reset_otp
from users.tasks.send_email_password_reset_success import send_email_password_reset_success
from django.urls import reverse
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.hashers import check_password


# ----------------- Public: Request OTP -----------------
class RequestPasswordResetOTPView(APIView):
    authentication_classes = []  # No authentication required
    permission_classes = [AllowAny]

    def post(self, request):
        identifier = request.data.get("identifier")  # email or phone number
        if not identifier:
            return Response({"error": "Please provide email or phone number."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(email=identifier)
        except CustomUser.DoesNotExist:
            try:
                user = CustomUser.objects.get(phone_number=identifier)
            except CustomUser.DoesNotExist:
                return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        otp_code = generate_otp()
        expiration = timezone.now() + timedelta(minutes=15)

        PasswordResetOTP.objects.create(
            user=user,
            otp_code=otp_code,
            expires_at=expiration
        )

        reset_link = request.build_absolute_uri(reverse("reset-password-link"))

        # Celery task
        send_email_password_reset_otp.delay(
            user_id=str(user.id),
            full_names=user.full_names,
            email=user.email,
            otp_code=otp_code,
            reset_link=reset_link
        )

        return Response({"detail": "OTP sent to your registered contact."}, status=status.HTTP_200_OK)


# ----------------- Public: Verify OTP -----------------
class VerifyResetOTPView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        identifier = request.data.get("identifier")
        otp = request.data.get("otp")

        if not identifier or not otp:
            return Response({"error": "Identifier and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(email=identifier)
        except CustomUser.DoesNotExist:
            try:
                user = CustomUser.objects.get(phone_number=identifier)
            except CustomUser.DoesNotExist:
                return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            latest_otp = PasswordResetOTP.objects.filter(user=user).latest("created_at")
        except PasswordResetOTP.DoesNotExist:
            return Response({"error": "No OTP found. Please request a new one."}, status=status.HTTP_404_NOT_FOUND)

        if latest_otp.is_used:
            return Response({"error": "OTP already used."}, status=status.HTTP_400_BAD_REQUEST)

        if latest_otp.otp_code != otp:
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

        if latest_otp.expires_at < timezone.now():
            return Response({"error": "OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)

        latest_otp.is_used = True
        latest_otp.save()

        return Response({"detail": "OTP verified."}, status=status.HTTP_200_OK)


# ----------------- Public: Reset password using OTP -----------------
class ResetPasswordView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        identifier = request.data.get("identifier")
        otp = request.data.get("otp")
        password = request.data.get("password")

        if not identifier or not otp or not password:
            return Response({"error": "Identifier, OTP and new password are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(email=identifier)
        except CustomUser.DoesNotExist:
            try:
                user = CustomUser.objects.get(phone_number=identifier)
            except CustomUser.DoesNotExist:
                return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            otp_obj = PasswordResetOTP.objects.filter(user=user).latest("created_at")
        except PasswordResetOTP.DoesNotExist:
            return Response({"error": "No OTP found. Please request a new one."}, status=status.HTTP_404_NOT_FOUND)

        if otp_obj.is_used:
            return Response({"error": "OTP already used."}, status=status.HTTP_400_BAD_REQUEST)

        if otp_obj.otp_code != otp:
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

        if otp_obj.expires_at < timezone.now():
            return Response({"error": "OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)

        otp_obj.is_used = True
        otp_obj.save()

        user.set_password(password)
        user.save()

        send_email_password_reset_success.delay(
            user_id=str(user.id),
            full_names=user.full_names,
            email=user.email
        )

        return Response({"detail": "Password reset successfully."}, status=status.HTTP_200_OK)


# ----------------- Authenticated: Change password using old password -----------------
class AuthenticatedChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not old_password or not new_password:
            return Response({"error": "Old and new passwords are required."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user

        if not check_password(old_password, user.password):
            return Response({"error": "Old password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        send_email_password_reset_success.delay(
            user_id=str(user.id),
            full_names=user.full_names,
            email=user.email
        )

        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)
