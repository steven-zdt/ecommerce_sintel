"""
Resolucion del entorno activo para filtrar SiteMetaTag.environment.

Unico punto de extension: si en el futuro el proyecto agrega
settings/testing.py o settings/staging.py, solo hay que setear
SEO_ACTIVE_ENVIRONMENT en el entorno correspondiente -- ningun otro archivo
de este modulo necesita cambiar.
"""
from django.conf import settings


def resolve_current_environment() -> str:
    from seo.models import SiteMetaTag

    override = getattr(settings, 'SEO_ACTIVE_ENVIRONMENT', '') or ''
    valid_values = {choice for choice, _ in SiteMetaTag.ENV_CHOICES}
    if override in valid_values:
        return override

    return SiteMetaTag.ENV_DEVELOPMENT if getattr(settings, 'DEBUG', False) else SiteMetaTag.ENV_PRODUCTION
