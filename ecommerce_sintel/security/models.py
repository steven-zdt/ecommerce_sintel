from django.conf import settings
from django.db import models
from ecommerce.base_models import SintelBaseModel


class SecurityEvent(SintelBaseModel):
    """
    Registro append-only de eventos de seguridad transversales. Nunca se edita
    ni se borra una vez creado -- solo se consulta (ver SecuritySelector).
    Poblado unicamente via SecurityCommands.log_event(), nunca con
    SecurityEvent.objects.create() directo desde otras apps.
    """
    LOGIN_SUCCESS  = 'LOGIN_SUCCESS'
    LOGIN_FAILED   = 'LOGIN_FAILED'
    KYC_REJECTED   = 'KYC_REJECTED'
    KYC_BLOCKED    = 'KYC_BLOCKED'
    RATE_LIMIT_HIT = 'RATE_LIMIT_HIT'
    FILE_REJECTED  = 'FILE_REJECTED'
    PAYMENT_WEBHOOK_INVALID_SIGNATURE = 'PAYMENT_WEBHOOK_INVALID_SIGNATURE'
    PAYMENT_APPROVED = 'PAYMENT_APPROVED'
    PAYMENT_DECLINED = 'PAYMENT_DECLINED'
    PAYMENT_CARD_REMOVED = 'PAYMENT_CARD_REMOVED'
    PAYMENT_TRANSACTION_ABANDONED = 'PAYMENT_TRANSACTION_ABANDONED'
    PAYMENT_FEATURE_FLAG_CHANGED = 'PAYMENT_FEATURE_FLAG_CHANGED'
    COUPON_REJECTED = 'COUPON_REJECTED'
    INVENTORY_MANUAL_ADJUSTMENT = 'INVENTORY_MANUAL_ADJUSTMENT'
    OPERATION_FORCE_CANCELLED = 'OPERATION_FORCE_CANCELLED'
    NOTIFICATION_CHANNEL_FAILED = 'NOTIFICATION_CHANNEL_FAILED'
    AI_ACTION_EXECUTED = 'AI_ACTION_EXECUTED'
    # D-02 (auditoria enterprise): de las decenas de acciones administrativas
    # destructivas del BFF admin (dashboard/api/views.py), solo 3 puntos
    # dejaban SecurityEvent -- la mayoria de los destroy()/cambios de estado
    # no dejaban mas rastro que el propio soft-delete. Tipo generico para
    # cualquier borrado admin, en vez de uno especifico por cada recurso.
    ADMIN_RESOURCE_DELETED = 'ADMIN_RESOURCE_DELETED'
    EVENT_CHOICES = [
        (LOGIN_SUCCESS,  'Login exitoso'),
        (LOGIN_FAILED,   'Login fallido'),
        (KYC_REJECTED,   'KYC rechazado'),
        (KYC_BLOCKED,    'KYC bloqueado'),
        (RATE_LIMIT_HIT, 'Limite de tasa alcanzado'),
        (FILE_REJECTED,  'Archivo rechazado'),
        (PAYMENT_WEBHOOK_INVALID_SIGNATURE, 'Webhook de pago con firma invalida'),
        (PAYMENT_APPROVED, 'Pago aprobado'),
        (PAYMENT_DECLINED, 'Pago rechazado'),
        (PAYMENT_CARD_REMOVED, 'Tarjeta guardada eliminada'),
        (PAYMENT_TRANSACTION_ABANDONED, 'Transaccion de pago abandonada (sin wompi_id tras el umbral)'),
        (PAYMENT_FEATURE_FLAG_CHANGED, 'Flag operativo de pagos modificado'),
        (COUPON_REJECTED, 'Cupon invalido rechazado'),
        (INVENTORY_MANUAL_ADJUSTMENT, 'Ajuste manual de inventario'),
        (OPERATION_FORCE_CANCELLED, 'Operacion cancelada forzosamente'),
        (NOTIFICATION_CHANNEL_FAILED, 'Canal de notificacion con fallo permanente'),
        (AI_ACTION_EXECUTED, 'Accion de escritura ejecutada por el AI Core'),
        (ADMIN_RESOURCE_DELETED, 'Recurso eliminado desde el panel administrativo'),
    ]

    SEVERITY_INFO     = 'INFO'
    SEVERITY_WARNING  = 'WARNING'
    SEVERITY_CRITICAL = 'CRITICAL'
    SEVERITY_CHOICES = [
        (SEVERITY_INFO,     'Info'),
        (SEVERITY_WARNING,  'Advertencia'),
        (SEVERITY_CRITICAL, 'Critico'),
    ]

    event_type = models.CharField(max_length=40, choices=EVENT_CHOICES, db_index=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default=SEVERITY_INFO, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='security_events',
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    path = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at', 'event_type']),
        ]

    def __str__(self):
        return f'SecurityEvent({self.event_type}, {self.severity})'
