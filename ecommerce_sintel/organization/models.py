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
from django.conf import settings
from django.db import models
from django.db.models import Q

from ecommerce.base_models import SintelBaseModel
from shared.models import SingletonMixin  # noqa: F401 -- reexportado, ver nota abajo

# Fase 10 (AUDITORIA/25_AUDITORIA_ORGANIZATION.md, 2026-08-01): SingletonMixin.save() antes
# desactivaba las demas filas y luego guardaba la propia SIN ningun lock -- dos requests
# concurrentes (dos pestanas del panel admin) podian cada una ver "sin fila activa" y crear su
# propia fila activa, dejando 2 filas activas simultaneas (get_*() sin ORDER BY explicito
# entonces devuelve una al azar). Este constraint parcial convierte esa condicion de carrera de
# corrupcion silenciosa en un IntegrityError -- Postgres serializa los INSERT/UPDATE concurrentes
# que compitan por la misma condicion.
ACTIVE_SINGLETON_CONDITION = Q(is_active=True, is_deleted=False)

# [Consolidado 2026-08-05, Sprint 2 auditoria transversal] `SingletonMixin` se definia aqui
# originalmente; ahora vive en `shared.models` (reexportado arriba sin cambio de comportamiento)
# porque Core y Payment reimplementaban el mismo `save()` de 3 lineas en vez de importarlo desde
# esta app -- y no podian importarlo desde aqui porque esta misma app prohibe que otras apps
# lean sus modelos (regla SSoT de arriba). `shared` es neutral: no es dato institucional de
# `organization`, es un mixin de comportamiento generico. Los 7 modelos de abajo (Company,
# Branding, etc.) no cambian: siguen heredando `SingletonMixin` igual que antes.


class Company(SingletonMixin, SintelBaseModel):
    """Agregado 'Empresa'."""
    trade_name = models.CharField(max_length=150, default='')
    description = models.TextField(blank=True, default='')
    founded_year = models.PositiveSmallIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresa'
        constraints = [
            models.UniqueConstraint(fields=['is_active'], condition=ACTIVE_SINGLETON_CONDITION, name='unique_active_company'),
        ]

    def __str__(self):
        return self.trade_name


class Branding(SingletonMixin, SintelBaseModel):
    """Agregado 'Branding'."""
    logo = models.ImageField(upload_to='organization/branding/', null=True, blank=True)
    favicon = models.ImageField(upload_to='organization/branding/', null=True, blank=True)
    tagline = models.CharField(max_length=300, blank=True, default='')
    # White-label F4 (2026-08-14): tokens de tema minimos, mapeados 1:1 a
    # --landing-primary/--landing-accent en frontend/src/apps/admin/
    # landing-design-system.css. Vacio ('') = "no hay override, usa el
    # default estatico del CSS" -- mismo criterio fail-open que el resto de
    # esta app (no default de negocio horneado). Formato libre (hex/rgb/etc.)
    # validado en el frontend antes de aplicarse via CSS custom property, no
    # aqui -- ver AUDITORIA/WHITE_LABEL/WHITE_LABEL_ARCHITECTURE_TARGET.md
    # Fase 28. No se derivan variantes strong/soft (requeriria color math) --
    # gap conocido, aceptado por ahora.
    primary_color = models.CharField(max_length=20, blank=True, default='')
    accent_color = models.CharField(max_length=20, blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Branding'
        verbose_name_plural = 'Branding'
        constraints = [
            models.UniqueConstraint(fields=['is_active'], condition=ACTIVE_SINGLETON_CONDITION, name='unique_active_branding'),
        ]

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
        constraints = [
            models.UniqueConstraint(fields=['is_active'], condition=ACTIVE_SINGLETON_CONDITION, name='unique_active_contactinfo'),
        ]

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
        constraints = [
            models.UniqueConstraint(fields=['is_active'], condition=ACTIVE_SINGLETON_CONDITION, name='unique_active_emailsettings'),
        ]

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
        constraints = [
            models.UniqueConstraint(fields=['is_active'], condition=ACTIVE_SINGLETON_CONDITION, name='unique_active_domainsettings'),
        ]

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
        constraints = [
            models.UniqueConstraint(fields=['is_active'], condition=ACTIVE_SINGLETON_CONDITION, name='unique_active_seosettings'),
        ]

    def __str__(self):
        return self.meta_title or f'SeoSettings #{self.pk}'


class CommunicationEvent(SintelBaseModel):
    """
    Agregado 'Centro de Comunicacion' (2026-07-31) -- log append-only de
    interacciones con el widget flotante de contacto (WhatsApp/IA/llamada/
    mensaje). NO es un singleton: cada interaccion real es una fila nueva.

    A diferencia del resto de esta app (todo lectura solo para admin), este
    modelo se escribe desde un endpoint PUBLICO (visitantes anonimos tambien
    disparan estos eventos) -- ver organization/api/views.py::CommunicationEventViewSet.
    """
    EVENT_PANEL_OPEN = 'panel_open'
    EVENT_CHANNEL_CLICK = 'channel_click'
    EVENT_CHOICES = [
        (EVENT_PANEL_OPEN, 'Apertura del panel'),
        (EVENT_CHANNEL_CLICK, 'Clic en canal'),
    ]

    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES, db_index=True)
    # 'whatsapp' | 'ai_assistant' | 'call' | 'message' -- vacio para panel_open.
    channel = models.CharField(max_length=30, blank=True, default='')
    # 'home' | 'shop' | 'renting' | 'services' | 'quotes' | 'general' -- modulo de origen.
    module = models.CharField(max_length=50, blank=True, default='')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='communication_events',
    )
    # page_path, context_label (nombre de producto/servicio si aplica), etc.
    # JSONField en vez de columnas nuevas por cada dato contextual -- este
    # payload crece con el tiempo (mas modulos/canales) sin requerir migracion.
    metadata = models.JSONField(blank=True, default=dict)

    class Meta:
        verbose_name = 'Evento de comunicacion'
        verbose_name_plural = 'Eventos de comunicacion'
        indexes = [models.Index(fields=['event_type', 'created_at'])]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.event_type}:{self.channel or "-"} ({self.module or "-"})'


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
        constraints = [
            models.UniqueConstraint(fields=['is_active'], condition=ACTIVE_SINGLETON_CONDITION, name='unique_active_legalentityinfo'),
        ]

    def __str__(self):
        return self.legal_name or f'LegalEntityInfo #{self.pk}'


class LegalDocument(SintelBaseModel):
    """Contenido de Terminos/Privacidad/Garantia/Devoluciones/Autorizacion.

    White-label F5 (2026-08-14, ver AUDITORIA/WHITE_LABEL/WHITE_LABEL_BUSINESS_RULE_CATALOG.md
    seccion 6): antes este contenido vivia 100% hardcodeado en
    frontend/src/components/auth/kyc/legalDocs.js, sin modelo de datos, sin poder editarse
    sin un deploy de codigo. `sections` preserva exactamente la misma forma que ya consume
    LegalTextModal.vue (`[{heading, paragraphs: [...], list: [...]}]`) para no tener que
    tocar la logica de render del modal -- solo cambia de donde vienen los datos.

    No es uno de los 9 agregados originales del plan de migracion (ver cabecera del
    archivo) -- se agrega aqui porque "informacion legal" ya es responsabilidad declarada
    de esta app y `LegalEntityInfo` ya modela los datos de la entidad legal; este modelo
    modela el CONTENIDO de los documentos, que es distinto pero relacionado.

    El seed inicial (migracion de datos) copia el texto EXACTO que ya estaba en
    legalDocs.js, incluyendo el placeholder `[PENDIENTE: razon social exacta...]` sin
    resolver -- no se inventa ningun dato legal nuevo, solo se mueve el mismo contenido a
    BD para que sea editable desde el panel sin requerir un deploy."""
    DOC_TERMINOS = 'terminos'
    DOC_PRIVACIDAD = 'politica'
    DOC_GARANTIA = 'garantia'
    DOC_DEVOLUCIONES = 'devoluciones'
    DOC_AUTORIZACION = 'autorizacion'
    DOC_TYPE_CHOICES = [
        (DOC_TERMINOS, 'Terminos y Condiciones'),
        (DOC_PRIVACIDAD, 'Politica de Privacidad y Tratamiento de Datos'),
        (DOC_GARANTIA, 'Politica de Garantia'),
        (DOC_DEVOLUCIONES, 'Politica de Devoluciones y Derecho de Retracto'),
        (DOC_AUTORIZACION, 'Autorizacion de Tratamiento de Datos'),
    ]

    doc_type = models.CharField(max_length=30, unique=True, choices=DOC_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    # Texto libre tal como lo mostraba el JS original (ej. '10 de julio de 2026'), no un
    # DateField -- el documento puede publicarse sin fecha exacta conocida.
    updated_label = models.CharField(max_length=100, blank=True, default='')
    sections = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Documento legal'
        verbose_name_plural = 'Documentos legales'

    def __str__(self):
        return self.title
