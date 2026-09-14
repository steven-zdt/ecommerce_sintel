import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

# Fase 14 (AUDITORIA/28_AUDITORIA_OPERATIONS.md, 2026-08-03): OperationTicket no tenia NINGUNA
# alerta de estancamiento -- a diferencia de orders/payment/renting/support (que si tienen su
# propio PeriodicTask equivalente vs cache/dedupe), un ticket podia quedar indefinidamente en
# ASSIGNED/SCHEDULED/EN_ROUTE (tecnico que nunca se presenta) sin que nadie se enterara. Umbral
# mas largo que el de soporte (2h) porque estas son operaciones fisicas de campo, no un chat.
_STALE_THRESHOLD_HOURS = 48
_STALE_STATUSES = ('ASSIGNED', 'SCHEDULED', 'EN_ROUTE')
_STALE_TICKET_SLUG = 'operacion_estancada'


@shared_task
def notify_stale_operation_tickets() -> None:
    """
    OperationTicket con status ASSIGNED/SCHEDULED/EN_ROUTE y sin ningun avance
    (updated_at) en _STALE_THRESHOLD_HOURS -- se notifica al tecnico/despachador
    activo asignado. Dedupe por NotificationLog via dispatch_notification_once:
    cada ticket se notifica una sola vez mientras siga estancado (mismo patron
    que support.tasks.notify_unattended_escalated_tickets).
    """
    from notifications.services.commands import NotificationCommands
    from operations.models import OperationTicket, OperationAssignment

    cutoff = timezone.now() - timedelta(hours=_STALE_THRESHOLD_HOURS)
    candidates = (
        OperationTicket.objects
        .filter(status__in=_STALE_STATUSES, updated_at__lt=cutoff, is_deleted=False)
        .prefetch_related('assignments__assignee')
    )

    notified = 0
    for ticket in candidates:
        assignee = next(
            (a.assignee for a in ticket.assignments.all()
             if a.status == OperationAssignment.STATUS_ACTIVE),
            None,
        )
        if assignee is None:
            continue

        sent = NotificationCommands.dispatch_notification_once(
            user=assignee,
            template_slug=_STALE_TICKET_SLUG,
            context={'ticket_number': ticket.ticket_number, 'operation_uuid': str(ticket.uuid)},
            dedupe_key=f'operationticket:{ticket.uuid}',
        )
        if sent:
            notified += 1

    if notified:
        logger.info(
            "notify_stale_operation_tickets: %s ticket(s) estancado(s) notificado(s) "
            "(sin avance desde antes de %s)", notified, cutoff,
        )
