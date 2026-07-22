from decimal import Decimal
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from shop.models import Category, Brand, Product, ProductVariant, ProductImage, ProductReview, Tax


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

class CategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True, default=None)

    class Meta:
        model = Category
        fields = (
            'id', 'uuid', 'name', 'slug', 'description', 'image',
            'parent', 'parent_name', 'is_active',
            'meta_title', 'meta_description',
        )


class CategoryInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        required=False,
        allow_null=True
    )
    description = serializers.CharField(required=False, allow_blank=True, default='')
    image = serializers.ImageField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False, default=True)
    # SEO — FASE 4
    meta_title = serializers.CharField(max_length=70, required=False, allow_blank=True, default='')
    meta_description = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("El nombre no puede estar vacio.")
        queryset = Category.objects.filter(name__iexact=value)
        if self.instance and hasattr(self.instance, 'pk') and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            existing = queryset.first()
            raise serializers.ValidationError(
                f"Ya existe una categoria con el nombre '{existing.name}'."
            )
        return value

    def validate_parent(self, value):
        if value is None:
            return value
        if hasattr(self, 'instance') and self.instance and value.id == self.instance.id:
            raise serializers.ValidationError("Una categoria no puede ser su propia categoria padre.")
        return value


# ---------------------------------------------------------------------------
# Brand
# ---------------------------------------------------------------------------

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ('id', 'uuid', 'name', 'slug', 'logo', 'is_active')


class BrandInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    logo = serializers.ImageField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False, default=True)

    def validate_name(self, value):
        value = value.strip()
        qs = Brand.objects.filter(name__iexact=value, is_deleted=False)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(f"Ya existe una marca con el nombre '{value}'.")
        return value


# ---------------------------------------------------------------------------
# Tax
# ---------------------------------------------------------------------------

class TaxSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tax
        fields = ('id', 'uuid', 'name', 'tax_type', 'value', 'is_active')


class TaxInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    tax_type = serializers.ChoiceField(choices=Tax.TaxType.choices)
    value = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=Decimal('0'))
    is_active = serializers.BooleanField(required=False, default=True)


# ---------------------------------------------------------------------------
# Product Image
# ---------------------------------------------------------------------------

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('id', 'uuid', 'image', 'alt_text', 'is_primary', 'display_order')


# ---------------------------------------------------------------------------
# Product Variant
# ---------------------------------------------------------------------------

class ProductVariantSerializer(serializers.ModelSerializer):
    images        = ProductImageSerializer(many=True, read_only=True)
    effective_price = serializers.SerializerMethodField()
    stock         = serializers.SerializerMethodField()
    price_info    = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = (
            'id', 'uuid', 'sku', 'price', 'discounted_price', 'stock', 'is_default',
            'attributes', 'discount_start_date', 'discount_end_date',
            'effective_price', 'price_info', 'images',
            'weight', 'length', 'width', 'height',
        )

    @extend_schema_field(serializers.IntegerField())
    def get_stock(self, obj) -> int:
        from inventory.services.selectors import InventorySelector
        return InventorySelector.get_stock_for_variant(obj)

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_effective_price(self, obj):
        from shop.services.pricing_service import PricingService
        return PricingService.calculate_variant_price(obj)

    @extend_schema_field(serializers.DictField())
    def get_price_info(self, obj):
        """
        Desglose financiero de la variante.

        Estructura de respuesta:
          base_price       — precio de lista configurado
          discounted_price — precio oferta configurado (o null si no aplica)
          has_discount     — True si el descuento esta activo en este momento
          applied_taxes    — lista de impuestos activos del sistema con su monto calculado
          total_tax_amount — suma de todos los impuestos sobre el precio efectivo
          final_price_net  — precio efectivo + total_tax_amount
        """
        from decimal import Decimal
        from shop.services.pricing_service import PricingService
        from shop.services.selectors import TaxSelector

        Q = Decimal('0.01')
        try:
            base_price       = Decimal(str(obj.price)).quantize(Q)
            effective        = PricingService.calculate_variant_price(obj).quantize(Q)
            has_discount     = effective < base_price

            raw_discounted   = obj.discounted_price
            discounted_str   = str(Decimal(str(raw_discounted)).quantize(Q)) if raw_discounted is not None else None

            active_taxes = list(TaxSelector.list_active())
            applied_taxes = []
            total_tax_amount = Decimal('0')
            for tax in active_taxes:
                amount = PricingService.calculate_tax_amount(effective, tax).quantize(Q)
                total_tax_amount += amount
                applied_taxes.append({
                    'name':     tax.name,
                    'tax_type': tax.tax_type,
                    'rate':     str(tax.value),
                    'amount':   str(amount),
                })

            final_price_net = (effective + total_tax_amount).quantize(Q)

            return {
                'base_price':       str(base_price),
                'discounted_price': discounted_str,
                'has_discount':     has_discount,
                'applied_taxes':    applied_taxes,
                'total_tax_amount': str(total_tax_amount.quantize(Q)),
                'final_price_net':  str(final_price_net),
            }
        except Exception:
            return None


class ProductVariantInputSerializer(serializers.Serializer):
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    discounted_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal('0'), allow_null=True, required=False
    )
    is_default = serializers.BooleanField(required=False, default=False)
    stock = serializers.IntegerField(min_value=0, required=False, default=0)
    # Atributos dinamicos — FASE 4
    attributes = serializers.DictField(
        child=serializers.CharField(),
        required=False,
        default=dict,
        help_text='Atributos clave-valor. Ej: {"color": "Rojo", "talla": "M"}.'
    )
    # Descuentos temporales — FASE 4
    discount_start_date = serializers.DateTimeField(allow_null=True, required=False, default=None)
    discount_end_date = serializers.DateTimeField(allow_null=True, required=False, default=None)
    # Logistica (max_digits=12 alineado con el modelo)
    weight = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False, allow_null=True)
    length = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False, allow_null=True)
    width  = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False, allow_null=True)
    height = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False, allow_null=True)

    def validate(self, data):
        start = data.get('discount_start_date')
        end = data.get('discount_end_date')
        if start and end and end <= start:
            raise serializers.ValidationError(
                "discount_end_date debe ser posterior a discount_start_date."
            )
        return data


# ---------------------------------------------------------------------------
# Product Review
# ---------------------------------------------------------------------------

class ProductReviewSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = ProductReview
        fields = ('id', 'uuid', 'user_email', 'rating', 'comment', 'is_verified_purchase', 'created_at')

    def validate(self, data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            product = self.context.get('product') or data.get('product')
            if product and ProductReview.objects.filter(user=request.user, product=product).exists():
                raise serializers.ValidationError("Ya has calificado este producto.")
        return data


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_uuid = serializers.UUIDField(source='category.uuid', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True, allow_null=True)
    brand_uuid = serializers.UUIDField(source='brand.uuid', read_only=True, allow_null=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    avg_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    stock = serializers.SerializerMethodField()
    sku = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            'id', 'uuid', 'name', 'slug', 'short_description', 'description', 'video_url', 'condition',
            'category', 'category_name', 'category_uuid',
            'brand', 'brand_name', 'brand_uuid',
            'is_featured', 'is_active',
            'meta_title', 'meta_description',
            'variants', 'images', 'avg_rating', 'review_count', 'stock', 'sku',
        )

    @extend_schema_field(serializers.CharField())
    def get_sku(self, obj) -> str | None:
        variants = obj.variants.all()
        first = next((variant for variant in variants if variant.is_default), None)
        if first is None:
            first = variants[0] if variants else None
        return first.sku if first else None

    @extend_schema_field(serializers.IntegerField())
    def get_stock(self, obj) -> int:
        from inventory.services.selectors import InventorySelector
        return sum(InventorySelector.get_stock_for_variant(variant) for variant in obj.variants.all())


class ProductInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    category = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=Category.objects.filter(is_active=True)
    )
    brand = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=Brand.objects.filter(is_active=True, is_deleted=False),
        required=False,
        allow_null=True
    )
    condition = serializers.ChoiceField(
        choices=Product.Condition.choices,
        default=Product.Condition.NEW,
        required=False
    )
    short_description = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True, default=None)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    video_url = serializers.URLField(required=False, allow_blank=True, allow_null=True, default=None)
    is_featured = serializers.BooleanField(default=False, required=False)
    is_active = serializers.BooleanField(default=True, required=False)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, required=True, min_value=Decimal('0.01'))
    discounted_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal('0'), allow_null=True, required=False
    )
    stock = serializers.IntegerField(min_value=0, required=False, default=0)
    # SEO — FASE 4
    meta_title = serializers.CharField(max_length=70, required=False, allow_blank=True, default='')
    meta_description = serializers.CharField(required=False, allow_blank=True, default='')


# ---- Cost Rules -----------------------------------------------------------

class ProductCostRuleSerializer(serializers.ModelSerializer):
    class Meta:
        from shop.models import ProductCostRule
        model = ProductCostRule
        fields = [
            'id', 'uuid', 'name', 'description', 'cost_type', 'context',
            'value', 'applies_globally', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'uuid', 'created_at']


class ProductCostRuleInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    cost_type = serializers.ChoiceField(choices=['FIXED', 'PERCENTAGE'])
    context = serializers.ChoiceField(choices=['TAX', 'DISCOUNT'])
    value = serializers.DecimalField(max_digits=12, decimal_places=4, min_value=Decimal('0'))
    applies_globally = serializers.BooleanField(default=False, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ProductCostAssignmentInputSerializer(serializers.Serializer):
    variant_uuid = serializers.UUIDField()
