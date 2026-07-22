from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from ecommerce.base_models import SintelBaseModel


class Quotation(SintelBaseModel):
    """
    Cotizacion / Solicitud de Cotizacion. Cubre tres flujos:
    1. Catalogo/personalizado (legacy): items/services/rental_items creados
       directamente por el cliente o el asesor, con precios reales.
    2. CPQ por plantilla (Fase 6): el cliente responde un cuestionario
       tecnico (template + answers) sin ver ningun precio. Queda en
       RECIBIDA y un asesor la revisa, agrega items/services con precio y
       la avanza por el flujo de estados hasta ENVIADA/ACEPTADA.
    """
    STATUS_DRAFT = 'BORRADOR'
    STATUS_RECEIVED = 'RECIBIDA'
    STATUS_UNDER_REVIEW = 'EN_REVISION'
    STATUS_PENDING_INFO = 'PENDIENTE_INFORMACION'
    STATUS_QUOTED = 'COTIZADA'
    STATUS_SENT = 'ENVIADA'
    STATUS_ACCEPTED = 'ACEPTADA'
    STATUS_REJECTED = 'RECHAZADA'
    STATUS_EXPIRED = 'VENCIDA'
    STATUS_CANCELLED = 'CANCELADA'
    STATUS_CHOICES = (
        (STATUS_DRAFT, 'Borrador'),
        (STATUS_RECEIVED, 'Recibida'),
        (STATUS_UNDER_REVIEW, 'En revision'),
        (STATUS_PENDING_INFO, 'Pendiente informacion'),
        (STATUS_QUOTED, 'Cotizada'),
        (STATUS_SENT, 'Enviada'),
        (STATUS_ACCEPTED, 'Aceptada'),
        (STATUS_REJECTED, 'Rechazada'),
        (STATUS_EXPIRED, 'Vencida'),
        (STATUS_CANCELLED, 'Cancelada'),
    )

    client_name = models.CharField(max_length=255)
    client_email = models.EmailField()
    valid_until = models.DateField()
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)

    is_custom = models.BooleanField(
        default=False,
        help_text='True when the quotation includes custom (non-catalog) services or materials.'
    )

    # Totals (calculated and stored to ensure consistency)
    subtotal_products = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    subtotal_services = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    subtotal_rentals = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    notes = models.TextField(blank=True, null=True)

    # Optional link to registered client
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quotations',
        help_text="Registered client (optional for anonymous quotes)"
    )

    # ─── Cuestionario tecnico: solicitud generada desde una plantilla ─────────
    template = models.ForeignKey(
        'QuoteTemplate', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='quotations',
        help_text='Plantilla usada para capturar el requerimiento. Null para el flujo catalogo/personalizado legacy.',
    )
    answers = models.JSONField(
        default=dict, blank=True,
        help_text='Respuestas del cliente organizadas por modulo: {"<module_uuid>": {"<question_key>": valor}}.',
    )

    # Datos del solicitante (flujo de cuestionario)
    company = models.CharField(max_length=255, blank=True, default='')
    document_type = models.CharField(max_length=10, choices=[('NIT', 'NIT'), ('CC', 'CC')], blank=True, default='')
    document_number = models.CharField(max_length=30, blank=True, default='')
    phone = models.CharField(max_length=30, blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    department = models.CharField(max_length=100, blank=True, default='')
    address = models.CharField(max_length=255, blank=True, default='')
    gps_location = models.CharField(max_length=100, blank=True, default='')
    project_name = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Quote {self.uuid} - {self.client_name}"


class QuotationTimeline(SintelBaseModel):
    """Historial append-only de cambios de estado de una Quotation (mismo patron que technical_services.OrderServiceTimeline)."""
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='timeline_events')
    status = models.CharField(max_length=25, choices=Quotation.STATUS_CHOICES)
    notes = models.TextField(blank=True, default='')
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='quotation_status_changes',
    )

    class Meta:
        verbose_name = 'Evento de Cotizacion'
        verbose_name_plural = 'Historial de Cotizacion'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.quotation.uuid} -> {self.status}"


class QuoteProduct(SintelBaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

class QuoteProductVariant(SintelBaseModel):
    product = models.ForeignKey(QuoteProduct, on_delete=models.CASCADE, related_name='variants')
    sku = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)

class QuotationItem(SintelBaseModel):
    """Snapshot of a ProductVariant (Shop or Quote) in a quotation."""
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    # Can link to Shop Product or Independent Quote Product
    variant = models.ForeignKey('shop.ProductVariant', on_delete=models.SET_NULL, null=True, blank=True)
    quote_variant = models.ForeignKey(QuoteProductVariant, on_delete=models.SET_NULL, null=True, blank=True)

    product_name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price_final = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        help_text='Precio unitario con costos adicionales aplicados (snapshot del motor de precios).'
    )

    @property
    def subtotal(self):
        effective = self.unit_price_final if self.unit_price_final else self.unit_price
        return effective * self.quantity

class QuotationService(SintelBaseModel):
    """Snapshot of a Technical Service in a quotation."""
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='services')
    service = models.ForeignKey('technical_services.TechnicalService', on_delete=models.SET_NULL, null=True, blank=True)
    service_name = models.CharField(max_length=255)
    hours = models.DecimalField(max_digits=6, decimal_places=2)
    labor_cost = models.DecimalField(max_digits=12, decimal_places=2)

    # Custom service fields (used when is_custom=True on the parent Quotation)
    custom_service_type = models.CharField(
        max_length=100, blank=True,
        help_text='Type label for a custom service (e.g. "Instalacion", "Mantenimiento").'
    )
    labor_description = models.TextField(
        blank=True,
        help_text='Detailed description of the labor scope for custom services.'
    )
    estimated_time_hours = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text='Estimated hours for custom service (may differ from billable hours).'
    )
    requires_full_cost_installation = models.BooleanField(
        default=False,
        help_text='True when installation cost must be included in the total.'
    )

    @property
    def material_cost(self):
        return sum(m.subtotal for m in self.materials.all())

    @property
    def subtotal(self):
        return self.labor_cost + self.material_cost

class QuotationMaterial(SintelBaseModel):
    """Snapshot of ServiceMaterial in a quotation."""
    quotation_service = models.ForeignKey(QuotationService, on_delete=models.CASCADE, related_name='materials')
    material_name = models.CharField(max_length=255)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.DecimalField(max_digits=8, decimal_places=2)

    @property
    def subtotal(self):
        return self.unit_price * self.quantity


class QuotationRentalItem(SintelBaseModel):
    """Snapshot of a renting.EquipmentVariant included in a hybrid quotation."""
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='rental_items')
    variant = models.ForeignKey(
        'renting.EquipmentVariant',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text='Source variant; nullable so the snapshot remains if the variant is deleted.'
    )

    # Snapshot fields — immutable after creation
    equipment_name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, blank=True)
    rental_price_per_day = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    rental_price_per_hour = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    rent_start_date = models.DateField()
    rent_end_date = models.DateField()
    computed_days = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        verbose_name = 'Item de Alquiler en Cotizacion'
        verbose_name_plural = 'Items de Alquiler en Cotizaciones'

    def __str__(self):
        return f"{self.equipment_name} ({self.rent_start_date} -> {self.rent_end_date})"


class QuotationAttachment(SintelBaseModel):
    """File uploaded by the client or admin to support a custom quotation."""
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='attachments')
    file = models.ImageField(upload_to='quotations/attachments/')
    note = models.CharField(
        max_length=255, blank=True, default='',
        help_text="Contexto del adjunto, ej. 'module_uuid:question_key' para respuestas de preguntas tipo archivo.",
    )

    class Meta:
        verbose_name = 'Adjunto de Cotizacion'
        verbose_name_plural = 'Adjuntos de Cotizaciones'

    def __str__(self):
        return f"Attachment for Quote {self.quotation.uuid}"


class QuotationItemCostSnapshot(SintelBaseModel):
    """
    Snapshot inmutable de un AdditionalCost aplicado a un QuotationItem.
    Garantiza que cotizaciones historicas no se alteren si los costos cambian.
    """
    quotation_item = models.ForeignKey(
        QuotationItem, on_delete=models.CASCADE, related_name='cost_snapshots'
    )
    cost_name = models.CharField(max_length=150)
    context = models.CharField(max_length=20)
    cost_type = models.CharField(max_length=10)
    value = models.DecimalField(max_digits=12, decimal_places=4)
    computed_amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_discount = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Snapshot de Costo en Cotizacion'
        verbose_name_plural = 'Snapshots de Costos en Cotizaciones'


# ─── Constructor de Cuestionarios Tecnicos ────────────────────────────────────
# El administrador construye plantillas de captura de requerimiento (no de
# calculo). Cada plantilla tiene tres modulos (Equipos/Materiales/Mano de
# Obra), cada modulo es un contenedor de preguntas. El cliente responde el
# cuestionario en /cotizar y genera una Quotation (solicitud) sin precios;
# el asesor comercial cotiza despues manualmente.

class QuoteTemplateCategory(SintelBaseModel):
    """
    Agrupa plantillas de cotizacion (ej. 'Seguridad Electronica', 'Redes').
    Pertenece a un Tipo de Servicio: Tipo de Servicio -> Categoria ->
    Subcategoria -> Tipo de Instalacion es la jerarquia real de la
    taxonomia de plantillas.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=150, unique=True, db_index=True)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=50, blank=True, default='', help_text="Clase de icono, ej. 'bi-camera-video'.")
    service_type = models.ForeignKey(
        'QuoteTemplateAttribute', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='categories', limit_choices_to={'kind': 'SERVICE_TYPE'},
        help_text='Tipo de Servicio al que pertenece esta categoria.',
    )
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = 'Categoria de Plantilla de Cotizacion'
        verbose_name_plural = 'Categorias de Plantillas de Cotizacion'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class QuoteTemplateSubcategory(SintelBaseModel):
    """Subcategoria dentro de una categoria (ej. Seguridad Electronica -> CCTV, Alarmas, Incendio)."""
    category = models.ForeignKey(QuoteTemplateCategory, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=150, db_index=True)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=50, blank=True, default='')
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Subcategoria de Plantilla de Cotizacion'
        verbose_name_plural = 'Subcategorias de Plantillas de Cotizacion'
        ordering = ['display_order', 'name']
        constraints = [
            models.UniqueConstraint(fields=['category', 'slug'], name='unique_subcategory_slug_per_category'),
        ]

    def __str__(self):
        return f"{self.category.name} / {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class QuoteTemplateAttribute(SintelBaseModel):
    """
    Catalogo reutilizable de valores para los atributos descriptivos de una
    plantilla: Tipo de Servicio (ej. 'Nueva instalacion', 'Mantenimiento',
    'Servicio tecnico'), Tipo de Instalacion y Tipo de Sistema. El admin los
    crea aqui y luego los elige por select al crear/editar una plantilla —
    mismo patron generico que QuoteTemplateModule (un solo modelo, un campo
    'kind' distingue los tres catalogos).
    """
    KIND_SERVICE_TYPE = 'SERVICE_TYPE'
    KIND_INSTALLATION_TYPE = 'INSTALLATION_TYPE'
    KIND_SYSTEM_TYPE = 'SYSTEM_TYPE'
    KIND_CHOICES = (
        (KIND_SERVICE_TYPE, 'Tipo de Servicio'),
        (KIND_INSTALLATION_TYPE, 'Tipo de Instalacion'),
        (KIND_SYSTEM_TYPE, 'Tipo de Sistema'),
    )

    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=150, db_index=True)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=50, blank=True, default='')
    subcategory = models.ForeignKey(
        QuoteTemplateSubcategory, on_delete=models.CASCADE, null=True, blank=True,
        related_name='installation_types',
        help_text='Solo aplica cuando kind=INSTALLATION_TYPE: subcategoria dueña de esta opcion.',
    )
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Atributo de Plantilla'
        verbose_name_plural = 'Atributos de Plantilla'
        ordering = ['kind', 'display_order', 'name']
        constraints = [
            models.UniqueConstraint(fields=['kind', 'slug'], name='unique_attribute_slug_per_kind'),
        ]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class QuoteTemplate(SintelBaseModel):
    """Plantilla de cuestionario tecnico (ej. 'Instalacion CCTV')."""
    category = models.ForeignKey(
        QuoteTemplateCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='templates',
    )
    subcategory = models.ForeignKey(
        QuoteTemplateSubcategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='templates',
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, db_index=True)
    code = models.CharField(max_length=50, unique=True, null=True, blank=True, help_text='Codigo corto interno, ej. CCTV-INST-001.')
    description = models.TextField(blank=True, default='')
    # Tipo de Servicio ya no se elige aca — se deriva de category.service_type
    # (Tipo de Servicio -> Categoria -> Subcategoria -> Tipo de Instalacion).
    installation_type = models.ForeignKey(
        QuoteTemplateAttribute, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
        limit_choices_to={'kind': QuoteTemplateAttribute.KIND_INSTALLATION_TYPE},
    )
    system_type = models.ForeignKey(
        QuoteTemplateAttribute, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
        limit_choices_to={'kind': QuoteTemplateAttribute.KIND_SYSTEM_TYPE},
    )
    version = models.PositiveIntegerField(default=1)
    is_published = models.BooleanField(default=False, db_index=True, help_text='Visible en /cotizar. Una plantilla no publicada solo se ve en el panel admin.')
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    COMPLEXITY_LOW = 'LOW'
    COMPLEXITY_MEDIUM = 'MEDIUM'
    COMPLEXITY_HIGH = 'HIGH'
    COMPLEXITY_CHOICES = (
        (COMPLEXITY_LOW, 'Baja'),
        (COMPLEXITY_MEDIUM, 'Media'),
        (COMPLEXITY_HIGH, 'Alta'),
    )
    # Indicador manual (nunca calculado) que el admin fija al crear/editar la
    # plantilla -- deliberadamente NO se deriva de las respuestas del cliente
    # para no recrear el motor de calculo eliminado (ver "Fuera de alcance"
    # en ARQUITECTURA_COMPLETA_QUOTES.md). blank='' = sin indicar.
    complexity_hint = models.CharField(max_length=10, choices=COMPLEXITY_CHOICES, blank=True, default='')

    class Meta:
        verbose_name = 'Plantilla de Cotizacion'
        verbose_name_plural = 'Plantillas de Cotizacion'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class QuoteEquipmentType(SintelBaseModel):
    """Catalogo reutilizable de tipos de equipo (Camara IP, NVR, DVR, Panel, Sensor, etc.)."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=150, unique=True, db_index=True)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=50, blank=True, default='')
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Tipo de Equipo'
        verbose_name_plural = 'Tipos de Equipo'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class QuoteTemplateModule(SintelBaseModel):
    """
    Modulo de una plantilla: contenedor de preguntas. Los tres modulos
    fijos de toda plantilla (Equipos/Materiales/Mano de Obra) son
    instancias de este mismo modelo, distinguidas por module_type. Los
    campos especificos de equipo (equipment_type/unit/min-max_quantity)
    solo se usan cuando module_type=EQUIPMENT.
    """
    MODULE_EQUIPMENT = 'EQUIPMENT'
    MODULE_MATERIALS = 'MATERIALS'
    MODULE_LABOR = 'LABOR'
    MODULE_TYPE_CHOICES = (
        (MODULE_EQUIPMENT, 'Equipos'),
        (MODULE_MATERIALS, 'Materiales'),
        (MODULE_LABOR, 'Mano de Obra'),
    )

    template = models.ForeignKey(QuoteTemplate, on_delete=models.CASCADE, related_name='modules')
    module_type = models.CharField(max_length=20, choices=MODULE_TYPE_CHOICES, default=MODULE_EQUIPMENT)
    equipment_type = models.ForeignKey(
        QuoteEquipmentType, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='template_items',
        help_text='Solo aplica cuando module_type=EQUIPMENT.',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    unit = models.CharField(max_length=50, blank=True, default='unidad')
    min_quantity = models.PositiveIntegerField(null=True, blank=True)
    max_quantity = models.PositiveIntegerField(null=True, blank=True)
    is_required = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Modulo de Plantilla'
        verbose_name_plural = 'Modulos de Plantilla'
        ordering = ['module_type', 'display_order', 'id']

    def __str__(self):
        return f"{self.template.name} / {self.get_module_type_display()} / {self.name}"


class QuoteQuestion(SintelBaseModel):
    """Una pregunta dinamica asociada a un modulo (Equipos/Materiales/Mano de Obra) de la plantilla."""
    TYPE_TEXT = 'TEXT'
    TYPE_TEXTAREA = 'TEXTAREA'
    TYPE_NUMBER = 'NUMBER'
    TYPE_DECIMAL = 'DECIMAL'
    TYPE_CURRENCY = 'CURRENCY'
    TYPE_BOOLEAN = 'BOOLEAN'
    TYPE_DATE = 'DATE'
    TYPE_TIME = 'TIME'
    TYPE_SELECT = 'SELECT'
    TYPE_MULTISELECT = 'MULTISELECT'
    TYPE_RADIO = 'RADIO'
    TYPE_CHECKBOX = 'CHECKBOX'
    TYPE_IMAGE = 'IMAGE'
    TYPE_FILE = 'FILE'
    TYPE_SIGNATURE = 'SIGNATURE'
    TYPE_GPS = 'GPS'
    TYPE_ADDRESS = 'ADDRESS'
    TYPE_EMAIL = 'EMAIL'
    TYPE_PHONE = 'PHONE'
    TYPE_NIT = 'NIT'
    TYPE_CC = 'CC'
    TYPE_COLOR = 'COLOR'
    TYPE_SLIDER = 'SLIDER'
    TYPE_TABLE = 'TABLE'
    TYPE_DYNAMIC_LIST = 'DYNAMIC_LIST'
    TYPE_AUTOCOMPLETE = 'AUTOCOMPLETE'
    QUESTION_TYPE_CHOICES = (
        (TYPE_TEXT, 'Texto'),
        (TYPE_TEXTAREA, 'Texto largo'),
        (TYPE_NUMBER, 'Numero'),
        (TYPE_DECIMAL, 'Decimal'),
        (TYPE_CURRENCY, 'Moneda'),
        (TYPE_BOOLEAN, 'Booleano'),
        (TYPE_DATE, 'Fecha'),
        (TYPE_TIME, 'Hora'),
        (TYPE_SELECT, 'Select'),
        (TYPE_MULTISELECT, 'Multiselect'),
        (TYPE_RADIO, 'Radio'),
        (TYPE_CHECKBOX, 'Checkbox'),
        (TYPE_IMAGE, 'Imagen'),
        (TYPE_FILE, 'Archivo'),
        (TYPE_SIGNATURE, 'Firma'),
        (TYPE_GPS, 'GPS'),
        (TYPE_ADDRESS, 'Direccion'),
        (TYPE_EMAIL, 'Email'),
        (TYPE_PHONE, 'Telefono'),
        (TYPE_NIT, 'NIT'),
        (TYPE_CC, 'Cedula (CC)'),
        (TYPE_COLOR, 'Color'),
        (TYPE_SLIDER, 'Deslizador'),
        (TYPE_TABLE, 'Tabla'),
        (TYPE_DYNAMIC_LIST, 'Lista dinamica'),
        (TYPE_AUTOCOMPLETE, 'Autocompletar'),
    )
    FILE_TYPES = (TYPE_IMAGE, TYPE_FILE, TYPE_SIGNATURE)

    module = models.ForeignKey(QuoteTemplateModule, on_delete=models.CASCADE, related_name='questions')
    key = models.SlugField(
        max_length=100, db_index=True,
        help_text='Identificador unico de la pregunta dentro de su modulo.',
    )
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default=TYPE_TEXT)
    label = models.CharField(max_length=500)
    description = models.TextField(blank=True, default='', help_text='Explicacion larga de la pregunta (distinta del texto de ayuda corto).')
    help_text = models.CharField(max_length=500, blank=True, default='')
    placeholder = models.CharField(max_length=255, blank=True, default='')
    is_required = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True, help_text='Se muestra al cliente en /cotizar. Desactivar para ocultarla sin borrarla.')
    default_value = models.CharField(max_length=500, blank=True, default='')
    unit = models.CharField(max_length=50, blank=True, default='', help_text="Unidad de medida, ej. 'metros', 'm2'.")
    group = models.CharField(max_length=150, blank=True, default='', help_text='Etiqueta de agrupacion visual dentro del modulo.')
    min_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    validation_regex = models.CharField(max_length=255, blank=True, default='', help_text='Patron opcional de validacion (ej. para NIT/CC/Email).')
    table_columns = models.JSONField(default=list, blank=True, help_text="Solo para TABLE: lista de nombres de columna, ej. ['Item', 'Cantidad'].")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    allow_other = models.BooleanField(
        default=False,
        help_text="Para SELECT/RADIO: agrega la opcion 'Otro' que permite al cliente escribir un valor libre.",
    )
    # Visibilidad condicional (Fase F, PLAN_MAESTRO_QUOTES_UX.md): esta
    # pregunta solo se muestra al cliente si la respuesta de
    # depends_on_question esta dentro de depends_on_values. Alcance
    # deliberadamente acotado a mostrar/ocultar -- NUNCA calcula precio,
    # mano de obra ni cantidades (eso sigue eliminado, ver "Fuera de
    # alcance" en ARQUITECTURA_COMPLETA_QUOTES.md). depends_on_question debe
    # pertenecer al mismo modulo (validado en QuoteQuestionInputSerializer,
    # no a nivel de base de datos -- mismo patron que la validacion
    # installation_type/subcategory de QuoteTemplateInputSerializer).
    depends_on_question = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='dependents',
        help_text='Pregunta cuya respuesta controla la visibilidad de esta (debe ser del mismo modulo).',
    )
    depends_on_values = models.JSONField(
        default=list, blank=True,
        help_text='Lista de valores de depends_on_question que activan la visibilidad de esta pregunta.',
    )

    class Meta:
        verbose_name = 'Pregunta de Plantilla'
        verbose_name_plural = 'Preguntas de Plantilla'
        ordering = ['display_order', 'id']
        constraints = [
            models.UniqueConstraint(fields=['module', 'key'], name='unique_question_key_per_module'),
        ]

    def __str__(self):
        return self.label

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = slugify(self.label).replace('-', '_')
        super().save(*args, **kwargs)


class QuoteQuestionOption(SintelBaseModel):
    """Opcion disponible para preguntas SELECT/MULTISELECT/RADIO/CHECKBOX/AUTOCOMPLETE."""
    question = models.ForeignKey(QuoteQuestion, on_delete=models.CASCADE, related_name='options')
    label = models.CharField(max_length=255)
    value = models.CharField(max_length=255, help_text='Valor almacenado en la respuesta.')
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Opcion de Pregunta'
        verbose_name_plural = 'Opciones de Pregunta'
        ordering = ['display_order', 'id']

    def __str__(self):
        return f"{self.question.key}: {self.label}"
