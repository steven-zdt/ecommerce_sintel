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
    # C1 (AUDITORIA_INTEGRAL_PRODUCCION_2026-08-04.md): _sync_wompi_status() recibia un
    # wompi_id arbitrario del cliente (query param `id`) y adoptaba su status sin verificar
    # que el 'reference'/monto devuelto por Wompi perteneciera a la Transaction propia --
    # este evento registra cuando esa validacion rechaza un intento real.
    PAYMENT_SYNC_REFERENCE_MISMATCH = 'PAYMENT_SYNC_REFERENCE_MISMATCH'
    # Plan "AI Provider Runtime" FASE 34 (2026-08-13): antes de esto, crear/editar/
    # eliminar/activar/probar un AIProvider o cambiar el modelo primario/fallback de
    # un canal no dejaba NINGUN rastro de auditoria (gap real, ver
    # ai_provider/.AGENT/AI_PROVIDER_RUNTIME_AUDIT.md seccion 11). Nunca incluir el
    # secreto (api_key) en metadata -- ver AIProviderCommands.
    AI_PROVIDER_CREATED = 'AI_PROVIDER_CREATED'
    AI_PROVIDER_UPDATED = 'AI_PROVIDER_UPDATED'
    AI_PROVIDER_ACTIVATED = 'AI_PROVIDER_ACTIVATED'
    AI_PROVIDER_DEACTIVATED = 'AI_PROVIDER_DEACTIVATED'
    AI_PROVIDER_TESTED = 'AI_PROVIDER_TESTED'
    AI_MODEL_CHANGED = 'AI_MODEL_CHANGED'
    AI_CHANNEL_CHANGED = 'AI_CHANNEL_CHANGED'
    # HARDENING F9 (2026-09-24): senales de alto nivel del turno de IA (salida bloqueada/redactada, inyeccion detectada).
    # metadata: solo categorias (flags), request_id y conversation_id -- NUNCA contenido del mensaje ni de la respuesta.
    AI_SECURITY_FLAG = 'AI_SECURITY_FLAG'
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
        (PAYMENT_SYNC_REFERENCE_MISMATCH, 'Reconciliacion de pago rechazada: reference/monto no coincide'),
        (AI_PROVIDER_CREATED, 'Proveedor de IA creado'),
        (AI_PROVIDER_UPDATED, 'Proveedor de IA actualizado'),
        (AI_PROVIDER_ACTIVATED, 'Proveedor de IA activado'),
        (AI_PROVIDER_DEACTIVATED, 'Proveedor de IA desactivado'),
        (AI_PROVIDER_TESTED, 'Conexion de proveedor de IA probada'),
        (AI_MODEL_CHANGED, 'Modelo de IA agregado/eliminado'),
        (AI_CHANNEL_CHANGED, 'Configuracion de canal de IA modificada (primario/fallback)'),
        (AI_SECURITY_FLAG, 'Senal de seguridad en un turno de IA (fuga bloqueada, secreto redactado, inyeccion)'),
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
