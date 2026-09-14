from decimal import Decimal
from django.utils import timezone
from rest_framework import serializers
from cart.models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    variant_sku  = serializers.SerializerMethodField()
    unit_price   = serializers.SerializerMethodField()
    subtotal     = serializers.SerializerMethodField()
    item_type    = serializers.SerializerMethodField()
    variant_uuid = serializers.SerializerMethodField()
    unit_price_with_tax = serializers.SerializerMethodField()
    final_price         = serializers.SerializerMethodField()
    image                = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            'uuid', 'item_type', 'variant_uuid',
            'product_name', 'variant_sku', 'image',
            'quantity', 'unit_price', 'subtotal',
            'unit_price_with_tax', 'final_price',
            'created_at',
        ]

    def _effective_price(self, variant):
        now = timezone.now()
        if (variant.discounted_price is not None and
                (not variant.discount_start_date or variant.discount_start_date <= now) and
                (not variant.discount_end_date   or variant.discount_end_date   >= now)):
            return variant.discounted_price
        return variant.price

    def get_product_name(self, obj):
        if obj.variant:
            return obj.variant.product.name
        if obj.service_variant:
            return obj.service_variant.service.name
        return ''

    def get_variant_sku(self, obj):
        if obj.variant:
            return obj.variant.sku
        if obj.service_variant:
            return obj.service_variant.sku
        return ''

    def get_variant_uuid(self, obj):
        if obj.variant:
            return str(obj.variant.uuid)
        if obj.service_variant:
            return str(obj.service_variant.uuid)
        return None

    def get_image(self, obj):
        """Imagen principal: is_primary si existe, si no la primera disponible, si no None."""
        images = None
        if obj.variant:
            images = list(obj.variant.product.images.all())
        elif obj.service_variant:
            images = list(obj.service_variant.service.images.all())
        if not images:
            return None
        primary = next((img for img in images if img.is_primary), images[0])
        request = self.context.get('request')
        url = primary.image.url
        return request.build_absolute_uri(url) if request else url

    def get_item_type(self, obj):
        if obj.variant:
            return 'product'
        if obj.service_variant:
            return 'service'
        return 'unknown'

    def get_unit_price(self, obj):
        if obj.variant:
            price = Decimal(str(self._effective_price(obj.variant)))
            return str(price.quantize(Decimal('0.01')))
        if obj.service_variant:
            sv = obj.service_variant
            if sv.fixed_price is not None:
                price = Decimal(str(sv.fixed_price))
                return str(price.quantize(Decimal('0.01')))
            try:
                from technical_services.services import ServiceSelector
                price = Decimal(str(ServiceSelector.get_variant_quotation(sv)['total_price']))
                return str(price.quantize(Decimal('0.01')))
            except Exception:
                return '0.00'
        return '0.00'

    def get_subtotal(self, obj):
        price = Decimal(self.get_unit_price(obj))
        return str((price * obj.quantity).quantize(Decimal('0.01')))

    def get_unit_price_with_tax(self, obj):
        """Regla 4: Calcular usando PricingService.calculate_variant_price(variant, include_active_taxes=True)"""
        if obj.variant:
            from shop.services.pricing_service import PricingService
            # N+1 fix: use pre-fetched taxes from serializer context if available
            active_taxes = self.context.get('active_taxes')
            price = PricingService.calculate_variant_price(
                obj.variant, include_active_taxes=True, active_taxes=active_taxes
            )
            return str(price.quantize(Decimal('0.01')))
        if obj.service_variant:
            # Para servicios, asumimos que el unit_price ya incluye el IVA correspondiente o se trata igual
            price = Decimal(self.get_unit_price(obj))
            return str(price.quantize(Decimal('0.01')))
        return '0.00'

    def get_final_price(self, obj):
        price = Decimal(self.get_unit_price_with_tax(obj))
        return str((price * obj.quantity).quantize(Decimal('0.01')))


class CartSerializer(serializers.ModelSerializer):
    items       = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    total       = serializers.SerializerMethodField()
    total_cart_value = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['uuid', 'items', 'total_items', 'total', 'total_cart_value', 'created_at']
        read_only_fields = fields

    def get_total_items(self, obj):
        return sum(item.quantity for item in obj.items.all())

    def get_total(self, obj):
        # Retorna el total sumando los precios finales calculados con impuestos
        # N+1 fix: pre-fetch active taxes once and reuse across all items
        from shop.services.selectors import TaxSelector
        active_taxes = TaxSelector.list_active()
        total = Decimal('0')
        for item in obj.items.all():
            serializer = CartItemSerializer(item, context={'active_taxes': active_taxes})
            total += Decimal(serializer.data['final_price'])
        return str(total.quantize(Decimal('0.01')))

    def get_total_cart_value(self, obj):
        # Modificación para total_cart_value solicitada en el paso 1
        return self.get_total(obj)


class AddCartItemSerializer(serializers.Serializer):
    variant_uuid         = serializers.UUIDField(required=False)
    service_variant_uuid = serializers.UUIDField(required=False)
    quantity             = serializers.IntegerField(min_value=1, default=1)

    def validate(self, data):
        if not data.get('variant_uuid') and not data.get('service_variant_uuid'):
            raise serializers.ValidationError(
                "Debe proporcionar un variant_uuid o service_variant_uuid."
            )
        return data


class UpdateCartItemSerializer(serializers.Serializer):
    variant_uuid         = serializers.UUIDField(required=False)
    service_variant_uuid = serializers.UUIDField(required=False)
    quantity             = serializers.IntegerField(min_value=0)

    def validate(self, data):
        if not data.get('variant_uuid') and not data.get('service_variant_uuid'):
            raise serializers.ValidationError(
                "Debe proporcionar un variant_uuid o service_variant_uuid."
            )
        return data
