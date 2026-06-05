from django.apps import AppConfig


class FinManagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fin_manager'
    verbose_name = 'FinPilot Finance Manager'

    def ready(self):
        pass  # signals would be registered here
