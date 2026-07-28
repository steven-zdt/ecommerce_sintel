from django.db import models
from django.conf import settings
from ecommerce.base_models import SintelBaseModel

CHANNEL_EMAIL      = 'EMAIL'
CHANNEL_WHATSAPP   = 'WHATSAPP'
CHANNEL_SMS        = 'SMS'
CHANNEL_WEB_SOCKET = 'WEB_SOCKET'

CHANNEL_CHOICES = [
    (CHANNEL_EMAIL,      'Correo electronico'),
    (CHANNEL_WHATSAPP,   'WhatsApp'),
    (CHANNEL_SMS,        'SMS'),
    (CHANNEL_WEB_SOCKET, 'Notificacion web en tiempo real'),
]


class NotificationTemplate(SintelBaseModel):
    """
    Plantilla configurable por evento de negocio.
    El slug es el contrato entre la app core y este sistema.
    Dejar un campo de canal vacío deshabilita ese canal para la plantilla.
    """
    slug                   = models.SlugField(max_length=100, unique=True, db_index=True)
    name                   = models.CharField(max_length=255)
    # ── Email ─────────────────────────────────────────────────────────────────
    subject                = models.CharField(max_length=255, blank=True, default='')
    email_body             = models.TextField(
        blank=True, default='',
        help_text='Soporta variables Django Template: {{ order_uuid }}, {{ total }}, etc.'
    )
    # ── WhatsApp (Meta Cloud API) ─────────────────────────────────────────────
    whatsapp_template_name = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Nombre exacto de la plantilla aprobada en Meta Business Manager.'
    )
    # ── SMS (modem GSM local, ver sms_bridge/bridge.py) ───────────────────────
    sms_body = models.CharField(
        max_length=160, blank=True, default='',
        help_text=(
            'Texto del SMS (max 160 caracteres = 1 segmento GSM-7, sin partir '
            'en varios mensajes). Soporta variables Django Template.'
        ),
    )
    # ── WebSocket (Django Channels) ───────────────────────────────────────────
    ws_event_type          = models.CharField(
        max_length=100, blank=True, default='',
        help_text='event_type que recibe el frontend (ej. ORDER_PAID_SUCCESS).'
    )
    is_active              = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name        = 'Plantilla de notificacion'
        verbose_name_plural = 'Plantillas de notificaciones'

    def __str__(self):
        return self.slug


class UserNotificationPreference(SintelBaseModel):
    """
    Preferencia de canal por usuario.
    Sin registros → el sistema asume todos los canales habilitados (opt-in implícito).
    """
    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
    )
    channel    = models.CharField(max_length=20, choices=CHANNEL_CHOICES, db_index=True)
    is_enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name        = 'Preferencia de notificacion'
        verbose_name_plural = 'Preferencias de notificacion'
        unique_together     = ('user', 'channel')

    def __str__(self):
        state = 'ON' if self.is_enabled else 'OFF'
        return f"{self.user.email} | {self.channel} | {state}"


class NotificationLog(SintelBaseModel):
    """
    Registro de auditoría de cada intento de envío por canal.
    Permite depurar fallos y auditar SLAs de entrega.
    """
    STATUS_PENDING = 'PENDING'
    STATUS_SENT    = 'SENT'
    STATUS_FAILED  = 'FAILED'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pendiente'),
        (STATUS_SENT,    'Enviado'),
        (STATUS_FAILED,  'Fallido'),
    ]

    user            = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='notification_logs',
    )
    template        = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        related_name='logs',
    )
    # Poblado SIEMPRE (incluso si `template` es None porque el slug no existe o
    # esta inactivo) -- sin este campo, un slug roto no dejaba ningun rastro
    # auditable de que evento de negocio se disparo (ver dispatch_notification).
    template_slug   = models.CharField(max_length=100, blank=True, default='')
    channel         = models.CharField(max_length=20, choices=CHANNEL_CHOICES, blank=True, db_index=True)
    status          = models.CharField(
        max_length=10, choices=STATUS_CHOICES,
        default=STATUS_PENDING, db_index=True,
    )
    sent_at         = models.DateTimeField(null=True, blank=True)
    payload_context = models.JSONField(
        default=dict,
        help_text='Variables de contexto enviadas al motor de plantillas.'
    )
    error_message   = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name        = 'Log de notificacion'
        verbose_name_plural = 'Logs de notificaciones'
        ordering            = ['-created_at']
        indexes             = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['template', 'channel', 'status']),
        ]

    def __str__(self):
        return f"{self.template} | {self.channel} | {self.status}"
