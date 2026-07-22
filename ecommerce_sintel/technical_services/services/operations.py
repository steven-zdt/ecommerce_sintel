from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from technical_services.models import ServiceOperation, ServiceOperationEvent

ASSIGNABLE_PROFILE_TYPES = {'TECHNICIAN', 'PROFESSIONAL', 'SPECIALIST', 'CONTRACTOR'}
CONFLICTING_SLOT_STATUSES = ['BOOKED', 'PENDING_RESERVATION', 'BLOCKED', 'VACATION', 'SICK_LEAVE']
SLA_TARGET_HOURS = 48


def _visit_window(operation):
    """(start_time, end_time) de la ventana de visita segun scheduled_time + duracion estimada."""
    if not operation.scheduled_date or not operation.scheduled_time:
        return None, None
    duration = operation.estimated_duration_minutes or 60
    start_dt = datetime.combine(operation.scheduled_date, operation.scheduled_time)
    end_dt = start_dt + timedelta(minutes=duration)
    return start_dt.time(), end_dt.time()


class ServiceOperationCommands:
    TRANSITIONS = {
        ServiceOperation.CUSTOMER_NOTIFIED: {ServiceOperation.READY_TO_VISIT},
        ServiceOperation.READY_TO_VISIT: {ServiceOperation.ON_THE_WAY},
        ServiceOperation.ON_THE_WAY: {ServiceOperation.ARRIVED},
        ServiceOperation.ARRIVED: {ServiceOperation.IN_PROGRESS},
        ServiceOperation.IN_PROGRESS: {ServiceOperation.COMPLETED},
    }

    @staticmethod
    @transaction.atomic
    def ensure_for_order(order, actor=None):
        detail = getattr(order, 'service_detail', None)
        operation, created = ServiceOperation.objects.get_or_create(
            order=order,
            defaults={'priority': detail.priority if detail else 'medium'},
        )
        if created:
            ServiceOperationEvent.objects.create(
                operation=operation, event_type='OPERATION_CREATED', actor=actor,
                description='Orden enviada a Operaciones de Servicios.',
            )
            item = order.items.filter(service_variant__isnull=False).first()
            context = {
                'order_uuid': str(order.uuid),
                'operation_uuid': str(operation.uuid),
                'service': item.item_name if item else '',
            }
            from notifications.services.commands import NotificationCommands
            transaction.on_commit(lambda: NotificationCommands.dispatch_notification(
                user=order.user, template_slug='service_operation_created', context=context,
            ))
        return operation

    @staticmethod
    @transaction.atomic
    def plan(operation, *, scheduled_date, scheduled_time, estimated_duration_minutes=None,
             notes='', actor=None):
        operation = ServiceOperation.objects.select_for_update().get(pk=operation.pk)
        if operation.status not in {ServiceOperation.READY_FOR_PLANNING, ServiceOperation.PLANNED}:
            raise ValueError('Solo se puede planear una operacion pendiente o ya planeada.')
        operation.scheduled_date = scheduled_date
        operation.scheduled_time = scheduled_time
        operation.estimated_duration_minutes = estimated_duration_minutes
        operation.notes = notes
        operation.status = ServiceOperation.PLANNED
        operation.save()
        ServiceOperationEvent.objects.create(
            operation=operation, event_type='PLANNED', actor=actor,
            description='Visita planeada.',
        )
        return operation

    @staticmethod
    @transaction.atomic
    def try_auto_assign_via_engine(operation, actor=None) -> bool:
        """
        Auto-asignacion real (Fase 7, 2026-07-14): usa TechnicianAvailabilityEngine
        como 'cerebro' (decide quien y cuando) delegando la mutacion real a
        plan()/assign_technician() ya existentes y probados -- cero logica de
        ProfessionalAvailability/notificaciones/eventos duplicada aqui.

        'Caso 1' del spec (pago aprobado, llamado desde
        ServiceCommands.confirm_slot_on_payment()); tambien expuesto como accion
        admin explicita ('Caso 2', confirmacion manual / reintento).

        NUNCA propaga excepcion: si el motor no encuentra a nadie, o si
        assign_technician() falla igual (ej. carrera con una asignacion manual
        concurrente sobre accounts.ProfessionalAvailability), la operacion queda
        exactamente como estaba para asignacion manual -- el fallback que ya
        existe hoy. Retorna True si asigno, False si no.
        """
        import logging
        logger = logging.getLogger(__name__)

        operation = ServiceOperation.objects.select_for_update().get(pk=operation.pk)
        if operation.status != ServiceOperation.READY_FOR_PLANNING or operation.technician_id:
            return False

        order_item = operation.order.items.filter(service_variant__isnull=False).first()
        if not order_item or not order_item.service_variant:
            return False
        variant = order_item.service_variant
        category = variant.service.category
        duration_minutes = int((variant.estimated_hours or Decimal('1.0')) * 60)

        detail = getattr(operation.order, 'service_detail', None)
        start_date = (detail.preferred_date if detail else None) or timezone.localdate()
        preferred_time = detail.preferred_time if detail else None

        from technical_services.services.technician_availability import TechnicianAvailabilityEngine
        match = TechnicianAvailabilityEngine.find_next_available_technician(
            start_date, duration_minutes, category=category, preferred_time=preferred_time,
        )
        if match is None:
            return False

        try:
            from users.models import User
            technician = User.objects.get(pk=match['technician_id'])
            operation = ServiceOperationCommands.plan(
                operation, scheduled_date=match['date'], scheduled_time=match['start_time'],
                estimated_duration_minutes=duration_minutes, actor=actor,
            )
            ServiceOperationCommands.assign_technician(operation, technician=technician, actor=actor)
            return True
        except Exception:
            logger.exception(
                "try_auto_assign_via_engine: fallo asignando operation=%s tecnico=%s -- "
                "queda para asignacion manual", operation.uuid, match.get('technician_uuid'),
            )
            return False

    @staticmethod
    def _check_conflict(user_profile, target_date, start_time, end_time, exclude_slot_id=None):
        from accounts.models import ProfessionalAvailability
        qs = ProfessionalAvailability.objects.select_for_update().filter(
            user_profile=user_profile, date=target_date,
            status__in=CONFLICTING_SLOT_STATUSES,
            start_time__lt=end_time, end_time__gt=start_time,
        )
        if exclude_slot_id:
            qs = qs.exclude(pk=exclude_slot_id)
        if qs.exists():
            raise ValueError(
                'El profesional tiene un conflicto de horario en ese periodo. '
                'Elige otro profesional u otro horario.'
            )

    @staticmethod
    @transaction.atomic
    def assign_technician(operation, *, technician, actor=None):
        from accounts.models import ProfessionalAvailability
        from accounts.services.profile_resolver import ProfileResolver
        from accounts.services.commands import AvailabilityCommands

        operation = ServiceOperation.objects.select_for_update().get(pk=operation.pk)
        if operation.status not in {ServiceOperation.PLANNED, ServiceOperation.TECHNICIAN_ASSIGNED}:
            raise ValueError('Solo se puede asignar tecnico a una operacion planeada.')
        if not operation.scheduled_date or not operation.scheduled_time:
            raise ValueError('La operacion debe planearse (fecha/hora) antes de asignar tecnico.')

        profile_type = ProfileResolver.get_type(technician)
        if profile_type not in ASSIGNABLE_PROFILE_TYPES:
            raise ValueError('El usuario seleccionado no es un tecnico ni contratista valido.')
        user_profile = ProfileResolver.get_profile(technician)
        if not user_profile:
            raise ValueError('El profesional seleccionado no tiene un perfil valido.')

        start_time, end_time = _visit_window(operation)
        same_technician = operation.technician_id == technician.id
        previous_slot_id = operation.availability_slot_id

        if previous_slot_id and not same_technician:
            AvailabilityCommands.release_booking(previous_slot_id)
            previous_slot_id = None

        ServiceOperationCommands._check_conflict(
            user_profile, operation.scheduled_date, start_time, end_time,
            exclude_slot_id=previous_slot_id,
        )

        slot, _ = ProfessionalAvailability.objects.select_for_update().get_or_create(
            user_profile=user_profile, date=operation.scheduled_date, start_time=start_time,
            defaults={'end_time': end_time, 'status': ProfessionalAvailability.AVAILABLE},
        )
        slot.booked_by = actor
        slot.save(update_fields=['booked_by', 'updated_at'])
        AvailabilityCommands.confirm_booking(slot.id)
        slot.refresh_from_db()

        operation.technician = technician
        operation.availability_slot = slot
        operation.status = ServiceOperation.TECHNICIAN_ASSIGNED
        operation.save()
        ServiceOperationEvent.objects.create(
            operation=operation, event_type='TECHNICIAN_ASSIGNED', actor=actor,
            description=f'Tecnico asignado: {technician.get_full_name() or technician.email}.',
        )
        context = {
            'order_uuid': str(operation.order.uuid),
            'operation_uuid': str(operation.uuid),
            'scheduled_date': str(operation.scheduled_date),
            'scheduled_time': str(operation.scheduled_time),
        }
        from notifications.services.commands import NotificationCommands
        transaction.on_commit(lambda: NotificationCommands.dispatch_notification(
            user=technician, template_slug='service_operation_assigned', context=context,
        ))
        return operation

    @staticmethod
    @transaction.atomic
    def unassign_technician(operation, actor=None):
        from accounts.services.commands import AvailabilityCommands
        operation = ServiceOperation.objects.select_for_update().get(pk=operation.pk)
        if operation.availability_slot_id:
            AvailabilityCommands.release_booking(operation.availability_slot_id)
        operation.technician = None
        operation.availability_slot = None
        operation.status = ServiceOperation.PLANNED
        operation.save()
        ServiceOperationEvent.objects.create(
            operation=operation, event_type='TECHNICIAN_UNASSIGNED', actor=actor,
            description='Tecnico desasignado.',
        )
        return operation

    @staticmethod
    @transaction.atomic
    def reschedule(operation, *, scheduled_date, scheduled_time,
                   estimated_duration_minutes=None, actor=None):
        from accounts.services.commands import AvailabilityCommands
        operation = ServiceOperation.objects.select_for_update().get(pk=operation.pk)
        if operation.status in {ServiceOperation.COMPLETED, ServiceOperation.CLOSED, ServiceOperation.CANCELLED}:
            raise ValueError('No se puede reprogramar una operacion cerrada, completada o cancelada.')

        technician = operation.technician
        if operation.availability_slot_id:
            AvailabilityCommands.release_booking(operation.availability_slot_id)

        operation.scheduled_date = scheduled_date
        operation.scheduled_time = scheduled_time
        if estimated_duration_minutes is not None:
            operation.estimated_duration_minutes = estimated_duration_minutes
        operation.availability_slot = None
        operation.technician = None
        operation.status = ServiceOperation.PLANNED
        operation.save()
        ServiceOperationEvent.objects.create(
            operation=operation, event_type='RESCHEDULED', actor=actor,
            description='Operacion reprogramada.',
        )

        if technician:
            return ServiceOperationCommands.assign_technician(operation, technician=technician, actor=actor)
        return operation

    @staticmethod
    @transaction.atomic
    def cancel(operation, *, reason='', actor=None):
        from accounts.services.commands import AvailabilityCommands
        operation = ServiceOperation.objects.select_for_update().get(pk=operation.pk)
        if operation.status in {ServiceOperation.COMPLETED, ServiceOperation.CLOSED}:
            raise ValueError('No se puede cancelar una operacion ya completada o cerrada.')
        if operation.availability_slot_id:
            AvailabilityCommands.release_booking(operation.availability_slot_id)
        operation.availability_slot = None
        operation.status = ServiceOperation.CANCELLED
        operation.notes = f"{operation.notes}\nCancelada: {reason}".strip()
        operation.save()
        ServiceOperationEvent.objects.create(
            operation=operation, event_type='CANCELLED', actor=actor,
            description=reason or 'Operacion cancelada.',
        )
        order = operation.order
        context = {'order_uuid': str(order.uuid), 'reason': reason}
        from notifications.services.commands import NotificationCommands
        transaction.on_commit(lambda: NotificationCommands.dispatch_notification(
            user=order.user, template_slug='service_operation_cancelled', context=context,
        ))
        return operation

    @staticmethod
    @transaction.atomic
    def notify_client(operation, actor=None):
        operation = ServiceOperation.objects.select_for_update().get(pk=operation.pk)
        if operation.status != ServiceOperation.TECHNICIAN_ASSIGNED:
            raise ValueError('Solo se puede notificar al cliente tras asignar un tecnico.')
        operation.status = ServiceOperation.CUSTOMER_NOTIFIED
        operation.save()
        ServiceOperationEvent.objects.create(
            operation=operation, event_type='CUSTOMER_NOTIFIED', actor=actor,
            description='Cliente notificado de la visita programada.',
        )
        order = operation.order
        detail = getattr(order, 'service_detail', None)
        technician = operation.technician
        context = {
            'order_uuid': str(order.uuid),
            'technician_name': (technician.get_full_name() or technician.email) if technician else '',
            'scheduled_date': str(operation.scheduled_date or ''),
            'scheduled_time': str(operation.scheduled_time or ''),
            'address': detail.address if detail else '',
        }
        from notifications.services.commands import NotificationCommands
        transaction.on_commit(lambda: NotificationCommands.dispatch_notification(
            user=order.user, template_slug='service_visit_scheduled', context=context,
        ))
        return operation

    @staticmethod
    @transaction.atomic
    def transition(operation, target_status, actor=None):
        operation = ServiceOperation.objects.select_for_update().get(pk=operation.pk)
        allowed = ServiceOperationCommands.TRANSITIONS.get(operation.status, set())
        if target_status not in allowed:
            raise ValueError(f'Transicion invalida: {operation.status} -> {target_status}.')
        operation.status = target_status
        now = timezone.now()
        update_fields = ['status', 'updated_at']
        if target_status == ServiceOperation.ARRIVED:
            operation.arrived_at = now
            update_fields.append('arrived_at')
        elif target_status == ServiceOperation.IN_PROGRESS:
            operation.started_at = now
            update_fields.append('started_at')
        elif target_status == ServiceOperation.COMPLETED:
            operation.completed_at = now
            update_fields.append('completed_at')
        operation.save(update_fields=update_fields)
        ServiceOperationEvent.objects.create(
            operation=operation, event_type=target_status, actor=actor,
            description=f'Operacion actualizada a {operation.get_status_display()}.',
        )
        if target_status == ServiceOperation.COMPLETED:
            from technical_services.services.commands import ServiceTimelineCommands
            ServiceTimelineCommands.add_timeline_event(
                operation.order, status='completed',
                notes='Servicio finalizado (Operaciones).', created_by=actor,
            )
            if operation.availability_slot_id:
                from accounts.services.commands import AvailabilityCommands
                AvailabilityCommands.release_booking(operation.availability_slot_id)
        return operation

    @staticmethod
    @transaction.atomic
    def close(operation, *, closure_status=None, actor=None):
        operation = ServiceOperation.objects.select_for_update().get(pk=operation.pk)
        if operation.status != ServiceOperation.COMPLETED:
            raise ValueError('Solo se puede cerrar una operacion completada.')
        operation.status = ServiceOperation.CLOSED
        operation.closure_status = closure_status or ServiceOperation.CLOSURE_CONFIRMED
        operation.save(update_fields=['status', 'closure_status', 'updated_at'])
        ServiceOperationEvent.objects.create(
            operation=operation, event_type='CLOSED', actor=actor,
            description='Operacion cerrada.',
        )
        return operation

    @staticmethod
    @transaction.atomic
    def report_incident(operation, *, notes, actor=None):
        operation = ServiceOperation.objects.select_for_update().get(pk=operation.pk)
        if operation.status in {ServiceOperation.COMPLETED, ServiceOperation.CLOSED}:
            raise ValueError('No se puede reportar una incidencia sobre una operacion cerrada.')
        operation.has_incident = True
        operation.incident_notes = notes
        operation.save(update_fields=['has_incident', 'incident_notes', 'updated_at'])
        ServiceOperationEvent.objects.create(
            operation=operation, event_type='INCIDENT_REPORTED', actor=actor,
            description=notes or 'Incidencia reportada.',
        )
        from notifications.services.commands import NotificationCommands
        transaction.on_commit(lambda: NotificationCommands.dispatch_notification(
            user=operation.order.user, template_slug='service_incident_reported',
            context={'order_uuid': str(operation.order.uuid), 'notes': notes},
            ws_group='admin_notifications',
        ))
        return operation

    @staticmethod
    @transaction.atomic
    def resolve_incident(operation, actor=None):
        operation = ServiceOperation.objects.select_for_update().get(pk=operation.pk)
        if not operation.has_incident:
            raise ValueError('La operacion no tiene una incidencia activa.')
        operation.has_incident = False
        operation.incident_notes = ''
        operation.save(update_fields=['has_incident', 'incident_notes', 'updated_at'])
        ServiceOperationEvent.objects.create(
            operation=operation, event_type='INCIDENT_RESOLVED', actor=actor,
            description='Incidencia resuelta.',
        )
        return operation


class ServiceOperationSelector:
    @staticmethod
    def queryset():
        return (
            ServiceOperation.objects.filter(is_deleted=False)
            .select_related('order__user', 'order__service_detail', 'technician')
            .prefetch_related('timeline__actor')
        )

    @staticmethod
    def list_for_admin(*, status='', search='', technician_id=None, date_from=None, date_to=None):
        qs = ServiceOperationSelector.queryset()
        if status:
            qs = qs.filter(status=status)
        if technician_id:
            qs = qs.filter(technician_id=technician_id)
        if date_from:
            qs = qs.filter(scheduled_date__gte=date_from)
        if date_to:
            qs = qs.filter(scheduled_date__lte=date_to)
        if search:
            qs = qs.filter(
                Q(order__uuid__icontains=search) | Q(order__user__email__icontains=search)
            )
        return qs

    @staticmethod
    def get_by_uuid(uuid):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(ServiceOperationSelector.queryset(), uuid=uuid)

    @staticmethod
    def dashboard_metrics():
        today = timezone.localdate()
        qs = ServiceOperation.objects.filter(is_deleted=False)
        active_statuses = [
            ServiceOperation.PLANNED, ServiceOperation.TECHNICIAN_ASSIGNED,
            ServiceOperation.CUSTOMER_NOTIFIED, ServiceOperation.READY_TO_VISIT,
            ServiceOperation.ON_THE_WAY, ServiceOperation.ARRIVED,
        ]
        completed_qs = qs.filter(
            status__in=[ServiceOperation.COMPLETED, ServiceOperation.CLOSED],
            completed_at__isnull=False,
        ).only('completed_at', 'created_at')
        durations = [
            (op.completed_at - op.created_at).total_seconds() / 3600 for op in completed_qs
        ]
        avg_hours = round(sum(durations) / len(durations), 1) if durations else None
        within_sla = len([d for d in durations if d <= SLA_TARGET_HOURS])
        sla_pct = round((within_sla / len(durations)) * 100, 1) if durations else None

        # Fase 7 (2026-07-14): technicians_busy/available ahora vienen del motor
        # calculado (TechnicianAvailabilityEngine.capacity_summary) en vez de la
        # bandera TechnicianProfile.is_available -- mismo numero que ve el panel
        # de Horarios y Ausencias, solo lectura, no cambia ningun flujo de escritura.
        from technical_services.services.technician_availability import TechnicianAvailabilityEngine
        capacity = TechnicianAvailabilityEngine.capacity_summary(today)

        return {
            'pending_planning': qs.filter(status=ServiceOperation.READY_FOR_PLANNING).count(),
            'scheduled_today': qs.filter(scheduled_date=today, status__in=active_statuses).count(),
            'in_progress': qs.filter(status=ServiceOperation.IN_PROGRESS).count(),
            'technicians_busy': capacity['technicians_busy'],
            'technicians_available': capacity['technicians_available'],
            'delayed': qs.filter(status__in=active_statuses, scheduled_date__lt=today).count(),
            'avg_completion_hours': avg_hours,
            'sla_percentage': sla_pct,
        }

    @staticmethod
    def technician_agenda(profile_uuid, date_from, date_to):
        from accounts.services.selectors import AvailabilitySelector
        return AvailabilitySelector.get_full_schedule(profile_uuid, date_from, date_to)

    @staticmethod
    def available_technicians(operation):
        """
        Candidatos para asignacion MANUAL: todos los tecnicos activos, sin filtrar
        por especialidad/categoria -- el administrador decide si esta calificado.
        Solo se excluyen los que tienen un conflicto real de horario (eso si es una
        restriccion dura, no una decision de calificacion).
        """
        from technical_services.services.selectors import TechnicianSelector
        from accounts.models import ProfessionalAvailability
        from accounts.services.profile_resolver import ProfileResolver

        candidates = TechnicianSelector.get_all_active_technicians()

        start_time, end_time = _visit_window(operation)
        results = []
        for user in candidates:
            profile = ProfileResolver.get_profile(user)
            if not profile:
                continue
            conflict = False
            if operation.scheduled_date and start_time and end_time:
                conflict = ProfessionalAvailability.objects.filter(
                    user_profile=profile, date=operation.scheduled_date,
                    status__in=CONFLICTING_SLOT_STATUSES,
                    start_time__lt=end_time, end_time__gt=start_time,
                ).exists()
            if not conflict:
                results.append(user)
        return results
