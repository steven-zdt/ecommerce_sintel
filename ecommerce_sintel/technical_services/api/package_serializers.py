"""
technical_services/api/package_serializers.py

Serializers del dominio de Paquetes de Servicio (2026-07-16). Separado de
api/serializers.py siguiendo el mismo patron ya usado para el dominio de
Operaciones (api/operation_serializers.py).
"""
from decimal import Decimal
from rest_framework import serializers
from technical_services.models import (
    ServicePackage, PackageIncludedItem, PackageAdditionalCost,
    ServiceRequestPackage, ServiceRequestAdditionalCost,
)


# ── Output ──────────────────────────────────────────────────────────────────────

class PackageIncludedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageIncludedItem
        fields = ['uuid', 'title', 'description', 'icon', 'position', 'is_active']
        read_only_fields = ['uuid']


class PackageAdditionalCostSerializer(serializers.ModelSerializer):
    cost_type_display = serializers.CharField(source='get_cost_type_display', read_only=True)
    unit_display = serializers.CharField(source='get_unit_display', read_only=True)

    class Meta:
        model = PackageAdditionalCost
        fields = [
            'uuid', 'name', 'description', 'cost_type', 'cost_type_display',
            'price', 'unit', 'unit_display', 'is_required', 'is_default',
            'position', 'is_active',
        ]
        read_only_fields = ['uuid']


class ServicePackageSerializer(serializers.ModelSerializer):
    included_items = serializers.SerializerMethodField()
    additional_costs = serializers.SerializerMethodField()

    class Meta:
        model = ServicePackage
        fields = [
            'uuid', 'name', 'slug', 'description', 'package_type', 'image', 'icon',
            'is_default', 'is_featured', 'is_active', 'position',
            'estimated_duration', 'base_price', 'notes',
            'included_items', 'additional_costs',
        ]
        read_only_fields = ['uuid', 'slug']

    @staticmethod
    def _active(related_manager):
        return [obj for obj in related_manager.all() if obj.is_active]

    def get_included_items(self, obj):
        return PackageIncludedItemSerializer(self._active(obj.included_items), many=True).data

    def get_additional_costs(self, obj):
        return PackageAdditionalCostSerializer(self._active(obj.additional_costs), many=True).data


class ServiceRequestAdditionalCostSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequestAdditionalCost
        fields = ['uuid', 'name_snapshot', 'unit_price_snapshot', 'quantity', 'subtotal_snapshot']
        read_only_fields = fields


class ServiceRequestPackageSerializer(serializers.ModelSerializer):
    additional_costs = ServiceRequestAdditionalCostSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceRequestPackage
        fields = ['uuid', 'package_name_snapshot', 'package_price_snapshot', 'additional_costs']
        read_only_fields = fields


# ── Input (admin CRUD) ──────────────────────────────────────────────────────────

class PackageIncludedItemInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    icon = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class PackageAdditionalCostInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    cost_type = serializers.ChoiceField(choices=PackageAdditionalCost.COST_TYPE_CHOICES, default=PackageAdditionalCost.TYPE_OTHER)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0'))
    unit = serializers.ChoiceField(choices=PackageAdditionalCost.UNIT_CHOICES, default=PackageAdditionalCost.UNIT_FIXED)
    is_required = serializers.BooleanField(default=False, required=False)
    is_default = serializers.BooleanField(default=False, required=False)
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ServicePackageInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    package_type = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    icon = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    is_default = serializers.BooleanField(default=False, required=False)
    is_featured = serializers.BooleanField(default=False, required=False)
    is_active = serializers.BooleanField(default=True, required=False)
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    estimated_duration = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    base_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0'), default=Decimal('0'))
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class ReorderInputSerializer(serializers.Serializer):
    """Payload generico de reorder: lista ordenada de uuids (drag&drop)."""
    ordered_uuids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


# ── Input (wizard: seleccion de paquete + adicionales en la solicitud) ─────────

class AdditionalCostSelectionInputSerializer(serializers.Serializer):
    additional_cost_uuid = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate_additional_cost_uuid(self, value):
        try:
            return PackageAdditionalCost.objects.get(uuid=value, is_deleted=False)
        except PackageAdditionalCost.DoesNotExist:
            raise serializers.ValidationError("El costo adicional seleccionado no existe.")
