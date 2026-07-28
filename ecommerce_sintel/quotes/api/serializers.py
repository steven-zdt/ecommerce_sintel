from datetime import date, timedelta
from rest_framework import serializers
from quotes.models import (
    Quotation, QuotationItem, QuotationService,
    QuotationMaterial, QuoteProduct, QuoteProductVariant,
    QuotationItemCostSnapshot, QuotationRentalItem, QuotationAttachment,
    QuotationTimeline, QuoteTemplateCategory, QuoteTemplateSubcategory,
    QuoteTemplate, QuoteTemplateAttribute, QuoteEquipmentType, QuoteTemplateModule,
    QuoteQuestion, QuoteQuestionOption,
)
from quotes.services.labor_conditions_evaluator import LaborConditionsEvaluator


class QuotationItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = QuotationItem
        fields = ['uuid', 'product_name', 'sku', 'quantity', 'unit_price', 'unit_price_final', 'subtotal']
        read_only_fields = fields


class QuotationMaterialSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = QuotationMaterial
        fields = ['uuid', 'material_name', 'unit_price', 'quantity', 'subtotal']
        read_only_fields = fields


class QuotationServiceSerializer(serializers.ModelSerializer):
    materials = QuotationMaterialSerializer(many=True, read_only=True)
    material_cost = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = QuotationService
        fields = [
            'uuid', 'service_name', 'hours', 'labor_cost',
            'custom_service_type', 'labor_description',
            'estimated_time_hours', 'requires_full_cost_installation',
            'materials', 'material_cost', 'subtotal',
        ]
        read_only_fields = fields


class QuotationRentalItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationRentalItem
        fields = [
            'uuid', 'equipment_name', 'sku',
            'rental_price_per_day', 'rental_price_per_hour',
            'rent_start_date', 'rent_end_date',
            'computed_days', 'subtotal',
        ]
        read_only_fields = fields


class QuotationAttachmentSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()

    class Meta:
        model = QuotationAttachment
        fields = ['uuid', 'file', 'note', 'file_name', 'file_size', 'created_at']
        read_only_fields = fields

    def get_file_name(self, obj):
        return obj.file.name.rsplit('/', 1)[-1] if obj.file else ''

    def get_file_size(self, obj):
        try:
            return obj.file.size
        except (ValueError, OSError):
            return None


class QuotationTimelineSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True, default='')

    class Meta:
        model = QuotationTimeline
        fields = ('uuid', 'status', 'status_display', 'notes', 'changed_by_name', 'created_at')
        read_only_fields = fields


class QuotationListSerializer(serializers.ModelSerializer):
    """Version liviana para listados — sin items/servicios/timeline anidados."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True, allow_null=True)
    # Q-07 (auditoria enterprise): source='attachments.count' dispara un
    # COUNT(*) por fila -- .count() en un related manager ignora el cache de
    # prefetch. El queryset ahora anota 'attachments_count' via Count() en
    # QuotationSelector.list_all_for_admin() y en el get_queryset() no-staff
    # del ViewSet; sin source, DRF lee el atributo anotado directo.
    attachments_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Quotation
        fields = [
            'id', 'uuid', 'client_name', 'client_email', 'status', 'status_display',
            'is_custom', 'template_name', 'total_amount', 'created_at', 'attachments_count',
        ]
        read_only_fields = fields


class QuotationSerializer(serializers.ModelSerializer):
    items = QuotationItemSerializer(many=True, read_only=True)
    services = QuotationServiceSerializer(many=True, read_only=True)
    rental_items = QuotationRentalItemSerializer(many=True, read_only=True)
    attachments = QuotationAttachmentSerializer(many=True, read_only=True)
    timeline = QuotationTimelineSerializer(source='timeline_events', many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True, allow_null=True)
    template_uuid = serializers.UUIDField(source='template.uuid', read_only=True, allow_null=True)
    labor_analysis = serializers.SerializerMethodField()

    class Meta:
        model = Quotation
        fields = [
            'id', 'uuid', 'client_name', 'client_email', 'valid_until',
            'status', 'status_display', 'is_custom',
            'subtotal_products', 'subtotal_services', 'subtotal_rentals',
            'total_amount', 'notes',
            'items', 'services', 'rental_items', 'attachments', 'timeline',
            'template_uuid', 'template_name', 'answers', 'labor_analysis',
            'company', 'document_type', 'document_number', 'phone',
            'city', 'department', 'address', 'gps_location', 'project_name',
            'created_at',
        ]
        read_only_fields = fields

    def get_labor_analysis(self, obj):
        """
        Resultado de LaborConditionsEvaluator para el asesor (FASE 10, plan
        "Simplificacion Inteligente" 2026-07-23) -- calculado en cada
        lectura a partir de installation_height, nunca persistido, para que
        un ajuste futuro de umbrales se refleje de inmediato sin migrar
        datos historicos.

        Gateado a staff (Q-03, auditoria enterprise): este mismo serializer
        se usa tanto para el asesor como para el cliente dueno de la
        cotizacion (get_queryset() del ViewSet permite a un no-staff ver su
        propia Quotation) -- sin este chequeo, el cliente recibia
        risk_level/required_access_equipment, datos de evaluacion interna de
        riesgo pensados solo para el asesor. Si no hay request en el
        contexto (algunas respuestas manuales de views.py no lo pasan), se
        omite por defecto -- fail-closed, no fail-open.
        """
        request = self.context.get('request')
        if not (request and request.user.is_authenticated and request.user.is_staff):
            return None
        if not obj.template_id:
            return None
        module = obj.template.modules.filter(module_type='LABOR', is_deleted=False).first()
        if not module:
            return None
        module_answers = (obj.answers or {}).get(str(module.uuid), {})
        result = LaborConditionsEvaluator.evaluate(module_answers.get('installation_height'))
        if result is None:
            return None
        return {
            'installation_height': str(result['installation_height']),
            'work_at_height': result['work_at_height'],
            'risk_level': result['risk_level'],
            'required_access_equipment': result['required_access_equipment'],
            'allowed_schedule': module_answers.get('allowed_schedule'),
            'site_access_requirements': module_answers.get('site_access_requirements'),
            'power_available': module_answers.get('power_available'),
        }


# --- Input serializers ---

class RentalItemInputSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField()
    rent_start_date = serializers.DateField()
    rent_end_date = serializers.DateField()

    def validate(self, attrs):
        if attrs['rent_end_date'] <= attrs['rent_start_date']:
            raise serializers.ValidationError("rent_end_date must be after rent_start_date.")
        return attrs


class CustomMaterialInputSerializer(serializers.Serializer):
    material_name = serializers.CharField(max_length=255)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    quantity = serializers.DecimalField(max_digits=8, decimal_places=2)


class CustomServiceInputSerializer(serializers.Serializer):
    custom_service_type = serializers.CharField(max_length=100, required=False, allow_blank=True)
    service_name = serializers.CharField(max_length=255)
    labor_description = serializers.CharField(required=False, allow_blank=True)
    hours = serializers.DecimalField(max_digits=6, decimal_places=2)
    labor_cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    estimated_time_hours = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    requires_full_cost_installation = serializers.BooleanField(default=False)
    materials = CustomMaterialInputSerializer(many=True, required=False, default=list)


class QuotationCreateInputSerializer(serializers.Serializer):
    client_name = serializers.CharField(max_length=255)
    client_email = serializers.EmailField()
    valid_until = serializers.DateField()
    notes = serializers.CharField(required=False, allow_blank=True)
    is_custom = serializers.BooleanField(default=False)

    product_items = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )
    service_items = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )
    rental_items = RentalItemInputSerializer(many=True, required=False, default=list)
    custom_service_data = CustomServiceInputSerializer(many=True, required=False, default=list)


class QuotationFromTemplateInputSerializer(serializers.Serializer):
    """Input del cuestionario tecnico dinamico en /cotizar. No incluye ningun precio."""
    # Solo plantillas publicadas y activas son elegibles -- sin este filtro,
    # un cliente autenticado que conozca/adivine el uuid de un borrador
    # puede crear una Solicitud real contra una plantilla que el admin
    # nunca aprobo publicar (hallazgo QA E2E 2026-07-22, HG-01).
    template = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=QuoteTemplate.objects.filter(is_published=True, is_active=True, is_internal=False),
    )
    answers = serializers.DictField(required=False, default=dict, help_text='{"<module_uuid>": {"<question_key>": valor}}')

    client_name = serializers.CharField(max_length=255)
    client_email = serializers.EmailField()
    valid_until = serializers.DateField(required=False, default=lambda: date.today() + timedelta(days=15))
    notes = serializers.CharField(required=False, allow_blank=True, default='')

    company = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    # Identificacion obligatoria del destinatario (propio usuario o tercero) — ninguna
    # solicitud se crea sin saber a quien pertenece.
    document_type = serializers.ChoiceField(choices=[('NIT', 'NIT'), ('CC', 'CC')])
    document_number = serializers.CharField(max_length=30, allow_blank=False)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')
    city = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    department = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    address = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    gps_location = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    project_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')


class QuotationStatusChangeInputSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Quotation.STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class QuotationAddItemInputSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class QuotationAddServiceInputSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField(required=False, allow_null=True)
    custom_service_type = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    service_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    labor_description = serializers.CharField(required=False, allow_blank=True, default='')
    hours = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, default='0.00')
    labor_cost = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default='0.00')
    estimated_time_hours = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    requires_full_cost_installation = serializers.BooleanField(default=False)
    materials = CustomMaterialInputSerializer(many=True, required=False, default=list)


class QuotationItemCostSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationItemCostSnapshot
        fields = ('uuid', 'cost_name', 'context', 'cost_type', 'value', 'computed_amount', 'is_discount')
        read_only_fields = fields


# ─── Constructor de Cuestionarios Tecnicos: Serializers de plantillas ────────

# --- Output ---

class QuoteTemplateAttributeSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source='get_kind_display', read_only=True)
    subcategory_uuid = serializers.UUIDField(source='subcategory.uuid', read_only=True, allow_null=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True, allow_null=True)

    class Meta:
        model = QuoteTemplateAttribute
        fields = (
            'uuid', 'kind', 'kind_display', 'name', 'slug', 'description', 'icon',
            'subcategory_uuid', 'subcategory_name', 'display_order', 'is_active',
        )
        read_only_fields = fields


class QuoteTemplateCategorySerializer(serializers.ModelSerializer):
    service_type = QuoteTemplateAttributeSerializer(read_only=True)

    class Meta:
        model = QuoteTemplateCategory
        fields = ('uuid', 'name', 'slug', 'description', 'icon', 'service_type', 'display_order', 'is_active')
        read_only_fields = fields


class QuoteTemplateSubcategorySerializer(serializers.ModelSerializer):
    category_uuid = serializers.UUIDField(source='category.uuid', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = QuoteTemplateSubcategory
        fields = (
            'uuid', 'category_uuid', 'category_name', 'name', 'slug',
            'description', 'icon', 'display_order', 'is_active',
        )
        read_only_fields = fields


class QuoteQuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuoteQuestionOption
        fields = ('uuid', 'label', 'value', 'display_order', 'is_active')
        read_only_fields = fields


class QuoteQuestionSerializer(serializers.ModelSerializer):
    question_type_display = serializers.CharField(source='get_question_type_display', read_only=True)
    options = QuoteQuestionOptionSerializer(many=True, read_only=True)
    # Se expone el `key` (no el uuid) de la pregunta de la que depende --
    # es lo que el wizard ya usa para leer respuestas (answerFor(moduleUuid,
    # key)), evita que el frontend tenga que resolver un uuid extra.
    depends_on_question_key = serializers.SerializerMethodField()

    class Meta:
        model = QuoteQuestion
        fields = (
            'uuid', 'key', 'question_type', 'question_type_display', 'label',
            'description', 'help_text', 'placeholder', 'is_required', 'is_visible',
            'default_value', 'unit', 'group', 'min_value', 'max_value',
            'validation_regex', 'table_columns',
            'display_order', 'is_active', 'allow_other', 'options',
            'depends_on_question_key', 'depends_on_values',
        )
        read_only_fields = fields

    def get_depends_on_question_key(self, obj):
        return obj.depends_on_question.key if obj.depends_on_question_id else None


class QuoteEquipmentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuoteEquipmentType
        fields = ('uuid', 'name', 'slug', 'description', 'icon', 'display_order', 'is_active')
        read_only_fields = fields


class QuoteTemplateModuleSerializer(serializers.ModelSerializer):
    module_type_display = serializers.CharField(source='get_module_type_display', read_only=True)
    equipment_type = QuoteEquipmentTypeSerializer(read_only=True)
    questions = QuoteQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = QuoteTemplateModule
        fields = (
            'uuid', 'module_type', 'module_type_display', 'equipment_type', 'name',
            'description', 'unit', 'min_quantity', 'max_quantity', 'is_required',
            'display_order', 'is_active', 'questions',
        )
        read_only_fields = fields


class QuoteTemplateListSerializer(serializers.ModelSerializer):
    """Version liviana para listados — sin el arbol completo de modulos."""
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True, allow_null=True)
    service_type_name = serializers.CharField(source='category.service_type.name', read_only=True, allow_null=True)
    installation_type_name = serializers.CharField(source='installation_type.name', read_only=True, allow_null=True)
    system_type_name = serializers.CharField(source='system_type.name', read_only=True, allow_null=True)

    complexity_hint_display = serializers.CharField(source='get_complexity_hint_display', read_only=True)

    class Meta:
        model = QuoteTemplate
        fields = (
            'uuid', 'name', 'slug', 'code', 'description', 'category_name', 'subcategory_name',
            'service_type_name', 'installation_type_name', 'system_type_name', 'version', 'is_published',
            'display_order', 'is_active', 'complexity_hint', 'complexity_hint_display',
        )
        read_only_fields = fields


class QuoteTemplateSerializer(serializers.ModelSerializer):
    """Version completa — incluye el arbol de modulos/preguntas/opciones."""
    category = QuoteTemplateCategorySerializer(read_only=True)
    subcategory = QuoteTemplateSubcategorySerializer(read_only=True)
    # Tipo de Servicio ya no es propio de la plantilla — se hereda de la categoria.
    service_type = QuoteTemplateAttributeSerializer(source='category.service_type', read_only=True)
    installation_type = QuoteTemplateAttributeSerializer(read_only=True)
    system_type = QuoteTemplateAttributeSerializer(read_only=True)
    modules = QuoteTemplateModuleSerializer(many=True, read_only=True)
    complexity_hint_display = serializers.CharField(source='get_complexity_hint_display', read_only=True)

    class Meta:
        model = QuoteTemplate
        fields = (
            'uuid', 'name', 'slug', 'code', 'description', 'category', 'subcategory',
            'service_type', 'installation_type', 'system_type', 'version', 'is_published',
            'display_order', 'is_active', 'modules', 'complexity_hint', 'complexity_hint_display',
        )
        read_only_fields = fields


# --- Input ---

class QuoteTemplateCategoryInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    icon = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    service_type = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=QuoteTemplateAttribute.objects.filter(kind=QuoteTemplateAttribute.KIND_SERVICE_TYPE),
        required=False, allow_null=True,
    )
    display_order = serializers.IntegerField(required=False, default=0)
    is_active = serializers.BooleanField(required=False, default=True)


class QuoteTemplateSubcategoryInputSerializer(serializers.Serializer):
    category = serializers.SlugRelatedField(slug_field='uuid', queryset=QuoteTemplateCategory.objects.all())
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    icon = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    display_order = serializers.IntegerField(required=False, default=0)
    is_active = serializers.BooleanField(required=False, default=True)


class QuoteTemplateInputSerializer(serializers.Serializer):
    category = serializers.SlugRelatedField(
        slug_field='uuid', queryset=QuoteTemplateCategory.objects.all(),
        required=False, allow_null=True,
    )
    subcategory = serializers.SlugRelatedField(
        slug_field='uuid', queryset=QuoteTemplateSubcategory.objects.all(),
        required=False, allow_null=True,
    )
    name = serializers.CharField(max_length=255)
    code = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    # Tipo de Servicio ya no se elige aca: se hereda de category.service_type
    # (Tipo de Servicio -> Categoria -> Subcategoria -> Tipo de Instalacion).
    installation_type = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=QuoteTemplateAttribute.objects.filter(kind=QuoteTemplateAttribute.KIND_INSTALLATION_TYPE),
        required=False, allow_null=True,
    )
    system_type = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=QuoteTemplateAttribute.objects.filter(kind=QuoteTemplateAttribute.KIND_SYSTEM_TYPE),
        required=False, allow_null=True,
    )
    version = serializers.IntegerField(required=False, default=1)
    is_published = serializers.BooleanField(required=False, default=False)
    display_order = serializers.IntegerField(required=False, default=0)
    is_active = serializers.BooleanField(required=False, default=True)
    # Indicador manual de complejidad (Fase E) -- nunca calculado, ver
    # QuoteTemplate.complexity_hint.
    complexity_hint = serializers.ChoiceField(
        choices=QuoteTemplate.COMPLEXITY_CHOICES, required=False, allow_blank=True, default='',
    )

    def validate(self, attrs):
        installation_type = attrs.get('installation_type')
        subcategory = attrs.get('subcategory')
        if installation_type and subcategory and installation_type.subcategory_id != subcategory.id:
            raise serializers.ValidationError({
                'installation_type': 'Este tipo de instalacion no pertenece a la subcategoria seleccionada.',
            })
        return attrs


class QuoteTemplateAttributeInputSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=QuoteTemplateAttribute.KIND_CHOICES)
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    icon = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    # Solo aplica cuando kind=INSTALLATION_TYPE: subcategoria dueña de esta opcion.
    subcategory = serializers.SlugRelatedField(
        slug_field='uuid', queryset=QuoteTemplateSubcategory.objects.all(),
        required=False, allow_null=True,
    )
    display_order = serializers.IntegerField(required=False, default=0)
    is_active = serializers.BooleanField(required=False, default=True)


class QuoteEquipmentTypeInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    icon = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    display_order = serializers.IntegerField(required=False, default=0)
    is_active = serializers.BooleanField(required=False, default=True)


class QuoteTemplateModuleInputSerializer(serializers.Serializer):
    module_type = serializers.ChoiceField(choices=QuoteTemplateModule.MODULE_TYPE_CHOICES, default=QuoteTemplateModule.MODULE_EQUIPMENT)
    equipment_type = serializers.SlugRelatedField(
        slug_field='uuid', queryset=QuoteEquipmentType.objects.all(),
        required=False, allow_null=True,
    )
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    unit = serializers.CharField(max_length=50, required=False, allow_blank=True, default='unidad')
    min_quantity = serializers.IntegerField(required=False, allow_null=True)
    max_quantity = serializers.IntegerField(required=False, allow_null=True)
    is_required = serializers.BooleanField(required=False, default=False)
    display_order = serializers.IntegerField(required=False, default=0)
    is_active = serializers.BooleanField(required=False, default=True)


class QuoteModuleReorderInputSerializer(serializers.Serializer):
    direction = serializers.ChoiceField(choices=[('up', 'up'), ('down', 'down')])


class QuoteQuestionInputSerializer(serializers.Serializer):
    key = serializers.SlugField(max_length=100, required=False, allow_blank=True, default='')
    question_type = serializers.ChoiceField(choices=QuoteQuestion.QUESTION_TYPE_CHOICES, default=QuoteQuestion.TYPE_TEXT)
    label = serializers.CharField(max_length=500)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    help_text = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    placeholder = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    is_required = serializers.BooleanField(required=False, default=False)
    is_visible = serializers.BooleanField(required=False, default=True)
    default_value = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    unit = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    group = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    min_value = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    max_value = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    validation_regex = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    table_columns = serializers.ListField(child=serializers.CharField(max_length=100), required=False, default=list)
    display_order = serializers.IntegerField(required=False, default=0)
    is_active = serializers.BooleanField(required=False, default=True)
    allow_other = serializers.BooleanField(required=False, default=False)
    # Visibilidad condicional (Fase F) — depends_on_question se valida contra
    # el modulo destino via context (ver AdminQuoteQuestionViewSet), porque
    # este serializer nunca recibe el modulo/uuid de la pregunta en el
    # payload (se resuelve aparte en la vista, mismo patron que el resto de
    # los Input serializers de este archivo).
    depends_on_question = serializers.SlugRelatedField(
        slug_field='uuid', queryset=QuoteQuestion.objects.filter(is_deleted=False),
        required=False, allow_null=True,
    )
    depends_on_values = serializers.ListField(child=serializers.CharField(max_length=255), required=False, default=list)

    def validate(self, attrs):
        depends_on = attrs.get('depends_on_question')
        if depends_on:
            module = self.context.get('module')
            if module and depends_on.module_id != module.id:
                raise serializers.ValidationError(
                    {'depends_on_question': 'La pregunta de la que depende debe pertenecer al mismo modulo.'}
                )
            if depends_on.uuid == self.context.get('exclude_question_uuid'):
                raise serializers.ValidationError(
                    {'depends_on_question': 'Una pregunta no puede depender de si misma.'}
                )
        return attrs


class QuoteQuestionOptionInputSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=255)
    value = serializers.CharField(max_length=255)
    display_order = serializers.IntegerField(required=False, default=0)
    is_active = serializers.BooleanField(required=False, default=True)


class QuoteQuestionDuplicateToModuleInputSerializer(serializers.Serializer):
    """Body de POST quote-questions/{uuid}/duplicate-to-module/ (Fase C)."""
    target_module = serializers.SlugRelatedField(
        slug_field='uuid', queryset=QuoteTemplateModule.objects.filter(is_deleted=False),
    )
