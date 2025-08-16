from django.apps import AppConfig


class ReportConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'report'

    def ready(self):

        # Import signals to ensure they are registered
        import report.signals.notification  # noqa: F401
        