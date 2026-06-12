from django.apps import AppConfig


class CorefisicaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'CoreFisica'

    def ready(self):
        # Conecta las señales de auditoría (audit trail).
        from . import signals  # noqa: F401
