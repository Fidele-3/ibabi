from django.db.models.signals import post_save
from django.dispatch import Signal, receiver
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.conf import settings
from users.models.customuser import CustomUser

from users.models.otp_password import LoginOTP
from users.tasks.send_login_otp_notification import send_login_otp_notification


@receiver(post_save, sender=LoginOTP)
def trigger_login_otp_notification(sender, instance, created, **kwargs):
    if not created:
        return

    user = instance.user
    otp_code = instance.otp_code

    send_login_otp_notification.delay(
        user_id=str(user.id),
        full_names=user.full_names,
        email=user.email,
        otp_code=otp_code,
        phone=user.phone_number
    )
