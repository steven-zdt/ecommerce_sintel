from decimal import Decimal
from rest_framework import serializers
from renting.models import (
    Equipment, EquipmentVariant, EquipmentImage, EquipmentReview,
    RentingCategory, RentingBrand, RentalLabor, RentalRequest, RentalProjectAttachment,
    EquipmentLogisticsConfig, EquipmentMarketing, EquipmentBlock, EquipmentReturnInspection,
    RentalIncludedItem, RentalExcludedItem, RentalFeature,
    RentalSpecificationGroup, RentalSpecification, RentalRequirement,
    RentalServiceIncluded, RentalOptionalService, RentalFAQ,
    RentalVideo, RentalDocument,
)


class RentalProjectAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalProjectAttachment
        fields = ['uuid', 'file', 'original_name', 'content_type', 'created_at']
        read_only_fields = fields


# ── Output serializers ────────────────────────────────────────────────────────

class RentingCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RentingCategory
        fields = ['id', 'uuid', 'name', 'slug', 'description', 'is_active']


class RentingBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentingBrand
        fields = ['id', 'uuid', 'name', 'slug']


class EquipmentImageSerializer(serializers.ModelSerializer):
    image_type_display = serializers.CharField(source='get_image_type_display', read_only=True)

    class Meta:
        model = EquipmentImage
        fields = ['uuid', 'image', 'alt_text', 'is_primary', 'image_type', 'image_type_display', 'position']
        read_only_fields = fields


class EquipmentImageInputSerializer(serializers.Serializer):
    image_type = serializers.ChoiceField(choices=EquipmentImage.IMAGE_TYPE_CHOICES, default=EquipmentImage.TYPE_GALLERY, required=False)
    alt_text = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    is_primary = serializers.BooleanField(default=False, required=False)
    position = serializers.IntegerField(min_value=0, default=0, required=False)


class EquipmentReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    # Mismo patron que shop.ProductReviewSerializer: expone el email para que
    # el frontend pueda detectar "esta es mi reseña" sin un endpoint aparte.
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = EquipmentReview
        fields = ['uuid', 'user_name', 'user_email', 'rating', 'comment', 'created_at']
        read_only_fields = fields

    def get_user_name(self, obj):
        return obj.user.get_short_name() if obj.user else 'Cliente'


class EquipmentReviewInputSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=2000)


# ── Catalogo enriquecido de Equipment ──────────────────────────────────────────

class RentalIncludedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalIncludedItem
        fields = ['uuid', 'title', 'description', 'icon', 'position', 'is_active']
        read_only_fields = ['uuid']


class RentalIncludedItemInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    icon = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class RentalExcludedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalExcludedItem
        fields = ['uuid', 'title', 'description', 'icon', 'position', 'is_active']
        read_only_fields = ['uuid']


class RentalExcludedItemInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    icon = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class RentalFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalFeature
        fields = ['uuid', 'title', 'value', 'icon', 'position', 'is_active']
        read_only_fields = ['uuid']


class RentalFeatureInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    value = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    icon = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class RentalSpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalSpecification
        fields = ['uuid', 'name', 'value', 'position', 'is_active']
        read_only_fields = ['uuid']


class RentalSpecificationGroupSerializer(serializers.ModelSerializer):
    specifications = RentalSpecificationSerializer(many=True, read_only=True)

    class Meta:
        model = RentalSpecificationGroup
        fields = ['uuid', 'name', 'position', 'is_active', 'specifications']
        read_only_fields = ['uuid']


class RentalSpecificationGroupInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class RentalSpecificationInputSerializer(serializers.Serializer):
    group = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=RentalSpecificationGroup.objects.filter(is_deleted=False),
    )
    name = serializers.CharField(max_length=150)
    value = serializers.CharField(max_length=255)
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class RentalRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalRequirement
        fields = ['uuid', 'title', 'description', 'position', 'is_active']
        read_only_fields = ['uuid']


class RentalRequirementInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class RentalServiceIncludedSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalServiceIncluded
        fields = ['uuid', 'title', 'description', 'icon', 'position', 'is_active']
        read_only_fields = ['uuid']


class RentalServiceIncludedInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    icon = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class RentalOptionalServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalOptionalService
        fields = ['uuid', 'title', 'description', 'price', 'icon', 'position', 'is_active']
        read_only_fields = ['uuid']


class RentalOptionalServiceInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0'))
    icon = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class RentalFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalFAQ
        fields = ['uuid', 'question', 'answer', 'position', 'is_active']
        read_only_fields = ['uuid']


class RentalFAQInputSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=500)
    answer = serializers.CharField()
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class RentalVideoSerializer(serializers.ModelSerializer):
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    embed_url = serializers.SerializerMethodField()

    class Meta:
        model = RentalVideo
        fields = [
            'uuid', 'title', 'source_type', 'source_type_display',
            'video_url', 'video_file', 'thumbnail', 'embed_url', 'position', 'is_active',
        ]
        read_only_fields = ['uuid']

    def get_embed_url(self, obj):
        import re
        if obj.source_type == RentalVideo.SOURCE_YOUTUBE and obj.video_url:
            match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([^&?/]+)', obj.video_url)
            return f'https://www.youtube.com/embed/{match.group(1)}' if match else obj.video_url
        if obj.source_type == RentalVideo.SOURCE_VIMEO and obj.video_url:
            match = re.search(r'vimeo\.com/(\d+)', obj.video_url)
            return f'https://player.vimeo.com/video/{match.group(1)}' if match else obj.video_url
        if obj.source_type == RentalVideo.SOURCE_MP4 and obj.video_file:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.video_file.url) if request else obj.video_file.url
        return obj.video_url or None


class RentalVideoInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    source_type = serializers.ChoiceField(choices=RentalVideo.SOURCE_TYPE_CHOICES, default=RentalVideo.SOURCE_YOUTUBE)
    video_url = serializers.URLField(required=False, allow_blank=True, default='')
    video_file = serializers.FileField(required=False, allow_null=True)
    thumbnail = serializers.ImageField(required=False, allow_null=True)
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class RentalDocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)

    class Meta:
        model = RentalDocument
        fields = [
            'uuid', 'title', 'description', 'document_type', 'document_type_display',
            'version', 'language', 'file', 'cover_image', 'downloads',
            'position', 'is_public', 'is_active', 'created_at',
        ]
        read_only_fields = ['uuid', 'downloads', 'created_at']


class RentalDocumentInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    document_type = serializers.ChoiceField(choices=RentalDocument.DOCUMENT_TYPE_CHOICES, default=RentalDocument.TYPE_OTRO)
    version = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    language = serializers.CharField(max_length=10, required=False, allow_blank=True, default='es')
    cover_image = serializers.ImageField(required=False, allow_null=True)
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_public = serializers.BooleanField(default=True, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ReorderInputSerializer(serializers.Serializer):
    """Payload generico de reorder: lista ordenada de uuids (drag&drop)."""
    ordered_uuids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class RentalLaborSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalLabor
        fields = ['id', 'uuid', 'name', 'description', 'price_per_hour', 'is_active']


class EquipmentVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentVariant
        fields = [
            'id', 'uuid', 'sku', 'rental_price_per_day',
            'rental_price_per_hour', 'stock', 'is_active'
        ]


class EquipmentLogisticsConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentLogisticsConfig
        fields = [
            'uuid', 'delivery_cost', 'pickup_cost',
            'installation_cost', 'calibration_cost',
            'training_cost', 'startup_cost', 'notes',
        ]


class EquipmentLogisticsConfigInputSerializer(serializers.Serializer):
    delivery_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0')
    )
    pickup_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0')
    )
    installation_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0')
    )
    calibration_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0')
    )
    training_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0')
    )
    startup_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0')
    )
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class EquipmentMarketingSerializer(serializers.ModelSerializer):
    """
    Payload publico/admin de marketing. discount_percentage/savings_percentage
    son calculados en vivo (nunca almacenados) a partir de los precios
    configurados -- nunca de otro equipo.
    """
    discount_percentage = serializers.SerializerMethodField()
    savings_percentage = serializers.SerializerMethodField()

    class Meta:
        model = EquipmentMarketing
        fields = [
            'uuid', 'reference_price', 'promo_price', 'show_discount_percentage',
            'discount_percentage', 'tags', 'main_message', 'featured_benefit',
            'trust_message', 'urgency_message', 'social_proof_message',
            'purchase_price_reference', 'financial_message', 'savings_percentage',
            'use_cases', 'cta_label', 'promo_banner_message', 'quick_benefits',
        ]

    def get_discount_percentage(self, obj):
        if not obj.show_discount_percentage:
            return None
        if not obj.reference_price or not obj.promo_price:
            return None
        if obj.reference_price <= 0 or obj.promo_price >= obj.reference_price:
            return None
        pct = (1 - (obj.promo_price / obj.reference_price)) * 100
        return round(pct)

    def get_savings_percentage(self, obj):
        if not obj.purchase_price_reference or obj.purchase_price_reference <= 0:
            return None
        effective_price = obj.promo_price or obj.reference_price
        if not effective_price:
            variant = min(
                (v for v in obj.equipment.variants.all() if v.is_active and not v.is_deleted and v.rental_price_per_day),
                key=lambda v: v.rental_price_per_day,
                default=None,
            )
            effective_price = variant.rental_price_per_day if variant else None
        if not effective_price or effective_price >= obj.purchase_price_reference:
            return None
        return round((1 - (effective_price / obj.purchase_price_reference)) * 100)


class EquipmentMarketingInputSerializer(serializers.Serializer):
    reference_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0')
    )
    promo_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0')
    )
    show_discount_percentage = serializers.BooleanField(default=True, required=False)
    tags = serializers.ListField(
        child=serializers.ChoiceField(choices=[c[0] for c in EquipmentMarketing.TAG_CHOICES]),
        required=False, default=list,
    )
    main_message = serializers.CharField(required=False, allow_blank=True, default='')
    featured_benefit = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    trust_message = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    urgency_message = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    social_proof_message = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    purchase_price_reference = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0')
    )
    financial_message = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    use_cases = serializers.ListField(child=serializers.CharField(max_length=100), required=False, default=list)
    cta_label = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    promo_banner_message = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    quick_benefits = serializers.ListField(required=False, default=list)


class EquipmentSerializer(serializers.ModelSerializer):
    """
    Serializer basico (listados/admin). Para el detalle publico enriquecido
    (galeria, incluye/no incluye, caracteristicas, especificaciones, requisitos,
    servicios, FAQ, videos, documentos, reviews) usar EquipmentDetailSerializer.
    """
    category = RentingCategorySerializer(read_only=True)
    brand = RentingBrandSerializer(read_only=True)
    images = EquipmentImageSerializer(many=True, read_only=True)
    variants = EquipmentVariantSerializer(many=True, read_only=True)
    category_uuid = serializers.UUIDField(source='category.uuid', read_only=True)
    brand_uuid = serializers.UUIDField(source='brand.uuid', read_only=True, allow_null=True)
    logistics_config = EquipmentLogisticsConfigSerializer(read_only=True, allow_null=True)
    marketing = EquipmentMarketingSerializer(read_only=True, allow_null=True)

    class Meta:
        model = Equipment
        fields = [
            'id', 'uuid', 'name', 'slug', 'description',
            'is_active', 'is_featured',
            'category_uuid', 'brand_uuid',
            'category', 'brand', 'images', 'variants',
            'logistics_config', 'marketing',
            'meta_title', 'meta_description', 'meta_keywords', 'og_image',
        ]


class EquipmentDetailSerializer(EquipmentSerializer):
    """
    Payload enriquecido de GET /renting/equipment/{uuid}/ -- un unico response
    con todas las secciones del catalogo (2026-07-16). RentingSelector.get_by_uuid()
    ya trae todo con select_related/prefetch_related para que estos campos no
    disparen queries N+1 adicionales.
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
    reviews = EquipmentReviewSerializer(many=True, read_only=True)

    class Meta(EquipmentSerializer.Meta):
        fields = EquipmentSerializer.Meta.fields + [
            'included_items', 'excluded_items', 'features', 'specification_groups',
            'requirements', 'services_included', 'optional_services', 'faqs',
            'videos', 'documents', 'reviews',
        ]

    @staticmethod
    def _active(related_manager):
        """Filtra en memoria (ya viene prefetcheado, is_deleted=False) los
        renglones activos -- is_active se respeta solo de cara al cliente."""
        return [obj for obj in related_manager.all() if obj.is_active]

    def get_included_items(self, obj):
        return RentalIncludedItemSerializer(self._active(obj.included_items), many=True).data

    def get_excluded_items(self, obj):
        return RentalExcludedItemSerializer(self._active(obj.excluded_items), many=True).data

    def get_features(self, obj):
        return RentalFeatureSerializer(self._active(obj.features), many=True).data

    def get_specification_groups(self, obj):
        """
        No reutiliza RentalSpecificationGroupSerializer tal cual: ese serializer
        tambien lo usa el panel admin (donde debe listar TODAS las specs,
        activas o no, para poder editarlas), asi que aqui se arma el payload
        publico a mano filtrando por is_active en ambos niveles (grupo y fila).
        """
        payload = []
        for group in self._active(obj.specification_groups):
            payload.append({
                'uuid': str(group.uuid),
                'name': group.name,
                'position': group.position,
                'is_active': group.is_active,
                'specifications': RentalSpecificationSerializer(self._active(group.specifications), many=True).data,
            })
        return payload

    def get_requirements(self, obj):
        return RentalRequirementSerializer(self._active(obj.requirements), many=True).data

    def get_services_included(self, obj):
        return RentalServiceIncludedSerializer(self._active(obj.services_included), many=True).data

    def get_optional_services(self, obj):
        return RentalOptionalServiceSerializer(self._active(obj.optional_services), many=True).data

    def get_faqs(self, obj):
        return RentalFAQSerializer(self._active(obj.faqs), many=True).data

    def get_videos(self, obj):
        return RentalVideoSerializer(self._active(obj.videos), many=True, context=self.context).data

    def get_documents(self, obj):
        public_docs = [d for d in obj.documents.all() if d.is_public and d.is_active]
        return RentalDocumentSerializer(public_docs, many=True, context=self.context).data


# ── Input serializers ─────────────────────────────────────────────────────────

class RentingCategoryInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    is_active = serializers.BooleanField(default=True)
    parent = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=RentingCategory.objects.filter(is_deleted=False),
        required=False,
        allow_null=True,
    )


class RentingBrandInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)


class RentalLaborInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    price_per_hour = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    is_active = serializers.BooleanField(default=True)


class EquipmentInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    is_active = serializers.BooleanField(default=True)
    is_featured = serializers.BooleanField(default=False)
    category = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=RentingCategory.objects.filter(is_deleted=False),
    )
    brand = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=RentingBrand.objects.filter(is_deleted=False),
        required=False,
        allow_null=True,
    )


class EquipmentVariantInputSerializer(serializers.Serializer):
    equipment = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=Equipment.objects.filter(is_deleted=False),
    )
    sku = serializers.CharField(max_length=100)
    rental_price_per_day = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0.01')
    )
    rental_price_per_hour = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0.01')
    )
    stock = serializers.IntegerField(min_value=0, default=0)
    is_active = serializers.BooleanField(default=True)

    def validate(self, attrs):
        if not attrs.get('rental_price_per_day') and not attrs.get('rental_price_per_hour'):
            raise serializers.ValidationError(
                'Debe especificar al menos un precio: por dia o por hora.'
            )
        return attrs


# ── RentalRequest serializers ──────────────────────────────────────────────────

class RentalRequestVariantSerializer(serializers.ModelSerializer):
    equipment_name = serializers.CharField(source='equipment.name', read_only=True)
    equipment_uuid = serializers.UUIDField(source='equipment.uuid', read_only=True)
    category_name = serializers.CharField(source='equipment.category.name', read_only=True)
    brand_name = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = EquipmentVariant
        fields = [
            'uuid', 'sku', 'rental_price_per_day', 'rental_price_per_hour', 'stock',
            'equipment_name', 'equipment_uuid', 'category_name', 'brand_name', 'primary_image',
        ]

    def get_brand_name(self, obj):
        return obj.equipment.brand.name if obj.equipment.brand else None

    def get_primary_image(self, obj):
        images = list(obj.equipment.images.all())
        img = next((i for i in images if i.is_primary), None) or (images[0] if images else None)
        if img and img.image:
            request = self.context.get('request')
            return request.build_absolute_uri(img.image.url) if request else img.image.url
        return None


class RentalRequestSerializer(serializers.ModelSerializer):
    project_attachments = RentalProjectAttachmentSerializer(many=True, read_only=True)
    equipment_variant = RentalRequestVariantSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    contact_doc_type_display = serializers.CharField(
        source='get_contact_doc_type_display', read_only=True
    )
    rental_mode_display = serializers.CharField(source='get_rental_mode_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    display_status = serializers.SerializerMethodField()
    return_inspection = serializers.SerializerMethodField()

    def get_display_status(self, obj):
        from renting.services.display import display_status_for_request
        return display_status_for_request(obj)

    def get_return_inspection(self, obj):
        inspection = getattr(obj, 'return_inspection', None)
        return EquipmentReturnInspectionSerializer(inspection).data if inspection else None

    class Meta:
        model = RentalRequest
        fields = [
            'uuid', 'status', 'status_display',
            'priority', 'priority_display', 'project_attachments',
            'equipment_variant',
            # Paso 2
            'location_address', 'location_city', 'location_department',
            'location_coordinates', 'project_type', 'access_conditions', 'location_notes',
            # Paso 3
            'contact_full_name', 'contact_doc_type', 'contact_doc_type_display',
            'contact_doc_number', 'contact_email', 'contact_phone',
            'contact_company', 'contact_position',
            # Paso 4
            'start_date', 'end_date', 'quantity', 'estimated_hours',
            'rental_mode', 'rental_mode_display', 'delivery_time', 'pickup_time',
            'operational_notes',
            # Paso 5
            'terms_accepted', 'terms_accepted_at',
            # Costos (calculados automaticamente desde EquipmentLogisticsConfig)
            'delivery_cost', 'pickup_cost',
            'installation_cost', 'calibration_cost', 'training_cost', 'startup_cost',
            # Totales
            'total_rental_days', 'base_cost',
            'transport_total', 'setup_total', 'tax_amount', 'grand_total',
            # Pago
            'wompi_reference', 'payment_status', 'paid_at', 'refund_required',
            'display_status', 'return_inspection',
            'created_at', 'updated_at',
        ]


class RentalRequestInputSerializer(serializers.Serializer):
    equipment_variant = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=EquipmentVariant.objects.filter(is_deleted=False, is_active=True),
    )
    # Paso 2
    location_address = serializers.CharField(max_length=500)
    location_city = serializers.CharField(max_length=100)
    location_department = serializers.CharField(max_length=100)
    location_coordinates = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    project_type = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    access_conditions = serializers.CharField(required=False, allow_blank=True, default='')
    location_notes = serializers.CharField(required=False, allow_blank=True, default='')
    # Paso 3
    contact_full_name = serializers.CharField(max_length=255)
    contact_doc_type = serializers.ChoiceField(choices=RentalRequest.DOC_TYPE_CHOICES, default=RentalRequest.DOC_CC)
    contact_doc_number = serializers.CharField(max_length=50)
    contact_email = serializers.EmailField()
    contact_phone = serializers.CharField(max_length=30)
    contact_company = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    contact_position = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    # Paso 4
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    estimated_hours = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)
    rental_mode = serializers.ChoiceField(choices=RentalRequest.RENTAL_MODE_CHOICES, default=RentalRequest.RENTAL_MODE_DAYS)
    delivery_time = serializers.TimeField(required=False, allow_null=True, default=None)
    pickup_time = serializers.TimeField(required=False, allow_null=True, default=None)
    operational_notes = serializers.CharField(required=False, allow_blank=True, default='')
    # Paso 4 — Prioridad
    priority = serializers.ChoiceField(
        choices=RentalRequest.PRIORITY_CHOICES,
        default=RentalRequest.PRIORITY_LOW,
        required=False,
    )
    # Paso 5
    terms_accepted = serializers.BooleanField()

    def validate(self, attrs):
        import datetime
        from django.utils import timezone

        start = attrs.get('start_date')
        end   = attrs.get('end_date')

        if start and end and end <= start:
            raise serializers.ValidationError(
                {'end_date': 'La fecha de fin debe ser posterior a la fecha de inicio.'}
            )

        if start:
            today = timezone.localdate()
            if start <= today:
                raise serializers.ValidationError({
                    'start_date': (
                        'La fecha de inicio no puede ser el mismo dia de la solicitud ni en el pasado.'
                    )
                })

            priority  = attrs.get('priority', RentalRequest.PRIORITY_LOW)
            min_days  = RentalRequest.PRIORITY_MIN_DAYS[priority]
            min_date  = today + datetime.timedelta(days=min_days)
            label     = 'baja' if priority == RentalRequest.PRIORITY_LOW else 'alta'
            if start < min_date:
                raise serializers.ValidationError({
                    'start_date': (
                        f'Con prioridad {label}, la fecha de inicio debe ser al menos '
                        f'{min_days} dias despues de hoy ({min_date.strftime("%Y-%m-%d")}).'
                    )
                })

        if not attrs.get('terms_accepted'):
            raise serializers.ValidationError(
                {'terms_accepted': 'Debe aceptar los terminos y condiciones.'}
            )
        variant = attrs['equipment_variant']
        mode = attrs.get('rental_mode', RentalRequest.RENTAL_MODE_DAYS)
        if mode == RentalRequest.RENTAL_MODE_DAYS and not variant.rental_price_per_day:
            raise serializers.ValidationError(
                {'rental_mode': 'Este equipo no tiene precio por dia configurado.'}
            )
        if mode == RentalRequest.RENTAL_MODE_HOURS and not variant.rental_price_per_hour:
            raise serializers.ValidationError(
                {'rental_mode': 'Este equipo no tiene precio por hora configurado.'}
            )
        if mode == RentalRequest.RENTAL_MODE_HOURS and (
            not attrs.get('delivery_time') or not attrs.get('pickup_time')
        ):
            raise serializers.ValidationError(
                {'delivery_time': 'Debe indicar hora de entrega y hora de recogida para renta por horas.'}
            )

        # Verificar disponibilidad por rango de fechas
        from renting.services.selectors import RentingSelector
        quantity = attrs.get('quantity', 1)
        if not RentingSelector.check_availability(
            variant.id, attrs['start_date'], attrs['end_date'], quantity
        ):
            raise serializers.ValidationError(
                {
                    'start_date': (
                        'No hay disponibilidad para el equipo en las fechas seleccionadas '
                        'con la cantidad solicitada. Por favor elige otras fechas.'
                    )
                }
            )

        return attrs


class RentalRequestExtendInputSerializer(serializers.Serializer):
    new_end_date = serializers.DateField()
    reason = serializers.CharField(required=False, allow_blank=True, default='')


# ---- Disponibilidad / calendario / timeline --------------------------------

class RentalPeriodSlotSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    start_time = serializers.TimeField(allow_null=True)
    end_time = serializers.TimeField(allow_null=True)
    rental_mode = serializers.CharField()
    quantity = serializers.IntegerField()
    status = serializers.CharField()


class EquipmentAvailabilityResponseSerializer(serializers.Serializer):
    available = serializers.BooleanField()
    variant_uuid = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    quantity = serializers.IntegerField()
    rental_mode = serializers.CharField()
    next_available_date = serializers.DateField(allow_null=True)
    next_available_time = serializers.TimeField(allow_null=True)
    occupied_slots = RentalPeriodSlotSerializer(many=True)


class EquipmentCalendarDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    available_units = serializers.IntegerField()
    status = serializers.ChoiceField(choices=['available', 'booked', 'full'])
    hour_bookings = RentalPeriodSlotSerializer(many=True)


class EquipmentCalendarResponseSerializer(serializers.Serializer):
    variant_uuid = serializers.UUIDField()
    range_start = serializers.DateField()
    range_end = serializers.DateField()
    stock = serializers.IntegerField()
    days = EquipmentCalendarDaySerializer(many=True)


class EquipmentTimelineResponseSerializer(serializers.Serializer):
    variant_uuid = serializers.UUIDField()
    range_start = serializers.DateField()
    range_end = serializers.DateField()
    periods = RentalPeriodSlotSerializer(many=True)


# ---- Equipment Blocks (mantenimiento/daño/inventario) ---------------------

class EquipmentBlockSerializer(serializers.ModelSerializer):
    equipment_variant_uuid = serializers.UUIDField(source='equipment_variant.uuid', read_only=True)
    equipment_variant_sku = serializers.CharField(source='equipment_variant.sku', read_only=True)
    equipment_name = serializers.CharField(source='equipment_variant.equipment.name', read_only=True)
    block_type_display = serializers.CharField(source='get_block_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True, allow_null=True)
    released_by_email = serializers.EmailField(source='released_by.email', read_only=True, allow_null=True)

    class Meta:
        model = EquipmentBlock
        fields = [
            'uuid', 'equipment_variant_uuid', 'equipment_variant_sku', 'equipment_name',
            'block_type', 'block_type_display', 'start_date', 'end_date', 'quantity',
            'status', 'status_display', 'reason',
            'created_by_email', 'released_by_email', 'released_at', 'release_reason',
            'created_at',
        ]
        read_only_fields = fields


class EquipmentBlockInputSerializer(serializers.Serializer):
    equipment_variant = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=EquipmentVariant.objects.filter(is_deleted=False),
    )
    block_type = serializers.ChoiceField(choices=EquipmentBlock.BLOCK_TYPE_CHOICES, default=EquipmentBlock.TYPE_MAINTENANCE)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    reason = serializers.CharField()

    def validate(self, attrs):
        if attrs['end_date'] < attrs['start_date']:
            raise serializers.ValidationError(
                {'end_date': 'La fecha de fin debe ser igual o posterior a la fecha de inicio.'}
            )
        return attrs


class EquipmentBlockReleaseInputSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default='')


# ---- Equipment Return Inspection --------------------------------------------

class EquipmentReturnInspectionSerializer(serializers.ModelSerializer):
    inspected_by_email = serializers.EmailField(source='inspected_by.email', read_only=True, allow_null=True)
    resulting_block_uuid = serializers.UUIDField(source='resulting_block.uuid', read_only=True, allow_null=True)

    class Meta:
        model = EquipmentReturnInspection
        fields = [
            'uuid', 'has_damage', 'condition_notes', 'missing_accessories',
            'inspected_by_email', 'resulting_block_uuid', 'created_at',
        ]
        read_only_fields = fields


class EquipmentReturnInspectionInputSerializer(serializers.Serializer):
    has_damage = serializers.BooleanField(default=False)
    condition_notes = serializers.CharField(required=False, allow_blank=True, default='')
    missing_accessories = serializers.CharField(required=False, allow_blank=True, default='')


# ---- Cost Rules -----------------------------------------------------------

class RentalCostRuleSerializer(serializers.ModelSerializer):
    class Meta:
        from renting.models import RentalCostRule
        model = RentalCostRule
        fields = [
            'id', 'uuid', 'name', 'description', 'cost_type', 'context',
            'value', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'uuid', 'created_at']


class RentalCostRuleInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    cost_type = serializers.ChoiceField(choices=['FIXED', 'PERCENTAGE'])
    context = serializers.ChoiceField(choices=['TAX', 'DISCOUNT', 'DEPOSIT', 'INSURANCE', 'SURCHARGE'])
    value = serializers.DecimalField(max_digits=12, decimal_places=4, min_value=Decimal('0'))
    is_active = serializers.BooleanField(default=True, required=False)


class RentalCostAssignmentInputSerializer(serializers.Serializer):
    variant_uuid = serializers.UUIDField()
