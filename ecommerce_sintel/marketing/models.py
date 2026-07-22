from django.db import models
from django.conf import settings
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

    def __str__(self):
        return f"{self.title} ({', '.join(self.channels)})"

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
