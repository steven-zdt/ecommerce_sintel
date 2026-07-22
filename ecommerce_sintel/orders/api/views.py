from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404

from users.api.permissions import IsBuyerOrAdmin
from orders.models import Order, ShippingAddress
from orders.services import OrderSelector, ShippingAddressSelector, OrderCommands, ShippingAddressCommands
from orders.services.fulfillment.commands import FulfillmentCommands
from orders.services.fulfillment.timeline import ShipmentTimelineCommands
from orders.services.fulfillment.tracking import ShipmentTrackingCommands
from orders.services.fulfillment.selectors import FulfillmentSelector
from orders.api.serializers import (
    OrderSerializer,
    ShippingAddressSerializer,
    OrderCreateInputSerializer,
    OrderActionCommentSerializer,
    OrderTimelineInputSerializer,
    OrderTrackingInputSerializer,
    AssignDispatchCenterSerializer,
    AssignCarrierSerializer,
    AssignDriverSerializer,
    AssignDispatcherSerializer,
    PackingInputSerializer,
    ScheduleDispatchSerializer,
    ShipmentTimelineSerializer,
    ShipmentTrackingSerializer,
    ShipmentBoardSerializer,
)


class ShippingAddressViewSet(viewsets.ModelViewSet):
    """
    ViewSet for individual users to manage their shipping addresses.
    Create/update pasan por ShippingAddressCommands para garantizar que solo
    una direccion por usuario tenga is_default=True a la vez.
    """
    serializer_class = ShippingAddressSerializer
    lookup_field = 'uuid'
    permission_classes = [IsBuyerOrAdmin]

    def get_queryset(self):
        if self.request.user.is_staff:
            return ShippingAddress.objects.filter(is_deleted=False)
        return ShippingAddressSelector.list_for_user(self.request.user)

    def perform_create(self, serializer):
        address = ShippingAddressCommands.create(self.request.user, **serializer.validated_data)
        serializer.instance = address

    def perform_update(self, serializer):
        address = ShippingAddressCommands.update(serializer.instance, **serializer.validated_data)
        serializer.instance = address

    @action(detail=True, methods=['post'], url_path='set-default')
    def set_default(self, request, uuid=None):
        """Marca esta direccion como la predeterminada (des-marca cualquier otra)."""
        address = get_object_or_404(self.get_queryset(), uuid=uuid)
        ShippingAddressCommands.set_as_default(request.user, address)
        return Response(ShippingAddressSerializer(address).data)

class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing and creating orders.
    Creation is handled via custom action create_from_cart.
    """
    serializer_class = OrderSerializer
    lookup_field = 'uuid'
    permission_classes = [IsBuyerOrAdmin]

    ACTION_THROTTLE_SCOPES = {
        'create_from_cart': 'order_create',
    }

    def get_throttles(self):
        from rest_framework.throttling import ScopedRateThrottle
        scope = self.ACTION_THROTTLE_SCOPES.get(self.action)
        if not scope:
            return []
        self.throttle_scope = scope
        return [ScopedRateThrottle()]

    def get_queryset(self):
        if self.request.user.is_staff:
            return OrderSelector.list_all_for_admin()
        return OrderSelector.list_for_user(self.request.user)

    @extend_schema(
        request=OrderCreateInputSerializer,
        responses={201: OrderSerializer}
    )
    @action(detail=False, methods=['post'])
    def create_from_cart(self, request):
        """
        Creates a new order using the current user's cart.
        """
        input_serializer = OrderCreateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        
        data = input_serializer.validated_data
        address_uuid   = data['shipping_address_uuid']
        coupon_code    = data.get('coupon_code')
        payment_method = data.get('payment_method', 'WOMPI')

        address = get_object_or_404(ShippingAddress, uuid=address_uuid, is_deleted=False)

        if address.user != request.user and not request.user.is_staff:
            return Response(
                {"detail": "Direccion de envio no valida para este usuario."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            order = OrderCommands.create_from_cart(
                user=request.user,
                shipping_address=address,
                coupon_code=coupon_code,
                payment_method=payment_method,
            )
            output_serializer = OrderSerializer(order)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _require_staff(self):
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            raise PermissionDenied('Acceso restringido: solo personal autorizado puede realizar esta acción.')

    def _get_order(self, uuid):
        return get_object_or_404(self.get_queryset(), uuid=uuid)

    @extend_schema(
        request=OrderActionCommentSerializer,
        responses={200: OrderSerializer}
    )
    @action(detail=True, methods=['post'], url_path='prepare')
    def prepare(self, request, uuid=None):
        self._require_staff()
        order = self._get_order(uuid)
        serializer = OrderActionCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = FulfillmentCommands.start_preparation(
            order,
            created_by=request.user,
            comment=serializer.validated_data.get('comment', ''),
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=PackingInputSerializer,
        responses={200: OrderSerializer}
    )
    @action(detail=True, methods=['post'], url_path='pack')
    def pack(self, request, uuid=None):
        self._require_staff()
        order = self._get_order(uuid)
        serializer = PackingInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        comment = data.pop('comment', '')
        order = FulfillmentCommands.complete_packing(
            order,
            created_by=request.user,
            comment=comment,
            **data,
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=AssignDispatchCenterSerializer,
        responses={200: OrderSerializer}
    )
    @action(detail=True, methods=['post'], url_path='assign-dispatch-center')
    def assign_dispatch_center(self, request, uuid=None):
        self._require_staff()
        order = self._get_order(uuid)
        serializer = AssignDispatchCenterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = FulfillmentCommands.assign_dispatch_center(
            order,
            dispatch_center_uuid=serializer.validated_data['dispatch_center_uuid'],
            assigned_by=request.user,
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=AssignCarrierSerializer,
        responses={200: OrderSerializer}
    )
    @action(detail=True, methods=['post'], url_path='assign-carrier')
    def assign_carrier(self, request, uuid=None):
        self._require_staff()
        order = self._get_order(uuid)
        serializer = AssignCarrierSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = FulfillmentCommands.assign_carrier(
            order,
            carrier_uuid=serializer.validated_data['carrier_uuid'],
            assigned_by=request.user,
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=AssignDriverSerializer,
        responses={200: OrderSerializer}
    )
    @action(detail=True, methods=['post'], url_path='assign-driver')
    def assign_driver(self, request, uuid=None):
        self._require_staff()
        order = self._get_order(uuid)
        serializer = AssignDriverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = FulfillmentCommands.assign_driver(
            order,
            driver_uuid=serializer.validated_data['driver_uuid'],
            assigned_by=request.user,
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=AssignDispatcherSerializer,
        responses={200: OrderSerializer}
    )
    @action(detail=True, methods=['post'], url_path='assign-dispatcher')
    def assign_dispatcher(self, request, uuid=None):
        self._require_staff()
        order = self._get_order(uuid)
        serializer = AssignDispatcherSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order = FulfillmentCommands.assign_dispatcher(
                order,
                dispatcher_profile_uuid=serializer.validated_data['dispatcher_profile_uuid'],
                assigned_by=request.user,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=ScheduleDispatchSerializer,
        responses={200: OrderSerializer}
    )
    @action(detail=True, methods=['post'], url_path='schedule-dispatch')
    def schedule_dispatch(self, request, uuid=None):
        self._require_staff()
        order = self._get_order(uuid)
        serializer = ScheduleDispatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = FulfillmentCommands.schedule_dispatch(
            order, created_by=request.user, **serializer.validated_data,
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)

    @extend_schema(responses={200: OrderSerializer})
    @action(detail=True, methods=['post'], url_path='confirm-delivery')
    def confirm_delivery(self, request, uuid=None):
        order = self._get_order(uuid)
        if order.user != request.user and not request.user.is_staff:
            raise PermissionDenied('Solo el cliente dueño del pedido puede confirmar la entrega.')
        try:
            order = FulfillmentCommands.confirm_delivery_by_customer(order, actor=request.user)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)

    @extend_schema(responses={200: ShipmentBoardSerializer(many=True)})
    @action(detail=False, methods=['get'], url_path='operations')
    def operations_board(self, request):
        """Bandeja operativa de Shop Operations (Fase 4) -- solo ordenes con Shipment ya creado (pago confirmado)."""
        self._require_staff()
        shipments = FulfillmentSelector.list_shipments_for_admin(
            status=request.query_params.get('status', ''),
            search=request.query_params.get('search', ''),
            date_from=request.query_params.get('date_from') or None,
            date_to=request.query_params.get('date_to') or None,
        )
        return Response(ShipmentBoardSerializer(shipments, many=True).data)

    @extend_schema(responses={200: dict})
    @action(detail=False, methods=['get'], url_path='operations-dashboard')
    def operations_dashboard(self, request):
        self._require_staff()
        return Response(FulfillmentSelector.dashboard_metrics())

    @extend_schema(
        request=OrderActionCommentSerializer,
        responses={200: OrderSerializer}
    )
    @action(detail=True, methods=['post'], url_path='dispatch')
    def dispatch_order(self, request, uuid=None):
        self._require_staff()
        order = self._get_order(uuid)
        serializer = OrderActionCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order = FulfillmentCommands.dispatch(
                order,
                created_by=request.user,
                comment=serializer.validated_data.get('comment', ''),
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=OrderActionCommentSerializer,
        responses={200: OrderSerializer}
    )
    @action(detail=True, methods=['post'], url_path='in-transit')
    def in_transit(self, request, uuid=None):
        self._require_staff()
        order = self._get_order(uuid)
        serializer = OrderActionCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = FulfillmentCommands.mark_in_transit(
            order,
            created_by=request.user,
            comment=serializer.validated_data.get('comment', ''),
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=OrderActionCommentSerializer,
        responses={200: OrderSerializer}
    )
    @action(detail=True, methods=['post'], url_path='out-for-delivery')
    def out_for_delivery(self, request, uuid=None):
        self._require_staff()
        order = self._get_order(uuid)
        serializer = OrderActionCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = FulfillmentCommands.mark_out_for_delivery(
            order,
            created_by=request.user,
            comment=serializer.validated_data.get('comment', ''),
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=OrderActionCommentSerializer,
        responses={200: OrderSerializer}
    )
    @action(detail=True, methods=['post'], url_path='deliver')
    def deliver(self, request, uuid=None):
        self._require_staff()
        order = self._get_order(uuid)
        serializer = OrderActionCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = FulfillmentCommands.deliver(
            order,
            created_by=request.user,
            comment=serializer.validated_data.get('comment', ''),
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=OrderActionCommentSerializer,
        responses={200: OrderSerializer}
    )
    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, uuid=None):
        self._require_staff()
        order = self._get_order(uuid)
        serializer = OrderActionCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = FulfillmentCommands.complete_order(
            order,
            created_by=request.user,
            comment=serializer.validated_data.get('comment', ''),
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)

    @extend_schema(responses={200: ShipmentTimelineSerializer(many=True)})
    @action(detail=True, methods=['get'], url_path='timeline')
    def timeline(self, request, uuid=None):
        order = self._get_order(uuid)
        timeline = ShipmentTimelineCommands.get_timeline(order)
        events = ShipmentTimelineSerializer(timeline, many=True).data

        # F3 (auditoria E2E): las ordenes de Servicios Tecnicos no tienen shipment
        # fisico, asi que ShipmentTimeline siempre queda vacio para ellas -- el
        # historial real vive en ServiceOperationEvent. En vez de mantener dos
        # timelines separados (uno por panel), este endpoint fusiona ambos por
        # fecha para que "Gestionar Ordenes" muestre el mismo historial que
        # "Operaciones de Servicios", sin duplicar el modelo de eventos.
        operation = getattr(order, 'service_operation', None)
        if operation is not None:
            events = list(events) + [
                {
                    'id': None,
                    'order': order.id,
                    'shipment': None,
                    'event_type': ev.event_type,
                    'comment': ev.description,
                    'location': '',
                    'ip_address': None,
                    'metadata': ev.metadata,
                    'created_at': ev.created_at,
                }
                for ev in operation.timeline.all()
            ]
            events.sort(key=lambda e: e['created_at'])

        return Response(events)

    @extend_schema(
        request=OrderTimelineInputSerializer,
        responses={201: ShipmentTimelineSerializer}
    )
    @action(detail=True, methods=['post'], url_path='add-timeline-event')
    def add_timeline_event(self, request, uuid=None):
        self._require_staff()
        order = self._get_order(uuid)
        serializer = OrderTimelineInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = ShipmentTimelineCommands.add_event(
            order=order,
            shipment=getattr(order, 'shipment', None),
            event_type=serializer.validated_data['event_type'],
            comment=serializer.validated_data.get('comment', ''),
            location=serializer.validated_data.get('location', ''),
            ip_address=serializer.validated_data.get('ip_address'),
            metadata=serializer.validated_data.get('metadata'),
            created_by=request.user,
        )
        return Response(ShipmentTimelineSerializer(event).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses={200: ShipmentTrackingSerializer(many=True)})
    @action(detail=True, methods=['get'], url_path='tracking')
    def tracking(self, request, uuid=None):
        order = self._get_order(uuid)
        events = ShipmentTrackingCommands.list_tracking_points(order)
        return Response(ShipmentTrackingSerializer(events, many=True).data)

    @extend_schema(
        request=OrderTrackingInputSerializer,
        responses={201: ShipmentTrackingSerializer}
    )
    @action(detail=True, methods=['post'], url_path='add-tracking-point')
    def add_tracking_point(self, request, uuid=None):
        self._require_staff()
        order = self._get_order(uuid)
        serializer = OrderTrackingInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tracking_event = ShipmentTrackingCommands.create_tracking_point(
            order=order,
            lat=float(serializer.validated_data['lat']),
            lng=float(serializer.validated_data['lng']),
            accuracy=float(serializer.validated_data.get('accuracy', 0.0)),
            timestamp=serializer.validated_data.get('timestamp'),
            metadata=serializer.validated_data.get('metadata'),
            created_by=request.user,
            shipment=getattr(order, 'shipment', None),
        )
        return Response(ShipmentTrackingSerializer(tracking_event).data, status=status.HTTP_201_CREATED)

