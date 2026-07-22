from datetime import datetime, time, timedelta

from renting.models import EquipmentBlock, EquipmentVariant, RentalPeriod, RentalRequest


class AvailabilityEngine:
    """
    Motor de disponibilidad de RentalPeriod por solapamiento de intervalos.

    Reemplaza el chequeo binario disponible/ocupado por un algoritmo unificado que
    soporta reservas por dias (rango completo, sin horas) y por horas (mismo dia,
    con hora de entrega/recogida), mezclando ambos modos sobre la misma variante.
    """

    BLOCKING_STATUSES = [RentalPeriod.STATUS_SCHEDULED, RentalPeriod.STATUS_ACTIVE]

    @staticmethod
    def _period_range(start_date, end_date, rental_mode, start_time, end_time):
        """
        Normaliza un rango fecha(+hora) a un intervalo datetime comparable.

        Modo dias: medianoche a medianoche, end_date exclusivo (dos reservas de dia
        pueden compartir el dia de entrega/recogida sin solaparse, igual que el
        algoritmo original).
        Modo horas: fecha+hora exactas de entrega/recogida.
        """
        if rental_mode == RentalRequest.RENTAL_MODE_HOURS and start_time and end_time:
            return (
                datetime.combine(start_date, start_time),
                datetime.combine(end_date, end_time),
            )
        return (
            datetime.combine(start_date, time.min),
            datetime.combine(end_date, time.min),
        )

    @staticmethod
    def is_available(
        variant_id,
        start_date,
        end_date,
        quantity: int = 1,
        rental_mode: str = RentalRequest.RENTAL_MODE_DAYS,
        start_time=None,
        end_time=None,
        exclude_period_id=None,
    ) -> bool:
        """
        True si hay `quantity` unidades libres de `variant_id` para el rango pedido.

        Prefiltro en BD inclusivo en ambos extremos (start_date__lte/end_date__gte)
        seguido de un test exacto en Python via `_period_range`. El prefiltro
        exclusivo original (`__lt`/`__gt`) excluia incorrectamente pares de reservas
        por horas el mismo dia (start_date == end_date en ambas) antes de que la
        hora pudiera desempatar.
        """
        try:
            variant = EquipmentVariant.objects.only('stock').get(id=variant_id)
        except EquipmentVariant.DoesNotExist:
            return False

        stock_total: int = variant.stock
        if stock_total < quantity:
            return False

        new_start_dt, new_end_dt = AvailabilityEngine._period_range(
            start_date, end_date, rental_mode, start_time, end_time
        )

        candidates = RentalPeriod.objects.filter(
            equipment_variant_id=variant_id,
            status__in=AvailabilityEngine.BLOCKING_STATUSES,
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).only('id', 'start_date', 'end_date', 'start_time', 'end_time', 'rental_mode', 'quantity')

        if exclude_period_id is not None:
            candidates = candidates.exclude(pk=exclude_period_id)

        occupied = 0
        for period in candidates:
            existing_start_dt, existing_end_dt = AvailabilityEngine._period_range(
                period.start_date, period.end_date, period.rental_mode,
                period.start_time, period.end_time,
            )
            if existing_start_dt < new_end_dt and existing_end_dt > new_start_dt:
                occupied += period.quantity

        blocks = EquipmentBlock.objects.filter(
            equipment_variant_id=variant_id,
            status=EquipmentBlock.STATUS_ACTIVE,
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).only('start_date', 'end_date', 'quantity')

        for block in blocks:
            block_start_dt, block_end_dt = AvailabilityEngine._period_range(
                block.start_date, block.end_date, RentalRequest.RENTAL_MODE_DAYS, None, None,
            )
            if block_start_dt < new_end_dt and block_end_dt > new_start_dt:
                occupied += block.quantity

        return (stock_total - occupied) >= quantity

    @staticmethod
    def find_next_available_slot(
        variant_id,
        start_date,
        quantity: int = 1,
        rental_mode: str = RentalRequest.RENTAL_MODE_DAYS,
        duration_days: int = 1,
        start_time=None,
        end_time=None,
        search_horizon_days: int = 90,
    ) -> dict | None:
        """
        Barrido dia a dia desde `start_date` buscando el primer hueco libre,
        deslizando la misma duracion (dias) o la misma ventana horaria (horas).
        Retorna {'date': date, 'time': time|None} o None si no hay hueco en el
        horizonte de busqueda.
        """
        candidate_date = start_date
        span_days = max(duration_days, 1)

        for _ in range(search_horizon_days):
            if rental_mode == RentalRequest.RENTAL_MODE_HOURS:
                candidate_end_date = candidate_date
            else:
                candidate_end_date = candidate_date + timedelta(days=span_days)

            if AvailabilityEngine.is_available(
                variant_id, candidate_date, candidate_end_date, quantity,
                rental_mode, start_time, end_time,
            ):
                return {'date': candidate_date, 'time': start_time}

            candidate_date += timedelta(days=1)

        return None

    @staticmethod
    def generate_schedule(variant_id, range_start, range_end, statuses=None, include_blocks: bool = True) -> list[dict]:
        """
        Lista de periodos (dict) que se solapan con [range_start, range_end].
        `statuses` default: solo los bloqueantes (scheduled/active), para calendario.
        Pasar los 4 estados de RentalPeriod.STATUS_CHOICES para el timeline (historial).

        `include_blocks=True` (default) agrega los EquipmentBlock que se solapan con
        el rango, con la MISMA forma de dict (status='blocked') para que calendar/timeline
        los reflejen como no disponibles. No expone reason/created_by -- esos endpoints
        son AllowAny.
        """
        statuses = statuses or AvailabilityEngine.BLOCKING_STATUSES
        include_released_blocks = RentalPeriod.STATUS_CANCELLED in statuses

        periods = RentalPeriod.objects.filter(
            equipment_variant_id=variant_id,
            status__in=statuses,
            start_date__lte=range_end,
            end_date__gte=range_start,
        ).order_by('start_date')

        schedule = [
            {
                'start_date': p.start_date,
                'end_date': p.end_date,
                'start_time': p.start_time,
                'end_time': p.end_time,
                'rental_mode': p.rental_mode,
                'quantity': p.quantity,
                'status': p.status,
            }
            for p in periods
        ]

        if include_blocks:
            block_statuses = (
                [EquipmentBlock.STATUS_ACTIVE, EquipmentBlock.STATUS_RELEASED]
                if include_released_blocks else [EquipmentBlock.STATUS_ACTIVE]
            )
            blocks = EquipmentBlock.objects.filter(
                equipment_variant_id=variant_id,
                status__in=block_statuses,
                start_date__lte=range_end,
                end_date__gte=range_start,
            ).order_by('start_date')

            schedule.extend([
                {
                    'start_date': b.start_date,
                    'end_date': b.end_date,
                    'start_time': None,
                    'end_time': None,
                    'rental_mode': RentalRequest.RENTAL_MODE_DAYS,
                    'quantity': b.quantity,
                    'status': 'blocked' if b.status == EquipmentBlock.STATUS_ACTIVE else 'block_released',
                }
                for b in blocks
            ])
            schedule.sort(key=lambda row: row['start_date'])

        return schedule
