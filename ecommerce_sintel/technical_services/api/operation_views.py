from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from technical_services.api.operation_serializers import (
    ServiceOperationAssignSerializer,
    ServiceOperationCancelSerializer,
    ServiceOperationCloseSerializer,
    ServiceOperationIncidentSerializer,
    ServiceOperationPlanSerializer,
    ServiceOperationPriceOverrideSerializer,
    ServiceOperationRescheduleSerializer,
    ServiceOperationSerializer,
    ServiceOperationTechnicianCandidateSerializer,
)
from technical_services.models import ServiceOperation
from technical_services.services.commands import OrderPricingCommands
from technical_services.services.operations import ServiceOperationCommands, ServiceOperationSelector
from users.api.permissions import IsAdminUser


def _err(exc):
    if isinstance(exc, DjangoValidationError):
        return '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc)
    return str(exc)


class ServiceOperationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = ServiceOperationSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        params = self.request.query_params
        return ServiceOperationSelector.list_for_admin(
            status=params.get('status', ''),
            search=params.get('search', ''),
            technician_id=params.get('technician_id') or None,
            date_from=params.get('date_from') or None,
            date_to=params.get('date_to') or None,
        )

    def get_object(self):
        return ServiceOperationSelector.get_by_uuid(self.kwargs['uuid'])

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        return Response(ServiceOperationSelector.dashboard_metrics())

    @action(detail=True, methods=['get'], url_path='available-technicians')
    def available_technicians(self, request, uuid=None):
        candidates = ServiceOperationSelector.available_technicians(self.get_object())
        return Response(
            ServiceOperationTechnicianCandidateSerializer(candidates, many=True).data
        )

    @action(detail=False, methods=['get'], url_path='technician-agenda')
    def technician_agenda(self, request):
        profile_uuid = request.query_params.get('profile_uuid')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if not profile_uuid or not date_from or not date_to:
            return Response(
                {'detail': 'profile_uuid, date_from y date_to son requeridos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        slots = ServiceOperationSelector.technician_agenda(profile_uuid, date_from, date_to)
        return Response([
            {
                'uuid': str(s.uuid), 'date': str(s.date),
                'start_time': str(s.start_time), 'end_time': str(s.end_time),
                'status': s.status, 'status_display': s.get_status_display(),
            }
            for s in slots
        ])

    @action(detail=True, methods=['post'])
    def plan(self, request, uuid=None):
        serializer = ServiceOperationPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            operation = ServiceOperationCommands.plan(
                self.get_object(), actor=request.user, **serializer.validated_data
            )
        except (ValueError, DjangoValidationError) as exc:
            return Response({'detail': _err(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ServiceOperationSerializer(operation).data)

    @action(detail=True, methods=['post'], url_path='assign-technician')
    def assign_technician(self, request, uuid=None):
        serializer = ServiceOperationAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            operation = ServiceOperationCommands.assign_technician(
                self.get_object(),
                technician=serializer.validated_data['technician_uuid'],
                actor=request.user,
            )
        except (ValueError, DjangoValidationError) as exc:
            return Response({'detail': _err(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ServiceOperationSerializer(operation).data)

    @action(detail=True, methods=['post'], url_path='auto-assign')
    def auto_assign(self, request, uuid=None):
        """
        POST /service-operations/{uuid}/auto-assign/ -- 'Caso 2' del spec
        (confirmacion/reintento manual por admin): usa TechnicianAvailabilityEngine
        para elegir tecnico+horario y asignar. No falla si no encuentra a
        nadie -- retorna assigned=False para que el admin siga con el flujo
        manual existente.
        """
        operation = self.get_object()
        assigned = ServiceOperationCommands.try_auto_assign_via_engine(operation, actor=request.user)
        operation.refresh_from_db()
        return Response({
            'assigned': assigned,
            'operation': ServiceOperationSerializer(operation).data,
        })

    @action(detail=True, methods=['post'], url_path='unassign-technician')
    def unassign_technician(self, request, uuid=None):
        try:
            operation = ServiceOperationCommands.unassign_technician(self.get_object(), actor=request.user)
        except (ValueError, DjangoValidationError) as exc:
            return Response({'detail': _err(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ServiceOperationSerializer(operation).data)

    @action(detail=True, methods=['post'], url_path='reschedule')
    def reschedule(self, request, uuid=None):
        serializer = ServiceOperationRescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            operation = ServiceOperationCommands.reschedule(
                self.get_object(), actor=request.user, **serializer.validated_data
            )
        except (ValueError, DjangoValidationError) as exc:
            return Response({'detail': _err(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ServiceOperationSerializer(operation).data)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, uuid=None):
        serializer = ServiceOperationCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            operation = ServiceOperationCommands.cancel(
                self.get_object(), actor=request.user, **serializer.validated_data
            )
        except (ValueError, DjangoValidationError) as exc:
            return Response({'detail': _err(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ServiceOperationSerializer(operation).data)

    @action(detail=True, methods=['post'], url_path='notify-client')
    def notify_client(self, request, uuid=None):
        try:
            operation = ServiceOperationCommands.notify_client(self.get_object(), actor=request.user)
        except (ValueError, DjangoValidationError) as exc:
            return Response({'detail': _err(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ServiceOperationSerializer(operation).data)

    def _transition(self, request, target):
        try:
            operation = ServiceOperationCommands.transition(self.get_object(), target, request.user)
        except (ValueError, DjangoValidationError) as exc:
            return Response({'detail': _err(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ServiceOperationSerializer(operation).data)

    @action(detail=True, methods=['post'], url_path='ready-to-visit')
    def ready_to_visit(self, request, uuid=None):
        return self._transition(request, ServiceOperation.READY_TO_VISIT)

    @action(detail=True, methods=['post'])
    def start(self, request, uuid=None):
        return self._transition(request, ServiceOperation.ON_THE_WAY)

    @action(detail=True, methods=['post'])
    def arrive(self, request, uuid=None):
        return self._transition(request, ServiceOperation.ARRIVED)

    @action(detail=True, methods=['post'], url_path='start-service')
    def start_service(self, request, uuid=None):
        return self._transition(request, ServiceOperation.IN_PROGRESS)

    @action(detail=True, methods=['post'])
    def complete(self, request, uuid=None):
        return self._transition(request, ServiceOperation.COMPLETED)

    @action(detail=True, methods=['post'])
    def close(self, request, uuid=None):
        serializer = ServiceOperationCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            operation = ServiceOperationCommands.close(
                self.get_object(), actor=request.user, **serializer.validated_data
            )
        except (ValueError, DjangoValidationError) as exc:
            return Response({'detail': _err(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ServiceOperationSerializer(operation).data)

    @action(detail=True, methods=['post'], url_path='report-incident')
    def report_incident(self, request, uuid=None):
        serializer = ServiceOperationIncidentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            operation = ServiceOperationCommands.report_incident(
                self.get_object(), actor=request.user, **serializer.validated_data
            )
        except (ValueError, DjangoValidationError) as exc:
            return Response({'detail': _err(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ServiceOperationSerializer(operation).data)

    @action(detail=True, methods=['post'], url_path='resolve-incident')
    def resolve_incident(self, request, uuid=None):
        try:
            operation = ServiceOperationCommands.resolve_incident(self.get_object(), actor=request.user)
        except (ValueError, DjangoValidationError) as exc:
            return Response({'detail': _err(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ServiceOperationSerializer(operation).data)

    # ── Plan "Manual Pricing Engine" FASE 16/18/19 -- precio comercial de la
    # orden asociada. Ver OrderPricingCommands: nunca toca Order.total_amount,
    # solo deja un registro auditado (decision confirmada con el usuario). ──

    @action(detail=True, methods=['post'], url_path='confirm-price')
    def confirm_price(self, request, uuid=None):
        operation = self.get_object()
        detail = getattr(operation.order, 'service_detail', None)
        if detail is None:
            return Response({'detail': 'Esta orden no tiene detalle de servicio.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            OrderPricingCommands.confirm_price(detail, changed_by=request.user)
        except (ValueError, DjangoValidationError) as exc:
            return Response({'detail': _err(exc)}, status=status.HTTP_400_BAD_REQUEST)
        operation.refresh_from_db()
        return Response(ServiceOperationSerializer(operation).data)

    @action(detail=True, methods=['post'], url_path='override-price')
    def override_price(self, request, uuid=None):
        operation = self.get_object()
        detail = getattr(operation.order, 'service_detail', None)
        if detail is None:
            return Response({'detail': 'Esta orden no tiene detalle de servicio.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ServiceOperationPriceOverrideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            OrderPricingCommands.override_price(
                detail, new_total=serializer.validated_data['new_total'],
                reason=serializer.validated_data['reason'], changed_by=request.user,
            )
        except (ValueError, DjangoValidationError) as exc:
            return Response({'detail': _err(exc)}, status=status.HTTP_400_BAD_REQUEST)
        operation.refresh_from_db()
        return Response(ServiceOperationSerializer(operation).data)
