import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


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


# ─── Fase 7 AI Core: canal WhatsApp entrante + Event Bus proactivo ───────────

@shared_task(
    bind=True,
    max_retries=1,
    default_retry_delay=30,
    name='notifications.process_whatsapp_inbound',
    queue='notifications',
    acks_late=True,
)
def process_whatsapp_inbound_task(self, wa_id: str, text: str):
    """
    Mensaje entrante de WhatsApp -> Action Graph -> respuesta por WhatsApp.
    El usuario se resuelve por los ultimos 10 digitos del telefono del
    UserProfile (celular colombiano); si no hay match, se ignora con log
    (no se responde a numeros desconocidos).
    """
    from accounts.models import UserProfile
    from notifications.clients.whatsapp import WhatsAppClient, WhatsAppApiError
    from support.services.ai_bridge import ask_ai

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
        return

    ai_response = ask_ai(profile.user, text, conversation_id=f'wa-{profile.user_id}')
    reply = (ai_response or {}).get('response') or ''
    if not reply.strip():
        logger.warning('[wa-inbound] AI sin respuesta para user=%s', profile.user.email)
        return

    try:
        WhatsAppClient().send_text(wa_id, reply)
    except WhatsAppApiError as exc:
        # Config/token de Meta invalido: se registra, no se reintenta en loop.
        logger.error('[wa-inbound] no se pudo responder por WhatsApp: %s', exc)


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
    """
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    from django.contrib.auth import get_user_model
    from support.services.ai_bridge import get_ai_bot_user
    from support.services.commands import ChatCommands

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
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
    # group_send plano (mismo formato que SupportChatConsumer.chat_message) --
    # ws_notify envuelve en 'payload' y el handler del consumer no lo entiende.
    layer = get_channel_layer()
    if layer is not None:
        async_to_sync(layer.group_send)(f'chat_{str(user.uuid)}', {
            'type': 'chat.message',
            'message': text,
            'sender_email': bot.email,
            'is_admin': True,
            'room_uuid': str(room.uuid),
            'created_at': msg.created_at.isoformat(),
        })
    logger.info('[ai-proactive] mensaje en sala %s por slug=%s', room.uuid, template_slug)
