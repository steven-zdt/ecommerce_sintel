from decimal import Decimal
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from django.contrib.contenttypes.models import ContentType
from shop.models import Category, Brand, Product, ProductVariant, ProductImage, ProductReview, Tax
from shared.models import CatalogRelation
from shared.services.content_blocks import ContentBlockConfigSelector, CatalogRelationSelector


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
    image_type_display = serializers.CharField(source='get_image_type_display', read_only=True)

    class Meta:
        model = ProductImage
        fields = ('id', 'uuid', 'image', 'alt_text', 'is_primary', 'image_type', 'image_type_display', 'display_order')


class ProductImageInputSerializer(serializers.Serializer):
    image_type = serializers.ChoiceField(choices=ProductImage.IMAGE_TYPE_CHOICES, default=ProductImage.TYPE_GALLERY, required=False)
    alt_text = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    is_primary = serializers.BooleanField(default=False, required=False)
    display_order = serializers.IntegerField(min_value=0, default=0, required=False)


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


class ProductDetailSerializer(ProductSerializer):
    """
    Payload enriquecido de GET /shop/products/{uuid}/ -- un unico response con
    todas las secciones del catalogo enriquecido (2026-08-03, espejo de
    EquipmentDetailSerializer en renting/api/serializers.py). ProductSelector.
    _get_detail_queryset() ya trae todo con prefetch_related filtrado para que
    estos campos no disparen queries N+1 adicionales.
    """
    included_items = serializers.SerializerMethodField()
    excluded_items = serializers.SerializerMethodField()
    features = serializers.SerializerMethodField()
    specification_groups = serializers.SerializerMethodField()
    requirements = serializers.SerializerMethodField()
    services_included = serializers.SerializerMethodField()
    optional_services = serializers.SerializerMethodField()
    faqs = serializers.SerializerMethodField()
    videos = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()
    functioning_steps = serializers.SerializerMethodField()
    # Fase 3, reingenieria PDP (2026-08-05) -- ver DISENO_FASE2_SHOP_CONTENIDO_PDP_2026-08-05.md.
    # content_blocks/related_products/compatible_products/accessories son aditivos: mismo
    # endpoint GET .../detail/, ningun campo existente cambia de forma.
    content_blocks = serializers.SerializerMethodField()
    related_products = serializers.SerializerMethodField()
    compatible_products = serializers.SerializerMethodField()
    accessories = serializers.SerializerMethodField()

    class Meta(ProductSerializer.Meta):
        fields = ProductSerializer.Meta.fields + (
            'included_items', 'excluded_items', 'features', 'specification_groups',
            'requirements', 'services_included', 'optional_services', 'faqs',
            'videos', 'documents', 'functioning_steps', 'scope', 'warranty', 'content_blocks',
            'related_products', 'compatible_products', 'accessories',
        )

    @staticmethod
    def _active(related_manager):
        """Filtra en memoria (ya viene prefetcheado, is_deleted=False) los
        renglones activos -- is_active se respeta solo de cara al cliente."""
        return [obj for obj in related_manager.all() if obj.is_active]

    def get_included_items(self, obj):
        return ProductIncludedItemSerializer(self._active(obj.included_items), many=True).data

    def get_excluded_items(self, obj):
        return ProductExcludedItemSerializer(self._active(obj.excluded_items), many=True).data

    def get_features(self, obj):
        return ProductFeatureSerializer(self._active(obj.features), many=True).data

    def get_specification_groups(self, obj):
        """
        No reutiliza ProductSpecificationGroupSerializer tal cual: ese serializer
        tambien lo usa el panel admin (donde debe listar TODAS las specs, activas
        o no, para poder editarlas), asi que aqui se arma el payload publico a
        mano filtrando por is_active en ambos niveles (grupo y fila).
        """
        payload = []
        for group in self._active(obj.specification_groups):
            payload.append({
                'uuid': str(group.uuid),
                'name': group.name,
                'position': group.position,
                'is_active': group.is_active,
                'specifications': ProductSpecificationSerializer(self._active(group.specifications), many=True).data,
            })
        return payload

    def get_requirements(self, obj):
        return ProductRequirementSerializer(self._active(obj.requirements), many=True).data

    def get_services_included(self, obj):
        return ProductServiceIncludedSerializer(self._active(obj.services_included), many=True).data

    def get_optional_services(self, obj):
        return ProductOptionalServiceSerializer(self._active(obj.optional_services), many=True).data

    def get_faqs(self, obj):
        return ProductFAQSerializer(self._active(obj.faqs), many=True).data

    def get_videos(self, obj):
        return ProductVideoSerializer(self._active(obj.videos), many=True, context=self.context).data

    def get_documents(self, obj):
        public_docs = [d for d in obj.documents.all() if d.is_public and d.is_active]
        return ProductDocumentSerializer(public_docs, many=True, context=self.context).data

    def get_functioning_steps(self, obj):
        return ProductFunctioningStepSerializer(self._active(obj.functioning_steps), many=True, context=self.context).data

    def get_content_blocks(self, obj):
        content_type = ContentType.objects.get_for_model(Product)
        return ContentBlockConfigSelector.resolve_for(content_type, obj.uuid)

    def _get_related(self, obj, relation_type):
        content_type = ContentType.objects.get_for_model(Product)
        products = CatalogRelationSelector.get_related_objects(content_type, obj.uuid, relation_type)
        return ProductSerializer(products, many=True, context=self.context).data

    def get_related_products(self, obj):
        return self._get_related(obj, CatalogRelation.RELATION_RELATED)

    def get_compatible_products(self, obj):
        return self._get_related(obj, CatalogRelation.RELATION_COMPATIBLE)

    def get_accessories(self, obj):
        return self._get_related(obj, CatalogRelation.RELATION_ACCESSORY)


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
    scope = serializers.CharField(required=False, allow_blank=True, default='')
    warranty = serializers.CharField(required=False, allow_blank=True, default='')
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


# ---------------------------------------------------------------------------
# Catalogo enriquecido de Product (2026-08-03) -- espejo de renting/api/serializers.py
# ---------------------------------------------------------------------------

from shop.models import (
    ProductIncludedItem, ProductExcludedItem, ProductFeature,
    ProductSpecificationGroup, ProductSpecification, ProductRequirement,
    ProductServiceIncluded, ProductOptionalService, ProductFAQ,
    ProductVideo, ProductDocument, ProductFunctioningStep,
)


class ProductIncludedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductIncludedItem
        fields = ['uuid', 'title', 'description', 'icon', 'position', 'is_active']
        read_only_fields = ['uuid']


class ProductIncludedItemInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    icon = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ProductExcludedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductExcludedItem
        fields = ['uuid', 'title', 'description', 'icon', 'position', 'is_active']
        read_only_fields = ['uuid']


class ProductExcludedItemInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    icon = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ProductFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFeature
        fields = ['uuid', 'title', 'value', 'icon', 'position', 'is_active']
        read_only_fields = ['uuid']


class ProductFeatureInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    value = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    icon = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ProductSpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSpecification
        fields = ['uuid', 'name', 'value', 'position', 'is_active']
        read_only_fields = ['uuid']


class ProductSpecificationGroupSerializer(serializers.ModelSerializer):
    specifications = ProductSpecificationSerializer(many=True, read_only=True)

    class Meta:
        model = ProductSpecificationGroup
        fields = ['uuid', 'name', 'position', 'is_active', 'specifications']
        read_only_fields = ['uuid']


class ProductSpecificationGroupInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ProductSpecificationInputSerializer(serializers.Serializer):
    group = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=ProductSpecificationGroup.objects.filter(is_deleted=False),
    )
    name = serializers.CharField(max_length=150)
    value = serializers.CharField(max_length=255)
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ProductRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductRequirement
        fields = ['uuid', 'title', 'description', 'position', 'is_active']
        read_only_fields = ['uuid']


class ProductRequirementInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ProductServiceIncludedSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductServiceIncluded
        fields = ['uuid', 'title', 'description', 'icon', 'position', 'is_active']
        read_only_fields = ['uuid']


class ProductServiceIncludedInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    icon = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ProductOptionalServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductOptionalService
        fields = ['uuid', 'title', 'description', 'price', 'icon', 'position', 'is_active']
        read_only_fields = ['uuid']


class ProductOptionalServiceInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0'))
    icon = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ProductFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFAQ
        fields = ['uuid', 'question', 'answer', 'position', 'is_active']
        read_only_fields = ['uuid']


class ProductFAQInputSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=500)
    answer = serializers.CharField()
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ProductVideoSerializer(serializers.ModelSerializer):
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    embed_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductVideo
        fields = [
            'uuid', 'title', 'source_type', 'source_type_display',
            'video_url', 'video_file', 'thumbnail', 'embed_url', 'position', 'is_active',
        ]
        read_only_fields = ['uuid']

    def get_embed_url(self, obj):
        import re
        if obj.source_type == ProductVideo.SOURCE_YOUTUBE and obj.video_url:
            match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([^&?/]+)', obj.video_url)
            return f'https://www.youtube.com/embed/{match.group(1)}' if match else obj.video_url
        if obj.source_type == ProductVideo.SOURCE_VIMEO and obj.video_url:
            match = re.search(r'vimeo\.com/(\d+)', obj.video_url)
            return f'https://player.vimeo.com/video/{match.group(1)}' if match else obj.video_url
        if obj.source_type == ProductVideo.SOURCE_MP4 and obj.video_file:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.video_file.url) if request else obj.video_file.url
        return obj.video_url or None


class ProductVideoInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    source_type = serializers.ChoiceField(choices=ProductVideo.SOURCE_TYPE_CHOICES, default=ProductVideo.SOURCE_YOUTUBE)
    video_url = serializers.URLField(required=False, allow_blank=True, default='')
    video_file = serializers.FileField(required=False, allow_null=True)
    thumbnail = serializers.ImageField(required=False, allow_null=True)
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ProductDocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)

    class Meta:
        model = ProductDocument
        fields = [
            'uuid', 'title', 'description', 'document_type', 'document_type_display',
            'version', 'language', 'file', 'cover_image', 'downloads',
            'position', 'is_public', 'is_active', 'created_at',
        ]
        read_only_fields = ['uuid', 'downloads', 'created_at']


class ProductDocumentInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    document_type = serializers.ChoiceField(choices=ProductDocument.DOCUMENT_TYPE_CHOICES, default=ProductDocument.TYPE_OTRO)
    version = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    language = serializers.CharField(max_length=10, required=False, allow_blank=True, default='es')
    cover_image = serializers.ImageField(required=False, allow_null=True)
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_public = serializers.BooleanField(default=True, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ProductFunctioningStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFunctioningStep
        fields = [
            'uuid', 'step_number', 'title', 'description', 'image',
            'estimated_time', 'position', 'is_active',
        ]
        read_only_fields = ['uuid']


class ProductFunctioningStepInputSerializer(serializers.Serializer):
    step_number = serializers.IntegerField(min_value=1, default=1, required=False)
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    image = serializers.ImageField(required=False, allow_null=True)
    estimated_time = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ProductCatalogReorderInputSerializer(serializers.Serializer):
    """Payload generico de reorder: lista ordenada de uuids (drag&drop)."""
    ordered_uuids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
