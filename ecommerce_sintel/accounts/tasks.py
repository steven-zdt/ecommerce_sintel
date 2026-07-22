"""
Tareas Celery para el módulo de disponibilidad de contratistas.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name='accounts.release_expired_slot',
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # Reintenta en 60 seg si falla
    acks_late=True,           # Confirmar solo tras ejecucion exitosa
)
def release_expired_slot(self, slot_id: int):
    """
    Libera un slot que lleva 15 minutos en estado PENDING_RESERVATION.
    Si el slot ya fue confirmado (BOOKED) o liberado manualmente, no hace nada.
    """
    from accounts.models import ProfessionalAvailability

    try:
        slot = ProfessionalAvailability.objects.get(id=slot_id, is_deleted=False)
    except ProfessionalAvailability.DoesNotExist:
        logger.info("[availability:task] Slot %d no existe o fue eliminado. Sin accion.", slot_id)
        return

    if slot.status != ProfessionalAvailability.PENDING_RESERVATION:
        logger.info(
            "[availability:task] Slot %d ya en estado '%s'. Sin accion.",
            slot_id, slot.status,
        )
        return

    from accounts.services.commands import AvailabilityCommands
    AvailabilityCommands.release_booking(slot_id)
    logger.info("[availability:task] Slot %d liberado automaticamente por expiracion.", slot_id)
