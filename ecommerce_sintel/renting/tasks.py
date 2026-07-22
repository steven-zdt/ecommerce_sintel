import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from renting.models import RentalRequest

logger = logging.getLogger(__name__)

# pending_payment nunca bloquea agenda (Fase 1 del Plan Maestro de Renting,
# 2026-07-07), asi que no hay urgencia de liberacion como con un carrito con
# stock reservado -- este umbral es solo limpieza operativa (que las
# solicitudes verdaderamente abandonadas dejen de aparecer como "pendientes"
# en el panel admin), no una carrera de disponibilidad.
_ABANDONED_THRESHOLD_HOURS = 48


@shared_task
def expire_abandoned_pending_payment_requests() -> None:
    """
    Reconciliacion periodica (Celery beat) para RentalRequest que quedaron en
    pending_payment sin que el cliente completara el pago (Wompi/Nequi/COD) ni
    la cancelara -- pestana cerrada, abandono del flujo, etc.

    Reusa RentalRequestCommands.release_on_payment_failure(), el mismo comando
    que usan los webhooks de Wompi/Nequi ante un pago rechazado: idempotente
    (no-op si la solicitud ya esta en un estado resuelto), y normalmente no-op
    sobre RentalPeriod porque pending_payment nunca crea uno.
    """
    from renting.services.commands import RentalRequestCommands

    cutoff = timezone.now() - timedelta(hours=_ABANDONED_THRESHOLD_HOURS)
    abandoned = RentalRequest.objects.filter(
        status=RentalRequest.STATUS_PENDING_PAYMENT,
        created_at__lt=cutoff,
    )
    count = abandoned.count()
    if not count:
        return

    logger.info(
        "expire_abandoned_pending_payment_requests: cancelando %s solicitud(es) "
        "abandonada(s) en pending_payment (creadas antes de %s)", count, cutoff,
    )
    for rental_request in abandoned:
        RentalRequestCommands.release_on_payment_failure(rental_request)


# Fase 11 AI Core (Proactividad): dias de antelacion antes del end_date en que
# el asistente escribe proactivamente al cliente avisando el vencimiento.
_EXPIRING_SOON_THRESHOLD_DAYS = 3
_PROACTIVE_SLUG = 'renting_por_vencer'


@shared_task
def notify_rentals_expiring_soon() -> None:
    """
    Fase 11 AI Core (Proactividad): RentalPeriod activos cuyo end_date cae
    dentro de _EXPIRING_SOON_THRESHOLD_DAYS -- el asistente deja un mensaje
    proactivo en la sala de soporte del cliente via el Event Bus
    (NotificationCommands.dispatch_notification -> AI_PROACTIVE_SLUGS).
    Dedupe por NotificationLog: cada periodo se notifica una sola vez.
    """
    from notifications.services.commands import NotificationCommands
    from renting.models import RentalPeriod

    today = timezone.localdate()
    horizon = today + timedelta(days=_EXPIRING_SOON_THRESHOLD_DAYS)
    candidates = RentalPeriod.objects.filter(
        status=RentalPeriod.STATUS_ACTIVE,
        end_date__range=(today, horizon),
        is_deleted=False,
    ).select_related('rental_request__user')

    notified = 0
    for period in candidates:
        sent = NotificationCommands.dispatch_notification_once(
            user=period.rental_request.user,
            template_slug=_PROACTIVE_SLUG,
            context={'rental_period_uuid': str(period.uuid), 'end_date': str(period.end_date)},
            dedupe_key=f'rental_period:{period.uuid}',
        )
        if sent:
            notified += 1

    if notified:
        logger.info(
            "notify_rentals_expiring_soon: %s periodo(s) notificado(s) "
            "(vencen antes de %s)", notified, horizon,
        )
