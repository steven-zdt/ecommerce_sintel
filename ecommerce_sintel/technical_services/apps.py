from django.apps import AppConfig


class TechnicalServicesConfig(AppConfig):
    name = 'technical_services'

    def ready(self):
        import technical_services.signals  # noqa: F401
