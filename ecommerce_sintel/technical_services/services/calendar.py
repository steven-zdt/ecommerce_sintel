from collections import defaultdict
from datetime import timedelta

from technical_services.models import ServiceOperation, WorkingSchedule, WorkingException
from technical_services.services.operations import _visit_window

# Tope defensivo (dia+semana per Fase 4, se puede subir si Fase 4 agrega vista
# mensual mas adelante).
MAX_CALENDAR_RANGE_DAYS = 31


def build_calendar_feed(technicians, start_date, end_date):
    """
    Agregado de calendario (Fase 4, 2026-07-14): para cada tecnico en
    `technicians` y cada fecha en [start_date, end_date], su horario laboral (si
    existe), sus excepciones y sus ServiceOperation confirmadas -- en bulk (3
    queries totales, sin N+1 por tecnico), pensado para una vista de linea de
    tiempo tipo Google Calendar.

    No vive en TechnicianAvailabilityEngine a proposito: mezcla datos de negocio
    (cliente/orden) con disponibilidad -- el motor se mantiene puro/calculado
    (ver docstring de TechnicianAvailabilityEngine).
    """
    if end_date < start_date:
        raise ValueError("end_date debe ser igual o posterior a start_date.")
    if (end_date - start_date).days + 1 > MAX_CALENDAR_RANGE_DAYS:
        raise ValueError(f"El rango no puede superar {MAX_CALENDAR_RANGE_DAYS} dias.")

    technician_ids = [technician.id for technician in technicians]

    schedules_by_tech_weekday = {
        (schedule.technician_id, schedule.weekday): schedule
        for schedule in WorkingSchedule.objects.filter(
            technician_id__in=technician_ids, is_active=True, is_deleted=False,
        )
    }

    exceptions_by_tech = defaultdict(list)
    for exception in WorkingException.objects.filter(
        technician_id__in=technician_ids, is_deleted=False,
        start_date__lte=end_date, end_date__gte=start_date,
    ):
        exceptions_by_tech[exception.technician_id].append(exception)

    blocking_statuses = [
        choice[0] for choice in ServiceOperation.STATUS_CHOICES
        if choice[0] != ServiceOperation.CANCELLED
    ]
    operations_by_tech_date = defaultdict(list)
    operations = (
        ServiceOperation.objects.filter(
            technician_id__in=technician_ids,
            scheduled_date__range=(start_date, end_date),
            status__in=blocking_statuses, is_deleted=False,
        )
        .select_related('order__user')
        .order_by('scheduled_time')
    )
    for operation in operations:
        operations_by_tech_date[(operation.technician_id, operation.scheduled_date)].append(operation)

    technicians_out = []
    for technician in technicians:
        days = []
        current = start_date
        while current <= end_date:
            schedule = schedules_by_tech_weekday.get((technician.id, current.weekday()))
            day_exceptions = [
                exc for exc in exceptions_by_tech[technician.id]
                if exc.start_date <= current <= exc.end_date
            ]
            day_operations = operations_by_tech_date[(technician.id, current)]

            days.append({
                'date': current,
                'working_window': (
                    {'start': schedule.start_time, 'end': schedule.end_time} if schedule else None
                ),
                'exceptions': [
                    {
                        'exception_type': exc.exception_type,
                        'exception_type_display': exc.get_exception_type_display(),
                        'start_time': exc.start_time,
                        'end_time': exc.end_time,
                        'reason': exc.reason,
                    }
                    for exc in day_exceptions
                ],
                'operations': [
                    {
                        'uuid': str(op.uuid),
                        'start_time': _visit_window(op)[0],
                        'end_time': _visit_window(op)[1],
                        'estimated_duration_minutes': op.estimated_duration_minutes or 60,
                        'status': op.status,
                        'status_display': op.get_status_display(),
                        'order_uuid': str(op.order.uuid),
                        'customer_name': op.order.user.get_short_name() or op.order.user.email,
                        'priority': op.priority,
                    }
                    for op in day_operations
                ],
            })
            current += timedelta(days=1)

        technicians_out.append({
            'technician_id': technician.id,
            'technician_uuid': str(technician.uuid),
            'technician_name': technician.get_full_name() or technician.email,
            'days': days,
        })

    return {'start_date': start_date, 'end_date': end_date, 'technicians': technicians_out}
