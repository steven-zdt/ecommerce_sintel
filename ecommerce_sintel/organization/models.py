"""
Modelos de organization -- Fase 4 (Definicion del Dominio).

9 agregados definidos por el plan de migracion, con decisiones confirmadas 2026-07-12:
- Empresa y Branding: SEPARADOS (no fusionados en un solo modelo).
- Correos: solo datos de negocio en BD (default_from_email, frontend_base_url,
  admin_login_url). El password SMTP sigue en .env -- es una credencial operativa,
  no un dato de negocio editable, y moverla a BD expuesta via panel admin
  empeoraria la postura de seguridad.
- Integraciones (tokens Meta/YouTube/TikTok/X/Google Business): misma logica que
  Correos -- se quedan en .env. No tienen modelo propio aqui; OrganizationService
  (Fase 5) los expondra como fachada de solo lectura sobre settings, sin tabla.
- Dominios y SEO: sin precedente en el codigo, incluidos con campos razonables
  que se pueden ajustar despues sin bloquear el resto de la migracion.

Todos los singletons siguen el mismo patron que ya usa `core`: `save()` desactiva
cualquier otro registro activo cuando `is_active=True`. Sin signals en esta app
-- la invalidacion de cache (si aplica) se hace explicita en OrganizationCommands
(Fase 5), no via post_save/post_delete.
"""
from django.db import models

from ecommerce.base_models import SintelBaseModel


class SingletonMixin(models.Model):
    """Desactiva cualquier otro registro activo al guardar uno nuevo como activo."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.is_active:
            type(self).objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class Company(SingletonMixin, SintelBaseModel):
    """Agregado 'Empresa'."""
    trade_name = models.CharField(max_length=150, default='Sintel')
    description = models.TextField(blank=True, default='')
    founded_year = models.PositiveSmallIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresa'

    def __str__(self):
        return self.trade_name


class Branding(SingletonMixin, SintelBaseModel):
    """Agregado 'Branding'."""
    logo = models.ImageField(upload_to='organization/branding/', null=True, blank=True)
    favicon = models.ImageField(upload_to='organization/branding/', null=True, blank=True)
    tagline = models.CharField(max_length=300, blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Branding'
        verbose_name_plural = 'Branding'

    def __str__(self):
        return self.tagline or f'Branding #{self.pk}'


class ContactInfo(SingletonMixin, SintelBaseModel):
    """Agregado 'Contacto' -- reemplaza a core.CompanyContactInfo (Fase 6/7)."""
    phone = models.CharField(max_length=100, blank=True, default='')
    email = models.CharField(max_length=254, blank=True, default='')
    address = models.CharField(max_length=500, blank=True, default='')
    working_hours = models.CharField(max_length=255, blank=True, default='')
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = 'Informacion de contacto'
        verbose_name_plural = 'Informacion de contacto'
        ordering = ['-is_active', '-created_at']

    def __str__(self):
        return self.email or f'Contacto #{self.pk}'


class SocialLink(SintelBaseModel):
    """Agregado 'Redes Sociales' -- reemplaza a core.FooterLink(category='social') (Fase 6/7)."""
    platform = models.CharField(max_length=100)
    url = models.CharField(max_length=500)
    icon_class = models.CharField(max_length=100, blank=True, default='')
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = 'Red social'
        verbose_name_plural = 'Redes sociales'
        ordering = ['display_order']

    def __str__(self):
        return self.platform


class EmailSettings(SingletonMixin, SintelBaseModel):
    """
    Agregado 'Correos' -- SOLO datos de negocio. El password SMTP y demas
    credenciales de envio siguen viviendo en settings/.env (ver docstring del
    modulo).
    """
    default_from_email = models.CharField(max_length=254, blank=True, default='')
    frontend_base_url = models.CharField(max_length=300, blank=True, default='')
    admin_login_url = models.CharField(
        max_length=300, blank=True, default='',
        help_text='Reemplaza el setting fantasma FRONTEND_ADMIN_LOGIN_URL '
                   '(nunca definido en .env, ver auditoria Fase 1).'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Configuracion de correo'
        verbose_name_plural = 'Configuracion de correo'

    def __str__(self):
        return self.default_from_email or f'EmailSettings #{self.pk}'


class DomainSettings(SingletonMixin, SintelBaseModel):
    """Agregado 'Dominios'. Sin precedente previo -- campos iniciales, ajustables."""
    primary_domain = models.CharField(max_length=255, blank=True, default='')
    admin_panel_domain = models.CharField(max_length=255, blank=True, default='')
    api_domain = models.CharField(max_length=255, blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Configuracion de dominios'
        verbose_name_plural = 'Configuracion de dominios'

    def __str__(self):
        return self.primary_domain or f'DomainSettings #{self.pk}'


class SeoSettings(SingletonMixin, SintelBaseModel):
    """Agregado 'SEO'. Sin precedente previo -- campos iniciales, ajustables."""
    meta_title = models.CharField(max_length=255, blank=True, default='')
    meta_description = models.CharField(max_length=500, blank=True, default='')
    og_image = models.ImageField(upload_to='organization/seo/', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Configuracion SEO'
        verbose_name_plural = 'Configuracion SEO'

    def __str__(self):
        return self.meta_title or f'SeoSettings #{self.pk}'


class LegalEntityInfo(SingletonMixin, SintelBaseModel):
    """Agregado 'Informacion Legal'. Dato nuevo -- no existia en ningun lugar del backend."""
    legal_name = models.CharField(max_length=255, blank=True, default='')
    tax_id = models.CharField(max_length=50, blank=True, default='')
    fiscal_address = models.CharField(max_length=500, blank=True, default='')
    legal_representative = models.CharField(max_length=255, blank=True, default='')
    city = models.CharField(max_length=150, blank=True, default='')
    department = models.CharField(max_length=150, blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Informacion legal'
        verbose_name_plural = 'Informacion legal'

    def __str__(self):
        return self.legal_name or f'LegalEntityInfo #{self.pk}'
