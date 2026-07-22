from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from renting.models import (
    RentalOperation, RentalOperationEvent, RentalPeriod, RentalRequest,
)

UPCOMING_RETURN_WINDOW_DAYS = 3

CUSTOMER_NOTIFICATION_BY_STATUS = {
    RentalOperation.DELIVERED: 'rental_equipment_delivered',
    RentalOperation.READY_FOR_PICKUP: 'rental_pickup_scheduled',
    RentalOperation.COMPLETED: 'rental_completed',
}


class RentalOperationCommands:
    TRANSITIONS = {
        RentalOperation.TRANSPORT_ASSIGNED: {
            RentalOperation.READY_FOR_DELIVERY,
        },
        RentalOperation.READY_FOR_DELIVERY: {RentalOperation.DELIVERED},
        RentalOperation.DELIVERED: {RentalOperation.IN_OPERATION},
        RentalOperation.IN_OPERATION: {RentalOperation.READY_FOR_PICKUP},
        RentalOperation.READY_FOR_PICKUP: {RentalOperation.PICKED_UP},
        RentalOperation.PICKED_UP: {RentalOperation.RETURN_INSPECTION},
        RentalOperation.RETURN_INSPECTION: {RentalOperation.COMPLETED},
    }

    @staticmethod
    @transaction.atomic
    def ensure_for_request(rental_request, actor=None):
        operation, created = RentalOperation.objects.get_or_create(
            rental_request=rental_request,
            defaults={'priority': rental_request.priority},
        )
        if created:
            RentalOperationEvent.objects.create(
                operation=operation, event_type='OPERATION_CREATED',
                description='Solicitud enviada a Operaciones de Renting.', actor=actor,
            )
            request = operation.rental_request
            context = {
                'request_uuid': str(request.uuid),
                'operation_uuid': str(operation.uuid),
                'equipment_name': request.equipment_variant.equipment.name,
            }
            from notifications.services.commands import NotificationCommands
            transaction.on_commit(lambda: NotificationCommands.dispatch_notification(
                user=request.user, template_slug='rental_operation_created',
                context=context, ws_group=f'user_{request.user.uuid}',
            ))
        return operation

    @staticmethod
    @transaction.atomic
    def schedule(operation, *, delivery_date, delivery_time, pickup_date,
                 pickup_time, estimated_duration_minutes=None, route='', notes='',
                 priority=None, actor=None):
        operation = RentalOperation.objects.select_for_update().get(pk=operation.pk)
        if operation.status not in {
            RentalOperation.READY_FOR_SCHEDULING, RentalOperation.SCHEDULED,
        }:
            raise ValueError('Solo se puede programar una operacion pendiente o programada.')
        if pickup_date < delivery_date:
            raise ValueError('La fecha de recogida no puede ser anterior a la entrega.')
        operation.delivery_date = delivery_date
        operation.delivery_time = delivery_time
        operation.pickup_date = pickup_date
        operation.pickup_time = pickup_time
        operation.estimated_duration_minutes = estimated_duration_minutes
        operation.route = route
        operation.notes = notes
        if priority:
            operation.priority = priority
        operation.status = RentalOperation.SCHEDULED
        operation.save()
        RentalOperationEvent.objects.create(
            operation=operation, event_type='SCHEDULED', actor=actor,
            description='Entrega y recogida programadas.',
        )
        return operation

    @staticmethod
    @transaction.atomic
    def assign_dispatcher(operation, *, dispatcher, vehicle='', actor=None):
        operation = RentalOperation.objects.select_for_update().get(pk=operation.pk)
        if operation.status != RentalOperation.SCHEDULED:
            raise ValueError('Solo se puede asignar transportista a una operacion programada.')
        if not dispatcher.is_active or not dispatcher.is_available:
            raise ValueError('El transportista seleccionado no esta disponible.')
        if not operation.delivery_date or not operation.delivery_time:
            raise ValueError('La operacion debe programarse antes de asignar transportista.')
        operation.assigned_dispatcher = dispatcher
        operation.assigned_vehicle = vehicle or dispatcher.vehicle_plate
        operation.status = RentalOperation.TRANSPORT_ASSIGNED
        operation.save()
        RentalOperationEvent.objects.create(
            operation=operation, event_type='DISPATCHER_ASSIGNED', actor=actor,
            description=f'Transportista asignado: {dispatcher.user.get_full_name() or dispatcher.user.email}.',
        )
        request = operation.rental_request
        context = {
            'request_uuid': str(request.uuid),
            'operation_uuid': str(operation.uuid),
            'equipment_name': request.equipment_variant.equipment.name,
            'address': request.location_address,
            'delivery_date': str(operation.delivery_date),
            'delivery_time': str(operation.delivery_time),
            'pickup_date': str(operation.pickup_date),
            'pickup_time': str(operation.pickup_time),
            'dispatcher_name': dispatcher.user.get_full_name() or dispatcher.user.email,
            'vehicle': operation.assigned_vehicle,
            'instructions': operation.notes,
        }
        from notifications.services.commands import NotificationCommands
        transaction.on_commit(lambda: NotificationCommands.dispatch_notification(
            user=dispatcher.user, template_slug='rental_dispatch_assigned',
            context=context, ws_group=f'user_{dispatcher.user.uuid}',
        ))
        transaction.on_commit(lambda: NotificationCommands.dispatch_notification(
            user=request.user, template_slug='rental_delivery_scheduled',
            context=context, ws_group=f'user_{request.user.uuid}',
        ))
        RentalOperationEvent.objects.create(
            operation=operation, event_type='NOTIFICATIONS_QUEUED', actor=actor,
            description='Correos de programacion encolados para cliente y transportista.',
        )
        return operation

    @staticmethod
    @transaction.atomic
    def transition(operation, target_status, actor=None):
        operation = RentalOperation.objects.select_for_update().get(pk=operation.pk)
        allowed = RentalOperationCommands.TRANSITIONS.get(operation.status, set())
        if target_status not in allowed:
            raise ValueError(f'Transicion invalida: {operation.status} -> {target_status}.')
        operation.status = target_status
        operation.save(update_fields=['status', 'updated_at'])

        rental_request = RentalRequest.objects.select_for_update().get(
            pk=operation.rental_request_id
        )
        if target_status == RentalOperation.IN_OPERATION:
            RentalPeriod.objects.filter(
                rental_request=rental_request,
                status=RentalPeriod.STATUS_SCHEDULED,
            ).update(status=RentalPeriod.STATUS_ACTIVE)
            rental_request.status = RentalRequest.STATUS_IN_OPERATION
            rental_request.save(update_fields=['status', 'updated_at'])
        elif target_status == RentalOperation.COMPLETED:
            RentalPeriod.objects.filter(
                rental_request=rental_request,
                status=RentalPeriod.STATUS_ACTIVE,
            ).update(status=RentalPeriod.STATUS_COMPLETED)
            rental_request.status = RentalRequest.STATUS_FINISHED
            rental_request.save(update_fields=['status', 'updated_at'])
        RentalOperationEvent.objects.create(
            operation=operation, event_type=target_status, actor=actor,
            description=f'Operacion actualizada a {operation.get_status_display()}.',
            metadata={'changed_at': timezone.now().isoformat()},
        )

        template_slug = CUSTOMER_NOTIFICATION_BY_STATUS.get(target_status)
        if template_slug:
            request = operation.rental_request
            context = {
                'request_uuid': str(request.uuid),
                'operation_uuid': str(operation.uuid),
                'equipment_name': request.equipment_variant.equipment.name,
                'address': request.location_address,
                'delivery_date': str(operation.delivery_date or ''),
                'pickup_date': str(operation.pickup_date or ''),
            }
            from notifications.services.commands import NotificationCommands
            transaction.on_commit(lambda: NotificationCommands.dispatch_notification(
                user=request.user, template_slug=template_slug,
                context=context, ws_group=f'user_{request.user.uuid}',
            ))
        return operation

    @staticmethod
    @transaction.atomic
    def report_incident(operation, *, notes, actor=None):
        operation = RentalOperation.objects.select_for_update().get(pk=operation.pk)
        if operation.status == RentalOperation.COMPLETED:
            raise ValueError('No se puede reportar una incidencia sobre una operacion completada.')
        operation.has_incident = True
        operation.incident_notes = notes
        operation.save(update_fields=['has_incident', 'incident_notes', 'updated_at'])
        RentalOperationEvent.objects.create(
            operation=operation, event_type='INCIDENT_REPORTED', actor=actor,
            description=notes or 'Incidencia reportada.',
        )
        return operation

    @staticmethod
    @transaction.atomic
    def resolve_incident(operation, actor=None):
        operation = RentalOperation.objects.select_for_update().get(pk=operation.pk)
        if not operation.has_incident:
            raise ValueError('La operacion no tiene una incidencia activa.')
        operation.has_incident = False
        operation.incident_notes = ''
        operation.save(update_fields=['has_incident', 'incident_notes', 'updated_at'])
        RentalOperationEvent.objects.create(
            operation=operation, event_type='INCIDENT_RESOLVED', actor=actor,
            description='Incidencia resuelta.',
        )
        return operation


class RentalOperationSelector:
    @staticmethod
    def queryset():
        return (
            RentalOperation.objects.filter(is_deleted=False)
            .select_related(
                'rental_request__user',
                'rental_request__equipment_variant__equipment',
                'assigned_dispatcher__user',
            )
            .prefetch_related('timeline__actor')
        )

    @staticmethod
    def list_for_admin(*, status='', search=''):
        qs = RentalOperationSelector.queryset()
        if status:
            qs = qs.filter(status=status)
        if search:
            qs = qs.filter(rental_request__equipment_variant__equipment__name__icontains=search)
        return qs

    @staticmethod
    def get_by_uuid(uuid):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(RentalOperationSelector.queryset(), uuid=uuid)

    @staticmethod
    def dashboard_metrics():
        today = timezone.localdate()
        qs = RentalOperation.objects.filter(is_deleted=False)
        pre_delivery = {
            RentalOperation.SCHEDULED, RentalOperation.TRANSPORT_ASSIGNED,
            RentalOperation.READY_FOR_DELIVERY,
        }
        pre_pickup = {RentalOperation.IN_OPERATION, RentalOperation.READY_FOR_PICKUP}
        return {
            'pending_scheduling': qs.filter(status=RentalOperation.READY_FOR_SCHEDULING).count(),
            'pending_dispatcher': qs.filter(status=RentalOperation.SCHEDULED).count(),
            'deliveries_today': qs.filter(
                delivery_date=today, status__in=pre_delivery,
            ).count(),
            'pickups_today': qs.filter(
                pickup_date=today, status__in=pre_pickup,
            ).count(),
            'in_operation': qs.filter(status=RentalOperation.IN_OPERATION).count(),
            'upcoming_returns': qs.filter(
                status=RentalOperation.IN_OPERATION,
                pickup_date__gte=today,
                pickup_date__lte=today + timedelta(days=UPCOMING_RETURN_WINDOW_DAYS),
            ).count(),
            'delayed': qs.filter(
                Q(status__in=pre_delivery, delivery_date__lt=today)
                | Q(status__in=pre_pickup, pickup_date__lt=today)
            ).count(),
            'incidents': qs.filter(
                has_incident=True,
            ).exclude(status=RentalOperation.COMPLETED).count(),
        }
