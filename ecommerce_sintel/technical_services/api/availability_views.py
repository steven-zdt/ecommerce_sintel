from datetime import date as date_type, time as time_type

from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema

from users.api.permissions import IsAdminUser
from technical_services.models import WorkingSchedule, WorkingException, ServiceCategory
from technical_services.services import (
    WorkingScheduleSelector, WorkingScheduleCommands,
    WorkingExceptionSelector, WorkingExceptionCommands,
    TechnicianAvailabilityEngine, TechnicianSelector, build_calendar_feed,
)
from technical_services.api.availability_serializers import (
    WorkingScheduleSerializer, WorkingScheduleInputSerializer,
    WorkingExceptionSerializer, WorkingExceptionInputSerializer,
    AvailableTechnicianSerializer, CapacitySummarySerializer,
    CapacitySummaryRangeSerializer, CalendarFeedSerializer,
)


class StandardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


def _parse_date(value):
    return date_type.fromisoformat(value)


def _parse_time(value):
    return time_type.fromisoformat(value)


@extend_schema(tags=['technician-availability'])
class TechnicianAvailabilityViewSet(viewsets.ViewSet):
    """
    Fuente unica de verdad de disponibilidad de tecnicos (motor calculado, no
    almacenado). Admin-only -- expone TechnicianAvailabilityEngine para poder
    probarlo end-to-end; no hay UI de calendario todavia (Fase 4).
    """
    permission_classes = [IsAdminUser]

    @extend_schema(responses={200: dict})
    @action(detail=False, methods=['get'], url_path='technicians')
    def technicians(self, request):
        """
        GET /technician-availability/technicians/?category=
        Lista simple de tecnicos activos (id/uuid/nombre) para poblar un
        selector en el panel admin (Fase 6) -- sin fecha/hora, a diferencia de
        list_available_technicians().
        """
        category = None
        category_uuid = request.query_params.get('category')
        if category_uuid:
            try:
                category = ServiceCategory.objects.get(uuid=category_uuid, is_deleted=False)
            except ServiceCategory.DoesNotExist:
                return Response({'detail': 'Categoria no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)

        candidates = (
            TechnicianSelector.get_active_technicians_for_category(category)
            if category is not None else TechnicianSelector.get_all_active_technicians()
        )
        return Response([
            {
                'technician_id': tech.id,
                'technician_uuid': str(tech.uuid),
                'technician_name': tech.get_full_name() or tech.email,
            }
            for tech in candidates
        ])

    @extend_schema(responses={200: AvailableTechnicianSerializer(many=True)})
    def list(self, request):
        """
        GET /technician-availability/?date=YYYY-MM-DD&start_time=HH:MM&end_time=HH:MM&category=<uuid>
        Nunca devuelve tecnicos ocupados.
        """
        try:
            date = _parse_date(request.query_params['date'])
            start_time = _parse_time(request.query_params['start_time'])
            end_time = _parse_time(request.query_params['end_time'])
        except (KeyError, ValueError):
            return Response(
                {'detail': 'Parametros requeridos: date (YYYY-MM-DD), start_time, end_time (HH:MM).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        category = None
        category_uuid = request.query_params.get('category')
        if category_uuid:
            try:
                category = ServiceCategory.objects.get(uuid=category_uuid, is_deleted=False)
            except ServiceCategory.DoesNotExist:
                return Response({'detail': 'Categoria no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)

        results = TechnicianAvailabilityEngine.list_available_technicians(date, start_time, end_time, category)
        return Response(AvailableTechnicianSerializer(results, many=True).data)

    @extend_schema(responses={200: CapacitySummarySerializer})
    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """GET /technician-availability/summary/?date=YYYY-MM-DD&category=<uuid>"""
        try:
            date = _parse_date(request.query_params['date'])
        except (KeyError, ValueError):
            return Response(
                {'detail': 'Parametro requerido: date (YYYY-MM-DD).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        category = None
        category_uuid = request.query_params.get('category')
        if category_uuid:
            try:
                category = ServiceCategory.objects.get(uuid=category_uuid, is_deleted=False)
            except ServiceCategory.DoesNotExist:
                return Response({'detail': 'Categoria no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)

        summary = TechnicianAvailabilityEngine.capacity_summary(date, category)
        return Response(CapacitySummarySerializer(summary).data)

    @extend_schema(responses={200: CapacitySummaryRangeSerializer})
    @action(detail=False, methods=['get'], url_path='range-summary')
    def range_summary(self, request):
        """
        GET /technician-availability/range-summary/?start_date=&end_date=&category=
        Ocupacion por semana/mes (Fase 3): capacity_summary() dia a dia mas los
        totales del rango. Rango maximo 92 dias (un trimestre).
        """
        try:
            start_date = _parse_date(request.query_params['start_date'])
            end_date = _parse_date(request.query_params['end_date'])
        except (KeyError, ValueError):
            return Response(
                {'detail': 'Parametros requeridos: start_date, end_date (YYYY-MM-DD).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        category = None
        category_uuid = request.query_params.get('category')
        if category_uuid:
            try:
                category = ServiceCategory.objects.get(uuid=category_uuid, is_deleted=False)
            except ServiceCategory.DoesNotExist:
                return Response({'detail': 'Categoria no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            summary_range = TechnicianAvailabilityEngine.capacity_summary_range(start_date, end_date, category)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(CapacitySummaryRangeSerializer(summary_range).data)

    @extend_schema(responses={200: CalendarFeedSerializer})
    @action(detail=False, methods=['get'], url_path='calendar')
    def calendar(self, request):
        """
        GET /technician-availability/calendar/?start_date=&end_date=&category=
        Fase 4: agregado de calendario para vista de linea de tiempo (dia/semana)
        -- un tecnico por fila, con su horario laboral, ausencias y
        ServiceOperation confirmadas por dia. Rango maximo 31 dias.
        """
        try:
            start_date = _parse_date(request.query_params['start_date'])
            end_date = _parse_date(request.query_params['end_date'])
        except (KeyError, ValueError):
            return Response(
                {'detail': 'Parametros requeridos: start_date, end_date (YYYY-MM-DD).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        category = None
        category_uuid = request.query_params.get('category')
        if category_uuid:
            try:
                category = ServiceCategory.objects.get(uuid=category_uuid, is_deleted=False)
            except ServiceCategory.DoesNotExist:
                return Response({'detail': 'Categoria no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)

        technicians = (
            TechnicianSelector.get_active_technicians_for_category(category)
            if category is not None else TechnicianSelector.get_all_active_technicians()
        )

        try:
            feed = build_calendar_feed(list(technicians), start_date, end_date)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(CalendarFeedSerializer(feed).data)


@extend_schema(tags=['technician-availability'])
class WorkingScheduleViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet,
):
    """Horario laboral recurrente de tecnicos. Admin-only."""
    serializer_class = WorkingScheduleSerializer
    lookup_field = 'uuid'
    permission_classes = [IsAdminUser]
    pagination_class = StandardPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return WorkingSchedule.objects.none()
        technician_uuid = self.request.query_params.get('technician')
        if technician_uuid:
            return WorkingScheduleSelector.list_for_technician(technician_uuid)
        return WorkingSchedule.objects.filter(is_deleted=False).order_by('technician_id', 'weekday')

    @extend_schema(request=WorkingScheduleInputSerializer, responses={201: WorkingScheduleSerializer})
    def create(self, request, *args, **kwargs):
        serializer = WorkingScheduleInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            schedule = WorkingScheduleCommands.upsert_schedule(
                technician=data['technician'], weekday=data['weekday'],
                start_time=data['start_time'], end_time=data['end_time'],
                is_active=data['is_active'],
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(WorkingScheduleSerializer(schedule).data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        WorkingScheduleCommands.delete_schedule(instance)


@extend_schema(tags=['technician-availability'])
class WorkingExceptionViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet,
):
    """Ausencias/bloqueos de tecnicos (vacaciones, permiso, incapacidad, etc). Admin-only."""
    serializer_class = WorkingExceptionSerializer
    lookup_field = 'uuid'
    permission_classes = [IsAdminUser]
    pagination_class = StandardPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return WorkingException.objects.none()
        technician_uuid = self.request.query_params.get('technician')
        if technician_uuid:
            return WorkingExceptionSelector.list_for_technician(technician_uuid)
        return WorkingException.objects.filter(is_deleted=False).order_by('-start_date')

    @extend_schema(request=WorkingExceptionInputSerializer, responses={201: WorkingExceptionSerializer})
    def create(self, request, *args, **kwargs):
        serializer = WorkingExceptionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            exception = WorkingExceptionCommands.create_exception(
                technician=data['technician'], exception_type=data['exception_type'],
                start_date=data['start_date'], end_date=data['end_date'],
                start_time=data['start_time'], end_time=data['end_time'],
                reason=data['reason'], created_by=request.user,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(WorkingExceptionSerializer(exception).data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        WorkingExceptionCommands.delete_exception(instance)
