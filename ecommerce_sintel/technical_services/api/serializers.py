from decimal import Decimal
from rest_framework import serializers
from shop.models import ProductVariant as _PV
from technical_services.models import (
    TechnicalService, ServiceVariant, ServiceMaterial,
    ServiceCategory, ServiceLevel, ServiceImage, ServiceConfiguration,
    OrderServiceDetail, OrderServiceTimeline, ServiceAttachment,
    ServicePriceHistory, ServiceFAQ, ServiceMarketing, ServiceReview,
)


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
        fields = ['uuid', 'image', 'alt_text', 'is_primary']


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
            'is_default', 'is_active', 'materials',
        ]

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
        fields = ['uuid', 'old_price', 'new_price', 'changed_by_email', 'created_at']


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
        if not obj.technician:
            return None
        from users.api.serializers import UserDetailSerializer
        return UserDetailSerializer(obj.technician).data


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
    timeline, service_detail__technician__technician_profile) -- current_status y category_name
    NUNCA disparan una query nueva por fila, solo leen las colecciones ya prefetcheadas.
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
        detail = getattr(obj, 'service_detail', None)
        technician = detail.technician if detail else None
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
    discount_pct = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
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
