"""
Signal handlers para seo app.

Invalida el cache de metaetiquetas activas cuando cambia cualquier
SiteMetaTag -- mismo patron que core/signals.py (post_save/post_delete ->
cache.delete(KEY)). Registrado en SeoConfig.ready().
"""
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from seo.models import SiteMetaTag, SiteVerificationFile

SEO_META_TAGS_CACHE_KEY = 'sintel_seo_meta_tags_v1'
VERIFICATION_FILE_CACHE_PREFIX = 'sintel_seo_verification_file_v1:'


@receiver(post_save, sender=SiteMetaTag)
@receiver(post_delete, sender=SiteMetaTag)
def invalidate_seo_meta_tags_cache(sender, instance, **kwargs):
    """Invalida el cache de metaetiquetas cuando se crea/edita/elimina una."""
    cache.delete(SEO_META_TAGS_CACHE_KEY)


@receiver(post_save, sender=SiteVerificationFile)
@receiver(post_delete, sender=SiteVerificationFile)
def invalidate_verification_file_cache(sender, instance, **kwargs):
    """Invalida el cache del archivo de verificacion (clave por filename)."""
    cache.delete(f'{VERIFICATION_FILE_CACHE_PREFIX}{instance.filename}')
