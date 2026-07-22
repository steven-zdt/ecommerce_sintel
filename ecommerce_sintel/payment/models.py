from django.db import models
from django.conf import settings
from ecommerce.base_models import SintelBaseModel
from orders.models import Order


# ── Wompi ─────────────────────────────────────────────────────────────────────

class Transaction(SintelBaseModel):
    """Transacciones procesadas a traves de la pasarela Wompi Colombia.
    Puede vincularse a una Order de tienda/servicio O a una RentalRequest.
    Solo uno de los dos campos FK debe estar establecido."""
    STATUS_CHOICES = [
        ('PENDING',  'Pendiente'),
        ('APPROVED', 'Aprobada'),
        ('DECLINED', 'Declinada'),
        ('VOIDED',   'Anulada'),
        ('ERROR',    'Error en pasarela'),
    ]

    order               = models.ForeignKey(Order, null=True, blank=True, on_delete=models.CASCADE, related_name='transactions')
    rental_request       = models.ForeignKey('renting.RentalRequest', null=True, blank=True, on_delete=models.CASCADE, related_name='wompi_transactions')
    wompi_id            = models.CharField(max_length=255, unique=True, null=True, blank=True)
    amount_in_cents     = models.BigIntegerField()
    currency            = models.CharField(max_length=3, default='COP')
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    payment_method_type = models.CharField(max_length=50, null=True, blank=True)
    redirect_url        = models.URLField(max_length=500, null=True, blank=True)
    integrity_signature = models.CharField(max_length=255, null=True, blank=True)
    # ADR-001 Fase 4 (observabilidad): mintado una vez en initialize/, propagado
    # en logs y en TransactionEvent durante todo el ciclo de vida de esta
    # transaccion (creacion, sync por polling, webhook) -- permite seguir un
    # intento de pago completo con un solo grep, sin depender de reconstruir
    # el hilo a mano por reference/wompi_id como hoy.
    correlation_id      = models.CharField(max_length=36, null=True, blank=True, db_index=True)

    class Meta:
        verbose_name        = 'Transaccion Wompi'
        verbose_name_plural = 'Transacciones Wompi'
        ordering            = ['-created_at']
        constraints         = [
            models.CheckConstraint(
                check=(
                    models.Q(order__isnull=False, rental_request__isnull=True) |
                    models.Q(order__isnull=True, rental_request__isnull=False)
                ),
                name='payment_transaction_exactly_one_target',
            ),
        ]

    def __str__(self):
        return f"Wompi {self.wompi_id} | {self.status}"


class TransactionEvent(SintelBaseModel):
    """
    Historial append-only de eventos de una Transaction Wompi (ADR-001 Fase 4).
    Separado de Transaction.status (que sigue siendo el estado ACTUAL, sin
    cambios de comportamiento para nada que ya lo consulte) -- este modelo
    existe solo para auditoria/observabilidad, nunca se edita ni se borra.

    NO incluye un campo de "id de evento de Wompi": se investigo contra
    docs.wompi.co (Fase 2 de este mismo proyecto) y el payload de webhook de
    Wompi no documenta un identificador de evento unico separado del id de
    transaccion -- inventar ese campo habria sido asumir algo no confirmado.
    """
    SOURCE_WEBHOOK    = 'WEBHOOK'
    SOURCE_API_SYNC   = 'API_SYNC'
    SOURCE_API_CREATE = 'API_CREATE'
    SOURCE_CHOICES = [
        (SOURCE_WEBHOOK,    'Webhook de Wompi'),
        (SOURCE_API_SYNC,   'Sincronizacion via API (polling)'),
        (SOURCE_API_CREATE, 'Creacion sincrona via API'),
    ]

    transaction     = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='events')
    source          = models.CharField(max_length=20, choices=SOURCE_CHOICES, db_index=True)
    previous_status = models.CharField(max_length=20, blank=True, default='')
    new_status      = models.CharField(max_length=20, blank=True, default='')
    correlation_id  = models.CharField(max_length=36, null=True, blank=True, db_index=True)
    raw_payload     = models.JSONField(null=True, blank=True)
    processed       = models.BooleanField(default=True)
    error_detail    = models.TextField(blank=True, default='')

    class Meta:
        verbose_name        = 'evento de transaccion Wompi'
        verbose_name_plural = 'eventos de transaccion Wompi'
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at', 'source']),
        ]

    def __str__(self):
        return f"TransactionEvent({self.source}, {self.previous_status}->{self.new_status})"


class PaymentFeatureFlags(SintelBaseModel):
    """
    Flags operativos del flujo de pagos Wompi (ADR-001 Fase 5: migracion
    gradual) -- editables desde /admin/ de Django, sin necesidad de desplegar
    codigo nuevo. Singleton: guardar un registro con is_active=True desactiva
    cualquier otro (mismo patron ya usado en organization/core -- se duplica
    aqui en vez de importarlo entre apps, siguiendo la convencion existente
    del proyecto de no crear dependencias cruzadas para un mixin de 3 lineas).
    """
    card_api_flow_enabled = models.BooleanField(
        default=True,
        help_text=(
            'Si esta activo, el checkout ofrece "Tarjeta" (flujo backend '
            'directo via WompiApiClient, sin abrir el Widget) ademas de '
            '"PSE / Otros". Si se desactiva, el checkout solo ofrece '
            '"PSE / Otros" (Widget completo de Wompi, que ya incluye tarjeta) '
            '-- reversion instantanea sin deploy si el flujo nuevo da '
            'problemas en produccion.'
        ),
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'flags de pagos'
        verbose_name_plural = 'flags de pagos'

    def save(self, *args, **kwargs):
        if self.is_active:
            PaymentFeatureFlags.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"PaymentFeatureFlags(card_api_flow_enabled={self.card_api_flow_enabled})"

    @classmethod
    def get_active(cls) -> "PaymentFeatureFlags":
        flags = cls.objects.filter(is_active=True).first()
        if flags is None:
            flags = cls.objects.create()
        return flags

    @classmethod
    def set_card_api_flow_enabled(cls, enabled: bool) -> "PaymentFeatureFlags":
        """ADR-001 Fase 7: toggle expuesto desde el panel admin Vue, ademas
        del ya existente en /admin/ de Django (Fase 5)."""
        flags = cls.get_active()
        flags.card_api_flow_enabled = enabled
        flags.save(update_fields=["card_api_flow_enabled", "updated_at"])
        return flags


# ── COD (Pago contra entrega) ─────────────────────────────────────────────────

class CodTransaction(SintelBaseModel):
    """Registro de ciclo de vida de una orden con pago contra entrega."""
    STATUS_CONFIRMED  = 'CONFIRMED'
    STATUS_DELIVERED  = 'DELIVERED'
    STATUS_CANCELLED  = 'CANCELLED'
    STATUS_CHOICES    = [
        (STATUS_CONFIRMED, 'Confirmado'),
        (STATUS_DELIVERED, 'Entregado'),
        (STATUS_CANCELLED, 'Cancelado'),
    ]

    order        = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='cod_transaction')
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CONFIRMED, db_index=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    notes        = models.TextField(blank=True, default='')

    class Meta:
        verbose_name        = 'Transaccion COD'
        verbose_name_plural = 'Transacciones COD'
        ordering            = ['-created_at']

    def __str__(self):
        return f"COD Order {self.order.uuid} | {self.status}"


# ── Nequi Push ────────────────────────────────────────────────────────────────

class NequiTransaction(SintelBaseModel):
    """Transacciones iniciadas mediante Nequi Push Notification.
    Puede vincularse a una Order de tienda/servicio O a una RentalRequest.
    Solo uno de los dos campos FK debe estar establecido."""
    STATUS_PENDING  = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_ERROR    = 'ERROR'
    STATUS_CHOICES  = [
        (STATUS_PENDING,  'Pendiente'),
        (STATUS_APPROVED, 'Aprobado'),
        (STATUS_REJECTED, 'Rechazado'),
        (STATUS_ERROR,    'Error'),
    ]

    order          = models.ForeignKey(Order, null=True, blank=True, on_delete=models.CASCADE, related_name='nequi_transactions')
    rental_request = models.ForeignKey('renting.RentalRequest', null=True, blank=True, on_delete=models.CASCADE, related_name='nequi_transactions')
    phone_number   = models.CharField(max_length=20)
    message_id     = models.CharField(max_length=255, unique=True, null=True, blank=True)
    amount         = models.DecimalField(max_digits=12, decimal_places=2)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)

    class Meta:
        verbose_name        = 'Transaccion Nequi'
        verbose_name_plural = 'Transacciones Nequi'
        ordering            = ['-created_at']
        constraints         = [
            models.CheckConstraint(
                check=(
                    models.Q(order__isnull=False, rental_request__isnull=True) |
                    models.Q(order__isnull=True, rental_request__isnull=False)
                ),
                name='payment_nequitransaction_exactly_one_target',
            ),
        ]

    def __str__(self):
        ref = self.order.uuid if self.order_id else (self.rental_request.uuid if self.rental_request_id else 'N/A')
        return f"Nequi {self.phone_number} | {self.status} | {ref}"


# ── Tarjetas tokenizadas (Wompi Card Tokenization) ────────────────────────────

class TokenizedCard(SintelBaseModel):
    """Tarjeta de credito/debito tokenizada via Wompi para cobros recurrentes."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tokenized_cards',
    )
    token_id = models.CharField(max_length=255, unique=True)
    masked_number = models.CharField(max_length=20)
    brand = models.CharField(max_length=30)
    exp_month = models.CharField(max_length=2)
    exp_year = models.CharField(max_length=4)
    cardholder_name = models.CharField(max_length=255, blank=True, default='')
    is_default = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name = 'tarjeta tokenizada'
        verbose_name_plural = 'tarjetas tokenizadas'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(is_default=True, is_deleted=False),
                name='payment_tokenizedcard_one_default_per_user',
            ),
        ]

    def __str__(self):
        return f"{self.brand} *{self.masked_number[-4:]} ({self.user.email})"
