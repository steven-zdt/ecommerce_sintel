import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


def _mark_meta_webhook_event(event_id, new_status, *, error_code='', bump_retry=False):
    """Avanza el ciclo de vida de un MetaWebhookEvent (FASE 6 integracion Meta
    Business). No-op y a prueba de fallos: event_id es None en las llamadas
    directas / tests de process_whatsapp_inbound_task, y la fila podria haberse
    purgado -- nunca debe tumbar el procesamiento del mensaje."""
    if not event_id:
        return
    try:
        from django.db.models import F
        from notifications.models import MetaWebhookEvent
        fields = {'status': new_status}
        if error_code:
            fields['error_code'] = error_code[:64]
        if new_status == MetaWebhookEvent.STATUS_PROCESSED:
            fields['processed_at'] = timezone.now()
        if bump_retry:
            fields['retry_count'] = F('retry_count') + 1
        MetaWebhookEvent.objects.filter(id=event_id).update(**fields)
    except Exception:
        logger.exception('[wa-inbound] no se pudo actualizar MetaWebhookEvent %s', event_id)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
    default_retry_delay=10,
    name='notifications.send_ws',
    queue='notifications',
    acks_late=True,
)
def send_ws_notification_task(
    self,
    user_id: int,
    template_slug: str,
    ws_group: str,
    event_type: str,
    context: dict,
):
    from django.contrib.auth import get_user_model
    from notifications.models import NotificationTemplate, NotificationLog, CHANNEL_WEB_SOCKET
    from ecommerce.ws_notify import ws_notify

    User     = get_user_model()
    try:
        user     = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error('Usuario no encontrado | user_id=%s. Abortando envio de notificacion WS.', user_id)
        return

    try:
        template = NotificationTemplate.objects.get(slug=template_slug)
    except NotificationTemplate.DoesNotExist:
        logger.error('Plantilla no encontrada | slug=%s. Abortando envio de notificacion WS.', template_slug)
        return

    log = NotificationLog.objects.create(
        user=user, template=template, template_slug=template_slug,
        channel=CHANNEL_WEB_SOCKET,
        status=NotificationLog.STATUS_PENDING,
        payload_context=context,
    )
    try:
        ws_notify(group=ws_group, event_type=event_type, payload=context)
        log.status  = NotificationLog.STATUS_SENT
        log.sent_at = timezone.now()
        log.save(update_fields=['status', 'sent_at'])
        logger.info('WS enviado | group=%s event=%s user=%s', ws_group, event_type, user.email)
    except Exception as exc:
        log.status        = NotificationLog.STATUS_FAILED
        log.error_message = str(exc)
        log.save(update_fields=['status', 'error_message'])
        logger.error('WS fallido | group=%s user=%s error=%s', ws_group, user.email, exc)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
    default_retry_delay=60,
    name='notifications.send_email',
    queue='notifications',
    acks_late=True,
)
def send_email_notification_task(
    self,
    user_id: int,
    template_slug: str,
    context: dict,
):
    from django.contrib.auth import get_user_model
    from django.core.mail import send_mail
    from django.template import Template, Context
    from django.conf import settings
    from notifications.models import NotificationTemplate, NotificationLog, CHANNEL_EMAIL

    User     = get_user_model()
    try:
        user     = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error('Usuario no encontrado | user_id=%s. Abortando envio de notificacion Email.', user_id)
        return

    try:
        template = NotificationTemplate.objects.get(slug=template_slug)
    except NotificationTemplate.DoesNotExist:
        logger.error('Plantilla no encontrada | slug=%s. Abortando envio de notificacion Email.', template_slug)
        return

    log = NotificationLog.objects.create(
        user=user, template=template, template_slug=template_slug,
        channel=CHANNEL_EMAIL,
        status=NotificationLog.STATUS_PENDING,
        payload_context=context,
    )
    try:
        from organization.services.selectors import OrganizationSelector
        email_settings = OrganizationSelector.get_email_settings()
        from_email = (email_settings.default_from_email if email_settings else '') or settings.DEFAULT_FROM_EMAIL

        subject = Template(template.subject).render(Context(context, autoescape=False)).strip()
        body = Template(template.email_body).render(Context(context, autoescape=False))
        is_html = '<html' in body.lower() or '<!doctype' in body.lower()
        send_mail(
            subject=subject,
            message=body if not is_html else '',
            from_email=from_email,
            recipient_list=[user.email],
            fail_silently=False,
            html_message=body if is_html else None,
        )
        log.status  = NotificationLog.STATUS_SENT
        log.sent_at = timezone.now()
        log.save(update_fields=['status', 'sent_at'])
        logger.info('Email enviado | to=%s template=%s', user.email, template_slug)
    except Exception as exc:
        log.status        = NotificationLog.STATUS_FAILED
        log.error_message = str(exc)
        log.save(update_fields=['status', 'error_message'])
        logger.error('Email fallido | to=%s template=%s error=%s', user.email, template_slug, exc)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
    default_retry_delay=120,
    name='notifications.send_whatsapp',
    queue='notifications',
    acks_late=True,
)
def send_whatsapp_notification_task(
    self,
    user_id: int,
    template_slug: str,
    phone: str,
    context: dict,
):
    from django.contrib.auth import get_user_model
    from notifications.models import NotificationTemplate, NotificationLog, CHANNEL_WHATSAPP
    from notifications.clients.whatsapp import WhatsAppClient, WhatsAppApiError, WhatsAppAuthError

    User     = get_user_model()
    try:
        user     = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error('Usuario no encontrado | user_id=%s. Abortando envio de notificacion WhatsApp.', user_id)
        return

    try:
        template = NotificationTemplate.objects.get(slug=template_slug)
    except NotificationTemplate.DoesNotExist:
        logger.error('Plantilla no encontrada | slug=%s. Abortando envio de notificacion WhatsApp.', template_slug)
        return

    log = NotificationLog.objects.create(
        user=user, template=template, template_slug=template_slug,
        channel=CHANNEL_WHATSAPP,
        status=NotificationLog.STATUS_PENDING,
        payload_context=context,
    )
    try:
        from notifications.clients.whatsapp import WhatsAppClient, WhatsAppApiError, WhatsAppAuthError, WhatsAppConfigError
        client = WhatsAppClient()
        client.send_template(
            to=f'57{phone}',   # prefijo Colombia
            template_name=template.whatsapp_template_name,
            variables=context,
        )
        log.status  = NotificationLog.STATUS_SENT
        log.sent_at = timezone.now()
        log.save(update_fields=['status', 'sent_at'])
        logger.info('WhatsApp enviado | to=57%s template=%s', phone, template_slug)
    except (WhatsAppAuthError, WhatsAppConfigError) as exc:
        # Token invalido o configuracion faltante: error permanente, no reintentar.
        log.status        = NotificationLog.STATUS_FAILED
        log.error_message = str(exc)
        log.save(update_fields=['status', 'error_message'])
        logger.critical(
            'WhatsApp error de configuracion/auth (sin reintento) | template=%s error=%s '
            '— Revisa settings de WhatsApp',
            template_slug, exc,
        )
        from security.models import SecurityEvent
        from security.services.commands import SecurityCommands
        SecurityCommands.log_event(
            SecurityEvent.NOTIFICATION_CHANNEL_FAILED, user=user, severity=SecurityEvent.SEVERITY_CRITICAL,
            metadata={'channel': 'WHATSAPP', 'template': template_slug, 'error': str(exc)},
        )
    except WhatsAppApiError as exc:
        log.status        = NotificationLog.STATUS_FAILED
        log.error_message = str(exc)
        log.save(update_fields=['status', 'error_message'])
        logger.error('WhatsApp fallido | to=57%s template=%s error=%s', phone, template_slug, exc)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    name='notifications.send_sms',
    queue='notifications',
    acks_late=True,
)
def send_sms_notification_task(
    self,
    user_id: int,
    template_slug: str,
    phone: str,
    context: dict,
):
    from django.contrib.auth import get_user_model
    from django.template import Template, Context
    from notifications.models import NotificationTemplate, NotificationLog, CHANNEL_SMS
    from notifications.clients.sms import SmsClient, SmsApiError, SmsConfigError, SmsBridgeUnreachableError

    User     = get_user_model()
    try:
        user     = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error('Usuario no encontrado | user_id=%s. Abortando envio de notificacion SMS.', user_id)
        return

    try:
        template = NotificationTemplate.objects.get(slug=template_slug)
    except NotificationTemplate.DoesNotExist:
        logger.error('Plantilla no encontrada | slug=%s. Abortando envio de notificacion SMS.', template_slug)
        return

    log = NotificationLog.objects.create(
        user=user, template=template, template_slug=template_slug,
        channel=CHANNEL_SMS,
        status=NotificationLog.STATUS_PENDING,
        payload_context=context,
    )
    try:
        body = Template(template.sms_body).render(Context(context, autoescape=False))
        message_ref = SmsClient().send(to=f'+57{phone}', message=body)
        log.status  = NotificationLog.STATUS_SENT
        log.sent_at = timezone.now()
        log.save(update_fields=['status', 'sent_at'])
        logger.info('SMS enviado | to=57%s template=%s ref=%s', phone, template_slug, message_ref)
    except SmsConfigError as exc:
        # SMS_BRIDGE_URL no configurado: error permanente, no reintentar.
        log.status        = NotificationLog.STATUS_FAILED
        log.error_message = str(exc)
        log.save(update_fields=['status', 'error_message'])
        logger.critical(
            'SMS error de configuracion (sin reintento) | template=%s error=%s '
            '— Revisa SMS_BRIDGE_URL/SMS_BRIDGE_TOKEN',
            template_slug, exc,
        )
        from security.models import SecurityEvent
        from security.services.commands import SecurityCommands
        SecurityCommands.log_event(
            SecurityEvent.NOTIFICATION_CHANNEL_FAILED, user=user, severity=SecurityEvent.SEVERITY_CRITICAL,
            metadata={'channel': 'SMS', 'template': template_slug, 'error': str(exc)},
        )
    except (SmsBridgeUnreachableError, SmsApiError) as exc:
        log.status        = NotificationLog.STATUS_FAILED
        log.error_message = str(exc)
        log.save(update_fields=['status', 'error_message'])
        logger.error('SMS fallido | to=57%s template=%s error=%s', phone, template_slug, exc)
        raise self.retry(exc=exc)


# ─── Fase 7 AI Core: canal WhatsApp entrante + Event Bus proactivo ───────────

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name='notifications.process_whatsapp_inbound',
    queue='notifications',
    acks_late=True,
)
def process_whatsapp_inbound_task(self, wa_id: str, text: str, event_id: int | None = None):
    """
    Mensaje entrante de WhatsApp -> Action Graph -> respuesta por WhatsApp.
    El usuario se resuelve por los ultimos 10 digitos del telefono del
    UserProfile (celular colombiano); si no hay match, se ignora con log
    (no se responde a numeros desconocidos).

    M2 (AUDITORIA/19_AUDITORIA_COMMUNICATION_CENTER_CANALES.md, 2026-08-01): antes esta
    conversacion no dejaba NINGUN rastro en BD -- invisible para cualquier agente humano en
    /panel/soporte y para Customer 360, a diferencia de todo lo demas en el proyecto (que se
    audita via SecurityEvent/NotificationLog). Ahora se persiste ambos lados (mensaje del
    cliente + respuesta de la IA) en la ChatRoom del usuario, reusando ChatCommands -- mismo
    patron que ai_proactive_room_message_task ya usa en sentido inverso (notificacion -> sala).
    Deliberadamente FUERA de alcance de este fix (evaluado y pospuesto en AUDITORIA/19 §2, no
    es un olvido): unificar el conversation_id de IA con el canal web (sigue siendo
    'wa-{user_id}', namespace separado de 'room-{uuid}').

    CERRADO (auditoria E2E AI Engine, 2026-08-17): este canal SI respeta ahora
    is_ai_mode_active/ai_paused y is_ai_rate_limited de la sala -- mismo criterio que
    SupportChatConsumer._ai_mode_active/_ai_rate_limited (support/consumers.py). Antes, un
    cliente cuyo chat web ya habia escalado a un humano (ai_paused=True) seguia recibiendo
    auto-respuestas de la IA si escribia por WhatsApp, sin que el agente humano se enterara.
    El mensaje del cliente se guarda y se difunde a /panel/soporte de todas formas -- solo se
    omite la llamada a ask_ai() y la respuesta automatica.
    """
    from accounts.models import UserProfile
    from notifications.clients.whatsapp import WhatsAppClient, WhatsAppApiError
    from support.services.ai_bridge import ask_ai, get_ai_bot_user, is_ai_mode_active, is_ai_rate_limited
    from support.services.commands import ChatCommands

    digits = ''.join(c for c in wa_id if c.isdigit())[-10:]
    profile = (
        UserProfile.objects
        .filter(phone_number__isnull=False, user__is_active=True)
        .filter(phone_number__endswith=digits)
        .select_related('user')
        .first()
    )
    if profile is None:
        logger.warning('[wa-inbound] numero sin usuario asociado: ...%s', digits[-4:])
        _mark_meta_webhook_event(event_id, 'PROCESSED', error_code='no_user_for_number')
        return

    room = ChatCommands.get_or_create_room(profile.user)
    if self.request.retries == 0:
        # Fase 9 (AUDITORIA/24_AUDITORIA_NOTIFICATIONS_SUPPORT.md, 2026-08-01): solo en el
        # primer intento -- si ask_ai() falla mas abajo y la tarea reintenta, Celery
        # re-ejecuta la funcion completa desde el inicio; sin este guard, el mensaje del
        # cliente se duplicaria una vez por cada reintento.
        ChatCommands.save_message(room, profile.user, text)
        _broadcast_chat_message(room, profile.user, text, profile.user.email, is_admin=False)

    room.refresh_from_db(fields=['status', 'ai_paused', 'assigned_admin'])
    if not is_ai_mode_active(room):
        logger.info('[wa-inbound] IA inactiva para room=%s (handoff activo) -- sin auto-respuesta', room.uuid)
        _mark_meta_webhook_event(event_id, 'PROCESSED', error_code='handoff_active')
        return
    if is_ai_rate_limited(room):
        logger.warning('[wa-inbound] rate limit de IA alcanzado para room=%s -- sin auto-respuesta', room.uuid)
        _mark_meta_webhook_event(event_id, 'PROCESSED', error_code='ai_rate_limited')
        return

    try:
        ai_response = ask_ai(profile.user, text, conversation_id=f'wa-{profile.user_id}')
    except Exception as exc:
        # Antes: max_retries=1 sin autoretry_for ni self.retry() -- un fallo transitorio del
        # AI Engine (timeout, red) perdia el mensaje del cliente de forma permanente y
        # silenciosa (el webhook ya habia dedupe por message_id, no hay una segunda entrega).
        logger.error(
            '[wa-inbound] ask_ai fallo (intento %s/%s) user=%s: %s',
            self.request.retries, self.max_retries, profile.user.email, exc,
        )
        _mark_meta_webhook_event(event_id, 'FAILED', error_code='ai_engine_error', bump_retry=True)
        raise self.retry(exc=exc)

    reply = (ai_response or {}).get('response') or ''
    if not reply.strip():
        logger.warning('[wa-inbound] AI sin respuesta para user=%s', profile.user.email)
        _mark_meta_webhook_event(event_id, 'PROCESSED', error_code='ai_empty_response')
        return

    bot = get_ai_bot_user()
    msg = ChatCommands.save_message(room, bot, reply, ai_metrics=(ai_response or {}).get('metrics'))
    _broadcast_chat_message(room, profile.user, reply, bot.email, is_admin=True, created_at=msg.created_at)

    try:
        WhatsAppClient().send_text(wa_id, reply)
        _mark_meta_webhook_event(event_id, 'PROCESSED')
    except WhatsAppApiError as exc:
        # Config/token de Meta invalido: se registra, no se reintenta en loop.
        logger.error('[wa-inbound] no se pudo responder por WhatsApp: %s', exc)
        _mark_meta_webhook_event(event_id, 'FAILED', error_code='whatsapp_send_failed')


def _broadcast_chat_message(room, user, text: str, sender_email: str, *, is_admin: bool, created_at=None) -> None:
    """group_send plano (mismo formato que SupportChatConsumer.chat_message) hacia el cliente y
    hacia support_admins -- para que un agente con el dashboard/widget abierto vea en vivo un
    mensaje que llego por WhatsApp, no solo al reabrir la sala despues."""
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    from django.utils import timezone

    layer = get_channel_layer()
    if layer is None:
        return
    payload = {
        'type': 'chat.message',
        'message': text,
        'sender_email': sender_email,
        'is_admin': is_admin,
        'room_uuid': str(room.uuid),
        'created_at': (created_at or timezone.now()).isoformat(),
    }
    async_to_sync(layer.group_send)(f'chat_{str(user.uuid)}', payload)
    async_to_sync(layer.group_send)('support_admins', payload)


@shared_task(
    bind=True,
    max_retries=1,
    default_retry_delay=30,
    name='notifications.ai_proactive_room_message',
    queue='notifications',
    acks_late=True,
)
def ai_proactive_room_message_task(self, user_id: int, template_slug: str, context: dict):
    """
    Event Bus (Componente 8): ademas de los canales normales del
    dispatch_notification, el asistente deja un mensaje proactivo en la sala
    del cliente (visible en el widget y en /panel/soporte). No inventa un bus
    nuevo: se dispara desde el MISMO dispatch usado por 11 apps.

    Fase 9 (AUDITORIA/24_AUDITORIA_NOTIFICATIONS_SUPPORT.md, 2026-08-01): antes
    solo difundia a chat_{user.uuid} -- un ticket escalado a un agente humano y
    sin seguimiento (slug ticket_soporte_sin_seguimiento) nunca alertaba a
    NINGUN canal del staff, solo tranquilizaba al cliente con el mensaje. Ahora
    reusa _broadcast_chat_message (mismo helper que ya usa el canal de
    WhatsApp entrante) para que support_admins tambien lo reciba en vivo -- el
    dashboard (SupportDashboardView.vue) ya marca unread_count/last_message
    para ese evento sin cambios adicionales.
    """
    from django.contrib.auth import get_user_model
    from support.services.ai_bridge import get_ai_bot_user
    from support.services.commands import ChatCommands

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    # Repaso de backlog (AUDITORIA/24_AUDITORIA_NOTIFICATIONS_SUPPORT.md, 2026-08-03): a
    # diferencia de los demas canales de dispatch_notification (que si respetan
    # UserNotificationPreference), este mensaje se creaba/difundia incondicionalmente. Mismo
    # criterio "opt-out" que el resto: sin preferencias registradas se asume habilitado; con
    # preferencias explicitas, solo se respeta si WEB_SOCKET esta entre las habilitadas -- para
    # este canal en particular, "enviar" y "crear el mensaje en la sala" son la misma accion, asi
    # que si esta desactivado no se crea nada (no solo se omite la difusion en vivo).
    from notifications.models import UserNotificationPreference, CHANNEL_WEB_SOCKET
    enabled_channels = list(
        UserNotificationPreference.objects.filter(user=user, is_enabled=True).values_list('channel', flat=True)
    )
    if enabled_channels and CHANNEL_WEB_SOCKET not in enabled_channels:
        logger.info('[ai-proactive] omitido -- user=%s desactivo el canal WEB_SOCKET', user.email)
        return

    parts = [f"Actualizacion de tu cuenta ({template_slug.replace('_', ' ')})."]
    for key in (
        'order_uuid', 'rental_uuid', 'status', 'total', 'message',
        # Fase 11 AI Core (Proactividad): claves de los 4 scanners nuevos
        # (quotes/renting/payment/support tasks.py).
        'quotation_uuid', 'rental_period_uuid', 'transaction_uuid', 'room_uuid',
        'end_date',
    ):
        if context.get(key):
            parts.append(f"{key.replace('_', ' ')}: {context[key]}")
    text = ' '.join(parts) + ' Escribeme por aqui si necesitas ayuda con esto.'

    bot = get_ai_bot_user()
    room = ChatCommands.get_or_create_room(user)
    msg = ChatCommands.save_message(room, bot, text)
    try:
        _broadcast_chat_message(room, user, text, bot.email, is_admin=True, created_at=msg.created_at)
    except Exception:
        # El mensaje ya quedo persistido (fuente de verdad); un fallo de WS es
        # fire-and-forget, igual que ws_notify() en el resto del proyecto --
        # no vale la pena reintentar toda la tarea (duplicaria save_message).
        logger.exception('[ai-proactive] fallo al difundir mensaje en sala %s', room.uuid)
    logger.info('[ai-proactive] mensaje en sala %s por slug=%s', room.uuid, template_slug)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    default_retry_delay=15,
    name='notifications.send_whatsapp_agent_reply',
    queue='notifications',
    acks_late=True,
)
def send_whatsapp_agent_reply_task(self, user_id: int, text: str):
    """
    Fase 16 (AUDITORIA/30_AUDITORIA_PRUEBAS_E2E.md, 2026-08-03): antes, cuando un ticket
    escalaba a un humano (ai_paused=True) y el agente respondia desde /panel/soporte, esa
    respuesta SOLO se difundia por WebSocket (support/consumers.py) -- un cliente que hablaba
    UNICAMENTE por WhatsApp (sin el widget web abierto, sin conexion WS activa) nunca la recibia
    -- se quedaba esperando en WhatsApp una respuesta que solo existia en el dashboard.

    Bridge minimo: si el usuario tiene un telefono colombiano valido (misma resolucion --
    _resolve_phone -- que ya usa dispatch_notification para el canal WhatsApp transaccional), se
    reenvia el texto del agente por el mismo canal freeform que ya usa
    process_whatsapp_inbound_task para la respuesta de la IA. Sujeto a la ventana de servicio de
    24h de Meta (si esta cerrada, la API rechaza el envio) -- se registra como fallo no
    bloqueante, mismo criterio que el resto de WhatsAppApiError en el proyecto (no se reintenta
    en loop infinito ante un error de la API, solo ante fallos transitorios de red).
    """
    from django.contrib.auth import get_user_model
    from notifications.clients.whatsapp import WhatsAppClient, WhatsAppApiError
    from notifications.services.commands import _resolve_phone

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    phone = _resolve_phone(user)
    if not phone:
        return

    try:
        WhatsAppClient().send_text(f'57{phone}', text)
    except WhatsAppApiError as exc:
        logger.error('[agent-reply] no se pudo reenviar por WhatsApp a %s: %s', user.email, exc)


# Retencion de MetaWebhookEvent (FASE 6.1 integracion Meta Business). El campo
# `payload` guarda el evento crudo de Meta, que para los mensajes entrantes
# incluye el texto del cliente -- misma clase de dato que ChatMessage. Politica:
#   > 30 dias  -> se sanitiza el payload (se deja {}), la fila queda para auditoria
#   > 180 dias -> se borra la fila completa
# Sembrada como PeriodicTask diaria (migration 0009).
_META_EVENT_SANITIZE_AFTER_DAYS = 30
_META_EVENT_DELETE_AFTER_DAYS = 180


@shared_task(
    name='notifications.purge_meta_webhook_events',
    queue='notifications',
)
def purge_meta_webhook_events_task():
    from datetime import timedelta
    from notifications.models import MetaWebhookEvent

    now = timezone.now()
    delete_cutoff = now - timedelta(days=_META_EVENT_DELETE_AFTER_DAYS)
    sanitize_cutoff = now - timedelta(days=_META_EVENT_SANITIZE_AFTER_DAYS)

    deleted, _ = MetaWebhookEvent.objects.filter(received_at__lt=delete_cutoff).delete()
    sanitized = (
        MetaWebhookEvent.objects
        .filter(received_at__lt=sanitize_cutoff, received_at__gte=delete_cutoff)
        .exclude(payload={})
        .update(payload={})
    )
    logger.info(
        '[meta-events-purge] %s filas borradas (>%sd), %s payloads sanitizados (>%sd)',
        deleted, _META_EVENT_DELETE_AFTER_DAYS, sanitized, _META_EVENT_SANITIZE_AFTER_DAYS,
    )
    return {'deleted': deleted, 'sanitized': sanitized}
