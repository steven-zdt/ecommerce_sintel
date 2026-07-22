import uuid
from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from ecommerce.base_models import SintelBaseModel

class RentingCategory(SintelBaseModel):
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
        verbose_name = 'categoría de renta'
        verbose_name_plural = 'categorías de rentas'
        
    def __str__(self):
        return self.name
        
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class RentingBrand(SintelBaseModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=150, unique=True, db_index=True)
    
    def __str__(self):
        return self.name
        
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Equipment(SintelBaseModel):
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="equipment_offered"
    )
    category = models.ForeignKey(RentingCategory, on_delete=models.CASCADE, related_name="equipments")
    brand = models.ForeignKey(RentingBrand, on_delete=models.CASCADE, related_name="equipments", null=True, blank=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)

    # SEO -- espejo de shop.Product (meta_title/meta_description), mas
    # meta_keywords/og_image para paridad con la ficha de producto pedida.
    # El schema.org (JSON-LD) NO se guarda como campo: se genera en el
    # serializer/frontend a partir de estos mismos campos normalizados.
    meta_title = models.CharField(max_length=70, blank=True, default='')
    meta_description = models.TextField(blank=True, default='')
    meta_keywords = models.CharField(max_length=255, blank=True, default='')
    og_image = models.ImageField(upload_to='renting/seo/', blank=True, null=True)

    class Meta:
        verbose_name = "equipo"
        verbose_name_plural = "equipos"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)

class EquipmentVariant(SintelBaseModel):
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='variants')
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    rental_price_per_day = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    rental_price_per_hour = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "variante de equipo"
        verbose_name_plural = "variantes de equipos"

    def __str__(self):
        return f"{self.equipment.name} - {self.sku}"

class EquipmentImage(SintelBaseModel):
    """Galeria avanzada del equipo -- extendida (2026-07-16) con image_type y
    position para soportar Principal/Galeria/Detalle/Instalacion/360/Plano/Ejemplo
    manteniendo compatibilidad con is_primary (imagen principal actual)."""

    TYPE_PRINCIPAL = 'PRINCIPAL'
    TYPE_GALLERY = 'GALERIA'
    TYPE_DETAIL = 'DETALLE'
    TYPE_INSTALLATION = 'INSTALACION'
    TYPE_360 = 'VISTA_360'
    TYPE_PLAN = 'PLANO'
    TYPE_EXAMPLE = 'EJEMPLO'
    IMAGE_TYPE_CHOICES = [
        (TYPE_PRINCIPAL, 'Principal'),
        (TYPE_GALLERY, 'Galeria'),
        (TYPE_DETAIL, 'Detalle'),
        (TYPE_INSTALLATION, 'Instalacion'),
        (TYPE_360, '360'),
        (TYPE_PLAN, 'Plano'),
        (TYPE_EXAMPLE, 'Ejemplo'),
    ]

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='renting/')
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPE_CHOICES, default=TYPE_GALLERY, db_index=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'imagen de equipo'
        verbose_name_plural = 'imagenes de equipo'
        ordering = ['position', 'created_at']

class EquipmentReview(SintelBaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='equipment_reviews')
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()

    class Meta:
        # Un usuario solo puede calificar un equipo una vez (mismo patron que
        # shop.ProductReview). El guard real de "solo quien lo alquilo y ya
        # lo devolvio" vive en EquipmentReviewCommands.create_review(), no aqui.
        unique_together = ('user', 'equipment')
        ordering = ['-created_at']

    def __str__(self):
        return f"Reseña de {self.user.email} para {self.equipment.name}"


# ── Catalogo enriquecido de Equipment (2026-07-16) ────────────────────────────
# Modelos normalizados para que el admin construya un producto de renting con
# el mismo nivel de detalle que shop: todo CRUD, nada de TextField/JSON para
# datos administrables. Todos son hijos directos de Equipment (mismo patron
# 1-a-muchos que EquipmentImage), con position para reordenar y is_active para
# activar/desactivar sin borrar (el borrado real usa is_deleted de SintelBaseModel).

class RentalIncludedItem(SintelBaseModel):
    """Que incluye el alquiler -- fila administrable (reemplaza el TextField libre)."""
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='included_items')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=100, blank=True, default='')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'item incluido en el alquiler'
        verbose_name_plural = 'items incluidos en el alquiler'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} incluye: {self.title}"


class RentalExcludedItem(SintelBaseModel):
    """Que NO incluye el alquiler -- fila administrable."""
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='excluded_items')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=100, blank=True, default='')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'item no incluido en el alquiler'
        verbose_name_plural = 'items no incluidos en el alquiler'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} no incluye: {self.title}"


class RentalFeature(SintelBaseModel):
    """Caracteristica destacada del equipo (titulo + valor), ej. 'Potencia: 20T'."""
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='features')
    title = models.CharField(max_length=255)
    value = models.CharField(max_length=255, blank=True, default='')
    icon = models.CharField(max_length=100, blank=True, default='')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'caracteristica de equipo'
        verbose_name_plural = 'caracteristicas de equipo'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} -- {self.title}: {self.value}"


class RentalSpecificationGroup(SintelBaseModel):
    """Agrupador de especificaciones tecnicas (ej. 'Motor', 'Dimensiones')."""
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='specification_groups')
    name = models.CharField(max_length=150)
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'grupo de especificaciones'
        verbose_name_plural = 'grupos de especificaciones'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} -- grupo {self.name}"


class RentalSpecification(SintelBaseModel):
    """
    Fila de ficha tecnica. equipment se mantiene denormalizado ademas de group
    (tal como lo pide el modelo) para poder listar/optimizar todas las specs de
    un equipo sin pasar por el join de group -- igual que el patron ya usado
    en RentalSpecificationGroup.equipment.
    """
    group = models.ForeignKey(RentalSpecificationGroup, on_delete=models.CASCADE, related_name='specifications')
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='specifications')
    name = models.CharField(max_length=150)
    value = models.CharField(max_length=255)
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'especificacion tecnica'
        verbose_name_plural = 'especificaciones tecnicas'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} -- {self.name}: {self.value}"


class RentalRequirement(SintelBaseModel):
    """Requisito para poder rentar el equipo (ej. acceso vehicular, punto electrico)."""
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='requirements')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'requisito de alquiler'
        verbose_name_plural = 'requisitos de alquiler'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} -- requiere: {self.title}"


class RentalServiceIncluded(SintelBaseModel):
    """Servicio que ya viene incluido en el precio del alquiler (ej. entrega basica)."""
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='services_included')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=100, blank=True, default='')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'servicio incluido'
        verbose_name_plural = 'servicios incluidos'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} -- servicio incluido: {self.title}"


class RentalOptionalService(SintelBaseModel):
    """
    Servicio adicional que el cliente puede contratar por un costo extra
    (catalogo informativo del producto -- distinto de RentalLabor, que es
    mano de obra generica reutilizable entre equipos).
    """
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='optional_services')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    icon = models.CharField(max_length=100, blank=True, default='')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'servicio opcional'
        verbose_name_plural = 'servicios opcionales'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} -- servicio opcional: {self.title}"


class RentalFAQ(SintelBaseModel):
    """Pregunta frecuente del equipo, mostrada en el detalle publico."""
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=500)
    answer = models.TextField()
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'pregunta frecuente'
        verbose_name_plural = 'preguntas frecuentes'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} -- FAQ: {self.question[:50]}"


class RentalVideo(SintelBaseModel):
    """
    Video del equipo. source_type distingue el origen porque cada uno se
    resuelve distinto en el frontend: YOUTUBE/VIMEO usan video_url (embed),
    MP4 usa video_file (subido, servido directo).
    """
    SOURCE_YOUTUBE = 'YOUTUBE'
    SOURCE_VIMEO = 'VIMEO'
    SOURCE_MP4 = 'MP4'
    SOURCE_TYPE_CHOICES = [
        (SOURCE_YOUTUBE, 'YouTube'),
        (SOURCE_VIMEO, 'Vimeo'),
        (SOURCE_MP4, 'Archivo MP4'),
    ]

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='videos')
    title = models.CharField(max_length=255, blank=True, default='')
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPE_CHOICES, default=SOURCE_YOUTUBE)
    video_url = models.URLField(blank=True, default='')
    video_file = models.FileField(upload_to='renting/videos/', blank=True, null=True)
    thumbnail = models.ImageField(upload_to='renting/videos/thumbs/', blank=True, null=True)
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'video de equipo'
        verbose_name_plural = 'videos de equipo'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} -- video: {self.title or self.source_type}"


class RentalDocument(SintelBaseModel):
    """
    Documento descargable del equipo: manual, ficha tecnica, guia, certificado,
    plano, catalogo, firmware o driver. is_public controla visibilidad en el
    detalle del cliente (documentos internos pueden quedar is_public=False).
    """
    TYPE_MANUAL = 'MANUAL'
    TYPE_FICHA_TECNICA = 'FICHA_TECNICA'
    TYPE_GUIA = 'GUIA'
    TYPE_CERTIFICADO = 'CERTIFICADO'
    TYPE_PLANO = 'PLANO'
    TYPE_CATALOGO = 'CATALOGO'
    TYPE_FIRMWARE = 'FIRMWARE'
    TYPE_DRIVER = 'DRIVER'
    TYPE_OTRO = 'OTRO'
    DOCUMENT_TYPE_CHOICES = [
        (TYPE_MANUAL, 'Manual'),
        (TYPE_FICHA_TECNICA, 'Ficha tecnica'),
        (TYPE_GUIA, 'Guia'),
        (TYPE_CERTIFICADO, 'Certificado'),
        (TYPE_PLANO, 'Plano'),
        (TYPE_CATALOGO, 'Catalogo'),
        (TYPE_FIRMWARE, 'Firmware'),
        (TYPE_DRIVER, 'Driver'),
        (TYPE_OTRO, 'Otro'),
    ]

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES, default=TYPE_OTRO, db_index=True)
    version = models.CharField(max_length=50, blank=True, default='')
    language = models.CharField(max_length=10, blank=True, default='es')
    file = models.FileField(upload_to='renting/documents/')
    cover_image = models.ImageField(upload_to='renting/documents/covers/', blank=True, null=True)
    downloads = models.PositiveIntegerField(default=0)
    position = models.PositiveIntegerField(default=0)
    is_public = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'documento de equipo'
        verbose_name_plural = 'documentos de equipo'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.equipment.name} -- {self.get_document_type_display()}: {self.title}"


class RentalLabor(SintelBaseModel):
    """Mano de obra asociada a la renta de equipos."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price_per_hour = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "mano de obra de renta"
        verbose_name_plural = "mano de obra de rentas"

    def __str__(self):
        return self.name


class RentalRequest(SintelBaseModel):
    """Solicitud de alquiler generada por el wizard de 8 pasos."""

    STATUS_DRAFT = 'draft'
    STATUS_PENDING_VALIDATION = 'pending_validation'
    STATUS_PENDING_PAYMENT = 'pending_payment'
    STATUS_PAID = 'paid'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_IN_OPERATION = 'in_operation'
    STATUS_FINISHED = 'finished'
    STATUS_CANCELLED = 'cancelled'
    STATUS_PAYMENT_CONFLICT = 'payment_conflict'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Borrador'),
        (STATUS_PENDING_VALIDATION, 'Pendiente de validacion'),
        (STATUS_PENDING_PAYMENT, 'Pendiente de pago'),
        (STATUS_PAID, 'Pagado'),
        (STATUS_CONFIRMED, 'Confirmado'),
        (STATUS_IN_OPERATION, 'En operacion'),
        (STATUS_FINISHED, 'Finalizado'),
        (STATUS_CANCELLED, 'Cancelado'),
        (STATUS_PAYMENT_CONFLICT, 'Conflicto de pago'),
    ]

    RENTAL_MODE_DAYS = 'days'
    RENTAL_MODE_HOURS = 'hours'
    RENTAL_MODE_CHOICES = [
        (RENTAL_MODE_DAYS, 'Por dias'),
        (RENTAL_MODE_HOURS, 'Por horas'),
    ]

    PRIORITY_LOW  = 'LOW'
    PRIORITY_HIGH = 'HIGH'
    PRIORITY_CHOICES = [
        (PRIORITY_LOW,  'Baja'),
        (PRIORITY_HIGH, 'Alta'),
    ]
    PRIORITY_MIN_DAYS = {
        PRIORITY_LOW:  7,
        PRIORITY_HIGH: 3,
    }

    DOC_CC = 'CC'
    DOC_NIT = 'NIT'
    DOC_CE = 'CE'
    DOC_PP = 'PP'
    DOC_TYPE_CHOICES = [
        (DOC_CC, 'Cedula de ciudadania'),
        (DOC_NIT, 'NIT'),
        (DOC_CE, 'Cedula de extranjeria'),
        (DOC_PP, 'Pasaporte'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rental_requests'
    )
    equipment_variant = models.ForeignKey(
        EquipmentVariant,
        on_delete=models.PROTECT,
        related_name='rental_requests'
    )
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES,
        default=STATUS_DRAFT, db_index=True
    )

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_LOW,
        db_index=True,
    )

    # Paso 2 — Lugar de operacion
    location_address = models.CharField(max_length=500, blank=True, default='')
    location_city = models.CharField(max_length=100, blank=True, default='')
    location_department = models.CharField(max_length=100, blank=True, default='')
    location_coordinates = models.CharField(max_length=100, blank=True, default='')
    project_type = models.CharField(max_length=255, blank=True, default='')
    access_conditions = models.TextField(blank=True, default='')
    location_notes = models.TextField(blank=True, default='')

    # Paso 3 — Responsable
    contact_full_name = models.CharField(max_length=255, blank=True, default='')
    contact_doc_type = models.CharField(
        max_length=10, choices=DOC_TYPE_CHOICES, default=DOC_CC
    )
    contact_doc_number = models.CharField(max_length=50, blank=True, default='')
    contact_email = models.EmailField(blank=True, default='')
    contact_phone = models.CharField(max_length=30, blank=True, default='')
    contact_company = models.CharField(max_length=255, blank=True, default='')
    contact_position = models.CharField(max_length=255, blank=True, default='')

    # Paso 4 — Configuracion de renta
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    estimated_hours = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    rental_mode = models.CharField(
        max_length=10, choices=RENTAL_MODE_CHOICES, default=RENTAL_MODE_DAYS
    )
    delivery_time = models.TimeField(null=True, blank=True)
    pickup_time = models.TimeField(null=True, blank=True)
    operational_notes = models.TextField(blank=True, default='')

    # Paso 5 — Contrato y terminos
    terms_accepted = models.BooleanField(default=False)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)

    # Paso 6 — Transporte y puesta en marcha
    delivery_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pickup_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    distance_km = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    installation_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    calibration_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    training_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    startup_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    labor_items = models.ManyToManyField(
        RentalLabor, blank=True, related_name='rental_requests'
    )

    # Totales calculados al confirmar
    total_rental_days = models.PositiveIntegerField(null=True, blank=True)
    base_cost = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    labor_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    transport_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    setup_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    grand_total = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )

    PAYMENT_WOMPI = 'WOMPI'
    PAYMENT_NEQUI = 'NEQUI'
    PAYMENT_COD   = 'COD'
    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_WOMPI, 'Wompi'),
        (PAYMENT_NEQUI, 'Nequi'),
        (PAYMENT_COD,   'Contra entrega'),
    ]

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default=PAYMENT_WOMPI,
    )

    # Paso 8 — Pago Wompi
    wompi_reference = models.CharField(max_length=255, blank=True, default='')
    wompi_transaction_id = models.CharField(max_length=255, blank=True, default='')
    payment_status = models.CharField(max_length=50, blank=True, default='')
    paid_at = models.DateTimeField(null=True, blank=True)

    # Conflicto de disponibilidad al confirmar pago o aprobar COD
    refund_required = models.BooleanField(default=False, db_index=True)
    admin_notes = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'solicitud de alquiler'
        verbose_name_plural = 'solicitudes de alquiler'
        ordering = ['-created_at']

    def __str__(self):
        return f"Renta {self.uuid} - {self.equipment_variant.equipment.name}"


class RentalProjectAttachment(SintelBaseModel):
    """Fotografía o documento de reconocimiento aportado por el cliente."""
    rental_request = models.ForeignKey(
        RentalRequest,
        on_delete=models.CASCADE,
        related_name='project_attachments',
    )
    file = models.FileField(upload_to='renting/project_attachments/%Y/%m/')
    original_name = models.CharField(max_length=255, blank=True, default='')
    content_type = models.CharField(max_length=100, blank=True, default='')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rental_project_attachments',
    )

    class Meta:
        ordering = ['created_at']


class RentalPeriod(SintelBaseModel):
    """
    Reserva de tiempo de una EquipmentVariant.
    Controla la disponibilidad por solapamiento de fechas en lugar de descontar stock fisico.
    Se crea automaticamente al confirmar una RentalRequest y se cancela si el pago falla.
    """

    STATUS_SCHEDULED = 'scheduled'
    STATUS_ACTIVE    = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_SCHEDULED, 'Programado'),
        (STATUS_ACTIVE,    'Activo'),
        (STATUS_COMPLETED, 'Completado'),
        (STATUS_CANCELLED, 'Cancelado'),
    ]

    rental_request = models.ForeignKey(
        RentalRequest,
        on_delete=models.CASCADE,
        related_name='periods',
    )
    equipment_variant = models.ForeignKey(
        EquipmentVariant,
        on_delete=models.PROTECT,
        related_name='rental_periods',
    )
    start_date = models.DateField(db_index=True)
    end_date   = models.DateField(db_index=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time   = models.TimeField(null=True, blank=True)
    rental_mode = models.CharField(
        max_length=10, choices=RentalRequest.RENTAL_MODE_CHOICES,
        default=RentalRequest.RENTAL_MODE_DAYS, db_index=True,
    )
    quantity   = models.PositiveIntegerField(default=1)
    status     = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default=STATUS_SCHEDULED, db_index=True,
    )

    class Meta:
        verbose_name = 'periodo de alquiler'
        verbose_name_plural = 'periodos de alquiler'
        indexes = [
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['equipment_variant', 'status']),
            models.Index(
                fields=['equipment_variant', 'start_date', 'end_date'],
                name='renting_period_var_range_idx',
            ),
        ]

    def __str__(self):
        return f"RentalPeriod {self.equipment_variant.sku} {self.start_date}>{self.end_date} [{self.status}]"


class EquipmentReturnInspection(SintelBaseModel):
    """
    Inspeccion de devolucion (2026-07-14). Registro opcional/aparte: NO gatea
    RentalRequestCommands.complete_period() (mark-returned) -- un admin la llena
    antes o despues, sin bloquear la operacion existente. Solo se permite sobre
    una RentalRequest ya en STATUS_FINISHED (el equipo ya volvio fisicamente).
    Si has_damage=True, EquipmentReturnInspectionCommands.create_inspection() crea
    automaticamente un EquipmentBlock (TYPE_DAMAGE) sobre la variante -- ver
    resulting_block.
    """

    rental_request = models.OneToOneField(
        RentalRequest,
        on_delete=models.CASCADE,
        related_name='return_inspection',
    )
    has_damage = models.BooleanField(default=False, db_index=True)
    condition_notes = models.TextField(blank=True, default='')
    missing_accessories = models.TextField(blank=True, default='')
    inspected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='equipment_return_inspections',
    )
    resulting_block = models.ForeignKey(
        'renting.EquipmentBlock', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='return_inspections',
    )

    class Meta:
        verbose_name = 'inspeccion de devolucion'
        verbose_name_plural = 'inspecciones de devolucion'
        ordering = ['-created_at']

    def __str__(self):
        return f"Inspeccion {self.rental_request.uuid} [{'con daño' if self.has_damage else 'ok'}]"


class RentalOperation(SintelBaseModel):
    """Ciclo operativo exclusivo de una solicitud de renting aprobada."""

    READY_FOR_SCHEDULING = 'READY_FOR_SCHEDULING'
    SCHEDULED = 'SCHEDULED'
    TRANSPORT_ASSIGNED = 'TRANSPORT_ASSIGNED'
    READY_FOR_DELIVERY = 'READY_FOR_DELIVERY'
    DELIVERED = 'DELIVERED'
    IN_OPERATION = 'IN_OPERATION'
    READY_FOR_PICKUP = 'READY_FOR_PICKUP'
    PICKED_UP = 'PICKED_UP'
    RETURN_INSPECTION = 'RETURN_INSPECTION'
    COMPLETED = 'COMPLETED'
    STATUS_CHOICES = [
        (READY_FOR_SCHEDULING, 'Pendiente de programar'),
        (SCHEDULED, 'Programada'),
        (TRANSPORT_ASSIGNED, 'Transportista asignado'),
        (READY_FOR_DELIVERY, 'Lista para entrega'),
        (DELIVERED, 'Entregada'),
        (IN_OPERATION, 'En operacion'),
        (READY_FOR_PICKUP, 'Lista para recogida'),
        (PICKED_UP, 'Recogida'),
        (RETURN_INSPECTION, 'Inspeccion de devolucion'),
        (COMPLETED, 'Completada'),
    ]

    rental_request = models.OneToOneField(
        RentalRequest, on_delete=models.PROTECT, related_name='rental_operation'
    )
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES,
        default=READY_FOR_SCHEDULING, db_index=True,
    )
    assigned_dispatcher = models.ForeignKey(
        'operations.DispatcherProfile', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='rental_operations',
    )
    assigned_vehicle = models.CharField(max_length=120, blank=True, default='')
    delivery_date = models.DateField(null=True, blank=True, db_index=True)
    delivery_time = models.TimeField(null=True, blank=True)
    pickup_date = models.DateField(null=True, blank=True, db_index=True)
    pickup_time = models.TimeField(null=True, blank=True)
    estimated_duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    route = models.TextField(blank=True, default='')
    notes = models.TextField(blank=True, default='')
    priority = models.CharField(
        max_length=10, choices=RentalRequest.PRIORITY_CHOICES,
        default=RentalRequest.PRIORITY_LOW, db_index=True,
    )
    has_incident = models.BooleanField(default=False, db_index=True)
    incident_notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', 'delivery_date'])]


class RentalOperationEvent(SintelBaseModel):
    operation = models.ForeignKey(
        RentalOperation, on_delete=models.CASCADE, related_name='timeline'
    )
    event_type = models.CharField(max_length=50, db_index=True)
    description = models.TextField(blank=True, default='')
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='rental_operation_events',
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['created_at']


class EquipmentLogisticsConfig(SintelBaseModel):
    """Costos de logistica y puesta en marcha configurados por el admin para un equipo.
    Todos los campos son opcionales — no todos los equipos requieren estos costos."""

    equipment = models.OneToOneField(
        Equipment,
        on_delete=models.CASCADE,
        related_name='logistics_config'
    )
    delivery_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='costo de entrega'
    )
    pickup_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='costo de recogida'
    )
    installation_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='costo de instalacion'
    )
    calibration_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='costo de calibracion'
    )
    training_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='costo de capacitacion'
    )
    startup_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='costo de puesta en marcha'
    )
    notes = models.TextField(blank=True, default='', verbose_name='notas adicionales')

    class Meta:
        verbose_name = 'configuracion de logistica'
        verbose_name_plural = 'configuraciones de logistica'

    def __str__(self):
        return f"Logistica -- {self.equipment.name}"


class EquipmentMarketing(SintelBaseModel):
    """
    Configuracion comercial/visual de un equipo para su presentacion publica
    (precio de venta, etiquetas, mensajes de conversion, CTA, banner, etc).

    NO almacena informacion tecnica, inventario, logistica ni disponibilidad
    -- eso vive en Equipment/EquipmentVariant/EquipmentLogisticsConfig. SEO
    (meta_title/meta_description/meta_keywords/og_image) tampoco se duplica
    aqui: ya existe en Equipment (migracion 0022), se reutiliza tal cual.

    OneToOne con Equipment: cada equipo tiene a lo sumo un registro de
    marketing, propio y exclusivo -- no hay herencia, plantillas ni
    configuraciones globales (mismo principio que RentalCostRule, ver
    ARQUITECTURA_COMPLETA_RENTIG.md).
    """

    TAG_OFFER        = 'OFERTA'
    TAG_NEW          = 'NUEVO'
    TAG_MOST_RENTED  = 'MAS_ALQUILADO'
    TAG_PREMIUM      = 'PREMIUM'
    TAG_RECOMMENDED  = 'RECOMENDADO'
    TAG_HOT          = 'HOT'
    TAG_TOP_SELLER   = 'TOP_VENTAS'
    TAG_EVENTS       = 'IDEAL_EVENTOS'
    TAG_LAST_UNITS   = 'ULTIMAS_UNIDADES'
    TAG_CHOICES = [
        (TAG_OFFER,       'Oferta'),
        (TAG_NEW,         'Nuevo'),
        (TAG_MOST_RENTED, 'Mas alquilado'),
        (TAG_PREMIUM,     'Premium'),
        (TAG_RECOMMENDED, 'Recomendado'),
        (TAG_HOT,         'Hot'),
        (TAG_TOP_SELLER,  'Top ventas'),
        (TAG_EVENTS,      'Ideal para eventos'),
        (TAG_LAST_UNITS,  'Ultimas unidades'),
    ]

    equipment = models.OneToOneField(
        Equipment,
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

    # Mensajes de conversion (texto libre, sin catalogo cerrado -- los
    # "ejemplos" del panel son solo sugerencias, no opciones fijas).
    main_message = models.TextField(blank=True, default='', verbose_name='mensaje principal')
    featured_benefit = models.CharField(max_length=255, blank=True, default='', verbose_name='beneficio destacado')
    trust_message = models.CharField(max_length=255, blank=True, default='', verbose_name='mensaje de confianza')
    urgency_message = models.CharField(max_length=255, blank=True, default='', verbose_name='mensaje de urgencia')
    social_proof_message = models.CharField(max_length=255, blank=True, default='', verbose_name='prueba social')

    # Comparativa economica (comprar vs alquilar)
    purchase_price_reference = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='precio estimado de compra',
    )
    financial_message = models.CharField(max_length=255, blank=True, default='', verbose_name='mensaje financiero')

    # Casos de uso -- lista libre de strings (ej. ["Eventos", "Construccion"]).
    use_cases = models.JSONField(default=list, blank=True, verbose_name='casos de uso')

    # Call To Action del boton principal de alquiler.
    cta_label = models.CharField(max_length=100, blank=True, default='', verbose_name='texto del CTA')

    # Banner promocional -- un unico mensaje, se muestra solo si esta configurado.
    promo_banner_message = models.CharField(max_length=255, blank=True, default='', verbose_name='banner promocional')

    # Beneficios rapidos -- lista de {"icon": "bi-truck", "label": "..."}.
    quick_benefits = models.JSONField(default=list, blank=True, verbose_name='beneficios rapidos')

    class Meta:
        verbose_name = 'marketing de equipo'
        verbose_name_plural = 'marketing de equipos'

    def __str__(self):
        return f"Marketing -- {self.equipment.name}"


class RentalCostRule(SintelBaseModel):
    """
    Regla de costo de un equipo especifico. NO existen reglas globales/heredadas
    -- cada regla solo aplica al Equipment donde el admin la creo, via su
    asignacion explicita a una EquipmentVariant de ESE equipo (RentalCostAssignment).
    Nunca se lee ni se comparte con ningun otro Equipment (ver renting/CLAUDE.md,
    regla "cada equipo es un universo independiente").
    """
    TYPE_FIXED = 'FIXED'
    TYPE_PERCENTAGE = 'PERCENTAGE'
    COST_TYPE_CHOICES = [
        (TYPE_FIXED, 'Valor fijo (COP)'),
        (TYPE_PERCENTAGE, 'Porcentaje (%)'),
    ]

    CTX_TAX = 'TAX'
    CTX_DISCOUNT = 'DISCOUNT'
    CTX_DEPOSIT = 'DEPOSIT'
    CTX_INSURANCE = 'INSURANCE'
    CTX_SURCHARGE = 'SURCHARGE'
    CONTEXT_CHOICES = [
        (CTX_TAX, 'Impuesto (IVA)'),
        (CTX_DISCOUNT, 'Descuento'),
        (CTX_DEPOSIT, 'Deposito de garantia'),
        (CTX_INSURANCE, 'Seguro del equipo'),
        (CTX_SURCHARGE, 'Recargo adicional'),
    ]

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    cost_type = models.CharField(max_length=10, choices=COST_TYPE_CHOICES, db_index=True)
    context = models.CharField(max_length=20, choices=CONTEXT_CHOICES, db_index=True)
    value = models.DecimalField(max_digits=12, decimal_places=4)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = 'regla de costo de alquiler'
        verbose_name_plural = 'reglas de costo de alquiler'

    def __str__(self):
        return f"{self.name} ({self.context})"


class EquipmentBlock(SintelBaseModel):
    """
    Bloqueo manual de una EquipmentVariant por mantenimiento, daño o conteo de
    inventario -- no esta atado a ninguna RentalRequest. AvailabilityEngine lo
    suma como unidades ocupadas junto con RentalPeriod (ver services/availability.py).
    Una sola fila cubre todo el ciclo de vida (creacion + liberacion) como historial
    auditable, sin necesitar una tabla de eventos aparte.
    """

    TYPE_MAINTENANCE = 'MAINTENANCE'
    TYPE_DAMAGE = 'DAMAGE'
    TYPE_INVENTORY = 'INVENTORY'
    TYPE_OTHER = 'OTHER'
    BLOCK_TYPE_CHOICES = [
        (TYPE_MAINTENANCE, 'Mantenimiento'),
        (TYPE_DAMAGE, 'Daño'),
        (TYPE_INVENTORY, 'Conteo de inventario'),
        (TYPE_OTHER, 'Otro'),
    ]

    STATUS_ACTIVE = 'active'
    STATUS_RELEASED = 'released'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Activo'),
        (STATUS_RELEASED, 'Liberado'),
    ]

    equipment_variant = models.ForeignKey(
        EquipmentVariant,
        on_delete=models.CASCADE,
        related_name='blocks',
    )
    block_type = models.CharField(
        max_length=20, choices=BLOCK_TYPE_CHOICES, default=TYPE_MAINTENANCE, db_index=True,
    )
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True,
    )
    reason = models.TextField()

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='equipment_blocks_created',
    )
    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='equipment_blocks_released',
    )
    released_at = models.DateTimeField(null=True, blank=True)
    release_reason = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'bloqueo de equipo'
        verbose_name_plural = 'bloqueos de equipo'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['equipment_variant', 'status']),
            models.Index(
                fields=['equipment_variant', 'start_date', 'end_date'],
                name='renting_block_var_range_idx',
            ),
        ]

    def __str__(self):
        return f"Bloqueo {self.equipment_variant.sku} {self.start_date}>{self.end_date} [{self.status}]"


class RentalCostAssignment(SintelBaseModel):
    rule = models.ForeignKey(
        RentalCostRule, on_delete=models.CASCADE, related_name='assignments'
    )
    variant = models.ForeignKey(
        'renting.EquipmentVariant', on_delete=models.CASCADE, related_name='cost_assignments'
    )

    class Meta:
        verbose_name = 'asignacion de regla de costo de alquiler'
        verbose_name_plural = 'asignaciones de reglas de costo de alquiler'
        unique_together = ('rule', 'variant')

    def __str__(self):
        return f"{self.rule.name} -> {self.variant.sku}"
