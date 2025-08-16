from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta
from django.utils import timezone
from ibabi.models import ibabiSession
from users.tasks.send_ibabi_reminder import send_ibabi_notifications


@receiver(post_save, sender=ibabiSession)
def schedule_ibabi_notifications(sender, instance, created, **kwargs):
   
    if created:
        
        send_ibabi_notifications.delay(session_id=str(instance.id))
