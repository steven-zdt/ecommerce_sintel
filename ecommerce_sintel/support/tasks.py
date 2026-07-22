import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

# Fase 11 AI Core (Proactividad): horas sin actividad en una sala escalada a
# humano (ai_paused=True, Human Handoff de Fase 7) antes de que el asistente
# deje un mensaje de seguimiento proactivo.
_UNATTENDED_THRESHOLD_HOURS = 2
_PROACTIVE_SLUG = 'ticket_soporte_sin_seguimiento'


@shared_task
def notify_unattended_escalated_tickets() -> None:
    """
    Fase 11 AI Core (Proactividad): ChatRoom abiertas, escaladas a un humano
    (ai_paused=True) y sin ninguna actividad en _UNATTENDED_THRESHOLD_HOURS --
    el asistente deja un mensaje de seguimiento en la misma sala via el Event
    Bus (NotificationCommands.dispatch_notification -> AI_PROACTIVE_SLUGS).
    Dedupe por NotificationLog: cada sala se notifica una sola vez.
    """
    from notifications.services.commands import NotificationCommands
    from support.models import ChatRoom

    cutoff = timezone.now() - timedelta(hours=_UNATTENDED_THRESHOLD_HOURS)
    candidates = ChatRoom.objects.filter(
        status=ChatRoom.STATUS_OPEN,
        ai_paused=True,
        updated_at__lt=cutoff,
        is_deleted=False,
    ).select_related('user')

    notified = 0
    for room in candidates:
        sent = NotificationCommands.dispatch_notification_once(
            user=room.user,
            template_slug=_PROACTIVE_SLUG,
            context={'room_uuid': str(room.uuid)},
            dedupe_key=f'chatroom:{room.uuid}',
        )
        if sent:
            notified += 1

    if notified:
        logger.info(
            "notify_unattended_escalated_tickets: %s sala(s) escalada(s) sin seguimiento "
            "notificada(s) (inactivas desde antes de %s)", notified, cutoff,
        )
