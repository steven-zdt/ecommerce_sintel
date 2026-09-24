from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from ecommerce.base_models import SintelBaseModel
from shop.models import ProductVariant
from technical_services.models import ServiceVariant
from renting.models import EquipmentVariant

class FlashOffer(SintelBaseModel):
    """
    Ofertas relámpago con tiempo limitado.
    """
    name = models.CharField(max_length=255)
    description = models.TextField()
    
    # Can target a product, service, or rental equipment
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    service_variant = models.ForeignKey(ServiceVariant, on_delete=models.CASCADE, null=True, blank=True)
    equipment_variant = models.ForeignKey(EquipmentVariant, on_delete=models.CASCADE, null=True, blank=True)

    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        # A diferencia de payment/cart (donde el target es obligatorio), aqui una FlashOffer
        # SIN ningun target es un caso valido -- oferta general de la vitrina, no ligada a un
        # item especifico (confirmado por datos reales en produccion). La constraint solo
        # prohibe apuntar a mas de un tipo de item a la vez (ambiguo).
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(service_variant__isnull=True, equipment_variant__isnull=True) |
                    models.Q(variant__isnull=True, equipment_variant__isnull=True) |
                    models.Q(variant__isnull=True, service_variant__isnull=True)
                ),
                name='marketing_flashoffer_at_most_one_target',
            ),
        ]

    def __str__(self):
        return self.name

class PersonalOffer(SintelBaseModel):
    """
    Ofertas personalizadas para usuarios específicos basadas en su historial.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='personal_offers')
    name = models.CharField(max_length=255)
    
    # Target specific items
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    service_variant = models.ForeignKey(ServiceVariant, on_delete=models.CASCADE, null=True, blank=True)
    equipment_variant = models.ForeignKey(EquipmentVariant, on_delete=models.CASCADE, null=True, blank=True)
    
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.CharField(max_length=255, help_text="Ej: Cliente recurrente, Interés en tecnología")
    
    expires_at = models.DateTimeField()
    is_redeemed = models.BooleanField(default=False)

    def __str__(self):
        return f"Offer for {self.user.email}: {self.name}"

class MarketingCampaign(SintelBaseModel):
    """
    Campañas publicitarias multicanal.
    """
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('youtube', 'YouTube'),
        ('tiktok', 'TikTok'),
        ('x', 'X (Twitter)'),
        ('google_business', 'Google Business Profile'),
    ]

    title = models.CharField(max_length=255)
    content = models.TextField()
    channels = models.JSONField(
        default=list,
        help_text="List of active channels: email, whatsapp, facebook, instagram, youtube"
    )
    scheduled_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    target_audience = models.JSONField(default=dict, help_text="Filters for users (e.g. 'spent_more_than': 1000)")
    is_completed = models.BooleanField(default=False)

    # PLAN_SINTEL_MARKETING_CAMPANAS_CRUD_CATALOG_MEDIA_CANALES_LOOP.md, Fase 9 ("Campana
    # desde cero", seccion 12) + Fase 10 ("Contenido estructurado", seccion 13, 2026-09-23).
    # Mapeo de contrato conceptual del plan a campos reales, sin duplicar:
    #   headline      -> title (ya existia, Fase 10 no agrega otro campo)
    #   subheadline   -> subheadline (nuevo)
    #   body          -> content (ya existia, es el "Mensaje principal" de Fase 9)
    #   benefit_text  -> NO agregado -- CampaignBenefit (Fase 8) ya cubre esto de forma
    #                    estructurada (benefit_type + label), un texto libre duplicado seria
    #                    la misma info dos veces sin fuente de verdad clara.
    #   cta_label/cta_url -> nuevos (Fase 9 "CTA", Fase 10)
    #   terms         -> nuevo (Fase 9 "Condiciones")
    # "Descripcion" (Fase 9) es un campo propio, mas corto que `content` -- resumen breve para
    # listados/previews, no el mensaje persuasivo completo.
    # "Vigencia" (Fase 9) -> valid_from/valid_until, DISTINTO de scheduled_at/sent_at (esos son
    # de ENVIO -- cuando se despacha la campana -- , vigencia es cuando la OFERTA es valida,
    # ej. una campana puede enviarse hoy pero la oferta ser valida todo el mes).
    # "Audiencia" (Fase 9) -> target_audience YA EXISTIA (JSONField, arriba) pero nunca se
    # expuso en el serializer -- corregido en esta fase, no se duplica con un campo nuevo.
    description = models.CharField(max_length=500, blank=True, default='')
    subheadline = models.CharField(max_length=255, blank=True, default='')
    cta_label = models.CharField(max_length=100, blank=True, default='')
    cta_url = models.URLField(max_length=500, blank=True, default='')
    terms = models.TextField(blank=True, default='')
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} ({', '.join(self.channels)})"


class CampaignItem(SintelBaseModel):
    """
    Item de catalogo referenciado por una MarketingCampaign (Fase 7 del plan de arriba,
    "campanas compuestas" -- ej. "Lleva 02 camaras y te damos transporte e instalacion
    gratis"). Reemplaza el campo singular source_content_type/source_object_uuid que
    Fase 3/4/5/6 habian agregado directo en MarketingCampaign (nunca commiteado, sin datos
    reales que migrar -- confirmado 0 campanas con source seteado en dev antes de este
    cambio) por una relacion 1-a-muchos: una campana puede tener 0 items (Fase 3, "Desde
    cero"), 1 (el caso Fase 4/5/6 original) o varios de tipos mixtos (Fase 7).

    Mismo patron que shared.models.CatalogRelation: content_type + object_uuid, NUNCA
    GenericForeignKey (ver docstring de CatalogRelation para el motivo real).
    "02 camaras" se representa como UN CampaignItem con quantity=2 (misma camara, mismo
    producto) -- no dos items separados -- porque son la misma referencia de catalogo, solo
    la cantidad cambia, igual que OrderItem.quantity en Orders.
    """
    campaign = models.ForeignKey(MarketingCampaign, on_delete=models.CASCADE, related_name='items')
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE,
        related_name='marketing_campaign_items',
        help_text='Tipo de entidad de catalogo referenciada (ej. shop.Product).',
    )
    object_uuid = models.UUIDField(db_index=True, help_text='UUID de la entidad de catalogo referenciada.')
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = 'item de campana'
        verbose_name_plural = 'items de campana'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.content_type.model}:{self.object_uuid} x{self.quantity} -- {self.campaign.title}"


class CampaignBenefit(SintelBaseModel):
    """
    Beneficio adjunto a una MarketingCampaign (Fase 8 del plan de arriba, set minimo real
    pedido: envio/instalacion gratis, descuento % o fijo). Deliberadamente NO se reutilizo
    FlashOffer -- conceptualmente distinto: FlashOffer es un descuento con ventana de tiempo
    aplicado a UN variant especifico (Product/Service/Equipment), mientras que un beneficio de
    campana es texto libre + tipo, adjunto a la campana en si (puede combinarse con cualquier
    fuente, incluida "Desde cero"), sin ventana de tiempo propia (la campana ya tiene
    scheduled_at/sent_at).
    """
    BENEFIT_FREE_SHIPPING = 'FREE_SHIPPING'
    BENEFIT_FREE_INSTALLATION = 'FREE_INSTALLATION'
    BENEFIT_DISCOUNT_PERCENT = 'DISCOUNT_PERCENT'
    BENEFIT_DISCOUNT_FIXED = 'DISCOUNT_FIXED'
    BENEFIT_TYPE_CHOICES = [
        (BENEFIT_FREE_SHIPPING, 'Transporte gratis'),
        (BENEFIT_FREE_INSTALLATION, 'Instalacion gratis'),
        (BENEFIT_DISCOUNT_PERCENT, 'Descuento porcentual'),
        (BENEFIT_DISCOUNT_FIXED, 'Descuento fijo'),
    ]

    campaign = models.ForeignKey(MarketingCampaign, on_delete=models.CASCADE, related_name='benefits')
    benefit_type = models.CharField(max_length=20, choices=BENEFIT_TYPE_CHOICES)
    label = models.CharField(max_length=255, help_text='Texto libre mostrado al cliente, ej. "Transporte gratis".')
    value = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text='Solo para DISCOUNT_PERCENT/DISCOUNT_FIXED -- porcentaje o monto fijo.',
    )

    class Meta:
        verbose_name = 'beneficio de campana'
        verbose_name_plural = 'beneficios de campana'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.get_benefit_type_display()} -- {self.campaign.title}"

class CampaignMedia(SintelBaseModel):
    """
    Imagen o video publicitario adjunto a una MarketingCampaign (Fase 11-14 del plan de
    arriba). Un solo modelo para ambos tipos (a diferencia de shop.ProductImage/ProductVideo,
    que son 2 modelos separados) porque el plan pide explicitamente "CampaignMedia" como una
    sola entidad con un campo `type` -- no se duplica esa decision aqui.

    `file` es un FileField generico (no ImageField) a proposito: Django's ImageField aplica
    su propia validacion Pillow SOLO a imagenes, y este modelo acepta imagen O video en el
    mismo campo -- la validacion real (MIME/extension/tamano/dimensiones) vive en
    services/commands.py::CampaignMediaCommands, explicita y uniforme para ambos tipos, en vez
    de delegar en el comportamiento implicito de un ImageField (que ademas rompe con archivos
    de video).

    `duration` (solo video) queda SIN VALIDAR a proposito -- no existe en el proyecto ninguna
    libreria de metadata de video (ffmpeg-python/moviepy/pymediainfo, confirmado por grep en
    requirements.txt) y el plan no exige agregar una dependencia nueva solo para esto
    ("definir limites reales... no exige libreria especifica"). Ver MARKETING_GAPS.md.

    Subida SINCRONA (sin Celery) -- mismo patron real que TODO el resto del proyecto usa para
    imagen/video (ProductImage/ProductVideo/EquipmentImage/ServiceVideo, confirmado por grep:
    ninguno usa una task async para el upload en si), consistente con "no duplicar arquitectura".
    """
    TYPE_IMAGE = 'IMAGE'
    TYPE_VIDEO = 'VIDEO'
    MEDIA_TYPE_CHOICES = [
        (TYPE_IMAGE, 'Imagen'),
        (TYPE_VIDEO, 'Video'),
    ]

    campaign = models.ForeignKey(MarketingCampaign, on_delete=models.CASCADE, related_name='media')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, db_index=True)
    file = models.FileField(upload_to='marketing/campaigns/')
    mime_type = models.CharField(max_length=100, blank=True, default='')
    size = models.PositiveIntegerField(default=0, help_text='Tamano real en bytes.')
    width = models.PositiveIntegerField(null=True, blank=True, help_text='Solo imagen/video, leido del archivo real.')
    height = models.PositiveIntegerField(null=True, blank=True, help_text='Solo imagen/video, leido del archivo real.')
    duration = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text='Segundos, solo video -- NO validado, ver docstring de este modelo.',
    )
    file_hash = models.CharField(
        max_length=64, blank=True, default='', db_index=True,
        help_text='SHA-256 del contenido real, para deduplicacion.',
    )
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'media de campana'
        verbose_name_plural = 'media de campanas'
        ordering = ['sort_order', 'created_at']

    def __str__(self):
        return f"{self.get_media_type_display()} -- {self.campaign.title}"


class SalesAnalysis(SintelBaseModel):
    """
    Caché de analítica para el Dashboard de Marketing.
    Refleja el estado de la metadata de las apps.
    """
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    total_sales_amount = models.DecimalField(max_digits=12, decimal_places=2)
    top_product = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    top_service = models.ForeignKey(ServiceVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    top_equipment = models.ForeignKey(EquipmentVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Cart to Order conversion")

    # Snapshot of aggregated stats per app (JSON)
    shop_snapshot = models.JSONField(default=dict)
    renting_snapshot = models.JSONField(default=dict)
    services_snapshot = models.JSONField(default=dict)

    def __str__(self):
        return f"Analysis {self.period_start} to {self.period_end}"


class CampaignLog(SintelBaseModel):
    """
    Audit trail for each campaign dispatch attempt per channel.
    Used for idempotency: if is_sent=True, the worker skips re-sending.
    """
    campaign = models.ForeignKey(MarketingCampaign, on_delete=models.CASCADE, related_name='logs')
    channel = models.CharField(max_length=20)
    recipient = models.CharField(max_length=255, help_text="Email, phone number, or page/account ID")
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('campaign', 'channel', 'recipient')
        verbose_name = 'log de campaña'
        verbose_name_plural = 'logs de campaña'

    def __str__(self):
        status = 'OK' if self.is_sent else 'ERROR'
        return f"{status} [{self.channel}] {self.recipient} — {self.campaign.title}"


class AgentRun(SintelBaseModel):
    """
    Audit log for each Marketing Intelligence Agent execution.
    """
    STATUS_CHOICES = [
        ('running', 'Ejecutando'),
        ('completed_no_action', 'Completado — Sin acción'),
        ('completed_dispatched', 'Completado — Campaña despachada'),
        ('failed', 'Fallido'),
    ]

    triggered_by = models.CharField(max_length=20, default='manual')  # 'manual' | 'scheduled'
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='running')
    llm_provider = models.CharField(max_length=30, blank=True, null=True)
    llm_decision = models.JSONField(null=True, blank=True)
    campaign = models.ForeignKey(
        MarketingCampaign, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='agent_runs'
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'ejecución del agente'
        verbose_name_plural = 'ejecuciones del agente'

    def __str__(self):
        return f"[{self.status}] AgentRun {self.uuid} ({self.triggered_by}) @ {self.created_at.strftime('%Y-%m-%d %H:%M')}"
