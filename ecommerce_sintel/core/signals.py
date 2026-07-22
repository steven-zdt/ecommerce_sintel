"""
Signal handlers para core app.

Invalida cache automáticamente cuando cambia contenido:
- home-feed cache: HomeBanner, HomeCard, HomeModuleConfig, FooterCTAConfig
- footer cache: FooterLink (navegacion)
- site-config cache: NavbarLink

NOTA (2026-07-12): SiteBrandConfig y CompanyContactInfo se migraron a
`organization` (Company/Branding/ContactInfo) -- ver
Documentacion/Arquitectura_general/MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md.
`organization` no usa signals (regla explicita del plan de migracion); la
invalidacion de `SITE_CONFIG_CACHE_KEY`/`FOOTER_CACHE_KEY` para esos datos
ahora se hace explicita en dashboard/api/views.py (`_invalidate_site_config_cache()`
/ `_invalidate_footer_cache()`), justo despues de llamar a
`OrganizationCommands.upsert_company/upsert_branding/upsert_contact_info`.
"""

from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from core.models import (
    HomeBanner,
    HomeCard,
    HomeCardGroup,
    HomeModuleConfig,
    FooterLink,
    FooterGroup,
    NavbarLink,
    FooterCTAConfig,
    BrandSliderItem,
    BrandSliderConfig,
    AboutUsConfig,
    AboutUsValue,
)

# Cache keys (must match values in views.py)
HOME_FEED_CACHE_KEY = 'sintel_home_feed_v1'
FOOTER_CACHE_KEY = 'sintel_footer_v1'
SITE_CONFIG_CACHE_KEY = 'sintel_site_config_v1'
ABOUT_US_CACHE_KEY = 'sintel_about_us_v1'


# ── Home Feed Cache Invalidation ──────────────────────────────────────────

@receiver(post_save, sender=HomeBanner)
@receiver(post_delete, sender=HomeBanner)
def invalidate_home_feed_on_banner_change(sender, instance, **kwargs):
    """Invalida home-feed cuando se edita/elimina un banner."""
    cache.delete(HOME_FEED_CACHE_KEY)


@receiver(post_save, sender=HomeCard)
@receiver(post_delete, sender=HomeCard)
def invalidate_home_feed_on_card_change(sender, instance, **kwargs):
    """Invalida home-feed cuando se edita/elimina una tarjeta."""
    cache.delete(HOME_FEED_CACHE_KEY)


@receiver(post_save, sender=HomeCardGroup)
@receiver(post_delete, sender=HomeCardGroup)
def invalidate_home_feed_on_card_group_change(sender, instance, **kwargs):
    """Invalida home-feed cuando se edita/elimina un grupo de tarjetas."""
    cache.delete(HOME_FEED_CACHE_KEY)


@receiver(post_save, sender=HomeModuleConfig)
@receiver(post_delete, sender=HomeModuleConfig)
def invalidate_home_feed_on_module_config_change(sender, instance, **kwargs):
    """Invalida home-feed cuando se edita/elimina configuración de módulo."""
    cache.delete(HOME_FEED_CACHE_KEY)


@receiver(post_save, sender=FooterCTAConfig)
@receiver(post_delete, sender=FooterCTAConfig)
def invalidate_home_feed_on_footer_cta_change(sender, instance, **kwargs):
    """Invalida home-feed cuando se edita/elimina el CTA final (viaja en home-feed.footer_cta)."""
    cache.delete(HOME_FEED_CACHE_KEY)


@receiver(post_save, sender=BrandSliderItem)
@receiver(post_delete, sender=BrandSliderItem)
def invalidate_home_feed_on_brand_slider_item_change(sender, instance, **kwargs):
    """Invalida home-feed cuando se edita/elimina un logo del slider de marcas."""
    cache.delete(HOME_FEED_CACHE_KEY)


@receiver(post_save, sender=BrandSliderConfig)
@receiver(post_delete, sender=BrandSliderConfig)
def invalidate_home_feed_on_brand_slider_config_change(sender, instance, **kwargs):
    """Invalida home-feed cuando se edita la configuracion del slider de marcas."""
    cache.delete(HOME_FEED_CACHE_KEY)


# ── Footer Cache Invalidation ────────────────────────────────────────────

@receiver(post_save, sender=FooterLink)
@receiver(post_delete, sender=FooterLink)
def invalidate_footer_on_link_change(sender, instance, **kwargs):
    """Invalida footer cuando se edita/elimina un enlace."""
    cache.delete(FOOTER_CACHE_KEY)


@receiver(post_save, sender=FooterGroup)
@receiver(post_delete, sender=FooterGroup)
def invalidate_footer_on_group_change(sender, instance, **kwargs):
    """Invalida footer cuando se edita/elimina un grupo (columna) del footer."""
    cache.delete(FOOTER_CACHE_KEY)


# ── About Us Cache Invalidation ──────────────────────────────────────────

@receiver(post_save, sender=AboutUsConfig)
@receiver(post_delete, sender=AboutUsConfig)
def invalidate_about_us_on_config_change(sender, instance, **kwargs):
    """Invalida about-us cuando se edita la configuracion (historia/mision/vision)."""
    cache.delete(ABOUT_US_CACHE_KEY)


@receiver(post_save, sender=AboutUsValue)
@receiver(post_delete, sender=AboutUsValue)
def invalidate_about_us_on_value_change(sender, instance, **kwargs):
    """Invalida about-us cuando se edita/elimina un valor institucional."""
    cache.delete(ABOUT_US_CACHE_KEY)


# ── Site Config Cache Invalidation ──────────────────────────────────────

@receiver(post_save, sender=NavbarLink)
@receiver(post_delete, sender=NavbarLink)
def invalidate_site_config_on_navbar_change(sender, instance, **kwargs):
    """Invalida site-config cuando se edita/elimina enlace navbar."""
    cache.delete(SITE_CONFIG_CACHE_KEY)
