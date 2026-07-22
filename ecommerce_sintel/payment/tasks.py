import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from payment.models import Transaction, TransactionEvent

logger = logging.getLogger(__name__)

# ADR-001 Fase 6: umbral para considerar una Transaction sin wompi_id como
# "abandonada" en vez de simplemente "todavia en curso" -- suficientemente
# largo para no marcar transacciones que un usuario normal completaria en el
# widget en menos de un par de minutos.
_ABANDONED_THRESHOLD_MINUTES = 30
_ABANDONED_MARKER = "Transaccion abandonada"


@shared_task
def reconcile_pending_wompi_transactions() -> None:
    """
    Reconciliacion periodica (Celery beat) para Transactions Wompi que quedaron
    PENDING sin que llegara webhook ni el usuario volviera a consultar
    /payment/result -- pestana cerrada, navegador colgado, etc.

    Dos pasadas:
    1. Transactions con wompi_id ya conocido: se consultan de verdad contra la
       API de Wompi (GET /transactions/{id}).
    2. (ADR-001 Fase 6) Transactions SIN wompi_id, ya viejas: Wompi no ofrece
       endpoint de busqueda por 'reference', asi que NO se pueden reconciliar
       de verdad -- se marcan con un TransactionEvent (una sola vez, no se
       repite en cada corrida) para que dejen de estar invisibles y un admin
       (panel de pagos, Fase 7) pueda encontrarlas y decidir manualmente.
    """
    from payment.online.api.views import _sync_wompi_status

    now = timezone.now()

    stale = Transaction.objects.filter(
        status="PENDING",
        wompi_id__isnull=False,
        created_at__lt=now - timedelta(minutes=1),
    )
    count = stale.count()
    if count:
        logger.info("reconcile_pending_wompi_transactions: revisando %s transaccion(es) pendientes", count)
        for wompi_tx in stale:
            _sync_wompi_status(wompi_tx)

    abandoned = Transaction.objects.filter(
        status="PENDING",
        wompi_id__isnull=True,
        created_at__lt=now - timedelta(minutes=_ABANDONED_THRESHOLD_MINUTES),
    ).exclude(
        events__source=TransactionEvent.SOURCE_API_SYNC,
        events__error_detail__icontains=_ABANDONED_MARKER,
    )
    abandoned_count = abandoned.count()
    if abandoned_count:
        # ADR-001 Fase 8 (alertas operativas): se reusa SecurityEvent -- ya
        # visible en /panel/seguridad -- en vez de dispatch_notification, para
        # no arriesgar notificar por error al CLIENTE (dispatch_notification
        # resuelve canales/email a partir del 'user' que se le pase; esta
        # tarea de background no tiene un admin especifico a quien atribuir el
        # evento, y el 'user' de la transaccion es el CLIENTE, no un admin --
        # ver decision explicita en Fase 6 de no notificar al cliente aqui).
        from security.models import SecurityEvent
        from security.services.commands import SecurityCommands

        for wompi_tx in abandoned:
            TransactionEvent.objects.create(
                transaction=wompi_tx, source=TransactionEvent.SOURCE_API_SYNC,
                previous_status="PENDING", new_status="",
                correlation_id=wompi_tx.correlation_id, processed=False,
                error_detail=(
                    f"{_ABANDONED_MARKER}: sin wompi_id tras "
                    f"{_ABANDONED_THRESHOLD_MINUTES} minutos. Wompi no ofrece "
                    "busqueda por reference, no se puede reconciliar automaticamente."
                ),
            )
            SecurityCommands.log_event(
                SecurityEvent.PAYMENT_TRANSACTION_ABANDONED, severity=SecurityEvent.SEVERITY_WARNING,
                metadata={
                    'transaction_uuid': str(wompi_tx.uuid),
                    'correlation_id': wompi_tx.correlation_id,
                    'order': str(wompi_tx.order.uuid) if wompi_tx.order_id else None,
                    'rental_request': str(wompi_tx.rental_request.uuid) if wompi_tx.rental_request_id else None,
                    'minutes_pending': _ABANDONED_THRESHOLD_MINUTES,
                },
            )
        logger.warning(
            "reconcile_pending_wompi_transactions: %s transaccion(es) abandonada(s) sin wompi_id marcada(s) para revision",
            abandoned_count,
        )


# Fase 11 AI Core (Proactividad): ventana reciente de pagos rechazados a
# revisar en cada corrida (la tarea corre cada hora -- ver migracion
# 0009_seed_notify_declined_payments_periodic_task).
_DECLINED_FOLLOWUP_WINDOW_HOURS = 24
_PROACTIVE_SLUG = 'pago_rechazado_seguimiento'


@shared_task
def notify_declined_payments_followup() -> None:
    """
    Fase 11 AI Core (Proactividad): Transactions DECLINED recientes -- el
    asistente deja un mensaje proactivo en la sala de soporte del cliente via
    el Event Bus (NotificationCommands.dispatch_notification ->
    AI_PROACTIVE_SLUGS), ofreciendo ayuda para reintentar el pago. Dedupe por
    NotificationLog: cada transaccion se notifica una sola vez.
    """
    from notifications.services.commands import NotificationCommands

    cutoff = timezone.now() - timedelta(hours=_DECLINED_FOLLOWUP_WINDOW_HOURS)
    candidates = Transaction.objects.filter(
        status="DECLINED",
        updated_at__gte=cutoff,
        is_deleted=False,
    ).select_related('order__user', 'rental_request__user')

    notified = 0
    for tx in candidates:
        user = tx.order.user if tx.order_id else tx.rental_request.user
        sent = NotificationCommands.dispatch_notification_once(
            user=user,
            template_slug=_PROACTIVE_SLUG,
            context={'transaction_uuid': str(tx.uuid), 'status': tx.status},
            dedupe_key=f'transaction:{tx.uuid}',
        )
        if sent:
            notified += 1

    if notified:
        logger.info(
            "notify_declined_payments_followup: %s transaccion(es) declinada(s) notificada(s) "
            "(desde %s)", notified, cutoff,
        )
