from renting.models import RentalRequest, RentalPeriod

# Vocabulario de 7 estados visibles para el cliente/admin (Plan Maestro Fase 1).
# Traduce los estados internos de RentalRequest/RentalPeriod sin agregar columnas nuevas.
# "Disponible" no aparece aqui: es una propiedad de un dia del calendario sin periodos
# bloqueantes, no un estado de RentalRequest/RentalPeriod (ver renting/services/availability.py).

_REQUEST_DISPLAY_STATUS = {
    RentalRequest.STATUS_DRAFT: 'Borrador',
    RentalRequest.STATUS_PENDING_VALIDATION: 'Pendiente de aprobacion',
    RentalRequest.STATUS_PENDING_PAYMENT: 'Pendiente de pago',
    RentalRequest.STATUS_PAID: 'Programado',
    RentalRequest.STATUS_CONFIRMED: 'Programado',
    RentalRequest.STATUS_IN_OPERATION: 'En operacion',
    RentalRequest.STATUS_FINISHED: 'Finalizado',
    RentalRequest.STATUS_CANCELLED: 'Cancelado',
    RentalRequest.STATUS_PAYMENT_CONFLICT: 'Conflicto de pago',
}

_PERIOD_DISPLAY_STATUS = {
    RentalPeriod.STATUS_SCHEDULED: 'Programado',
    RentalPeriod.STATUS_ACTIVE: 'En operacion',
    RentalPeriod.STATUS_COMPLETED: 'Finalizado',
    RentalPeriod.STATUS_CANCELLED: 'Cancelado',
}


def display_status_for_request(rental_request: RentalRequest) -> str:
    return _REQUEST_DISPLAY_STATUS.get(rental_request.status, rental_request.status)


def display_status_for_period(period: RentalPeriod) -> str:
    return _PERIOD_DISPLAY_STATUS.get(period.status, period.status)
