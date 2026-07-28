import re
import logging
from django.core.cache import cache
from django.db import transaction

from notifications.models import (
    NotificationTemplate, NotificationLog, UserNotificationPreference,
    CHANNEL_EMAIL, CHANNEL_WHATSAPP, CHANNEL_SMS, CHANNEL_WEB_SOCKET,
)

logger        = logging.getLogger(__name__)
_PHONE_RE     = re.compile(r'^[3][0-9]{9}$')
_ALL_CHANNELS = {CHANNEL_EMAIL, CHANNEL_WHATSAPP, CHANNEL_SMS, CHANNEL_WEB_SOCKET}

# N-03 (auditoria enterprise): dispatch_notification no tenia ningun limite
# de tasa propio -- muchos de sus 8+ llamadores (kyc, operations, renting,
# technical_services) tampoco tienen throttle en su propio endpoint, asi que
# una accion de negocio repetida podia generar SMS/WhatsApp sin limite al
# mismo destinatario (costo real por SMS). Se gatea aqui, en el unico punto
# de entrada real, en vez de en cada endpoint disperso.
_RATE_LIMITED_CHANNELS = {CHANNEL_SMS, CHANNEL_WHATSAPP}
_RATE_LIMIT_MAX = 5
_RATE_LIMIT_WINDOW_SECONDS = 3600


def _channel_rate_limited(channel: str, recipient: str) -> bool:
    if channel not in _RATE_LIMITED_CHANNELS or not recipient:
        return False
    key = f'notif_throttle:{channel}:{recipient}'
    count = cache.get(key)
    if count is None:
        cache.set(key, 1, timeout=_RATE_LIMIT_WINDOW_SECONDS)
        return False
    if count >= _RATE_LIMIT_MAX:
        return True
    try:
        cache.incr(key)
    except ValueError:
        # la llave expiro entre el get() y el incr() -- tratar como primer envio
        cache.set(key, 1, timeout=_RATE_LIMIT_WINDOW_SECONDS)
    return False


def _resolve_phone(user) -> str | None:
    """
    Resuelve el mejor número de teléfono colombiano disponible para el usuario.
    Cascada: UserProfile.phone_number → ShippingAddress más reciente.
    Retorna None si no hay un número de 10 dígitos que inicie con 3.
    """
    from accounts.services import ProfileResolver
    profile = ProfileResolver.get_profile(user)
    if profile:
        raw = str(getattr(profile, 'phone_number', '') or '').strip()
        if _PHONE_RE.match(raw):
            return raw

    from orders.models import ShippingAddress
    phone = (
        ShippingAddress.objects
        .filter(user=user, is_deleted=False)
        .order_by('-created_at')
        .values_list('phone_number', flat=True)
        .first()
    )
    if phone and _PHONE_RE.match(str(phone).strip()):
        return str(phone).strip()

    return None


class NotificationCommands:

    @staticmethod
    def dispatch_notification(
        user,
        template_slug: str,
        context: dict,
        ws_group: str | None = None,
    ) -> None:
        """
        Punto de entrada centralizado para todos los eventos de notificación.

        DEBE llamarse siempre desde transaction.on_commit() para garantizar
        que el estado de BD esté confirmado antes de notificar.

        1. Busca la plantilla activa por slug; aborta si no existe.
        2. Determina los canales habilitados para el usuario.
           Sin preferencias registradas → asume todos los canales habilitados.
        3. Por cada canal disponible, verifica que el usuario tenga los datos
           necesarios y que la plantilla esté configurada para ese canal.
        4. Despacha una tarea Celery independiente por canal (sin bloquear el
           hilo de la API). Cada tarea registra su resultado en NotificationLog.

        Args:
            user:          Instancia de User (propietario del evento).
            template_slug: Identificador único de la plantilla de negocio.
            context:       Variables para renderizar la plantilla.
            ws_group:      Grupo de Channels destino. None → f"user_{user.uuid}".
        """
        try:
            template = NotificationTemplate.objects.get(
                slug=template_slug, is_active=True
            )
        except NotificationTemplate.DoesNotExist:
            logger.warning(
                "dispatch_notification: plantilla '%s' no encontrada o inactiva "
                "(user=%s). Evento ignorado.",
                template_slug, getattr(user, 'email', user),
            )
            NotificationLog.objects.create(
                user=user, template=None, template_slug=template_slug,
                status=NotificationLog.STATUS_FAILED,
                payload_context=context,
                error_message='Plantilla no encontrada o inactiva.',
            )
            return

        # list() en vez de .exists() + set(): esta funcion se llama en cada evento
        # de negocio del proyecto (8 callers), evitar una segunda consulta idéntica.
        enabled_channels = list(
            UserNotificationPreference.objects
            .filter(user=user, is_enabled=True)
            .values_list('channel', flat=True)
        )
        active_channels: set[str] = set(enabled_channels) if enabled_channels else _ALL_CHANNELS

        from notifications.tasks import (
            send_ws_notification_task,
            send_email_notification_task,
            send_whatsapp_notification_task,
            send_sms_notification_task,
        )

        # ── WebSocket ─────────────────────────────────────────────────────────
        if CHANNEL_WEB_SOCKET in active_channels and template.ws_event_type:
            group = ws_group or f'user_{user.uuid}'
            send_ws_notification_task.delay(
                user_id=user.pk,
                template_slug=template_slug,
                ws_group=group,
                event_type=template.ws_event_type,
                context=context,
            )

        # ── Email ─────────────────────────────────────────────────────────────
        if CHANNEL_EMAIL in active_channels and user.email and template.email_body:
            send_email_notification_task.delay(
                user_id=user.pk,
                template_slug=template_slug,
                context=context,
            )

        # ── WhatsApp ──────────────────────────────────────────────────────────
        phone = _resolve_phone(user)
        if (
            CHANNEL_WHATSAPP in active_channels
            and phone
            and template.whatsapp_template_name
        ):
            if _channel_rate_limited(CHANNEL_WHATSAPP, phone):
                logger.warning(
                    "dispatch_notification: WhatsApp rate-limited para %s (template=%s)",
                    phone, template_slug,
                )
            else:
                send_whatsapp_notification_task.delay(
                    user_id=user.pk,
                    template_slug=template_slug,
                    phone=phone,
                    context=context,
                )

        # ── SMS (modem GSM local, ver sms_bridge/bridge.py) ─────────────────────
        if (
            CHANNEL_SMS in active_channels
            and phone
            and template.sms_body
        ):
            if _channel_rate_limited(CHANNEL_SMS, phone):
                logger.warning(
                    "dispatch_notification: SMS rate-limited para %s (template=%s)",
                    phone, template_slug,
                )
            else:
                send_sms_notification_task.delay(
                    user_id=user.pk,
                    template_slug=template_slug,
                    phone=phone,
                    context=context,
                )

        # ── AI Core Event Bus (Fase 7, Componente 8) ─────────────────────────
        # El Action Graph se suscribe como UN CONSUMIDOR MAS de este mismo
        # dispatch (no un bus paralelo): para los slugs configurados, el
        # asistente deja un mensaje proactivo en la sala del cliente.
        from django.conf import settings as dj_settings
        if template_slug in getattr(dj_settings, 'AI_PROACTIVE_SLUGS', []):
            from notifications.tasks import ai_proactive_room_message_task
            ai_proactive_room_message_task.delay(
                user_id=user.pk,
                template_slug=template_slug,
                context=context,
            )

    @staticmethod
    def dispatch_notification_once(user, template_slug: str, context: dict, dedupe_key: str) -> bool:
        """
        Fase 11 AI Core (Proactividad): variante de dispatch_notification() para
        scanners periodicos (Celery beat) que detectan la MISMA condicion en
        cada corrida (ej. "cotizacion sin respuesta") y no deben renotificar la
        misma entidad. El marcador de dedupe se crea de forma SINCRONA (no
        depende de que un canal async ya haya corrido) -- dispatch_notification()
        por si sola no sirve para esto: sus NotificationLog reales los crean las
        tareas Celery por canal (send_ws/email/whatsapp_notification_task), que
        corren en segundo plano y dejarian una ventana de carrera si dos
        corridas del scan se solapan.

        Retorna False (no notifica) si `dedupe_key` ya fue notificado antes
        bajo este `template_slug`; True si se disparo dispatch_notification().
        """
        already_notified = NotificationLog.objects.filter(
            template_slug=template_slug, channel='', payload_context__dedupe_key=dedupe_key,
        ).exists()
        if already_notified:
            return False
        NotificationLog.objects.create(
            user=user, template=None, template_slug=template_slug,
            channel='', status=NotificationLog.STATUS_SENT,
            payload_context={**context, 'dedupe_key': dedupe_key},
        )
        NotificationCommands.dispatch_notification(user, template_slug, context)
        return True


class NotificationPreferenceCommands:
    """Write-side for per-user notification channel preferences."""

    @staticmethod
    @transaction.atomic
    def set_preference(user, channel: str, is_enabled: bool) -> UserNotificationPreference:
        """
        Upsert a UserNotificationPreference for (user, channel).
        Returns the saved instance.
        """
        pref, _ = UserNotificationPreference.objects.update_or_create(
            user=user,
            channel=channel,
            defaults={'is_enabled': bool(is_enabled)},
        )
        return pref


class NotificationTemplateCommands:
    """Edicion administrativa de plantillas — el slug nunca se toca desde desde aqui:
    es el contrato fijo con los callers de dispatch_notification()."""

    TEMPLATE_ALLOWED_FIELDS = {
        'name', 'subject', 'email_body',
        'whatsapp_template_name', 'sms_body', 'ws_event_type', 'is_active',
    }

    @staticmethod
    @transaction.atomic
    def update_template(template, data: dict):
        for field, value in data.items():
            if field in NotificationTemplateCommands.TEMPLATE_ALLOWED_FIELDS:
                setattr(template, field, value)
        template.save()
        return template
