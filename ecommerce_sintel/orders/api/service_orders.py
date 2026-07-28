"""
orders/api/service_orders.py

ViewSet unificado para solicitudes de servicio tecnico.
La logica de negocio vive en technical_services/services/;
este modulo solo expone la API bajo el prefijo /api/v1/orders/.
"""
from django.db import transaction
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema

from orders.models import Order, OrderItem
from technical_services.api.serializers import (
    ServiceOrderSerializer,
    ServiceRequestInputSerializer,
    ServiceTimelineInputSerializer,
    ServiceAttachmentInputSerializer,
    OrderServiceTimelineSerializer,
    ServiceAttachmentSerializer,
    TechnicianAssignmentInputSerializer,
    OrderServiceDetailSerializer,
    ServiceAssignmentQueueSerializer,
    TechnicianCandidateSerializer,
    PriorityChangeInputSerializer,
)
from technical_services.services import (
    ServiceCommands,
    ServiceTimelineCommands,
    ServiceAttachmentCommands,
    ServiceAssignmentCommands,
)
from technical_services.services.selectors import TechnicianSelector


class ServiceOrderPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


@extend_schema(tags=['orders'])
class ServiceOrderViewSet(viewsets.ModelViewSet):
    """
    Endpoint unificado de ordenes de servicio tecnico.

    - POST   /api/v1/orders/service-orders/               -> Crear solicitud (cliente autenticado)
    - GET    /api/v1/orders/service-orders/               -> Listar mis solicitudes
    - GET    /api/v1/orders/service-orders/:uuid/         -> Ver detalle
    - POST   /api/v1/orders/service-orders/:uuid/timeline/      -> Agregar evento (admin)
    - POST   /api/v1/orders/service-orders/:uuid/attachments/   -> Subir adjunto
    - POST   /api/v1/orders/service-orders/:uuid/assign-technician/ -> Asignar tecnico (admin)
    - POST   /api/v1/orders/service-orders/:uuid/auto-assign/       -> Asignacion automatica (admin)
    """
    lookup_field = 'uuid'
    serializer_class = ServiceOrderSerializer
    pagination_class = ServiceOrderPagination
    permission_classes = [permissions.IsAuthenticated]

    # O-05 (auditoria enterprise): el mismo tipo de recurso (Order) esta
    # protegido de forma desigual segun por que puerta se cree -- OrderViewSet
    # (orders/api/views.py) ya tiene 'order_create' en create_from_cart, este
    # ViewSet no tenia ningun throttle propio en su create().
    ACTION_THROTTLE_SCOPES = {'create': 'order_create'}

    def get_throttles(self):
        scope = self.ACTION_THROTTLE_SCOPES.get(self.action)
        if not scope:
            return []
        self.throttle_scope = scope
        return [ScopedRateThrottle()]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
        qs = (
            Order.objects
            .filter(service_detail__isnull=False)
            .select_related(
                'service_detail', 'service_detail__technician',
                'service_detail__technician__technician_profile',
            )
            .prefetch_related(
                'items',
                Prefetch(
                    'items',
                    queryset=OrderItem.objects.select_related('service_variant__service__category'),
                    to_attr='service_items_prefetch',
                ),
                'timeline', 'attachments',
            )
        )
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)

        # Filtros del tablero de asignacion de tecnicos (solo tienen efecto si se envian).
        params = self.request.query_params
        priority = params.get('priority')
        if priority:
            qs = qs.filter(service_detail__priority=priority)
        has_technician = params.get('has_technician')
        if has_technician in ('true', 'false'):
            qs = qs.filter(service_detail__technician__isnull=has_technician == 'false')
        category = params.get('category')
        if category:
            qs = qs.filter(items__service_variant__service__category__slug=category).distinct()
        search = params.get('search')
        if search:
            qs = qs.filter(
                Q(uuid__icontains=search)
                | Q(tracking_number__icontains=search)
                | Q(user__email__icontains=search)
                | Q(items__item_name__icontains=search)
            ).distinct()
        return qs.order_by('-created_at')

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy',
                           'assign_technician', 'auto_assign_technician',
                           'unassign_technician', 'change_priority', 'available_technicians']:
            from users.api.permissions import IsAdminUser
            return [IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = ServiceRequestInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        variant              = data.pop('variant_uuid')
        quantity             = data.pop('quantity')
        duration             = data.pop('duration', None)
        discount_pct         = data.pop('discount_pct', None)
        selected_technician  = data.pop('selected_technician_uuid', None)
        selected_slot_id     = data.pop('selected_slot_id', None)
        contact_person       = data.pop('contact_person', None)
        package              = data.pop('package_uuid', None)
        additional_cost_selections = data.pop('additional_costs', None)

        service_detail_data = {
            'priority':       data.get('priority'),
            'description':    data.get('description'),
            'address':        data.get('address'),
            'scheduled_at':   data.get('scheduled_at'),
            'preferred_date': data.get('preferred_date'),
            'preferred_time': data.get('preferred_time'),
            'location_reference': data.get('location_reference'),
            'neighborhood': data.get('neighborhood'),
            'service_notes': data.get('service_notes'),
            'allow_schedule_changes': data.get('allow_schedule_changes', True),
            'contact_person': contact_person,
        }

        try:
            order = ServiceCommands.request_service(
                user=request.user,
                variant=variant,
                quantity=quantity,
                duration=duration,
                discount_pct=discount_pct,
                service_detail_data=service_detail_data,
                selected_technician=selected_technician,
                selected_slot_id=selected_slot_id,
                package=package,
                additional_cost_selections=additional_cost_selections,
            )
            order = self.get_queryset().get(uuid=order.uuid)
            return Response(ServiceOrderSerializer(order).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        request=ServiceTimelineInputSerializer,
        responses={201: OrderServiceTimelineSerializer},
    )
    @action(detail=True, methods=['post'], url_path='timeline')
    def add_timeline_event(self, request, uuid=None):
        """Agrega un evento de estado al timeline de la orden. Solo admin."""
        if not request.user.is_staff:
            return Response(
                {'detail': 'No tiene permisos para modificar la linea de tiempo.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        order = get_object_or_404(self.get_queryset(), uuid=uuid)
        serializer = ServiceTimelineInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            event = ServiceTimelineCommands.add_timeline_event(
                order=order,
                status=serializer.validated_data['status'],
                notes=serializer.validated_data.get('notes', ''),
                created_by=request.user,
            )
            return Response(OrderServiceTimelineSerializer(event).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        request=ServiceAttachmentInputSerializer,
        responses={201: ServiceAttachmentSerializer},
    )
    @action(detail=True, methods=['post'], url_path='attachments',
            parser_classes=[MultiPartParser, FormParser])
    def upload_attachment(self, request, uuid=None):
        """Sube un archivo adjunto (PDF/PNG/JPEG, max 5 MB)."""
        order = get_object_or_404(self.get_queryset(), uuid=uuid)
        serializer = ServiceAttachmentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            attachment = ServiceAttachmentCommands.add_attachment(
                order=order,
                file=serializer.validated_data['file'],
                uploaded_by=request.user,
                doc_type=serializer.validated_data.get('doc_type', ''),
            )
            return Response(ServiceAttachmentSerializer(attachment).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        request=TechnicianAssignmentInputSerializer,
        responses={200: OrderServiceDetailSerializer},
    )
    @action(detail=True, methods=['post'], url_path='assign-technician')
    def assign_technician(self, request, uuid=None):
        """Asigna manualmente un tecnico a la orden. Solo admin."""
        order = get_object_or_404(self.get_queryset(), uuid=uuid)
        serializer = TechnicianAssignmentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            detail = ServiceAssignmentCommands.assign_technician(
                order=order,
                technician=serializer.validated_data['technician_uuid'],
                notes=request.data.get('notes', ''),
                assigned_by=request.user,
            )
            return Response(OrderServiceDetailSerializer(detail).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(request=None, responses={200: OrderServiceDetailSerializer})
    @action(detail=True, methods=['post'], url_path='auto-assign')
    def auto_assign_technician(self, request, uuid=None):
        """Selecciona y asigna automaticamente el mejor tecnico disponible. Solo admin."""
        order = get_object_or_404(self.get_queryset(), uuid=uuid)
        try:
            detail = ServiceAssignmentCommands.auto_assign_technician(
                order=order,
                assigned_by=request.user,
            )
            return Response(OrderServiceDetailSerializer(detail).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(request=None, responses={200: OrderServiceDetailSerializer})
    @action(detail=True, methods=['post'], url_path='unassign-technician')
    def unassign_technician(self, request, uuid=None):
        """Cancela la asignacion de tecnico de la orden. Solo admin."""
        order = get_object_or_404(self.get_queryset(), uuid=uuid)
        try:
            detail = ServiceAssignmentCommands.unassign_technician(
                order=order,
                unassigned_by=request.user,
                notes=request.data.get('notes', ''),
            )
            return Response(OrderServiceDetailSerializer(detail).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(request=PriorityChangeInputSerializer, responses={200: OrderServiceDetailSerializer})
    @action(detail=True, methods=['post'], url_path='change-priority')
    def change_priority(self, request, uuid=None):
        """Cambia la prioridad de la orden de servicio. Solo admin."""
        order = get_object_or_404(self.get_queryset(), uuid=uuid)
        serializer = PriorityChangeInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            detail = ServiceAssignmentCommands.change_priority(
                order=order,
                priority=serializer.validated_data['priority'],
                changed_by=request.user,
            )
            return Response(OrderServiceDetailSerializer(detail).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(responses={200: TechnicianCandidateSerializer(many=True)})
    @action(detail=True, methods=['get'], url_path='available-technicians')
    def available_technicians(self, request, uuid=None):
        """
        Lista todos los tecnicos activos para asignacion manual. No se filtra por
        especialidad/categoria -- es el administrador quien decide si un tecnico
        esta calificado para la orden, no un filtro automatico. La asignacion
        automatica (auto-assign) si sigue exigiendo coincidencia de categoria.
        """
        get_object_or_404(self.get_queryset(), uuid=uuid)
        candidates = TechnicianSelector.get_all_active_technicians()
        return Response(TechnicianCandidateSerializer(candidates, many=True).data)

    @extend_schema(responses={200: ServiceAssignmentQueueSerializer(many=True)})
    @action(detail=False, methods=['get'], url_path='assignment-queue')
    def assignment_queue(self, request):
        """
        Tablero de Asignacion de Tecnicos (/panel/asignacion-tecnicos): version liviana del
        listado con los filtros de get_queryset() (priority/has_technician/category/search).
        Solo admin -- ver get_permissions.
        """
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(ServiceAssignmentQueueSerializer(page, many=True).data)
        return Response(ServiceAssignmentQueueSerializer(qs, many=True).data)

    @action(detail=True, methods=['post'], url_path='confirm-cod')
    def confirm_cod(self, request, uuid=None):
        """
        Confirma pago en sitio (contra entrega) para una orden de servicio tecnico.
        Activa el ServiceBooking y registra la transaccion COD.
        POST /api/v1/orders/service-orders/:uuid/confirm-cod/
        """
        from payment.cod.services.commands import CodCommands
        from payment.models import CodTransaction

        order = get_object_or_404(self.get_queryset(), uuid=uuid)

        if order.user != request.user:
            return Response(
                {'detail': 'No tienes permiso sobre esta orden.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if order.status != Order.STATUS_PENDING_PAYMENT:
            return Response(
                {'detail': 'La orden no esta en estado pendiente.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if CodTransaction.objects.filter(order=order).exists():
            return Response(
                {'detail': 'Esta orden ya tiene un pago en sitio registrado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # Bug real (F1 auditoria E2E): la Order de un servicio tecnico se crea
            # antes de elegir metodo de pago, asi que payment_method quedaba en el
            # default del modelo ('WOMPI') aunque el cliente pagara en sitio. Fijarlo
            # aqui, en el unico lugar donde "pagar en sitio" se confirma de verdad.
            if order.payment_method != 'COD':
                order.payment_method = 'COD'
                order.save(update_fields=['payment_method'])

            ServiceCommands.confirm_slot_on_payment(order)
            CodCommands.confirm_order(order)

        return Response(
            {'detail': 'Pago en sitio confirmado. El servicio ha sido agendado.'},
            status=status.HTTP_200_OK,
        )
