from django.apps import AppConfig


class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        import users.signals.account_notifications
        import users.signals.otp_notification
        from users.signals.pasword_reset_success import notify_password_reset
        from users.signals.otp_login import send_login_otp_notification
    
        
