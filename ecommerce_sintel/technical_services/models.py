from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from ecommerce.base_models import SintelBaseModel
from shared.models import AbstractCostRule, AbstractCostAssignment, AbstractReview

class ServiceCategory(SintelBaseModel):
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='children',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=150, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'categoría de servicio'
        verbose_name_plural = 'categorías de servicios'
        
    def __str__(self):
        return self.name
        
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class ServiceLevel(SintelBaseModel):
    """Analogous to Brand: Junior, Senior, Specialized, etc."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=150, unique=True, db_index=True)
    
    def __str__(self):
        return self.name
        
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
        

class ServiceConfiguration(SintelBaseModel):
    """Global configuration for labor costs in Colombia."""
    name = models.CharField(max_length=100, default="Estándar Colombia 2024")
    smlv = models.DecimalField(max_digits=12, decimal_places=2, default=1300000.00)
    transport_subsidy = models.DecimalField(max_digits=12, decimal_places=2, default=162000.00)
    benefit_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=53.10, 
        help_text="Percentage of social benefits and taxes"
    )
    indirect_costs_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=15.00, 
        help_text="Indirect costs / Overhead percentage"
    )
    iva_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=19.00,
        help_text="Active tax rate (IVA percentage)"
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class TechnicalService(SintelBaseModel):
    """Offerings for technical installation and professional services (Analogous to Product)."""
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="technical_services",
        null=True, blank=True
    )
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name="services", null=True, blank=True)
    level = models.ForeignKey(ServiceLevel, on_delete=models.CASCADE, related_name="services", null=True, blank=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    description = models.TextField()
    # Bloques "Alcance"/"Garantia"/"Cobertura" de la reingenieria SDP (2026-08-05) -- texto
    # unico, mismo patron que shop.Product.scope/warranty, no ameritan modelo hijo propio.
    scope = models.TextField(blank=True, default='')
    warranty = models.TextField(blank=True, default='')
    coverage_notes = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_purchasable = models.BooleanField(default=True)

    # SEO -- espejo de renting.Equipment (meta_title/meta_description/
    # meta_keywords/og_image), replicado tal cual por el plan de unificacion
    # con Renting (ver technical_services/.AGENT/docs/
    # PLAN_UNIFICACION_SERVICES_CON_RENTING.md, Etapa 6). Vive directo en
    # TechnicalService, NO en ServiceMarketing -- misma decision que Equipment.
    meta_title = models.CharField(max_length=70, blank=True, default='')
    meta_description = models.TextField(blank=True, default='')
    meta_keywords = models.CharField(max_length=255, blank=True, default='')
    og_image = models.ImageField(upload_to='services/seo/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or str(self.uuid)[:8]
            candidate = base
            counter = 2
            while TechnicalService.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base}-{counter}"
                counter += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class ServiceVariant(SintelBaseModel):
    """Specific technical offering (Analogous to ProductVariant)."""
    HOURLY = 'HOURLY'
    DAILY = 'DAILY'
    FIXED = 'FIXED'

    PRICING_STRATEGY_CHOICES = [
        (HOURLY, 'Hourly'),
        (DAILY, 'Daily'),
        (FIXED, 'Fixed'),
    ]

    # Plan "Manual Pricing Engine" (2026-08-13), FASE 1 -- contrato formal de
    # pricing_source. AUTOMATIC (default) preserva el comportamiento actual sin
    # ningun cambio: LaborCostCalculator + ServicePricingCalculator sobre
    # pricing_strategy/fixed_price, exactamente como hoy (ver SERVICE_MANUAL_
    # PRICING_BASELINE.md §2). Los 3 modos MANUAL_* apagan ese calculo por
    # completo (FASE 4, ServiceQuotationResolver) -- pricing_strategy/fixed_price
    # de la variante quedan sin efecto cuando pricing_source != AUTOMATIC, pero NO
    # se eliminan del modelo (permite volver a AUTOMATIC sin perder la
    # configuracion de mano de obra ya cargada).
    SOURCE_AUTOMATIC = 'AUTOMATIC'
    SOURCE_MANUAL_PROJECT = 'MANUAL_PROJECT'
    SOURCE_MANUAL_GENERAL = 'MANUAL_GENERAL'
    SOURCE_MANUAL_HOURLY = 'MANUAL_HOURLY'
    PRICING_SOURCE_CHOICES = [
        (SOURCE_AUTOMATIC, 'Automatico'),
        (SOURCE_MANUAL_PROJECT, 'Manual - Proyecto completo'),
        (SOURCE_MANUAL_GENERAL, 'Manual - Precio general'),
        (SOURCE_MANUAL_HOURLY, 'Manual - Por horas'),
    ]
    _MANUAL_SOURCES = (SOURCE_MANUAL_PROJECT, SOURCE_MANUAL_GENERAL, SOURCE_MANUAL_HOURLY)

    service = models.ForeignKey(TechnicalService, on_delete=models.CASCADE, related_name='variants')
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    estimated_hours = models.DecimalField(max_digits=6, decimal_places=2, default=1.0)
    complexity_factor = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1.00,
        help_text="Multiplier for specialized labor"
    )
    fixed_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    pricing_strategy = models.CharField(
        max_length=10,
        choices=PRICING_STRATEGY_CHOICES,
        default=HOURLY
    )
    min_duration = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum allowed duration (hours or days depending on pricing strategy)"
    )
    max_duration = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum allowed duration (hours or days depending on pricing strategy)"
    )
    simultaneous_capacity = models.PositiveIntegerField(
        default=1,
        help_text="Numero maximo de servicios de este tipo que se pueden ejecutar al mismo tiempo."
    )
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)

    pricing_source = models.CharField(
        max_length=20, choices=PRICING_SOURCE_CHOICES, default=SOURCE_AUTOMATIC, db_index=True,
        help_text="AUTOMATIC = LaborCostCalculator/SMLV (comportamiento actual). MANUAL_* = precio "
                   "definido directamente por el administrador, ver ManualPricingCalculator.",
    )
    manual_unit_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="MANUAL_GENERAL: precio fijo total. MANUAL_HOURLY: tarifa por hora (se multiplica "
                   "por duration). No aplica a MANUAL_PROJECT ni AUTOMATIC.",
    )
    manual_project_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Solo MANUAL_PROJECT: precio total fijo del proyecto, duration no lo modifica.",
    )

    def clean(self):
        super().clean()
        if self.pricing_source == self.SOURCE_AUTOMATIC:
            if self.manual_unit_price is not None or self.manual_project_price is not None:
                raise ValidationError(
                    'pricing_source AUTOMATIC no debe tener manual_unit_price ni manual_project_price.'
                )
        elif self.pricing_source == self.SOURCE_MANUAL_PROJECT:
            if not self.manual_project_price or self.manual_project_price <= Decimal('0'):
                raise ValidationError('MANUAL_PROJECT requiere manual_project_price > 0.')
            if self.manual_unit_price is not None:
                raise ValidationError('MANUAL_PROJECT no debe tener manual_unit_price (usar manual_project_price).')
        elif self.pricing_source in (self.SOURCE_MANUAL_GENERAL, self.SOURCE_MANUAL_HOURLY):
            if not self.manual_unit_price or self.manual_unit_price <= Decimal('0'):
                raise ValidationError(f'{self.pricing_source} requiere manual_unit_price > 0.')
            if self.manual_project_price is not None:
                raise ValidationError(f'{self.pricing_source} no debe tener manual_project_price.')

    @property
    def is_manual_pricing(self) -> bool:
        return self.pricing_source in self._MANUAL_SOURCES

    def __str__(self):
        return f"{self.service.name} - {self.sku}"

class ServiceMaterial(SintelBaseModel):
    """Materials or supplies required for a specific service variant."""
    variant = models.ForeignKey(
        ServiceVariant, 
        on_delete=models.CASCADE, 
        related_name='materials',
        null=True, blank=True
    )
    product_variant = models.ForeignKey(
        'shop.ProductVariant', 
        on_delete=models.CASCADE,
        related_name='used_in_services',
        null=True, blank=True
    )
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=1.0)

    def __str__(self):
        return f"{self.product_variant.sku} for {self.variant.sku}"

class ServiceImage(SintelBaseModel):
    service = models.ForeignKey(TechnicalService, on_delete=models.CASCADE, related_name='images')
    variant = models.ForeignKey(ServiceVariant, on_delete=models.CASCADE, related_name='images', null=True, blank=True)
    image = models.ImageField(upload_to='services/')
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    # Galeria descriptiva (plan "Rediseno ServiceForm + Content/Media", FASE 4,
    # 2026-08-14) -- caption/description dan contexto a cada foto (no solo el
    # alt_text tecnico de accesibilidad), display_order permite reordenar la
    # galeria manualmente en vez de depender del orden de subida.
    caption = models.CharField(max_length=150, blank=True, default='')
    description = models.TextField(blank=True, default='')
    display_order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ['display_order', 'created_at']

class ServiceReview(AbstractReview):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='service_reviews')
    service = models.ForeignKey(TechnicalService, on_delete=models.CASCADE, related_name='reviews')

    class Meta:
        unique_together = ('user', 'service')


class ServiceFAQ(SintelBaseModel):
    """Pregunta frecuente del servicio, mostrada en el detalle publico.

    Replica tal cual renting.RentalFAQ -- ver plan de unificacion con Renting
    (technical_services/.AGENT/docs/PLAN_UNIFICACION_SERVICES_CON_RENTING.md,
    Etapa 6). Modelo separado de ServiceMarketing a proposito, misma decision
    que Renting (FAQ vive aparte de la config comercial).
    """
    service = models.ForeignKey(TechnicalService, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=500)
    answer = models.TextField()
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'pregunta frecuente'
        verbose_name_plural = 'preguntas frecuentes'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.service.name} -- FAQ: {self.question[:50]}"


class ServiceMarketing(SintelBaseModel):
    """
    Configuracion comercial/visual de un servicio para su presentacion publica
    (precio de referencia, etiquetas, mensajes de conversion, CTA, banner, etc).

    Replica tal cual renting.EquipmentMarketing -- ver plan de unificacion con
    Renting (technical_services/.AGENT/docs/
    PLAN_UNIFICACION_SERVICES_CON_RENTING.md, Etapa 6). NO almacena informacion
    tecnica, de precios de mano de obra, materiales ni disponibilidad -- eso
    vive en TechnicalService/ServiceVariant/ServiceMaterial/
    TechnicianAvailabilityEngine. SEO (meta_title/meta_description/
    meta_keywords/og_image) tampoco se duplica aqui: vive en TechnicalService,
    se reutiliza tal cual (misma decision que Equipment). Deliberadamente SIN
    campos de campana con fecha ni testimonios -- ni siquiera
    EquipmentMarketing los tiene hoy; agregarlos seria una funcionalidad nueva
    para ambos modulos, no una adopcion de un patron ya probado (ver Riesgos
    del plan).

    OneToOne con TechnicalService: cada servicio tiene a lo sumo un registro
    de marketing, propio y exclusivo -- no hay herencia, plantillas ni
    configuraciones globales (mismo principio que EquipmentMarketing).
    """

    TAG_OFFER = 'OFERTA'
    TAG_NEW = 'NUEVO'
    TAG_MOST_REQUESTED = 'MAS_SOLICITADO'
    TAG_PREMIUM = 'PREMIUM'
    TAG_RECOMMENDED = 'RECOMENDADO'
    TAG_HOT = 'HOT'
    TAG_TOP_RATED = 'TOP_CALIFICADO'
    TAG_EVENTS = 'IDEAL_EMPRESAS'
    TAG_LIMITED = 'CUPOS_LIMITADOS'
    TAG_CHOICES = [
        (TAG_OFFER, 'Oferta'),
        (TAG_NEW, 'Nuevo'),
        (TAG_MOST_REQUESTED, 'Mas solicitado'),
        (TAG_PREMIUM, 'Premium'),
        (TAG_RECOMMENDED, 'Recomendado'),
        (TAG_HOT, 'Hot'),
        (TAG_TOP_RATED, 'Top calificado'),
        (TAG_EVENTS, 'Ideal para empresas'),
        (TAG_LIMITED, 'Cupos limitados'),
    ]

    service = models.OneToOneField(
        TechnicalService,
        on_delete=models.CASCADE,
        related_name='marketing',
    )

    # Precio comercial
    reference_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='precio de referencia (anterior)',
    )
    promo_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='precio promocional',
    )
    show_discount_percentage = models.BooleanField(
        default=True, verbose_name='mostrar porcentaje de descuento',
    )

    # Etiquetas comerciales -- lista de codigos de TAG_CHOICES.
    tags = models.JSONField(default=list, blank=True, verbose_name='etiquetas comerciales')

    # Mensajes de conversion (texto libre, sin catalogo cerrado).
    main_message = models.TextField(blank=True, default='', verbose_name='mensaje principal')
    featured_benefit = models.CharField(max_length=255, blank=True, default='', verbose_name='beneficio destacado')
    trust_message = models.CharField(max_length=255, blank=True, default='', verbose_name='mensaje de confianza')
    urgency_message = models.CharField(max_length=255, blank=True, default='', verbose_name='mensaje de urgencia')
    social_proof_message = models.CharField(max_length=255, blank=True, default='', verbose_name='prueba social')

    # NOTA: EquipmentMarketing tiene ademas `purchase_price_reference`/
    # `financial_message` para la comparativa "comprar vs alquilar" -- se
    # omite aqui a proposito: un servicio tecnico no tiene una alternativa de
    # "compra" analoga, ese par de campos no aplica al dominio.

    # Casos de uso -- lista libre de strings (ej. ["Oficinas", "Bodegas"]).
    use_cases = models.JSONField(default=list, blank=True, verbose_name='casos de uso')

    # Call To Action del boton principal de solicitud.
    cta_label = models.CharField(max_length=100, blank=True, default='', verbose_name='texto del CTA')

    # Banner promocional -- un unico mensaje, se muestra solo si esta configurado.
    promo_banner_message = models.CharField(max_length=255, blank=True, default='', verbose_name='banner promocional')

    # Beneficios rapidos -- lista de {"icon": "bi-shield-check", "label": "..."}.
    quick_benefits = models.JSONField(default=list, blank=True, verbose_name='beneficios rapidos')

    class Meta:
        verbose_name = 'marketing de servicio'
        verbose_name_plural = 'marketing de servicios'

    def __str__(self):
        return f"Marketing -- {self.service.name}"


# ── Catalogo enriquecido de TechnicalService (2026-08-05) ──────────────────────
# Espejo de shop.Product*/renting.Rental* (mismo shape: fila hija con
# position/is_active, soft-delete real via SintelBaseModel) -- ver
# technical_services/.AGENT/docs/UI_MODULO_SERVICES.md para el detalle completo
# de la reingenieria SDP que motivo estos modelos.

class ServiceIncludedItem(SintelBaseModel):
    """Que incluye el servicio, mostrado en el detalle publico."""
    service = models.ForeignKey(TechnicalService, on_delete=models.CASCADE, related_name='included_items')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=50, blank=True, default='')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'item incluido de servicio'
        verbose_name_plural = 'items incluidos de servicio'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.service.name} -- incluye: {self.title}"


class ServiceExcludedItem(SintelBaseModel):
    """Que NO incluye el servicio, mostrado en el detalle publico."""
    service = models.ForeignKey(TechnicalService, on_delete=models.CASCADE, related_name='excluded_items')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=50, blank=True, default='')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'item no incluido de servicio'
        verbose_name_plural = 'items no incluidos de servicio'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.service.name} -- no incluye: {self.title}"


class ServiceRequirement(SintelBaseModel):
    """Requisito del cliente / condicion de instalacion antes de prestar el servicio."""
    service = models.ForeignKey(TechnicalService, on_delete=models.CASCADE, related_name='requirements')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'requisito de servicio'
        verbose_name_plural = 'requisitos de servicio'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.service.name} -- requisito: {self.title}"


class ServiceSpecificationGroup(SintelBaseModel):
    """Grupo de la ficha tecnica (ej. 'General', 'Cobertura')."""
    service = models.ForeignKey(TechnicalService, on_delete=models.CASCADE, related_name='specification_groups')
    name = models.CharField(max_length=100)
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'grupo de ficha tecnica de servicio'
        verbose_name_plural = 'grupos de ficha tecnica de servicio'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.service.name} -- grupo: {self.name}"


class ServiceSpecification(SintelBaseModel):
    """Fila de la ficha tecnica, agrupada bajo ServiceSpecificationGroup."""
    service = models.ForeignKey(TechnicalService, on_delete=models.CASCADE, related_name='specifications')
    group = models.ForeignKey(ServiceSpecificationGroup, on_delete=models.CASCADE, related_name='specifications')
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=255)
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'especificacion de servicio'
        verbose_name_plural = 'especificaciones de servicio'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.service.name} -- {self.name}: {self.value}"


class ServiceDocument(SintelBaseModel):
    """
    Documento descargable del servicio: manual, ficha tecnica, certificado,
    normativa, catalogo. is_public controla visibilidad en el detalle del
    cliente (documentos internos pueden quedar is_public=False).
    """
    TYPE_MANUAL = 'MANUAL'
    TYPE_FICHA_TECNICA = 'FICHA_TECNICA'
    TYPE_CERTIFICADO = 'CERTIFICADO'
    TYPE_NORMATIVA = 'NORMATIVA'
    TYPE_CATALOGO = 'CATALOGO'
    TYPE_OTRO = 'OTRO'
    DOCUMENT_TYPE_CHOICES = [
        (TYPE_MANUAL, 'Manual'),
        (TYPE_FICHA_TECNICA, 'Ficha tecnica'),
        (TYPE_CERTIFICADO, 'Certificado'),
        (TYPE_NORMATIVA, 'Normativa'),
        (TYPE_CATALOGO, 'Catalogo'),
        (TYPE_OTRO, 'Otro'),
    ]

    service = models.ForeignKey(TechnicalService, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES, default=TYPE_OTRO, db_index=True)
    file = models.FileField(upload_to='services/documents/')
    cover_image = models.ImageField(upload_to='services/documents/covers/', blank=True, null=True)
    downloads = models.PositiveIntegerField(default=0)
    position = models.PositiveIntegerField(default=0)
    is_public = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'documento de servicio'
        verbose_name_plural = 'documentos de servicio'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.service.name} -- documento: {self.title}"


class ServiceVideo(SintelBaseModel):
    """Video del servicio (lista) -- YouTube/Vimeo/archivo propio."""
    SOURCE_YOUTUBE = 'YOUTUBE'
    SOURCE_VIMEO = 'VIMEO'
    SOURCE_MP4 = 'MP4'
    SOURCE_TYPE_CHOICES = [
        (SOURCE_YOUTUBE, 'YouTube'),
        (SOURCE_VIMEO, 'Vimeo'),
        (SOURCE_MP4, 'Archivo MP4'),
    ]

    service = models.ForeignKey(TechnicalService, on_delete=models.CASCADE, related_name='videos')
    title = models.CharField(max_length=255, blank=True, default='')
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPE_CHOICES, default=SOURCE_YOUTUBE)
    video_url = models.URLField(blank=True, default='')
    video_file = models.FileField(upload_to='services/videos/', blank=True, null=True)
    thumbnail = models.ImageField(upload_to='services/videos/thumbs/', blank=True, null=True)
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'video de servicio'
        verbose_name_plural = 'videos de servicio'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.service.name} -- video: {self.title or self.source_type}"


class ServiceProcessStep(SintelBaseModel):
    """
    Paso del proceso de prestacion del servicio (Fase 10 del brief SDP) --
    sin equivalente en Shop/Renting, genuinamente nuevo. step_number es
    editable (no se infiere de position) porque el admin puede querer un
    numero visible distinto del orden de arrastre (ej. renumerar tras borrar
    un paso intermedio sin correr los demas).
    """
    service = models.ForeignKey(TechnicalService, on_delete=models.CASCADE, related_name='process_steps')
    step_number = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    image = models.ImageField(upload_to='services/process/', blank=True, null=True)
    estimated_time = models.CharField(max_length=100, blank=True, default='', help_text='Ej: 30 min, 1-2 horas')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'paso del proceso de servicio'
        verbose_name_plural = 'pasos del proceso de servicio'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.service.name} -- paso {self.step_number}: {self.title}"


class OrderServiceDetail(SintelBaseModel):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    RATE_TYPE_CHOICES = [
        ('HOURLY', 'Por hora'),
        ('DAILY', 'Por dia'),
        ('PROJECT', 'Por proyecto'),
    ]

    order = models.OneToOneField('orders.Order', on_delete=models.CASCADE, related_name='service_detail')
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_services')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    description = models.TextField()
    address = models.CharField(max_length=255)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    preferred_date = models.DateField(null=True, blank=True)
    preferred_time = models.TimeField(null=True, blank=True)
    location_reference = models.TextField(blank=True, default='')
    neighborhood = models.CharField(max_length=120, blank=True, default='')
    service_notes = models.TextField(blank=True, default='')
    allow_schedule_changes = models.BooleanField(default=True)

    # Snapshot historico: congela la tarifa exacta cobrada al momento de la orden
    professional_type_snapshot = models.CharField(max_length=50, null=True, blank=True)
    applied_rate_type = models.CharField(max_length=20, choices=RATE_TYPE_CHOICES, null=True, blank=True)
    applied_rate_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Plan "Manual Pricing Engine" (2026-08-13) FASE 2 -- snapshot comercial
    # ampliado. applied_rate_type/applied_rate_amount (arriba) quedan sin tocar
    # por compatibilidad (siguen siendo consumidos por OrderServiceDetailSerializer
    # y solo capturan pricing_strategy/labor_cost, ver SERVICE_MANUAL_PRICING_
    # BASELINE.md §1) -- estos 5 campos nuevos son el snapshot real y completo,
    # tomado de ServiceVariant.pricing_source en el momento exacto de la orden
    # (nunca del valor actual de la variante, que puede cambiar despues).
    pricing_source_snapshot = models.CharField(
        max_length=20, null=True, blank=True,
        help_text="ServiceVariant.pricing_source al momento de la orden (AUTOMATIC/MANUAL_*).",
    )
    pricing_mode_snapshot = models.CharField(
        max_length=20, null=True, blank=True,
        help_text="Para AUTOMATIC: pricing_strategy (HOURLY/DAILY/FIXED) usado en el calculo. "
                   "None para modos MANUAL_* (pricing_source_snapshot ya es suficiente).",
    )
    unit_price_snapshot = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Tarifa unitaria aplicada (labor_cost en AUTOMATIC, manual_unit_price en "
                   "MANUAL_GENERAL/MANUAL_HOURLY). None en MANUAL_PROJECT.",
    )
    project_price_snapshot = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Solo MANUAL_PROJECT: manual_project_price aplicado.",
    )
    duration_snapshot = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Horas/dias usados en el calculo (irrelevante para MANUAL_PROJECT/MANUAL_GENERAL).",
    )
    # Registro completo de la cotizacion (mismo dict que retorna
    # ServiceSelector.get_variant_quotation()/ServiceQuotationResolver) -- los 5
    # campos de arriba son para queries/filtros rapidos sin parsear JSON: este es
    # el registro historico completo (material_cost, reglas de costo aplicadas,
    # descuento, IVA, total) para auditoria/disputas, mismo patron ya usado por
    # `contact_person` (JSONField) en este mismo modelo.
    quotation_snapshot = models.JSONField(null=True, blank=True)

    # Plan "Manual Pricing Engine" (2026-08-13) FASE 18-19 -- estado del precio
    # comercial visible/editable desde /panel/servicios/operaciones. Decision
    # explicita (confirmada con el usuario): el override queda como registro
    # AUDITADO (este campo + OrderPriceAdjustment abajo) y NUNCA modifica
    # Order.total_amount/OrderItem.price -- lo que Wompi ya cobro o va a cobrar
    # no se toca aqui. Un ajuste de cobro real (nota de credito, reembolso
    # parcial) es un proceso de negocio aparte, fuera de alcance de este plan.
    PRICE_STATUS_ESTIMATED = 'ESTIMATED'
    PRICE_STATUS_CONFIRMED = 'CONFIRMED'
    PRICE_STATUS_OVERRIDDEN = 'OVERRIDDEN'
    PRICE_STATUS_LOCKED = 'LOCKED'
    PRICE_STATUS_CHOICES = [
        (PRICE_STATUS_ESTIMATED, 'Estimado'),
        (PRICE_STATUS_CONFIRMED, 'Confirmado'),
        (PRICE_STATUS_OVERRIDDEN, 'Modificado por administrador'),
        (PRICE_STATUS_LOCKED, 'Bloqueado'),
    ]
    price_status = models.CharField(max_length=20, choices=PRICE_STATUS_CHOICES, default=PRICE_STATUS_ESTIMATED)
    confirmed_total = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Total revisado/ajustado por un administrador (solo informativo -- "
                   "NO reemplaza Order.total_amount, ver OrderPricingCommands).",
    )

    # Slot de disponibilidad reservado (referencia desacoplada, sin FK cross-app)
    booked_slot_id   = models.IntegerField(null=True, blank=True, db_index=True,
                                            help_text="ID del ProfessionalAvailability reservado.")
    booked_date      = models.DateField(null=True, blank=True, help_text="Fecha del slot reservado.")
    booked_start_time = models.TimeField(null=True, blank=True, help_text="Hora de inicio del slot reservado.")

    # Encargado del servicio: persona responsable de coordinar y supervisar la ejecucion
    contact_person = models.JSONField(
        null=True, blank=True,
        help_text="Datos del encargado del servicio: nombre, cargo, contacto, etc."
    )

    # Horario confirmado por el admin (distinto al preferido por el cliente)
    confirmed_date = models.DateField(null=True, blank=True)
    confirmed_time = models.TimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'detalle de servicio de orden'
        verbose_name_plural = 'detalles de servicio de ordenes'

    def __str__(self):
        return f"Detail for Order {self.order.uuid}"


class OrderPriceAdjustment(SintelBaseModel):
    """Plan 'Manual Pricing Engine' FASE 19 -- registro append-only de cada
    override de precio comercial hecho por un administrador sobre una orden ya
    creada. `reason` es obligatorio a nivel de Command (OrderPricingCommands.
    override_price), no a nivel de modelo, para poder reusar full_clean() sin
    exigirlo en otros flujos hipoteticos futuros que no pasen por ese Command."""
    order_service_detail = models.ForeignKey(
        OrderServiceDetail, on_delete=models.CASCADE, related_name='price_adjustments',
    )
    old_total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    new_total = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField(blank=True, default='')
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='service_price_overrides',
    )

    class Meta:
        verbose_name = 'ajuste de precio de orden'
        verbose_name_plural = 'ajustes de precio de ordenes'
        ordering = ['-created_at']

    def __str__(self):
        return f"Ajuste orden {self.order_service_detail.order_id}: {self.old_total} -> {self.new_total}"


class OrderServiceTimeline(SintelBaseModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='timeline')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='service_timeline_events')

    class Meta:
        verbose_name = 'evento de linea de tiempo de servicio'
        verbose_name_plural = 'eventos de linea de tiempo de servicios'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.order.uuid} - {self.status} at {self.created_at}"


class ServiceAttachment(SintelBaseModel):
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='service_attachments/')
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    mime_type = models.CharField(max_length=100)
    doc_type = models.CharField(max_length=50, blank=True, default='', help_text="Tipo de documento: foto, plano, manual, video, otro")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='service_attachments')

    class Meta:
        verbose_name = 'adjunto de servicio'
        verbose_name_plural = 'adjuntos de servicios'

    def __str__(self):
        return f"{self.file_name} for Order {self.order.uuid}"


class ServiceBooking(SintelBaseModel):
    """Bloque de tiempo reservado para una instancia de ServiceVariant.
    Controla la disponibilidad temporal (capacidad simultanea) sin depender de StockRecord.
    """
    STATUS_SCHEDULED = 'scheduled'
    STATUS_ACTIVE    = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_SCHEDULED, 'Programado'),
        (STATUS_ACTIVE,    'En progreso'),
        (STATUS_COMPLETED, 'Completado'),
        (STATUS_CANCELLED, 'Cancelado'),
    ]

    order_service_detail = models.ForeignKey(
        'OrderServiceDetail',
        on_delete=models.CASCADE,
        related_name='bookings',
    )
    service_variant = models.ForeignKey(
        ServiceVariant,
        on_delete=models.PROTECT,
        related_name='bookings',
    )
    start_time = models.DateTimeField(db_index=True)
    end_time   = models.DateTimeField(db_index=True)
    status     = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_SCHEDULED,
        db_index=True,
    )

    class Meta:
        verbose_name = 'reserva de servicio'
        verbose_name_plural = 'reservas de servicio'
        indexes = [
            models.Index(fields=['start_time', 'end_time']),
            models.Index(fields=['service_variant', 'status']),
        ]

    def __str__(self) -> str:
        return f"ServiceBooking {self.service_variant.sku} [{self.start_time} - {self.end_time}]"


class ServiceCostRule(AbstractCostRule):
    CTX_TAX = 'TAX'
    CTX_DISCOUNT = 'DISCOUNT'
    CTX_SETUP = 'SETUP'
    CTX_OPERATIONAL = 'OPERATIONAL'
    CONTEXT_CHOICES = [
        (CTX_TAX, 'Impuesto adicional'),
        (CTX_DISCOUNT, 'Descuento'),
        (CTX_SETUP, 'Costo de instalacion/configuracion'),
        (CTX_OPERATIONAL, 'Costo operativo adicional'),
    ]

    context = models.CharField(max_length=20, choices=CONTEXT_CHOICES, db_index=True)
    applies_globally = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name = 'regla de costo de servicio'
        verbose_name_plural = 'reglas de costo de servicio'


class ServiceCostAssignment(AbstractCostAssignment):
    rule = models.ForeignKey(
        ServiceCostRule, on_delete=models.CASCADE, related_name='assignments'
    )
    variant = models.ForeignKey(
        'technical_services.ServiceVariant', on_delete=models.CASCADE, related_name='cost_assignments'
    )

    class Meta:
        verbose_name = 'asignacion de regla de costo de servicio'
        verbose_name_plural = 'asignaciones de reglas de costo de servicio'
        unique_together = ('rule', 'variant')


class ServicePriceHistory(SintelBaseModel):
    variant = models.ForeignKey(ServiceVariant, on_delete=models.CASCADE, related_name='price_history')
    old_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    new_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_price_changes'
    )

    # Plan "Manual Pricing Engine" (2026-08-13) FASE 6 -- old_price/new_price
    # (arriba) quedan intactos, siguen registrando SOLO cambios de fixed_price
    # (poblados por ServiceVariantCommands.update_variant(), sin tocar). Estos
    # campos nuevos son un segundo tipo de entrada de historial, poblada
    # exclusivamente por ServicePricingCommands.set_manual_pricing() (FASE 7) --
    # una fila de ServicePriceHistory nunca mezcla ambos tipos: o trae
    # old_price/new_price (cambio de fixed_price) o trae pricing_source_old/new
    # + unit/project_price_old/new (cambio de fuente de precio), no ambos.
    pricing_source_old = models.CharField(max_length=20, null=True, blank=True)
    pricing_source_new = models.CharField(max_length=20, null=True, blank=True)
    unit_price_old = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    unit_price_new = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    project_price_old = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    project_price_new = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    reason = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'historial de precio de servicio'
        verbose_name_plural = 'historiales de precios de servicios'
        ordering = ['-created_at']

    def __str__(self):
        return f"Price history for {self.variant.sku}: {self.old_price} -> {self.new_price}"


class ServiceOperation(SintelBaseModel):
    """
    Ciclo operativo de una orden de servicio tecnico ya pagada: recepcion, planeacion,
    asignacion de tecnico, desplazamiento, ejecucion y cierre. Dominio separado del
    comercial -- OrderServiceDetail sigue siendo solo el snapshot de la orden, nunca el
    centro operativo.
    """
    READY_FOR_PLANNING  = 'READY_FOR_PLANNING'
    PLANNED             = 'PLANNED'
    TECHNICIAN_ASSIGNED = 'TECHNICIAN_ASSIGNED'
    CUSTOMER_NOTIFIED   = 'CUSTOMER_NOTIFIED'
    READY_TO_VISIT      = 'READY_TO_VISIT'
    ON_THE_WAY          = 'ON_THE_WAY'
    ARRIVED             = 'ARRIVED'
    IN_PROGRESS         = 'IN_PROGRESS'
    COMPLETED           = 'COMPLETED'
    CLOSED              = 'CLOSED'
    CANCELLED           = 'CANCELLED'

    STATUS_CHOICES = [
        (READY_FOR_PLANNING,  'Pendiente de planeacion'),
        (PLANNED,             'Planeada'),
        (TECHNICIAN_ASSIGNED, 'Tecnico asignado'),
        (CUSTOMER_NOTIFIED,   'Cliente notificado'),
        (READY_TO_VISIT,      'Lista para visita'),
        (ON_THE_WAY,          'Tecnico en camino'),
        (ARRIVED,             'Tecnico en sitio'),
        (IN_PROGRESS,         'Servicio en progreso'),
        (COMPLETED,           'Servicio realizado'),
        (CLOSED,              'Cerrada'),
        (CANCELLED,           'Cancelada'),
    ]

    CLOSURE_PENDING   = 'PENDING'
    CLOSURE_CONFIRMED = 'CONFIRMED'
    CLOSURE_DISPUTED  = 'DISPUTED'
    CLOSURE_CHOICES = [
        (CLOSURE_PENDING,   'Pendiente'),
        (CLOSURE_CONFIRMED, 'Confirmado'),
        (CLOSURE_DISPUTED,  'En disputa'),
    ]

    order = models.OneToOneField(
        'orders.Order', on_delete=models.PROTECT, related_name='service_operation',
    )
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES,
        default=READY_FOR_PLANNING, db_index=True,
    )
    scheduled_date = models.DateField(null=True, blank=True, db_index=True)
    scheduled_time = models.TimeField(null=True, blank=True)
    estimated_duration_minutes = models.PositiveIntegerField(null=True, blank=True)

    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='service_operations',
    )
    # FK real (a diferencia del booked_slot_id suelto de OrderServiceDetail) porque este
    # modelo es nuevo: sincroniza de verdad con accounts.ProfessionalAvailability.
    availability_slot = models.ForeignKey(
        'accounts.ProfessionalAvailability', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='service_operations',
    )
    vehicle = models.CharField(max_length=120, blank=True, default='')
    route = models.TextField(blank=True, default='')
    notes = models.TextField(blank=True, default='')

    arrived_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    customer_signature = models.TextField(blank=True, default='')
    closure_status = models.CharField(
        max_length=10, choices=CLOSURE_CHOICES, default=CLOSURE_PENDING,
    )

    has_incident = models.BooleanField(default=False, db_index=True)
    incident_notes = models.TextField(blank=True, default='')

    priority = models.CharField(
        max_length=20,
        choices=OrderServiceDetail.PRIORITY_CHOICES,
        default='medium',
    )

    class Meta:
        verbose_name = 'operacion de servicio'
        verbose_name_plural = 'operaciones de servicio'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', 'scheduled_date'])]

    def __str__(self):
        return f"ServiceOperation for Order {self.order.uuid}"


class ServiceOperationEvent(SintelBaseModel):
    """Timeline append-only de una ServiceOperation."""
    operation = models.ForeignKey(
        ServiceOperation, on_delete=models.CASCADE, related_name='timeline',
    )
    event_type = models.CharField(max_length=50, db_index=True)
    description = models.TextField(blank=True, default='')
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='service_operation_events',
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.event_type} for ServiceOperation {self.operation_id}"


class WorkingSchedule(SintelBaseModel):
    """
    Horario laboral recurrente de un tecnico (2026-07-14, TechnicianAvailabilityEngine
    Fase 2). Una fila por tecnico/dia de la semana -- un solo bloque horario por dia
    (horarios partidos quedan fuera de alcance de esta fase).
    """
    MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY = range(7)
    WEEKDAY_CHOICES = [
        (MONDAY, 'Lunes'), (TUESDAY, 'Martes'), (WEDNESDAY, 'Miercoles'),
        (THURSDAY, 'Jueves'), (FRIDAY, 'Viernes'), (SATURDAY, 'Sabado'),
        (SUNDAY, 'Domingo'),
    ]

    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='working_schedules',
    )
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = 'horario laboral'
        verbose_name_plural = 'horarios laborales'
        unique_together = ('technician', 'weekday')
        ordering = ['technician_id', 'weekday']

    def __str__(self):
        return f"WorkingSchedule {self.technician_id} weekday={self.weekday} [{self.start_time}-{self.end_time}]"


class WorkingException(SintelBaseModel):
    """
    Ausencia/bloqueo de un tecnico sobre un rango de fechas (2026-07-14,
    TechnicianAvailabilityEngine Fase 2): vacaciones, permiso, incapacidad,
    capacitacion o mantenimiento. start_time/end_time nulos = dia completo.

    TYPE_EXTRA_HOURS (Fase 6, 2026-07-14) es la unica excepcion "positiva": en
    vez de RESTAR disponibilidad, SUMA una ventana de tiempo puntual a un dia
    especifico (horario extendido), sin tocar el WorkingSchedule recurrente.
    Por eso exige start_time/end_time (no puede ser "dia completo" -- no tiene
    sentido sumar un dia entero sin limites). Ver TechnicianAvailabilityEngine.
    """
    TYPE_VACATION = 'VACATION'
    TYPE_PERMIT = 'PERMIT'
    TYPE_SICK_LEAVE = 'SICK_LEAVE'
    TYPE_TRAINING = 'TRAINING'
    TYPE_MAINTENANCE = 'MAINTENANCE'
    TYPE_EXTRA_HOURS = 'EXTRA_HOURS'
    TYPE_CHOICES = [
        (TYPE_VACATION, 'Vacaciones'),
        (TYPE_PERMIT, 'Permiso'),
        (TYPE_SICK_LEAVE, 'Incapacidad'),
        (TYPE_TRAINING, 'Capacitacion'),
        (TYPE_MAINTENANCE, 'Mantenimiento'),
        (TYPE_EXTRA_HOURS, 'Horas extra'),
    ]

    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='working_exceptions',
    )
    exception_type = models.CharField(max_length=20, choices=TYPE_CHOICES, db_index=True)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    reason = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        verbose_name = 'ausencia de tecnico'
        verbose_name_plural = 'ausencias de tecnico'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['technician', 'start_date', 'end_date']),
        ]

    def __str__(self):
        return f"WorkingException {self.technician_id} {self.exception_type} {self.start_date}>{self.end_date}"


# ── Paquetes de Servicio (2026-07-16) ─────────────────────────────────────────
# Dominio nuevo y aditivo: TechnicalService pasa de vender un servicio suelto a
# vender una solucion compuesta por un paquete configurable (equipo/alcance) mas
# costos adicionales opcionales. NO reemplaza ServiceVariant (que sigue siendo la
# estrategia de precio HOURLY/DAILY/FIXED del servicio base) -- ServicePackage es
# una capa comercial adicional, opcional, sobre un TechnicalService. Los servicios
# sin paquetes configurados siguen funcionando exactamente igual (compatibilidad
# hacia atras): ServiceCommands.request_service() solo activa esta rama si el
# caller manda un `package`.

class ServicePackage(SintelBaseModel):
    """Paquete comercial de un servicio (ej. 'Mantenimiento CCTV 8 Camaras')."""
    service = models.ForeignKey(TechnicalService, on_delete=models.CASCADE, related_name='packages')
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True, default='')
    package_type = models.CharField(max_length=100, blank=True, default='')
    image = models.ImageField(upload_to='technical_services/packages/', blank=True, null=True)
    icon = models.CharField(max_length=100, blank=True, default='')
    is_default = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    position = models.PositiveIntegerField(default=0)
    estimated_duration = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text='Duracion estimada en horas',
    )
    base_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'paquete de servicio'
        verbose_name_plural = 'paquetes de servicio'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.service.name} -- {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.service.slug}-{self.name}") or str(self.uuid)[:8]
            candidate = base
            counter = 2
            while ServicePackage.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base}-{counter}"
                counter += 1
            self.slug = candidate
        super().save(*args, **kwargs)


class PackageIncludedItem(SintelBaseModel):
    """Que incluye el paquete -- fila administrable (tarjetas con icono, no texto libre)."""
    package = models.ForeignKey(ServicePackage, on_delete=models.CASCADE, related_name='included_items')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=100, blank=True, default='')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'item incluido en el paquete'
        verbose_name_plural = 'items incluidos en el paquete'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.package.name} incluye: {self.title}"


class PackageAdditionalCost(SintelBaseModel):
    """
    Costo opcional que el cliente puede agregar a un paquete (escalera, trabajo en
    altura, operario adicional, etc.). `unit` define como se multiplica `price`
    contra la cantidad/duracion que elija el cliente en PackagePriceCalculator.
    """
    TYPE_TOOL = 'HERRAMIENTA'
    TYPE_LADDER = 'ESCALERA'
    TYPE_ACCESSORY = 'ACCESORIO'
    TYPE_CONSUMABLE = 'CONSUMIBLE'
    TYPE_LABOR = 'OPERARIO'
    TYPE_SUPERVISOR = 'SUPERVISOR'
    TYPE_HEIGHT_WORK = 'TRABAJO_ALTURA'
    TYPE_NIGHT_SHIFT = 'HORARIO_NOCTURNO'
    TYPE_URGENCY = 'URGENCIA'
    TYPE_OTHER = 'OTRO'
    COST_TYPE_CHOICES = [
        (TYPE_TOOL, 'Herramienta'),
        (TYPE_LADDER, 'Escalera'),
        (TYPE_ACCESSORY, 'Accesorio'),
        (TYPE_CONSUMABLE, 'Consumible'),
        (TYPE_LABOR, 'Operario'),
        (TYPE_SUPERVISOR, 'Supervisor'),
        (TYPE_HEIGHT_WORK, 'Trabajo en altura'),
        (TYPE_NIGHT_SHIFT, 'Horario nocturno'),
        (TYPE_URGENCY, 'Urgencia'),
        (TYPE_OTHER, 'Otro'),
    ]

    UNIT_FIXED = 'FIJO'
    UNIT_HOUR = 'HORA'
    UNIT_DAY = 'DIA'
    UNIT_UNIT = 'UNIDAD'
    UNIT_PERSON = 'PERSONA'
    UNIT_CHOICES = [
        (UNIT_FIXED, 'Fijo'),
        (UNIT_HOUR, 'Por hora'),
        (UNIT_DAY, 'Por dia'),
        (UNIT_UNIT, 'Por unidad'),
        (UNIT_PERSON, 'Por persona'),
    ]

    package = models.ForeignKey(ServicePackage, on_delete=models.CASCADE, related_name='additional_costs')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    cost_type = models.CharField(max_length=20, choices=COST_TYPE_CHOICES, default=TYPE_OTHER, db_index=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default=UNIT_FIXED)
    is_required = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'costo adicional de paquete'
        verbose_name_plural = 'costos adicionales de paquete'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.package.name} -- {self.name} ({self.get_unit_display()})"


class ServiceRequestPackage(SintelBaseModel):
    """
    Snapshot del paquete elegido en una orden -- 1:1 con Order, igual patron que
    OrderServiceDetail. Congela nombre/precio al momento de la compra: si el
    admin luego cambia el precio del ServicePackage, las ordenes ya creadas
    conservan lo que realmente se cobro.
    """
    order = models.OneToOneField('orders.Order', on_delete=models.CASCADE, related_name='request_package')
    package = models.ForeignKey(ServicePackage, on_delete=models.PROTECT, related_name='requests')
    package_name_snapshot = models.CharField(max_length=255)
    package_price_snapshot = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = 'paquete solicitado'
        verbose_name_plural = 'paquetes solicitados'

    def __str__(self):
        return f"Paquete {self.package_name_snapshot} para Order {self.order.uuid}"


class ServiceRequestAdditionalCost(SintelBaseModel):
    """Snapshot de un costo adicional seleccionado por el cliente en una orden."""
    request_package = models.ForeignKey(ServiceRequestPackage, on_delete=models.CASCADE, related_name='additional_costs')
    additional_cost = models.ForeignKey(PackageAdditionalCost, on_delete=models.PROTECT, related_name='requests')
    name_snapshot = models.CharField(max_length=255)
    unit_price_snapshot = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    subtotal_snapshot = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = 'costo adicional solicitado'
        verbose_name_plural = 'costos adicionales solicitados'

    def __str__(self):
        return f"{self.name_snapshot}"
