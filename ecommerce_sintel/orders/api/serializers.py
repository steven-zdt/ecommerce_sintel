from rest_framework import serializers
from orders.models import (
    Order,
    OrderItem,
    ShippingAddress,
    Coupon,
    Shipment,
    ShipmentTimeline,
    ShipmentTrackingEvent,
)

class ShippingAddressSerializer(serializers.ModelSerializer):
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    address_line_2 = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    state = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    label = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')

    class Meta:
        model = ShippingAddress
        fields = [
            'id', 'uuid', 'label', 'full_name', 'address_line_1', 'address_line_2',
            'city', 'state', 'postal_code', 'country', 'phone_number', 'is_default'
        ]
        read_only_fields = ['id', 'uuid']

    def validate_phone_number(self, value):
        phone = ''.join(ch for ch in str(value or '') if ch.isdigit())
        if len(phone) != 10 or not phone.startswith('3'):
            raise serializers.ValidationError(
                'Ingresa un celular colombiano valido de 10 digitos, iniciando en 3.'
            )
        return phone

    def validate_country(self, value):
        country = str(value or '').strip()
        if country.upper() in {'CO', 'COL'}:
            return 'Colombia'
        if country.lower() != 'colombia':
            raise serializers.ValidationError('Por ahora solo se admiten envios dentro de Colombia.')
        return 'Colombia'

    def validate(self, attrs):
        text_fields = [
            'full_name', 'address_line_1', 'address_line_2',
            'city', 'state', 'postal_code', 'country',
        ]
        for field in text_fields:
            if field in attrs and attrs[field] is not None:
                attrs[field] = str(attrs[field]).strip()

        # En un PATCH parcial (self.partial=True) un campo ausente de attrs
        # simplemente no se esta tocando -- solo se exige no-vacio si el campo
        # SI vino en la request, o si esto es una creacion/PUT completo (donde
        # los 3 son siempre obligatorios). Bug real encontrado 2026-07-17: un
        # PATCH solo con {is_default: true} (ej. el action set-default) fallaba
        # con 400 porque esta validacion no distinguia partial de full update.
        for field in ('full_name', 'address_line_1', 'city'):
            if field in attrs:
                if not attrs[field]:
                    raise serializers.ValidationError({field: 'Este campo es requerido.'})
            elif not self.partial:
                raise serializers.ValidationError({field: 'Este campo es requerido.'})

        return attrs

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['uuid', 'item_name', 'sku', 'quantity', 'price']
        read_only_fields = fields

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_address = ShippingAddressSerializer(read_only=True)
    shipment = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'uuid', 'status', 'payment_method', 'total_amount',
            'discount_amount', 'tracking_number', 'shipping_address',
            'items', 'shipment', 'created_at', 'user',
        ]
        read_only_fields = fields

    def get_user(self, obj):
        from accounts.services.profile_resolver import ProfileResolver
        profile = ProfileResolver.get_profile(obj.user)
        return {
            'full_name': obj.user.get_full_name() or obj.user.email,
            'first_name': profile.first_name if profile else '',
            'last_name': profile.last_name if profile else '',
            'email': obj.user.email,
            'phone_number': profile.phone_number if profile else None,
        }

    def get_shipment(self, obj):
        try:
            shipment = obj.shipment
        except Shipment.DoesNotExist:
            return None
        return ShipmentSerializer(shipment).data

class ShipmentSerializer(serializers.ModelSerializer):
    dispatch_center = serializers.CharField(source='dispatch_center.name', read_only=True, default='')
    carrier = serializers.CharField(source='carrier.name', read_only=True, default='')
    driver = serializers.CharField(source='driver.name', read_only=True, default='')
    dispatcher_name = serializers.SerializerMethodField()
    dispatcher_uuid = serializers.SerializerMethodField()
    responsible_email = serializers.ReadOnlyField(source='responsible.email', default='')
    shipping_method_display = serializers.CharField(source='get_shipping_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Shipment
        fields = [
            'uuid', 'order', 'shipment_number', 'status', 'status_display',
            'dispatch_center', 'carrier', 'driver', 'vehicle',
            'assigned_dispatcher', 'dispatcher_name', 'dispatcher_uuid', 'responsible_email',
            'shipping_method', 'shipping_method_display', 'tracking_code',
            'estimated_delivery', 'actual_delivery', 'dispatch_scheduled_at', 'route',
            'package_type', 'package_weight', 'package_volume', 'package_dimensions',
            'evidence_photos', 'delivery_signature', 'customer_confirmed_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_dispatcher_name(self, obj):
        if not obj.assigned_dispatcher:
            return ''
        user = obj.assigned_dispatcher.user
        return user.get_full_name() or user.email

    def get_dispatcher_uuid(self, obj):
        return str(obj.assigned_dispatcher.uuid) if obj.assigned_dispatcher else None


class ShipmentOrderSummarySerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    status = serializers.CharField()
    user_email = serializers.ReadOnlyField(source='user.email')
    user_name = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    shipping_address = ShippingAddressSerializer(read_only=True)

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    def get_items_count(self, obj):
        # N+1 fix: uses prefetched items instead of issuing a COUNT query per shipment
        return sum(1 for i in obj.items.all() if i.variant_id is not None)


class ShipmentBoardSerializer(ShipmentSerializer):
    order = ShipmentOrderSummarySerializer(read_only=True)

    class Meta(ShipmentSerializer.Meta):
        fields = ShipmentSerializer.Meta.fields + ['order']
        read_only_fields = fields

class ShipmentTimelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentTimeline
        fields = [
            'id', 'order', 'shipment', 'event_type', 'comment',
            'location', 'ip_address', 'metadata', 'created_at',
        ]
        read_only_fields = fields

class ShipmentTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentTrackingEvent
        fields = [
            'id', 'order', 'shipment', 'lat', 'lng', 'accuracy',
            'timestamp', 'metadata', 'created_at',
        ]
        read_only_fields = fields

class OrderActionCommentSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default='')

class OrderTimelineInputSerializer(serializers.Serializer):
    event_type = serializers.CharField(max_length=128)
    comment = serializers.CharField(required=False, allow_blank=True, default='')
    location = serializers.CharField(required=False, allow_blank=True, default='')
    ip_address = serializers.IPAddressField(required=False, allow_null=True)
    metadata = serializers.JSONField(required=False, default=dict)

class OrderTrackingInputSerializer(serializers.Serializer):
    lat = serializers.DecimalField(max_digits=9, decimal_places=6)
    lng = serializers.DecimalField(max_digits=9, decimal_places=6)
    accuracy = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, default=0.0)
    timestamp = serializers.DateTimeField(required=False)
    metadata = serializers.JSONField(required=False, default=dict)

class AssignDispatchCenterSerializer(serializers.Serializer):
    dispatch_center_uuid = serializers.UUIDField()

class AssignCarrierSerializer(serializers.Serializer):
    carrier_uuid = serializers.UUIDField()

class AssignDriverSerializer(serializers.Serializer):
    driver_uuid = serializers.UUIDField()

class AssignDispatcherSerializer(serializers.Serializer):
    dispatcher_profile_uuid = serializers.UUIDField()

class PackingInputSerializer(serializers.Serializer):
    package_type = serializers.CharField(required=False, allow_blank=True, default='')
    package_weight = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)
    package_volume = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)
    package_dimensions = serializers.CharField(required=False, allow_blank=True, default='')
    evidence_photos = serializers.ListField(child=serializers.URLField(), required=False, default=list)
    comment = serializers.CharField(required=False, allow_blank=True, default='')

class ScheduleDispatchSerializer(serializers.Serializer):
    shipping_method = serializers.ChoiceField(choices=Shipment.SHIPPING_METHOD_CHOICES, required=False, allow_blank=True, default='')
    dispatch_scheduled_at = serializers.DateTimeField(required=False, allow_null=True)
    estimated_delivery = serializers.DateTimeField(required=False, allow_null=True)
    route = serializers.CharField(required=False, allow_blank=True, default='')

class OrderCreateInputSerializer(serializers.Serializer):
    shipping_address_uuid = serializers.UUIDField()
    coupon_code = serializers.CharField(required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(
        choices=[code for code, _ in Order.PAYMENT_METHOD_CHOICES]
    )
