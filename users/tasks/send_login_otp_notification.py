from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from users.models.notification import Notification
from users.models.customuser import CustomUser
import logging
from uuid import UUID

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_login_otp_notification(self, user_id: str, full_names: str, email: str, otp_code: str, phone: str = None):
    notif = None
    try:
        user = CustomUser.objects.get(id=UUID(user_id))

        subject = "Your Login OTP Code"
        message = f"Hi {full_names}, your OTP code for login is: {otp_code}. Please use this code to complete your login."

        notif = Notification.objects.create(
            recipient=user,
            triggered_by=None,
            notification_type='email',
            subject=subject,
            message=message,
            is_sent=False
        )

        context = {
            "full_names": full_names,
            "otp_code": otp_code
        }

        text_content = render_to_string("emails/login_otp.txt", context)
        html_content = render_to_string("emails/login_otp.html", context)
        from_email = settings.DEFAULT_FROM_EMAIL

        # Send email
        msg = EmailMultiAlternatives(subject, text_content, from_email, [email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        notif.is_sent = True
        notif.sent_at = timezone.now()
        notif.save()

        logger.info(f"Login OTP email sent to {email}")

        # Optionally send SMS if phone is provided
        if phone:
            # Here you would call your SMS sending function or service
            # For example, trigger an SMS sending task or external API call
            logger.info(f"Login OTP SMS sent to {phone} (simulate)")

    except CustomUser.DoesNotExist:
        logger.error(f"User with ID {user_id} does not exist.")
    except Exception as e:
        if notif:
            notif.is_sent = False
            notif.save()
        logger.error(f"Error sending login OTP notification to {email}: {e}")
        raise self.retry(exc=e, countdown=60)
