from datetime import datetime, timedelta
from decimal import Decimal

from technical_services.models import ServiceOperation, WorkingException, WorkingSchedule
from technical_services.services.operations import _visit_window

# Tope defensivo para capacity_summary_range() -- evita un loop dia-a-dia
# desbocado si alguien pide un rango enorme por error (un trimestre generoso).
MAX_SUMMARY_RANGE_DAYS = 92


class TechnicianAvailabilityEngine:
    """
    Fuente unica de verdad de disponibilidad de tecnicos (2026-07-14, Fase 2 del
    proyecto TechnicianAvailabilityEngine). Todo se calcula en el momento, nunca se
    almacena un booleano de disponibilidad -- ver auditoria en memoria del proyecto
    (project_technician_availability_engine_audit) para el porque.

    Disponibilidad = Horario laboral (WorkingSchedule) - Servicios confirmados
    (ServiceOperation, calculado -- NO existe una tabla ServiceSlot separada, seria
    la misma duplicacion que ya causo problemas con ServiceBooking) - Ausencias
    (WorkingException: vacaciones/permiso/incapacidad/capacitacion/mantenimiento).

    Fase 2 es aditiva: NO reemplaza TechnicianProfile.is_available,
    accounts.ProfessionalAvailability ni technical_services.ServiceBooking todavia
    -- esos 3 sistemas existentes siguen funcionando exactamente igual. Este motor
    es un camino de lectura nuevo, en paralelo, para que los siguientes fases lo
    vayan adoptando gradualmente.
    """

    # Todo estado de ServiceOperation "ocupa" agenda salvo CANCELLED -- COMPLETED
    # cuenta porque, si ya paso, la hora efectivamente se uso ese dia.
    BLOCKING_OPERATION_STATUSES = [
        choice[0] for choice in ServiceOperation.STATUS_CHOICES
        if choice[0] != ServiceOperation.CANCELLED
    ]

    @staticmethod
    def get_working_window(technician_id, date):
        """(start_time, end_time) del WorkingSchedule activo para ese dia de la
        semana, o (None, None) si el tecnico no tiene horario ese dia."""
        schedule = WorkingSchedule.objects.filter(
            technician_id=technician_id, weekday=date.weekday(),
            is_active=True, is_deleted=False,
        ).first()
        if schedule is None:
            return None, None
        return schedule.start_time, schedule.end_time

    @staticmethod
    def get_exceptions(technician_id, date):
        """WorkingException que se solapan con `date` (start_date<=date<=end_date)."""
        return WorkingException.objects.filter(
            technician_id=technician_id, start_date__lte=date, end_date__gte=date,
            is_deleted=False,
        )

    @staticmethod
    def get_extra_hours(technician_id, date):
        """
        Ventanas de EXTRA_HOURS (Fase 6) para `date`, como lista de
        (start_time, end_time) -- la unica excepcion que SUMA en vez de restar.
        """
        return [
            (exc.start_time, exc.end_time)
            for exc in TechnicianAvailabilityEngine.get_exceptions(technician_id, date)
            if exc.exception_type == WorkingException.TYPE_EXTRA_HOURS
            and exc.start_time is not None and exc.end_time is not None
        ]

    @staticmethod
    def get_confirmed_slots(technician_id, date):
        """
        'ServiceSlot' calculado: ventanas ocupadas por ServiceOperation confirmadas
        ese dia para ese tecnico. Reusa _visit_window() (operations.py) -- no
        duplica el calculo de duracion.
        """
        operations = ServiceOperation.objects.filter(
            technician_id=technician_id, scheduled_date=date,
            status__in=TechnicianAvailabilityEngine.BLOCKING_OPERATION_STATUSES,
            is_deleted=False,
        )
        slots = []
        for operation in operations:
            start_time, end_time = _visit_window(operation)
            if start_time is not None and end_time is not None:
                slots.append((start_time, end_time))
        return slots

    @staticmethod
    def _subtract_interval(intervals, sub_start, sub_end):
        """Resta [sub_start, sub_end) de cada intervalo de `intervals`."""
        result = []
        for start, end in intervals:
            if sub_end <= start or sub_start >= end:
                result.append((start, end))
                continue
            if sub_start > start:
                result.append((start, sub_start))
            if sub_end < end:
                result.append((sub_end, end))
        return result

    @staticmethod
    def free_windows(technician_id, date):
        """
        (Horario laboral + Horas extra) MENOS ausencias MENOS servicios
        confirmados, como lista de (start_time, end_time) libres.

        EXTRA_HOURS (Fase 6) es la unica excepcion que SUMA: se agrega como
        base de disponibilidad junto al horario laboral (incluso si el
        tecnico no trabaja ese dia -- ej. lo llaman en su dia libre) ANTES de
        restar las demas ausencias/servicios, para que una ausencia de dia
        completo tambien anule las horas extra de ese mismo dia.
        """
        working_start, working_end = TechnicianAvailabilityEngine.get_working_window(technician_id, date)
        intervals = [(working_start, working_end)] if working_start is not None else []
        intervals += TechnicianAvailabilityEngine.get_extra_hours(technician_id, date)
        if not intervals:
            return []

        reducing_exceptions = [
            exc for exc in TechnicianAvailabilityEngine.get_exceptions(technician_id, date)
            if exc.exception_type != WorkingException.TYPE_EXTRA_HOURS
        ]
        for exception in reducing_exceptions:
            if exception.start_time is None or exception.end_time is None:
                return []  # ausencia de dia completo: no queda nada libre
            intervals = TechnicianAvailabilityEngine._subtract_interval(
                intervals, exception.start_time, exception.end_time,
            )
            if not intervals:
                return []

        for slot_start, slot_end in TechnicianAvailabilityEngine.get_confirmed_slots(technician_id, date):
            intervals = TechnicianAvailabilityEngine._subtract_interval(intervals, slot_start, slot_end)
            if not intervals:
                return []

        return intervals

    @staticmethod
    def is_available(technician_id, date, start_time, end_time):
        """True si [start_time, end_time) cabe entero dentro de algun hueco libre."""
        return any(
            start <= start_time and end_time <= end
            for start, end in TechnicianAvailabilityEngine.free_windows(technician_id, date)
        )

    @staticmethod
    def _window_hours(date, windows):
        total = Decimal('0')
        for start, end in windows:
            delta = datetime.combine(date, end) - datetime.combine(date, start)
            total += Decimal(delta.total_seconds()) / Decimal(3600)
        return total

    @staticmethod
    def occupied_hours(technician_id, date):
        """Suma de duracion de servicios confirmados ese dia (sin contar ausencias)."""
        slots = TechnicianAvailabilityEngine.get_confirmed_slots(technician_id, date)
        return TechnicianAvailabilityEngine._window_hours(date, slots)

    @staticmethod
    def _candidates(category=None):
        from technical_services.services.selectors import TechnicianSelector
        if category is not None:
            return TechnicianSelector.get_active_technicians_for_category(category)
        return TechnicianSelector.get_all_active_technicians()

    @staticmethod
    def _best_slot_in_windows(date, windows, duration_minutes, preferred_time):
        """
        Mejor hueco dentro de `windows` que cubra `duration_minutes`. Si
        `preferred_time` cabe dentro de una ventana, se usa como inicio
        (preferido sobre cualquier ventana que no lo respete, incluso si esa
        empieza mas temprano); si no cabe, se usa el inicio natural de la
        ventana. Retorna (start_time, end_time) o None si ninguna ventana
        alcanza para la duracion pedida.
        """
        best = None  # (start_time, end_time, matches_pref)
        for start, end in windows:
            window_end_dt = datetime.combine(date, end)

            slot_start = start
            if preferred_time is not None and preferred_time > start:
                preferred_start_dt = datetime.combine(date, preferred_time)
                if preferred_start_dt + timedelta(minutes=duration_minutes) <= window_end_dt:
                    slot_start = preferred_time

            slot_start_dt = datetime.combine(date, slot_start)
            slot_end_dt = slot_start_dt + timedelta(minutes=duration_minutes)
            if slot_end_dt > window_end_dt:
                continue  # ni el inicio natural de la ventana alcanza para la duracion

            matches_pref = preferred_time is not None and slot_start == preferred_time
            candidate = (slot_start, slot_end_dt.time(), matches_pref)
            if (
                best is None
                or (candidate[2] and not best[2])
                or (candidate[2] == best[2] and candidate[0] < best[0])
            ):
                best = candidate
        return (best[0], best[1]) if best else None

    @staticmethod
    def find_next_available_technician(start_date, duration_minutes, category=None,
                                        preferred_time=None, search_horizon_days=7):
        """
        Barre dia a dia desde start_date (hasta search_horizon_days) buscando el
        primer tecnico+hueco que cubra duration_minutes. Solo lectura -- no
        reserva nada, la mutacion real la hace el caller (ver
        ServiceOperationCommands.try_auto_assign_via_engine).
        """
        candidate_date = start_date
        for _ in range(search_horizon_days):
            best_overall = None  # (technician, start_time, end_time, matches_pref)
            for technician in TechnicianAvailabilityEngine._candidates(category):
                windows = TechnicianAvailabilityEngine.free_windows(technician.id, candidate_date)
                slot = TechnicianAvailabilityEngine._best_slot_in_windows(
                    candidate_date, windows, duration_minutes, preferred_time,
                )
                if slot is None:
                    continue
                slot_start, slot_end = slot
                matches_pref = preferred_time is not None and slot_start == preferred_time
                if (
                    best_overall is None
                    or (matches_pref and not best_overall[3])
                    or (matches_pref == best_overall[3] and slot_start < best_overall[1])
                ):
                    best_overall = (technician, slot_start, slot_end, matches_pref)

            if best_overall:
                technician, slot_start, slot_end, _ = best_overall
                return {
                    'technician_id': technician.id,
                    'technician_uuid': str(technician.uuid),
                    'technician_name': technician.get_full_name() or technician.email,
                    'date': candidate_date,
                    'start_time': slot_start,
                    'end_time': slot_end,
                }
            candidate_date += timedelta(days=1)

        return None

    @staticmethod
    def list_available_technicians(date, start_time, end_time, category=None):
        """
        Candidatos activos (filtrados por category si se pasa, SIN depender de
        TechnicianProfile.is_available) evaluados con is_available(). Nunca
        devuelve tecnicos ocupados -- regla explicita del usuario.
        """
        results = []
        for technician in TechnicianAvailabilityEngine._candidates(category):
            windows = TechnicianAvailabilityEngine.free_windows(technician.id, date)
            fits = any(start <= start_time and end_time <= end for start, end in windows)
            if fits:
                results.append({
                    'technician_id': technician.id,
                    'technician_uuid': str(technician.uuid),
                    'technician_name': technician.get_full_name() or technician.email,
                    'free_windows': windows,
                })
        return results

    @staticmethod
    def capacity_summary(date, category=None):
        """
        Agregado de capacidad para `date` sobre los tecnicos activos (filtrados por
        category si se pasa). 'occupied_hours' = capacity_hours - free_hours
        (incluye servicios confirmados Y ausencias, es el numero unico que muestra
        el dashboard); occupied_hours() por separado da solo servicios confirmados.
        """
        technicians_total = 0
        technicians_available = 0
        capacity_hours = Decimal('0')
        free_hours = Decimal('0')

        for technician in TechnicianAvailabilityEngine._candidates(category):
            working_start, working_end = TechnicianAvailabilityEngine.get_working_window(technician.id, date)
            extra_hours_windows = TechnicianAvailabilityEngine.get_extra_hours(technician.id, date)
            if working_start is None and not extra_hours_windows:
                continue  # el tecnico no trabaja ese dia ni tiene horas extra -- no cuenta en la capacidad

            technicians_total += 1
            if working_start is not None:
                capacity_hours += TechnicianAvailabilityEngine._window_hours(date, [(working_start, working_end)])
            capacity_hours += TechnicianAvailabilityEngine._window_hours(date, extra_hours_windows)

            windows = TechnicianAvailabilityEngine.free_windows(technician.id, date)
            free_hours += TechnicianAvailabilityEngine._window_hours(date, windows)
            if windows:
                technicians_available += 1

        return {
            'date': date,
            'technicians_total': technicians_total,
            'technicians_available': technicians_available,
            'technicians_busy': technicians_total - technicians_available,
            'capacity_hours': capacity_hours,
            'free_hours': free_hours,
            'occupied_hours': capacity_hours - free_hours,
        }

    @staticmethod
    def capacity_summary_range(start_date, end_date, category=None):
        """
        Ocupacion por semana/mes (Fase 3): capacity_summary() dia a dia sobre
        [start_date, end_date] mas los totales del rango. Simple loop sobre el
        calculo ya existente -- sin modelo ni query nuevos.
        """
        if end_date < start_date:
            raise ValueError("end_date debe ser igual o posterior a start_date.")
        span_days = (end_date - start_date).days + 1
        if span_days > MAX_SUMMARY_RANGE_DAYS:
            raise ValueError(f"El rango no puede superar {MAX_SUMMARY_RANGE_DAYS} dias.")

        days = []
        current = start_date
        while current <= end_date:
            days.append(TechnicianAvailabilityEngine.capacity_summary(current, category))
            current += timedelta(days=1)

        totals = {
            'capacity_hours': sum((d['capacity_hours'] for d in days), Decimal('0')),
            'free_hours': sum((d['free_hours'] for d in days), Decimal('0')),
            'occupied_hours': sum((d['occupied_hours'] for d in days), Decimal('0')),
        }

        return {
            'start_date': start_date,
            'end_date': end_date,
            'days': days,
            'totals': totals,
        }
