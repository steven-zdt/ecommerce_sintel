from decimal import Decimal
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from shop.models import ProductVariant as _PV
from shop.api.serializers import ProductSerializer
from technical_services.models import (
    TechnicalService, ServiceVariant, ServiceMaterial,
    ServiceCategory, ServiceLevel, ServiceImage, ServiceConfiguration,
    OrderServiceDetail, OrderServiceTimeline, ServiceAttachment,
    ServicePriceHistory, ServiceFAQ, ServiceMarketing, ServiceReview,
    ServiceIncludedItem, ServiceExcludedItem, ServiceRequirement,
    ServiceSpecificationGroup, ServiceSpecification,
    ServiceDocument, ServiceVideo, ServiceProcessStep,
)
from shared.models import CatalogRelation
from shared.services.content_blocks import ContentBlockConfigSelector, CatalogRelationSelector


# ─── Output Serializers ───────────────────────────────────────────────────────

class ServiceCategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True, default=None)

    class Meta:
        model = ServiceCategory
        fields = ['id', 'uuid', 'name', 'slug', 'description', 'parent', 'parent_name', 'is_active']


class ServiceLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceLevel
        fields = ['id', 'uuid', 'name', 'slug']


class ServiceConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceConfiguration
        fields = ['id', 'uuid', 'name', 'smlv', 'transport_subsidy',
                  'benefit_rate', 'indirect_costs_rate', 'iva_rate', 'is_active', 'created_at']


class ServiceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceImage
        fields = ['uuid', 'image', 'alt_text', 'is_primary', 'caption', 'description', 'display_order']


class ServiceImageUpdateInputSerializer(serializers.Serializer):
    """Payload de PATCH .../images/{uuid}/ -- solo metadatos (sin archivo),
    ver ServiceImageCommands.update_metadata() (FASE 4 galeria descriptiva)."""
    alt_text = serializers.CharField(required=False, allow_blank=True)
    caption = serializers.CharField(required=False, allow_blank=True, max_length=150)
    description = serializers.CharField(required=False, allow_blank=True)


class ServiceImageReorderInputSerializer(serializers.Serializer):
    """Payload de POST .../reorder_images/ -- lista de uuids de ServiceImage
    en el orden final deseado, mismo patron que ContentBlocksTab.vue usa
    para reordenar bloques (ordered_block_types)."""
    ordered_uuids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class ServiceMaterialSerializer(serializers.ModelSerializer):
    product_sku = serializers.ReadOnlyField(source='product_variant.sku')
    product_name = serializers.ReadOnlyField(source='product_variant.product.name')
    product_variant_uuid = serializers.UUIDField(source='product_variant.uuid', read_only=True)

    class Meta:
        model = ServiceMaterial
        fields = ['uuid', 'product_variant_uuid', 'product_sku', 'product_name', 'quantity']


class ServiceVariantSerializer(serializers.ModelSerializer):
    materials = ServiceMaterialSerializer(many=True, read_only=True)
    calculated_price = serializers.SerializerMethodField()
    price_info = serializers.SerializerMethodField()

    class Meta:
        model = ServiceVariant
        fields = [
            'id', 'uuid', 'sku', 'pricing_strategy', 'estimated_hours', 'complexity_factor',
            'fixed_price', 'min_duration', 'max_duration', 'simultaneous_capacity',
            'calculated_price', 'price_info',
            # Plan "Manual Pricing Engine" (2026-08-13) FASE 8 -- solo lectura aqui a
            # proposito: el panel debe cambiar estos 3 campos exclusivamente via la
            # accion dedicada set-pricing/ (ServicePricingCommands.set_manual_pricing,
            # con historial + validacion cruzada), nunca via el PATCH generico de esta
            # variante -- ver SetVariantPricingInputSerializer abajo.
            'pricing_source', 'manual_unit_price', 'manual_project_price', 'is_manual_pricing',
            'is_default', 'is_active', 'materials',
        ]
        # is_manual_pricing (property del modelo, no columna) ya queda read-only
        # automaticamente al no ser un campo escribible -- listarla aqui de mas
        # rompe con "may not also be listed in read_only_fields" si DRF la
        # detecta como declarada.
        read_only_fields = ['pricing_source', 'manual_unit_price', 'manual_project_price']

    def get_calculated_price(self, obj):
        from technical_services.services import ServiceSelector
        try:
            return float(ServiceSelector.get_variant_quotation(obj)['total_price'])
        except Exception:
            return None

    def get_price_info(self, obj):
        from technical_services.services import ServiceSelector
        try:
            q = ServiceSelector.get_variant_quotation(obj)
            return {
                'base': float(q['base_amount']),
                'labor_cost': float(q['labor_cost']),
                'material_cost': float(q['material_cost']),
                'discount_pct': float(q['discount_pct']),
                'discount_amount': float(q['discount_amount']),
                'iva_rate': float(q['iva_rate']),
                'iva_amount': float(q['iva_amount']),
                'total': float(q['total_price']),
                'total_price': float(q['total_price']),
            }
        except Exception:
            return None


class ServicePriceHistorySerializer(serializers.ModelSerializer):
    changed_by_email = serializers.ReadOnlyField(source='changed_by.email')

    class Meta:
        model = ServicePriceHistory
        # Plan "Manual Pricing Engine" FASE 6 -- pricing_source_old/new,
        # unit_price_old/new, project_price_old/new y reason son NULL en las
        # entradas generadas por cambios de fixed_price (ServiceVariantCommands.
        # update_variant) y old_price/new_price son NULL en las generadas por
        # ServicePricingCommands.set_manual_pricing -- el frontend distingue el
        # tipo de entrada por cual grupo de campos viene poblado.
        fields = [
            'uuid', 'old_price', 'new_price',
            'pricing_source_old', 'pricing_source_new',
            'unit_price_old', 'unit_price_new',
            'project_price_old', 'project_price_new',
            'reason', 'changed_by_email', 'created_at',
        ]


class SetVariantPricingInputSerializer(serializers.Serializer):
    """Payload de POST .../service-variants/{uuid}/set-pricing/ -- unica via
    admitida para cambiar ServiceVariant.pricing_source (FASE 8). unit_price/
    project_price se validan cruzados contra pricing_source en
    ServicePricingCommands.set_manual_pricing() (via ServiceVariant.clean()),
    no aqui -- este serializer solo valida forma/tipos."""
    pricing_source = serializers.ChoiceField(choices=ServiceVariant.PRICING_SOURCE_CHOICES)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    project_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True, default='')


class ServiceFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceFAQ
        fields = ['uuid', 'question', 'answer', 'position', 'is_active']
        read_only_fields = ['uuid']


class ServiceFAQInputSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=500)
    answer = serializers.CharField()
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ServiceMarketingSerializer(serializers.ModelSerializer):
    """
    Payload publico/admin de marketing. discount_percentage es calculado en
    vivo (nunca almacenado) a partir de los precios configurados -- mismo
    patron que renting.EquipmentMarketingSerializer. Sin `savings_percentage`
    (comprar vs alquilar no aplica al dominio de servicios, ver modelo).
    """
    discount_percentage = serializers.SerializerMethodField()

    class Meta:
        model = ServiceMarketing
        fields = [
            'uuid', 'reference_price', 'promo_price', 'show_discount_percentage',
            'discount_percentage', 'tags', 'main_message', 'featured_benefit',
            'trust_message', 'urgency_message', 'social_proof_message',
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


class ServiceMarketingInputSerializer(serializers.Serializer):
    reference_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0')
    )
    promo_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0')
    )
    show_discount_percentage = serializers.BooleanField(default=True, required=False)
    tags = serializers.ListField(
        child=serializers.ChoiceField(choices=[c[0] for c in ServiceMarketing.TAG_CHOICES]),
        required=False, default=list,
    )
    main_message = serializers.CharField(required=False, allow_blank=True, default='')
    featured_benefit = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    trust_message = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    urgency_message = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    social_proof_message = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    use_cases = serializers.ListField(child=serializers.CharField(max_length=100), required=False, default=list)
    cta_label = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    promo_banner_message = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    quick_benefits = serializers.ListField(required=False, default=list)


class ServiceReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    # Mismo patron que renting.EquipmentReviewSerializer: expone el email para
    # que el frontend detecte "esta es mi reseña" sin un endpoint aparte.
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = ServiceReview
        fields = ['uuid', 'user_name', 'user_email', 'rating', 'comment', 'created_at']
        read_only_fields = fields

    def get_user_name(self, obj):
        return obj.user.get_short_name() if obj.user else 'Cliente'


class ServiceReviewInputSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=2000)


class AvailableTechnicianSerializer(serializers.Serializer):
    """Ficha publica minima de un tecnico disponible para la categoria del
    servicio -- solo datos que accounts.TechnicianProfile realmente tiene hoy
    (sin calificacion/anios de experiencia, que no existen como campos)."""
    uuid = serializers.UUIDField()
    full_name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    def get_full_name(self, user):
        return user.get_full_name() or user.get_short_name()

    def get_avatar(self, user):
        profile = getattr(user, 'profile', None)
        if profile and profile.profile_picture:
            request = self.context.get('request')
            url = profile.profile_picture.url
            return request.build_absolute_uri(url) if request else url
        return None


class TechnicalServiceSerializer(serializers.ModelSerializer):
    category = ServiceCategorySerializer(read_only=True)
    category_uuid = serializers.UUIDField(source='category.uuid', read_only=True, allow_null=True)
    level = ServiceLevelSerializer(read_only=True)
    level_uuid = serializers.UUIDField(source='level.uuid', read_only=True, allow_null=True)
    images = ServiceImageSerializer(many=True, read_only=True)
    variants = serializers.SerializerMethodField()
    marketing = ServiceMarketingSerializer(read_only=True, allow_null=True)
    faqs = serializers.SerializerMethodField()

    class Meta:
        model = TechnicalService
        fields = [
            'id', 'uuid', 'name', 'slug', 'description',
            'is_active', 'is_featured', 'is_purchasable',
            'category', 'category_uuid', 'level', 'level_uuid',
            'images', 'variants', 'marketing', 'faqs',
            'meta_title', 'meta_description', 'meta_keywords', 'og_image',
        ]

    def get_variants(self, obj):
        # obj.variants.all() reutiliza el cache de prefetch_related('variants', ...);
        # un .filter(...) explicito en el manager lo ignora y dispara una query nueva
        # por cada TechnicalService (bug real medido 2026-07-03: 31 queries para 2
        # servicios con 1 variante + 1 material cada uno).
        variants = [v for v in obj.variants.all() if not v.is_deleted]
        return ServiceVariantSerializer(variants, many=True).data

    def get_faqs(self, obj):
        # obj.faqs.all() reutiliza el cache de Prefetch('faqs', ...) del
        # selector (ver ServiceSelector) -- mismo cuidado anti-N+1 que
        # get_variants() de arriba, no usar obj.faqs.filter(...) aqui.
        faqs = [f for f in obj.faqs.all() if not f.is_deleted and f.is_active]
        return ServiceFAQSerializer(faqs, many=True).data


class TechnicalServiceDetailSerializer(TechnicalServiceSerializer):
    """
    Payload enriquecido de GET /services/services/{uuid}/detail/ -- espejo de
    ProductDetailSerializer (shop/api/serializers.py). Mismo endpoint base,
    campos aditivos unicamente (mismo contrato de TechnicalServiceSerializer +
    catalogo enriquecido + orquestacion de bloques + relaciones). Reingenieria
    SDP 2026-08-05 -- ver technical_services/.AGENT/docs/UI_MODULO_SERVICES.md.
    """
    included_items = serializers.SerializerMethodField()
    excluded_items = serializers.SerializerMethodField()
    requirements = serializers.SerializerMethodField()
    specification_groups = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()
    videos = serializers.SerializerMethodField()
    process_steps = serializers.SerializerMethodField()
    materials = serializers.SerializerMethodField()
    content_blocks = serializers.SerializerMethodField()
    related_services = serializers.SerializerMethodField()
    compatible_services = serializers.SerializerMethodField()
    recommended_products = serializers.SerializerMethodField()

    class Meta(TechnicalServiceSerializer.Meta):
        fields = TechnicalServiceSerializer.Meta.fields + [
            'scope', 'warranty', 'coverage_notes',
            'included_items', 'excluded_items', 'requirements', 'specification_groups',
            'documents', 'videos', 'process_steps', 'materials', 'content_blocks',
            'related_services', 'compatible_services', 'recommended_products',
        ]

    @staticmethod
    def _active(related_manager):
        return [obj for obj in related_manager.all() if obj.is_active]

    def get_included_items(self, obj):
        return ServiceIncludedItemSerializer(self._active(obj.included_items), many=True).data

    def get_excluded_items(self, obj):
        return ServiceExcludedItemSerializer(self._active(obj.excluded_items), many=True).data

    def get_requirements(self, obj):
        return ServiceRequirementSerializer(self._active(obj.requirements), many=True).data

    def get_specification_groups(self, obj):
        payload = []
        for group in self._active(obj.specification_groups):
            payload.append({
                'uuid': str(group.uuid),
                'name': group.name,
                'position': group.position,
                'is_active': group.is_active,
                'specifications': ServiceSpecificationSerializer(self._active(group.specifications), many=True).data,
            })
        return payload

    def get_documents(self, obj):
        public_docs = [d for d in obj.documents.all() if d.is_public and d.is_active]
        return ServiceDocumentSerializer(public_docs, many=True, context=self.context).data

    def get_videos(self, obj):
        return ServiceVideoSerializer(self._active(obj.videos), many=True, context=self.context).data

    def get_process_steps(self, obj):
        return ServiceProcessStepSerializer(self._active(obj.process_steps), many=True, context=self.context).data

    def get_materials(self, obj):
        """
        Bloque "Materiales utilizados" (Fase 11 del brief SDP) -- ServiceMaterial
        ya existia (referencia shop.ProductVariant, usado por el motor de
        costos), nunca se habia expuesto al cliente. Se agregan por
        product_variant (deduplicado) entre todas las variantes activas del
        servicio -- reusa el prefetch ya cargado por ServiceSelector.get_by_uuid
        (variants__materials__product_variant__product), sin queries nuevas.
        """
        seen = set()
        materials = []
        for variant in obj.variants.all():
            if variant.is_deleted:
                continue
            for material in variant.materials.all():
                pv = material.product_variant
                if pv is None or pv.id in seen:
                    continue
                seen.add(pv.id)
                materials.append(material)
        return ServiceMaterialSerializer(materials, many=True, context=self.context).data

    def get_content_blocks(self, obj):
        from shared.models import ContentBlockConfig
        content_type = ContentType.objects.get_for_model(TechnicalService)
        return ContentBlockConfigSelector.resolve_for(content_type, obj.uuid, ContentBlockConfig.SERVICE_DEFAULT_ORDER)

    def _get_related(self, obj, relation_type):
        content_type = ContentType.objects.get_for_model(TechnicalService)
        targets = CatalogRelationSelector.get_related_objects(content_type, obj.uuid, relation_type)
        return TechnicalServiceSerializer(targets, many=True, context=self.context).data

    def get_related_services(self, obj):
        return self._get_related(obj, CatalogRelation.RELATION_RELATED)

    def get_compatible_services(self, obj):
        return self._get_related(obj, CatalogRelation.RELATION_COMPATIBLE)

    def get_recommended_products(self, obj):
        """
        Fase 21 del brief (Productos recomendados) -- relacion cruzada real:
        CatalogRelation.related_content_type puede apuntar a shop.Product sin
        que este modulo dependa de la logica de negocio de Shop, solo de su
        serializer de lectura publico (mismo nivel de acoplamiento que ya
        existe hoy via ServiceMaterial.product_variant -> shop.ProductVariant).
        """
        content_type = ContentType.objects.get_for_model(TechnicalService)
        products = CatalogRelationSelector.get_related_objects(content_type, obj.uuid, CatalogRelation.RELATION_ACCESSORY)
        return ProductSerializer(products, many=True, context=self.context).data


# ─── Input Serializers ────────────────────────────────────────────────────────

class ServiceCategoryInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    parent = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=ServiceCategory.objects.all(),
        required=False,
        allow_null=True,
    )
    is_active = serializers.BooleanField(required=False, default=True)

    def validate_name(self, value):
        value = value.strip()
        qs = ServiceCategory.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(f"Ya existe una categoria con el nombre '{value}'.")
        return value


class ServiceLevelInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)

    def validate_name(self, value):
        value = value.strip()
        qs = ServiceLevel.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(f"Ya existe un nivel con el nombre '{value}'.")
        return value


class TechnicalServiceInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(allow_blank=True, default='')
    scope = serializers.CharField(allow_blank=True, required=False, default='')
    warranty = serializers.CharField(allow_blank=True, required=False, default='')
    coverage_notes = serializers.CharField(allow_blank=True, required=False, default='')
    category = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=ServiceCategory.objects.all(),
        required=False,
        allow_null=True,
    )
    level = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=ServiceLevel.objects.all(),
        required=False,
        allow_null=True,
    )
    is_active = serializers.BooleanField(required=False, default=True)
    is_featured = serializers.BooleanField(required=False, default=False)
    is_purchasable = serializers.BooleanField(required=False, default=True)
    meta_title = serializers.CharField(max_length=70, allow_blank=True, required=False)
    meta_description = serializers.CharField(allow_blank=True, required=False)
    meta_keywords = serializers.CharField(max_length=255, allow_blank=True, required=False)


class ServiceVariantInputSerializer(serializers.Serializer):
    sku = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    pricing_strategy = serializers.ChoiceField(
        choices=ServiceVariant.PRICING_STRATEGY_CHOICES,
        default=ServiceVariant.HOURLY,
        required=False,
    )
    estimated_hours = serializers.DecimalField(max_digits=6, decimal_places=2, default=Decimal('1.00'))
    complexity_factor = serializers.DecimalField(max_digits=4, decimal_places=2, default=Decimal('1.00'))
    fixed_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, allow_null=True, required=False
    )
    min_duration = serializers.DecimalField(max_digits=6, decimal_places=2, allow_null=True, required=False)
    max_duration = serializers.DecimalField(max_digits=6, decimal_places=2, allow_null=True, required=False)
    simultaneous_capacity = serializers.IntegerField(
        min_value=1,
        default=1,
        required=False,
        help_text="Numero maximo de instancias simultaneas. Reemplaza el stock fisico.",
    )
    is_default = serializers.BooleanField(required=False, default=False)
    is_active = serializers.BooleanField(required=False, default=True)

    def validate_sku(self, value):
        # Allow empty SKU (backend auto-generates)
        if not value or not value.strip():
            return value
        qs = ServiceVariant.objects.filter(sku=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(f"El SKU '{value}' ya esta en uso.")
        return value.strip()


class TechnicalServiceAdminCreateSerializer(TechnicalServiceInputSerializer):
    initial_variant = serializers.DictField(required=False, allow_empty=True, write_only=True)

    def validate_initial_variant(self, value):
        if not value:
            return None
        allowed = {
            'pricing_strategy',
            'estimated_hours',
            'complexity_factor',
            'fixed_price',
        }
        variant_payload = {k: v for k, v in value.items() if k in allowed}
        serializer = ServiceVariantInputSerializer(data=variant_payload, partial=True)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class ServiceMaterialInputSerializer(serializers.Serializer):
    product_variant = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=_PV.objects.all(),
    )
    quantity = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=Decimal('0.01'))


class ServiceConfigurationInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, default='Configuracion Colombia')
    smlv = serializers.DecimalField(max_digits=12, decimal_places=2)
    transport_subsidy = serializers.DecimalField(max_digits=12, decimal_places=2)
    benefit_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    indirect_costs_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    iva_rate = serializers.DecimalField(max_digits=5, decimal_places=2, default=Decimal('19.00'))
    is_active = serializers.BooleanField(required=False, default=True)


# ─── Service Request Satellite Output Serializers ─────────────────────────────

class ContactPersonSerializer(serializers.Serializer):
    full_name       = serializers.CharField(max_length=150)
    document_type   = serializers.ChoiceField(choices=['CC', 'CE', 'PP', 'TI', 'NIT', 'OTRO'])
    document_number = serializers.CharField(max_length=30)
    cargo           = serializers.CharField(max_length=100)
    email           = serializers.EmailField()
    phone           = serializers.CharField(max_length=20)
    phone_alt       = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    company         = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    department      = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    access_notes    = serializers.CharField(required=False, allow_blank=True, default='')


class OrderServiceDetailSerializer(serializers.ModelSerializer):
    technician     = serializers.SerializerMethodField()
    contact_person = serializers.JSONField(read_only=True)

    class Meta:
        model = OrderServiceDetail
        fields = [
            'uuid', 'priority', 'description', 'address', 'scheduled_at',
            'preferred_date', 'preferred_time', 'location_reference', 'neighborhood',
            'service_notes', 'allow_schedule_changes', 'technician',
            'professional_type_snapshot', 'applied_rate_type', 'applied_rate_amount',
            'booked_date', 'booked_start_time',
            'contact_person',
        ]

    def get_technician(self, obj):
        # Migracion "autoridad unica de tecnico" FASE 4/9 (2026-08-14): prioriza
        # ServiceOperation.technician (la fuente real) sobre el snapshot legacy
        # obj.technician, evitando exponer un valor obsoleto si la asignacion se
        # movio desde el panel de Servicios/la fachada admin en vez de este
        # endpoint legacy. Fallback a obj.technician solo si aun no existe
        # ServiceOperation para la orden (caso residual, ensure_for_order() la
        # crea automaticamente en el flujo normal).
        operation = getattr(obj.order, 'service_operation', None)
        technician = operation.technician if operation and operation.technician_id else obj.technician
        if not technician:
            return None
        from users.api.serializers import UserDetailSerializer
        return UserDetailSerializer(technician).data


class OrderServiceTimelineSerializer(serializers.ModelSerializer):
    created_by_email = serializers.ReadOnlyField(source='created_by.email')

    class Meta:
        model = OrderServiceTimeline
        fields = ['uuid', 'status', 'notes', 'created_by_email', 'created_at']


class ServiceAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.ReadOnlyField(source='uploaded_by.email')

    class Meta:
        model = ServiceAttachment
        fields = ['uuid', 'file', 'file_name', 'file_size', 'mime_type', 'doc_type', 'uploaded_by_email', 'created_at']


from orders.models import Order
from orders.api.serializers import OrderItemSerializer


class ServiceOrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    service_detail = OrderServiceDetailSerializer(read_only=True)
    timeline = OrderServiceTimelineSerializer(many=True, read_only=True)
    attachments = ServiceAttachmentSerializer(many=True, read_only=True)
    user_email = serializers.ReadOnlyField(source='user.email')
    request_package = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'uuid', 'status', 'total_amount', 'discount_amount',
            'tracking_number', 'items', 'service_detail', 'timeline',
            'attachments', 'user_email', 'created_at', 'request_package',
        ]
        read_only_fields = fields

    def get_request_package(self, obj):
        request_package = getattr(obj, 'request_package', None)
        if request_package is None:
            return None
        from technical_services.api.package_serializers import ServiceRequestPackageSerializer
        return ServiceRequestPackageSerializer(request_package).data


# ─── Tablero de Asignacion de Tecnicos (/panel/asignacion-tecnicos) ──────────

class TechnicianCandidateSerializer(serializers.Serializer):
    """Candidato para asignacion, expuesto por TechnicianSelector.get_candidates_for_order."""
    uuid = serializers.UUIDField()
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField()
    is_available = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    profile_uuid = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_is_available(self, obj):
        from accounts.services.profile_resolver import ProfileResolver
        profile = ProfileResolver.get_technician_profile(obj)
        return bool(profile and profile.is_available)

    def get_average_rating(self, obj):
        from accounts.services.profile_resolver import ProfileResolver
        profile = ProfileResolver.get_profile(obj)
        return float(profile.average_rating) if profile else None

    def get_profile_uuid(self, obj):
        from accounts.services.profile_resolver import ProfileResolver
        profile = ProfileResolver.get_profile(obj)
        return str(profile.uuid) if profile else None


class PriorityChangeInputSerializer(serializers.Serializer):
    priority = serializers.ChoiceField(choices=OrderServiceDetail.PRIORITY_CHOICES)


class ServiceAssignmentQueueSerializer(serializers.ModelSerializer):
    """
    Listado liviano para el tablero de asignacion de tecnicos. Requiere que la orden venga
    con select_related/prefetch_related de get_queryset() (items__service_variant__service__category,
    timeline, service_detail__technician__technician_profile, service_operation__technician__
    technician_profile -- este ultimo agregado en FASE 4 2026-08-14, ver
    TECHNICIAN_ASSIGNMENT_MIGRATION_FASE0_2026-08-14.md) -- current_status, category_name y
    technician NUNCA disparan una query nueva por fila, solo leen las colecciones ya prefetcheadas.
    """
    client_email = serializers.ReadOnlyField(source='user.email')
    client_name = serializers.SerializerMethodField()
    service_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    priority = serializers.SerializerMethodField()
    current_status = serializers.SerializerMethodField()
    technician = serializers.SerializerMethodField()
    estimated_hours = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'uuid', 'tracking_number', 'client_email', 'client_name',
            'service_name', 'category_name', 'priority', 'current_status',
            'technician', 'estimated_hours', 'location', 'created_at',
        ]
        read_only_fields = fields

    def _first_service_item(self, obj):
        for item in obj.service_items_prefetch:
            if item.service_variant_id:
                return item
        return None

    def get_client_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    def get_service_name(self, obj):
        item = self._first_service_item(obj)
        return item.item_name if item else None

    def get_category_name(self, obj):
        item = self._first_service_item(obj)
        if not item or not item.service_variant or not item.service_variant.service.category:
            return None
        return item.service_variant.service.category.name

    def get_priority(self, obj):
        detail = getattr(obj, 'service_detail', None)
        return detail.priority if detail else None

    def get_current_status(self, obj):
        events = list(obj.timeline.all())
        return events[-1].status if events else None

    def get_technician(self, obj):
        # FASE 4/9 (2026-08-14): ServiceOperation.technician es la fuente real --
        # ver docstring de OrderServiceDetailSerializer.get_technician().
        operation = getattr(obj, 'service_operation', None)
        detail = getattr(obj, 'service_detail', None)
        technician = operation.technician if operation and operation.technician_id else (
            detail.technician if detail else None
        )
        if not technician:
            return None
        from accounts.services.profile_resolver import ProfileResolver
        tech_profile = ProfileResolver.get_technician_profile(technician)
        user_profile = ProfileResolver.get_profile(technician)
        return {
            'uuid': str(technician.uuid),
            'profile_uuid': str(user_profile.uuid) if user_profile else None,
            'full_name': technician.get_full_name(),
            'email': technician.email,
            'is_available': bool(tech_profile and tech_profile.is_available),
        }

    def get_estimated_hours(self, obj):
        item = self._first_service_item(obj)
        if not item or not item.service_variant:
            return None
        return float(item.service_variant.estimated_hours)

    def get_location(self, obj):
        detail = getattr(obj, 'service_detail', None)
        if not detail:
            return None
        return {'address': detail.address, 'neighborhood': detail.neighborhood}


# ─── Service Request Input Serializers ────────────────────────────────────────

class ServiceRequestInputSerializer(serializers.Serializer):
    variant_uuid = serializers.UUIDField()
    quantity = serializers.IntegerField(default=1, min_value=1)
    duration = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    # discount_pct acotado 0..100: sin estos limites, un cliente podia enviar
    # >100 (total negativo) o <0 (subir el precio). Ver R-01 de la auditoria.
    discount_pct = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True,
        min_value=0, max_value=100,
    )
    selected_technician_uuid = serializers.UUIDField(required=False, allow_null=True)
    selected_slot_id = serializers.IntegerField(required=False, allow_null=True)

    # Paquete de servicio (2026-07-16, aditivo): opcional -- si no se envia,
    # el flujo de compra de un servicio suelto sigue igual (compatibilidad).
    package_uuid = serializers.UUIDField(required=False, allow_null=True)
    additional_costs = serializers.ListField(
        child=serializers.DictField(), required=False, default=list,
        help_text='Lista de {"additional_cost_uuid": "...", "quantity": N}',
    )

    # Detail metadata
    priority     = serializers.ChoiceField(choices=OrderServiceDetail.PRIORITY_CHOICES, default='medium')
    description  = serializers.CharField()
    address      = serializers.CharField(max_length=255)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)
    preferred_date = serializers.DateField(required=False, allow_null=True)
    preferred_time = serializers.TimeField(required=False, allow_null=True)
    location_reference = serializers.CharField(required=False, allow_blank=True, default='')
    neighborhood = serializers.CharField(required=False, allow_blank=True, default='')
    service_notes = serializers.CharField(required=False, allow_blank=True, default='')
    allow_schedule_changes = serializers.BooleanField(required=False, default=True)

    # Encargado del servicio (obligatorio)
    contact_person = ContactPersonSerializer()

    def validate_variant_uuid(self, value):
        try:
            return ServiceVariant.objects.get(uuid=value, is_deleted=False)
        except ServiceVariant.DoesNotExist:
            raise serializers.ValidationError("Service variant does not exist.")

    def validate_selected_technician_uuid(self, value):
        if value is None:
            return None
        from users.models import User
        try:
            return User.objects.get(uuid=value, is_active=True, is_deleted=False)
        except User.DoesNotExist:
            raise serializers.ValidationError("El profesional seleccionado no existe o no esta disponible.")

    def validate_scheduled_at(self, value):
        if value is None:
            return value
        from django.utils import timezone
        if value <= timezone.now():
            raise serializers.ValidationError(
                "La fecha y hora de ejecucion debe ser en el futuro."
            )
        return value

    def validate_package_uuid(self, value):
        if value is None:
            return None
        from technical_services.models import ServicePackage
        try:
            return ServicePackage.objects.get(uuid=value, is_deleted=False)
        except ServicePackage.DoesNotExist:
            raise serializers.ValidationError("El paquete seleccionado no existe.")

    def validate(self, data):
        package = data.get('package_uuid')
        variant = data.get('variant_uuid')
        if package is not None and variant is not None and package.service_id != variant.service_id:
            raise serializers.ValidationError({'package_uuid': 'El paquete seleccionado no pertenece a este servicio.'})

        if data.get('additional_costs'):
            from technical_services.models import PackageAdditionalCost
            resolved = []
            for entry in data['additional_costs']:
                cost_uuid = entry.get('additional_cost_uuid')
                quantity = int(entry.get('quantity', 1))
                try:
                    cost = PackageAdditionalCost.objects.get(uuid=cost_uuid, is_deleted=False)
                except (PackageAdditionalCost.DoesNotExist, ValueError, TypeError):
                    raise serializers.ValidationError(
                        {'additional_costs': f'Costo adicional invalido: {cost_uuid}'}
                    )
                if package is not None and cost.package_id != package.id:
                    raise serializers.ValidationError(
                        {'additional_costs': f'El costo "{cost.name}" no pertenece al paquete seleccionado.'}
                    )
                resolved.append({'additional_cost': cost, 'quantity': quantity})
            data['additional_costs'] = resolved
        return data


class ServiceTimelineInputSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=OrderServiceTimeline.STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class ServiceAttachmentInputSerializer(serializers.Serializer):
    file = serializers.FileField()
    doc_type = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')


class TechnicianAssignmentInputSerializer(serializers.Serializer):
    technician_uuid = serializers.UUIDField()

    def validate_technician_uuid(self, value):
        from users.models import User
        try:
            return User.objects.get(
                uuid=value,
                is_active=True,
                is_deleted=False,
                technician_profile__isnull=False,
            )
        except User.DoesNotExist:
            raise serializers.ValidationError("Tecnico no encontrado o no disponible.")


# ---- Cost Rules -----------------------------------------------------------

class ServiceCostRuleSerializer(serializers.ModelSerializer):
    class Meta:
        from technical_services.models import ServiceCostRule
        model = ServiceCostRule
        fields = [
            'id', 'uuid', 'name', 'description', 'cost_type', 'context',
            'value', 'applies_globally', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'uuid', 'created_at']


class ServiceCostRuleInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    cost_type = serializers.ChoiceField(choices=['FIXED', 'PERCENTAGE'])
    context = serializers.ChoiceField(choices=['TAX', 'DISCOUNT', 'SETUP', 'OPERATIONAL'])
    value = serializers.DecimalField(max_digits=12, decimal_places=4, min_value=Decimal('0'))
    applies_globally = serializers.BooleanField(default=False, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ServiceCostAssignmentInputSerializer(serializers.Serializer):
    variant_uuid = serializers.UUIDField()


# ---------------------------------------------------------------------------
# Catalogo enriquecido de TechnicalService (2026-08-05) -- espejo de
# shop/api/serializers.py (mismo bloque, "Catalogo enriquecido de Product").
# ---------------------------------------------------------------------------

class ServiceIncludedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceIncludedItem
        fields = ['uuid', 'title', 'description', 'icon', 'position', 'is_active']
        read_only_fields = ['uuid']


class ServiceIncludedItemInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    icon = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ServiceExcludedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceExcludedItem
        fields = ['uuid', 'title', 'description', 'icon', 'position', 'is_active']
        read_only_fields = ['uuid']


class ServiceExcludedItemInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    icon = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ServiceRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequirement
        fields = ['uuid', 'title', 'description', 'position', 'is_active']
        read_only_fields = ['uuid']


class ServiceRequirementInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ServiceSpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceSpecification
        fields = ['uuid', 'name', 'value', 'position', 'is_active']
        read_only_fields = ['uuid']


class ServiceSpecificationGroupSerializer(serializers.ModelSerializer):
    specifications = ServiceSpecificationSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceSpecificationGroup
        fields = ['uuid', 'name', 'position', 'is_active', 'specifications']
        read_only_fields = ['uuid']


class ServiceSpecificationGroupInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ServiceSpecificationInputSerializer(serializers.Serializer):
    group = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=ServiceSpecificationGroup.objects.filter(is_deleted=False),
    )
    name = serializers.CharField(max_length=150)
    value = serializers.CharField(max_length=255)
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ServiceDocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)

    class Meta:
        model = ServiceDocument
        fields = [
            'uuid', 'title', 'description', 'document_type', 'document_type_display',
            'file', 'cover_image', 'downloads', 'position', 'is_public', 'is_active', 'created_at',
        ]
        read_only_fields = ['uuid', 'downloads', 'created_at']


class ServiceDocumentInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    document_type = serializers.ChoiceField(choices=ServiceDocument.DOCUMENT_TYPE_CHOICES, default=ServiceDocument.TYPE_OTRO)
    cover_image = serializers.ImageField(required=False, allow_null=True)
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_public = serializers.BooleanField(default=True, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ServiceVideoSerializer(serializers.ModelSerializer):
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    embed_url = serializers.SerializerMethodField()

    class Meta:
        model = ServiceVideo
        fields = [
            'uuid', 'title', 'source_type', 'source_type_display',
            'video_url', 'video_file', 'thumbnail', 'embed_url', 'position', 'is_active',
        ]
        read_only_fields = ['uuid']

    def get_embed_url(self, obj):
        import re
        if obj.source_type == ServiceVideo.SOURCE_YOUTUBE and obj.video_url:
            match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([^&?/]+)', obj.video_url)
            return f'https://www.youtube.com/embed/{match.group(1)}' if match else obj.video_url
        if obj.source_type == ServiceVideo.SOURCE_VIMEO and obj.video_url:
            match = re.search(r'vimeo\.com/(\d+)', obj.video_url)
            return f'https://player.vimeo.com/video/{match.group(1)}' if match else obj.video_url
        if obj.source_type == ServiceVideo.SOURCE_MP4 and obj.video_file:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.video_file.url) if request else obj.video_file.url
        return obj.video_url or None


class ServiceVideoInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    source_type = serializers.ChoiceField(choices=ServiceVideo.SOURCE_TYPE_CHOICES, default=ServiceVideo.SOURCE_YOUTUBE)
    video_url = serializers.URLField(required=False, allow_blank=True, default='')
    video_file = serializers.FileField(required=False, allow_null=True)
    thumbnail = serializers.ImageField(required=False, allow_null=True)
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ServiceProcessStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProcessStep
        fields = ['uuid', 'step_number', 'title', 'description', 'image', 'estimated_time', 'position', 'is_active']
        read_only_fields = ['uuid']


class ServiceProcessStepInputSerializer(serializers.Serializer):
    step_number = serializers.IntegerField(min_value=1, default=1, required=False)
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    image = serializers.ImageField(required=False, allow_null=True)
    estimated_time = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    position = serializers.IntegerField(min_value=0, default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ServiceCatalogReorderInputSerializer(serializers.Serializer):
    """Payload generico de reorder: lista ordenada de uuids (drag&drop)."""
    ordered_uuids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
