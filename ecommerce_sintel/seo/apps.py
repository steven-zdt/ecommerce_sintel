from django.apps import AppConfig


class SeoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'seo'
    verbose_name = 'SEO y Metaetiquetas'

    def ready(self):
        """Registra signal handlers al cargar la app."""
        import seo.signals  # noqa: F401
