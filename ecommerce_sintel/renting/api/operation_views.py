from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from renting.api.operation_serializers import (
    RentalOperationAssignSerializer,
    RentalOperationIncidentSerializer,
    RentalOperationScheduleSerializer,
    RentalOperationSerializer,
)
from renting.models import RentalOperation
from renting.services.operations import RentalOperationCommands, RentalOperationSelector
from users.api.permissions import IsAdminUser


class RentalOperationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = RentalOperationSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        return RentalOperationSelector.list_for_admin(
            status=self.request.query_params.get('status', ''),
            search=self.request.query_params.get('search', ''),
        )

    def get_object(self):
        return RentalOperationSelector.get_by_uuid(self.kwargs['uuid'])

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        return Response(RentalOperationSelector.dashboard_metrics())

    @action(detail=True, methods=['post'])
    def schedule(self, request, uuid=None):
        serializer = RentalOperationScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            operation = RentalOperationCommands.schedule(
                self.get_object(), actor=request.user, **serializer.validated_data
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RentalOperationSerializer(operation, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='assign-dispatcher')
    def assign_dispatcher(self, request, uuid=None):
        serializer = RentalOperationAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            operation = RentalOperationCommands.assign_dispatcher(
                self.get_object(), actor=request.user, **serializer.validated_data
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RentalOperationSerializer(operation, context={'request': request}).data)

    def _transition(self, request, target):
        try:
            operation = RentalOperationCommands.transition(self.get_object(), target, request.user)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RentalOperationSerializer(operation, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='dispatch')
    def mark_ready_for_delivery(self, request, uuid=None):
        return self._transition(request, RentalOperation.READY_FOR_DELIVERY)

    @action(detail=True, methods=['post'])
    def deliver(self, request, uuid=None):
        return self._transition(request, RentalOperation.DELIVERED)

    @action(detail=True, methods=['post'], url_path='start-operation')
    def start_operation(self, request, uuid=None):
        return self._transition(request, RentalOperation.IN_OPERATION)

    @action(detail=True, methods=['post'], url_path='ready-pickup')
    def ready_pickup(self, request, uuid=None):
        return self._transition(request, RentalOperation.READY_FOR_PICKUP)

    @action(detail=True, methods=['post'])
    def pickup(self, request, uuid=None):
        return self._transition(request, RentalOperation.PICKED_UP)

    @action(detail=True, methods=['post'], url_path='inspect-return')
    def inspect_return(self, request, uuid=None):
        return self._transition(request, RentalOperation.RETURN_INSPECTION)

    @action(detail=True, methods=['post'])
    def complete(self, request, uuid=None):
        return self._transition(request, RentalOperation.COMPLETED)

    @action(detail=True, methods=['post'], url_path='report-incident')
    def report_incident(self, request, uuid=None):
        serializer = RentalOperationIncidentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            operation = RentalOperationCommands.report_incident(
                self.get_object(), actor=request.user, **serializer.validated_data
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RentalOperationSerializer(operation, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='resolve-incident')
    def resolve_incident(self, request, uuid=None):
        try:
            operation = RentalOperationCommands.resolve_incident(self.get_object(), actor=request.user)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RentalOperationSerializer(operation, context={'request': request}).data)
