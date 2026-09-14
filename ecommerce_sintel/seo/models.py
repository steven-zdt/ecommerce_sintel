from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from ecommerce.base_models import SintelBaseModel


class SiteMetaTag(SintelBaseModel):
    """
    Metaetiqueta administrable del <head> del sitio publico (verificacion de
    dominio, analytics, pixels, SEO...). Renderizada server-side por
    seo.templatetags.seo_tags.render_meta_tags en templates/spa_shell.html --
    unico punto donde se construye el <head> real (ver ecommerce/urls.py).
    """
    PROVIDER_META = 'meta'
    PROVIDER_FACEBOOK = 'facebook'
    PROVIDER_INSTAGRAM = 'instagram'
    PROVIDER_GOOGLE_SEARCH_CONSOLE = 'google_search_console'
    PROVIDER_GOOGLE_TAG_MANAGER = 'google_tag_manager'
    PROVIDER_GOOGLE_ANALYTICS = 'google_analytics'
    PROVIDER_BING = 'bing'
    PROVIDER_PINTEREST = 'pinterest'
    PROVIDER_TIKTOK = 'tiktok'
    PROVIDER_LINKEDIN = 'linkedin'
    PROVIDER_APPLE = 'apple'
    PROVIDER_CLOUDFLARE = 'cloudflare'
    PROVIDER_CUSTOM = 'custom'
    PROVIDER_CHOICES = [
        (PROVIDER_META, 'Meta Business Suite'),
        (PROVIDER_FACEBOOK, 'Facebook'),
        (PROVIDER_INSTAGRAM, 'Instagram'),
        (PROVIDER_GOOGLE_SEARCH_CONSOLE, 'Google Search Console'),
        (PROVIDER_GOOGLE_TAG_MANAGER, 'Google Tag Manager'),
        (PROVIDER_GOOGLE_ANALYTICS, 'Google Analytics'),
        (PROVIDER_BING, 'Microsoft Bing'),
        (PROVIDER_PINTEREST, 'Pinterest'),
        (PROVIDER_TIKTOK, 'TikTok'),
        (PROVIDER_LINKEDIN, 'LinkedIn'),
        (PROVIDER_APPLE, 'Apple'),
        (PROVIDER_CLOUDFLARE, 'Cloudflare'),
        (PROVIDER_CUSTOM, 'Personalizado'),
    ]

    TYPE_DOMAIN_VERIFICATION = 'domain_verification'
    TYPE_ANALYTICS = 'analytics'
    TYPE_PIXEL = 'pixel'
    TYPE_SEO = 'seo'
    TYPE_SOCIAL = 'social'
    TYPE_CUSTOM = 'custom'
    TYPE_CHOICES = [
        (TYPE_DOMAIN_VERIFICATION, 'Verificacion de dominio'),
        (TYPE_ANALYTICS, 'Analytics'),
        (TYPE_PIXEL, 'Pixel de conversion'),
        (TYPE_SEO, 'SEO'),
        (TYPE_SOCIAL, 'Redes sociales'),
        (TYPE_CUSTOM, 'Personalizado'),
    ]

    ENV_ALL = 'all'
    ENV_DEVELOPMENT = 'development'
    ENV_TESTING = 'testing'
    ENV_STAGING = 'staging'
    ENV_PRODUCTION = 'production'
    ENV_CHOICES = [
        (ENV_ALL, 'Todos los entornos'),
        (ENV_DEVELOPMENT, 'Development'),
        (ENV_TESTING, 'Testing'),
        (ENV_STAGING, 'Staging'),
        (ENV_PRODUCTION, 'Production'),
    ]

    name = models.CharField(max_length=255)
    provider = models.CharField(max_length=30, choices=PROVIDER_CHOICES, db_index=True)
    tag_type = models.CharField(max_length=30, choices=TYPE_CHOICES, db_index=True)
    description = models.TextField(blank=True, default='')

    meta_name = models.CharField(max_length=255, blank=True, default='')
    meta_content = models.CharField(max_length=500, blank=True, default='')
    html_snippet = models.TextField(
        blank=True, default='',
        help_text='HTML crudo alternativo (solo etiquetas <meta>, sanitizado al guardar).',
    )

    priority = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    target_page = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Prefijo de ruta donde se renderiza (ej. /tienda). Vacio = todas las paginas.',
    )
    environment = models.CharField(max_length=20, choices=ENV_CHOICES, default=ENV_ALL, db_index=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        verbose_name = 'metaetiqueta del sitio'
        verbose_name_plural = 'metaetiquetas del sitio'
        ordering = ['priority', 'created_at']
        indexes = [
            models.Index(fields=['is_active', 'environment', 'priority']),
        ]

    def __str__(self):
        return f'{self.name} ({self.provider})'

    def clean(self):
        errors = {}
        has_meta_pair = bool(self.meta_name) and bool(self.meta_content)
        has_snippet = bool(self.html_snippet.strip())
        if not has_meta_pair and not has_snippet:
            errors['meta_name'] = (
                'Se requiere meta_name + meta_content, o un html_snippet valido.'
            )
        if bool(self.meta_name) != bool(self.meta_content):
            errors['meta_content'] = 'meta_name y meta_content deben completarse juntos.'
        if errors:
            raise ValidationError(errors)

    def to_html(self) -> str:
        """
        Construye el HTML final. Si hay html_snippet (ya sanitizado en
        validate() del serializer / clean() del modelo) se usa tal cual;
        si no, se arma desde meta_name/meta_content con auto-escape.
        """
        from django.utils.html import format_html

        if self.html_snippet.strip():
            return self.html_snippet.strip()
        return str(format_html('<meta name="{}" content="{}">', self.meta_name, self.meta_content))


FILENAME_VALIDATOR = RegexValidator(
    regex=r'^[A-Za-z0-9._-]+\.html$',
    message='El nombre de archivo debe terminar en .html y usar solo letras, numeros, puntos, guiones y guion bajo.',
)


class SiteVerificationFile(SintelBaseModel):
    """
    Archivo estatico de verificacion servido en la RAIZ del dominio
    (https://sintel.net.co/<filename>.html) -- metodo alternativo al de
    metaetiqueta (<meta> en el <head>) que algunos proveedores (Meta
    Business Suite, Google Search Console...) tambien ofrecen ("Subir
    archivo HTML"). Servido por seo.views.serve_verification_file, mapeado
    en ecommerce/urls.py ANTES del catch-all de la SPA -- de lo contrario
    ese catch-all interceptaria la request y devolveria spa_shell.html en
    vez del archivo real.
    """
    name = models.CharField(max_length=255)
    provider = models.CharField(max_length=30, choices=SiteMetaTag.PROVIDER_CHOICES, db_index=True)
    filename = models.CharField(max_length=255, unique=True, validators=[FILENAME_VALIDATOR])
    content = models.TextField(help_text='Contenido exacto que debe devolver el archivo.')
    is_active = models.BooleanField(default=True, db_index=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        verbose_name = 'archivo de verificacion del sitio'
        verbose_name_plural = 'archivos de verificacion del sitio'
        ordering = ['filename']

    def __str__(self):
        return self.filename


class SeoMetaTagAuditLog(SintelBaseModel):
    """
    Registro append-only de acciones administrativas sobre SiteMetaTag.
    Poblado exclusivamente desde seo.services.commands.MetaTagCommands
    (nunca via signals ni SiteMetaTag.objects.create() directo), mismo patron
    que users.models.UserAuditLog.
    """
    ACTION_CREATED = 'created'
    ACTION_UPDATED = 'updated'
    ACTION_ACTIVATED = 'activated'
    ACTION_DEACTIVATED = 'deactivated'
    ACTION_DUPLICATED = 'duplicated'
    ACTION_DELETED = 'deleted'
    ACTION_REORDERED = 'reordered'
    ACTION_IMPORTED = 'imported'
    ACTION_EXPORTED = 'exported'
    ACTION_CHOICES = [
        (ACTION_CREATED, 'Creada'),
        (ACTION_UPDATED, 'Actualizada'),
        (ACTION_ACTIVATED, 'Activada'),
        (ACTION_DEACTIVATED, 'Desactivada'),
        (ACTION_DUPLICATED, 'Duplicada'),
        (ACTION_DELETED, 'Eliminada'),
        (ACTION_REORDERED, 'Reordenada'),
        (ACTION_IMPORTED, 'Importada'),
        (ACTION_EXPORTED, 'Exportada'),
    ]

    # SET_NULL + snapshot de nombre: el log sobrevive aunque el tag se borre
    # fisicamente o el usuario se elimine (mismo criterio que UserAuditLog).
    meta_tag = models.ForeignKey(
        SiteMetaTag, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='audit_entries',
    )
    meta_tag_name = models.CharField(max_length=255, blank=True, default='')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    changes = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'auditoria de metaetiqueta'
        verbose_name_plural = 'auditorias de metaetiquetas'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['meta_tag', '-created_at'])]

    def __str__(self):
        return f'{self.action} | {self.meta_tag_name} | {self.created_at}'
