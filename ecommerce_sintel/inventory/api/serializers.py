from rest_framework import serializers
from inventory.models import StockRecord, InventoryTransaction
from inventory.services.selectors import StockRecordSelector


class StockRecordListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        data = list(data)
        self.child._variant_cache = StockRecordSelector.batch_load_item_variants(data)
        return super().to_representation(data)


class StockRecordSerializer(serializers.ModelSerializer):
    item_name = serializers.SerializerMethodField()
    content_type_label = serializers.SerializerMethodField()

    class Meta:
        model = StockRecord
        list_serializer_class = StockRecordListSerializer
        fields = [
            'id', 'uuid', 'sku', 'stock', 'is_active',
            'created_at', 'updated_at', 'item_name', 'content_type_label',
        ]
        read_only_fields = [
            'id', 'uuid', 'sku', 'stock', 'is_active',
            'created_at', 'updated_at', 'item_name', 'content_type_label',
        ]

    def get_item_name(self, obj):
        # En listados, _variant_cache viene precargado por StockRecordListSerializer
        # (1 query por content_type distinto). En retrieve() de un solo objeto no
        # hay cache -- se resuelve directo, una unica consulta es aceptable ahi.
        cache = getattr(self, '_variant_cache', None)
        if cache is not None:
            variant = cache.get((obj.content_type_id, obj.object_id))
        else:
            model_class = obj.content_type.model_class()
            variant = model_class.objects.filter(uuid=obj.object_id).first() if model_class else None
        return str(variant) if variant is not None else obj.sku

    def get_content_type_label(self, obj):
        _labels = {
            'productvariant': 'Producto',
            'servicevariant': 'Servicio',
            'equipmentvariant': 'Equipo',
        }
        try:
            return _labels.get(obj.content_type.model, 'Item')
        except Exception:
            return 'Item'


class InventoryTransactionSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    uuid = serializers.UUIDField(read_only=True)
    movement_type = serializers.CharField(read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    balance_after = serializers.IntegerField(read_only=True)
    reference = serializers.CharField(read_only=True, allow_null=True, required=False)
    created_at = serializers.DateTimeField(read_only=True)


class StockAdjustmentInputSerializer(serializers.Serializer):
    movement_type = serializers.ChoiceField(choices=['ENTRY', 'EXIT'])
    quantity = serializers.IntegerField(min_value=1)
    reference = serializers.CharField(max_length=255, required=False, allow_blank=True)


class StockRecordCreateSerializer(serializers.Serializer):
    variant_type = serializers.ChoiceField(
        choices=['product_variant', 'service_variant', 'equipment_variant']
    )
    variant_uuid = serializers.UUIDField()
    sku = serializers.CharField(max_length=100)
    initial_stock = serializers.IntegerField(min_value=0, default=0, required=False)
