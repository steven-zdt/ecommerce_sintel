# Extraido de accounts/services/commands.py -- Sprint 3 (2026-08-05, auditoria
# transversal): AvailabilityCommands es un dominio propio (agenda de disponibilidad
# de profesionales) sin relacion con la logica de identidad/auth de AccountCommands,
# a diferencia de CustomerPasswordResetCommands (que si se quedo en commands.py por
# depender directo de AccountCommands._blacklist_all_refresh_tokens). Reexportado
# desde commands.py para que los ~10 call sites existentes (accounts/tasks.py,
# accounts/api/views.py, technical_services/services/*.py) no necesiten cambiar su
# import.
import logging
from django.db import transaction
from rest_framework.exceptions import ValidationError

from accounts.models import ProfessionalAvailability

logger = logging.getLogger(__name__)


class AvailabilityCommands:
    """
    Gestiona el ciclo de vida de los slots de disponibilidad profesional.
    """

    @staticmethod
    @transaction.atomic
    def create_availability_blocks(
        user_profile: "UserProfile",
        start_date,
        end_date,
        work_start_hour: int = 8,
        work_end_hour: int = 18,
        slot_duration_hours: int = 2,
        exclude_weekends: bool = True,
        notes: str = "",
    ) -> list:
        """
        Genera bloques de disponibilidad para un rango de fechas.
        Retorna la lista de slots creados (ignora duplicados por unique_together).
        """
        import datetime
        from datetime import date as date_type, timedelta

        if isinstance(start_date, str):
            start_date = date_type.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = date_type.fromisoformat(end_date)

        if start_date > end_date:
            raise ValidationError("La fecha de inicio debe ser anterior o igual a la fecha de fin.")
        if slot_duration_hours <= 0:
            raise ValidationError("La duracion del slot debe ser mayor a 0 horas.")
        if work_start_hour >= work_end_hour:
            raise ValidationError("La hora de inicio del turno debe ser anterior a la hora de fin.")

        # Obtener combinaciones existentes
        existing_slots = ProfessionalAvailability.objects.filter(
            user_profile=user_profile,
            date__range=(start_date, end_date),
            is_deleted=False
        ).values_list('date', 'start_time')
        existing_set = {(d, t) for d, t in existing_slots}

        slots_to_create = []
        current = start_date
        while current <= end_date:
            # 5=Sabado, 6=Domingo
            if exclude_weekends and current.weekday() >= 5:
                current += timedelta(days=1)
                continue

            slot_start = work_start_hour
            while slot_start + slot_duration_hours <= work_end_hour:
                t_start = datetime.time(slot_start, 0)
                t_end   = datetime.time(slot_start + slot_duration_hours, 0)
                if (current, t_start) not in existing_set:
                    slots_to_create.append(
                        ProfessionalAvailability(
                            user_profile=user_profile,
                            date=current,
                            start_time=t_start,
                            end_time=t_end,
                            status=ProfessionalAvailability.AVAILABLE,
                            notes=notes,
                        )
                    )
                slot_start += slot_duration_hours

            current += timedelta(days=1)

        # ignore_conflicts=True respeta el unique_together y omite duplicados
        created = ProfessionalAvailability.objects.bulk_create(
            slots_to_create, ignore_conflicts=True
        )
        logger.info(
            "[availability:bulk_create] %d slots generados para %s (%s a %s)",
            len(created), user_profile, start_date, end_date,
        )
        return created

    @staticmethod
    @transaction.atomic
    def lock_slot_temporarily(
        slot_id: int,
        requesting_user,
    ) -> ProfessionalAvailability:
        """
        Bloquea un slot de forma pesimista (select_for_update) y programa
        su liberacion automatica a los 15 minutos via Celery.
        Lanza ValidationError si el slot no esta disponible.
        """
        slot_id = int(slot_id)
        try:
            slot = (
                ProfessionalAvailability.objects
                .select_for_update()
                .get(
                    id=slot_id,
                    status=ProfessionalAvailability.AVAILABLE,
                    is_deleted=False,
                )
            )
        except ProfessionalAvailability.DoesNotExist:
            raise ValidationError(
                "El slot seleccionado ya no esta disponible. Por favor elige otro horario."
            )

        slot.status    = ProfessionalAvailability.PENDING_RESERVATION
        slot.booked_by = requesting_user
        slot.save(update_fields=['status', 'booked_by', 'updated_at'])

        logger.info(
            "[availability:lock] Slot %d bloqueado temporalmente por %s",
            slot_id, requesting_user.email,
        )

        # Programar liberacion automatica: se ejecuta dentro del on_commit
        # para garantizar que el slot ya este en BD antes de que la tarea corra.
        from accounts.tasks import release_expired_slot
        transaction.on_commit(
            lambda: release_expired_slot.apply_async(
                args=[slot_id], countdown=900  # 15 minutos
            )
        )
        return slot

    @staticmethod
    @transaction.atomic
    def confirm_booking(slot_id: int) -> ProfessionalAvailability:
        """
        Confirma definitivamente la reserva de un slot.
        Llamado desde el callback de pago exitoso.
        """
        slot_id = int(slot_id)
        try:
            slot = (
                ProfessionalAvailability.objects
                .select_for_update()
                .get(id=slot_id, is_deleted=False)
            )
        except ProfessionalAvailability.DoesNotExist:
            raise ValidationError("Slot no encontrado.")

        if slot.status not in (
            ProfessionalAvailability.PENDING_RESERVATION,
            ProfessionalAvailability.AVAILABLE,
        ):
            raise ValidationError(
                f"No se puede confirmar un slot con estado '{slot.get_status_display()}'."
            )

        slot.status = ProfessionalAvailability.BOOKED
        slot.save(update_fields=['status', 'updated_at'])
        logger.info("[availability:confirm] Slot %d -> BOOKED", slot_id)
        return slot

    @staticmethod
    @transaction.atomic
    def release_booking(slot_id: int) -> ProfessionalAvailability:
        """
        Libera un slot y lo deja disponible de nuevo.
        Llamado por la tarea Celery de expiracion o ante pago fallido.
        """
        slot_id = int(slot_id)
        try:
            slot = (
                ProfessionalAvailability.objects
                .select_for_update()
                .get(id=slot_id, is_deleted=False)
            )
        except ProfessionalAvailability.DoesNotExist:
            return None  # Ya eliminado, sin accion necesaria

        # Solo liberar si estaba en un estado "reservable"
        if slot.status in (
            ProfessionalAvailability.PENDING_RESERVATION,
            ProfessionalAvailability.BOOKED,
        ):
            slot.status    = ProfessionalAvailability.AVAILABLE
            slot.booked_by = None
            slot.save(update_fields=['status', 'booked_by', 'updated_at'])
            logger.info("[availability:release] Slot %d -> AVAILABLE", slot_id)
        return slot

    @staticmethod
    @transaction.atomic
    def update_slot_status(
        slot_id: int,
        new_status: str,
        requesting_user,
        notes: str = None,
    ) -> ProfessionalAvailability:
        """
        Permite al profesional cambiar manualmente el estado de un slot
        (BLOCKED, VACATION, SICK_LEAVE, AVAILABLE).

        `notes` es opcional -- [AGREGADO 2026-08-04, hallazgo M7 de
        AUDITORIA_INTEGRAL_PRODUCCION_2026-08-04.md] antes el ViewSet escribia
        este campo directo sobre el modelo despues de llamar este Command,
        violando el Service Layer (ViewSets solo orquestan HTTP).
        """
        slot_id = int(slot_id)
        allowed = [
            ProfessionalAvailability.AVAILABLE,
            ProfessionalAvailability.BLOCKED,
            ProfessionalAvailability.VACATION,
            ProfessionalAvailability.SICK_LEAVE,
        ]
        if new_status not in allowed:
            raise ValidationError(
                f"Estado '{new_status}' no permitido. Opciones: {allowed}"
            )

        try:
            slot = (
                ProfessionalAvailability.objects
                .select_for_update()
                .get(
                    id=slot_id,
                    user_profile__user=requesting_user,
                    is_deleted=False,
                )
            )
        except ProfessionalAvailability.DoesNotExist:
            raise ValidationError("Slot no encontrado o no tienes permisos para modificarlo.")

        update_fields = ['status', 'updated_at']
        slot.status = new_status
        if notes is not None:
            slot.notes = notes
            update_fields.append('notes')
        slot.save(update_fields=update_fields)
        logger.info(
            "[availability:update_status] Slot %d -> %s por %s",
            slot.id, new_status, requesting_user.email
        )
        return slot
