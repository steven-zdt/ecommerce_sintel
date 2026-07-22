from rest_framework import mixins, viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django.contrib.contenttypes.models import ContentType

from users.api.permissions import IsAdminUser
from inventory.models import StockRecord, InventoryTransaction
from inventory.services import StockRecordSelector, InventorySelector, InventoryCommands
from inventory.api.serializers import (
    StockRecordSerializer,
    InventoryTransactionSerializer,
    StockAdjustmentInputSerializer,
    StockRecordCreateSerializer,
)
from inventory.services.dtos import StockAdjustmentDTO


class StockRecordViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Stock record management.
    - GET  /stock-records/          → list all records (any authenticated user)
    - POST /stock-records/          → create a new stock record (admin only)
    - GET  /stock-records/{uuid}/   → retrieve a single record
    - GET  /stock-records/{uuid}/movements/   → movement history
    - POST /stock-records/{uuid}/adjust-stock/ → manual ENTRY or EXIT (admin only)
    """
    serializer_class = StockRecordSerializer
    lookup_field = 'uuid'
    queryset = StockRecord.objects.none()

    def get_queryset(self):
        return StockRecordSelector.list_all_for_admin()

    def get_permissions(self):
        if self.action in ['create', 'adjust_stock']:
            return [IsAdminUser()]
        return [IsAdminUser()]

    def handle_exception(self, exc):
        from inventory.services.kardex import InsufficientStockError
        from django.core.exceptions import ValidationError as DjangoValidationError

        if isinstance(exc, InsufficientStockError):
            return Response(
                {'detail': exc.message if hasattr(exc, 'message') else str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
        if isinstance(exc, DjangoValidationError):
            return Response(
                {'detail': exc.message if hasattr(exc, 'message') else str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().handle_exception(exc)

    # ------------------------------------------------------------------
    # CREATE  POST /stock-records/
    # ------------------------------------------------------------------
    def create(self, request, *args, **kwargs):
        """Create a StockRecord for a ProductVariant, ServiceVariant or EquipmentVariant."""
        serializer = StockRecordCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        variant_type  = serializer.validated_data['variant_type']
        variant_uuid  = serializer.validated_data['variant_uuid']
        sku           = serializer.validated_data['sku']
        initial_stock = serializer.validated_data.get('initial_stock', 0)

        type_map = {
            'product_variant':   ('shop',                'productvariant'),
            'service_variant':   ('technical_services',  'servicevariant'),
            'equipment_variant': ('renting',             'equipmentvariant'),
        }
        app_label, model_name = type_map[variant_type]

        try:
            stock_record = InventoryCommands.create_stock_record(
                app_label=app_label,
                model_name=model_name,
                variant_uuid=variant_uuid,
                sku=sku,
                initial_stock=initial_stock,
            )
        except ValueError as exc:
            msg = str(exc)
            code = status.HTTP_409_CONFLICT if 'ya existe' in msg.lower() or 'ya esta' in msg.lower() else status.HTTP_400_BAD_REQUEST
            return Response({'detail': msg}, status=code)

        return Response(
            StockRecordSerializer(stock_record).data,
            status=status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------------------
    # GET  /stock-records/{uuid}/movements/
    # ------------------------------------------------------------------
    @extend_schema(responses={200: InventoryTransactionSerializer(many=True)})
    @action(detail=True, methods=['get'], url_path='movements')
    def movements(self, request, uuid=None):
        """Movement history for this stock record."""
        stock_record = self.get_object()
        qs = InventorySelector.list_movements(stock_record.id)

        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(InventoryTransactionSerializer(page, many=True).data)
        return Response(InventoryTransactionSerializer(qs, many=True).data)

    # ------------------------------------------------------------------
    # POST /stock-records/{uuid}/adjust-stock/
    # ------------------------------------------------------------------
    @extend_schema(request=StockAdjustmentInputSerializer, responses={201: InventoryTransactionSerializer})
    @action(
        detail=True,
        methods=['post'],
        url_path='adjust-stock',
        permission_classes=[IsAdminUser],
    )
    def adjust_stock(self, request, uuid=None):
        """Manual ENTRY or EXIT against an existing stock record."""
        stock_record = self.get_object()
        serializer = StockAdjustmentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data          = serializer.validated_data
        movement_type = data['movement_type']
        quantity      = data['quantity']
        reference     = data.get('reference') or 'Ajuste manual'

        dto = StockAdjustmentDTO(
            stock_record_uuid=stock_record.uuid,
            quantity=quantity,
            reference=reference,
        )

        tx_dto = (
            InventoryCommands.register_entry(dto)
            if movement_type == 'ENTRY'
            else InventoryCommands.register_exit(dto)
        )

        from security.models import SecurityEvent
        from security.services.commands import SecurityCommands
        SecurityCommands.log_event(
            SecurityEvent.INVENTORY_MANUAL_ADJUSTMENT, request=request, user=request.user,
            metadata={
                'stock_record': str(stock_record.uuid), 'movement_type': movement_type,
                'quantity': str(quantity), 'reference': reference,
            },
        )
        return Response(InventoryTransactionSerializer(tx_dto).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------

class InventoryTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only view of all inventory transactions."""
    queryset = InventoryTransaction.objects.all().order_by('-created_at')
    serializer_class = InventoryTransactionSerializer
    lookup_field = 'uuid'
