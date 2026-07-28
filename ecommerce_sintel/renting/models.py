import uuid
from decimal import Decimal

from django.db import models
from django.core.exceptions import ObjectDoesNotExist
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

    # Modalidad comercial (2026-07-22) -- distinto de rental_mode (dias/horas,
    # un eje de pricing). commercial_type es "que tipo de contrato es esto":
    # RENTAL paga de inmediato (Wompi/Nequi/COD), COMODATO nunca cobra y pasa
    # directo a pending_validation (ver RentalRequestCommands.create_request()).
    # Default RENTAL preserva el comportamiento de toda fila/codigo existente.
    COMMERCIAL_RENTAL = 'RENTAL'
    COMMERCIAL_COMODATO = 'COMODATO'
    COMMERCIAL_TYPE_CHOICES = [
        (COMMERCIAL_RENTAL, 'Renting'),
        (COMMERCIAL_COMODATO, 'Comodato'),
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
    commercial_type = models.CharField(
        max_length=10, choices=COMMERCIAL_TYPE_CHOICES,
        default=COMMERCIAL_RENTAL, db_index=True,
    )

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_LOW,
        db_index=True,
    )

    # Paso 2 -- Lugar de operacion  -> RentalRequestLocation ('location_info')
    # Paso 3 -- Responsable         -> RentalRequestContact  ('contact_info')
    # Las columnas se movieron en la migracion 0036 (auditoria DB-H1). Los
    # atributos siguen disponibles aqui via @property (bloque de delegacion al
    # final de la clase).

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

    # Paso 6 -- Transporte y puesta en marcha + totales calculados
    # -> RentalRequestCosts ('costs_info'), migracion 0036. labor_items se
    # queda aqui porque es ManyToMany (no se movio a proposito).
    labor_items = models.ManyToManyField(
        RentalLabor, blank=True, related_name='rental_requests'
    )

    PAYMENT_WOMPI    = 'WOMPI'
    PAYMENT_NEQUI    = 'NEQUI'
    PAYMENT_COD      = 'COD'
    # Comodato nunca cobra -- se salta process_payment_selection() por
    # completo (create_request() la fija directo, ver services/commands.py),
    # asi que sin esta constante el campo se quedaba en el default del modelo
    # ('WOMPI') para una solicitud que jamas se cobro (bug real, hallado en
    # smoke test 2026-07-22: el Order resultante quedaba marcado
    # payment_method='WOMPI' pese a no haber pasarela involucrada).
    PAYMENT_COMODATO = 'COMODATO'
    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_WOMPI, 'Wompi'),
        (PAYMENT_NEQUI, 'Nequi'),
        (PAYMENT_COD,   'Contra entrega'),
        (PAYMENT_COMODATO, 'Comodato (sin costo)'),
    ]

    # Paso 8 -- metodo de pago y rastro de la pasarela
    # -> RentalRequestPaymentInfo ('payment_info'), migracion 0036.

    # Conflicto de disponibilidad al confirmar pago o aprobar COD
    refund_required = models.BooleanField(default=False, db_index=True)
    admin_notes = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'solicitud de alquiler'
        verbose_name_plural = 'solicitudes de alquiler'
        ordering = ['-created_at']

    def __str__(self):
        return f"Renta {self.uuid} - {self.equipment_variant.equipment.name}"

    # -----------------------------------------------------------------------
    # Delegacion hacia los sub-modelos (auditoria DB-H1, migracion 0036)
    #
    # Los 35 campos de abajo ya no son columnas de esta tabla, pero siguen
    # siendo atributos normales de Python: se leen y se escriben igual que
    # antes (request.grand_total, request.contact_email = x, ...) y tambien
    # se aceptan como kwargs de RentalRequest(...) / .objects.create(...).
    #
    # LIMITE IMPORTANTE: una property NO es un campo. No sirven en filter(),
    # exclude(), order_by(), values(), annotate(), only(), filterset_fields ni
    # en save(update_fields=[...]) directo. Para el ORM hay que usar la
    # relacion: costs_info__grand_total, payment_info__payment_method, etc.
    # (save(update_fields=[...]) si esta cubierto: el override de save() de
    # abajo filtra los nombres movidos, porque el setter ya los persistio.)
    # -----------------------------------------------------------------------

    LOCATION_FIELD_NAMES = (
        'location_address', 'location_city', 'location_department',
        'location_coordinates', 'project_type', 'access_conditions',
        'location_notes',
    )
    CONTACT_FIELD_NAMES = (
        'contact_full_name', 'contact_doc_type', 'contact_doc_number',
        'contact_email', 'contact_phone', 'contact_company',
        'contact_position',
    )
    COSTS_FIELD_NAMES = (
        'delivery_cost', 'pickup_cost', 'distance_km', 'installation_cost',
        'calibration_cost', 'training_cost', 'startup_cost',
        'total_rental_days', 'base_cost', 'price_per_day_snapshot',
        'price_per_hour_snapshot', 'labor_total', 'transport_total',
        'setup_total', 'tax_amount', 'grand_total',
    )
    PAYMENT_FIELD_NAMES = (
        'payment_method', 'wompi_reference', 'wompi_transaction_id',
        'payment_status', 'paid_at',
    )

    SUBMODEL_RELATIONS = (
        ('location_info', LOCATION_FIELD_NAMES),
        ('contact_info', CONTACT_FIELD_NAMES),
        ('costs_info', COSTS_FIELD_NAMES),
        ('payment_info', PAYMENT_FIELD_NAMES),
    )

    MOVED_FIELD_NAMES = frozenset(
        LOCATION_FIELD_NAMES + CONTACT_FIELD_NAMES
        + COSTS_FIELD_NAMES + PAYMENT_FIELD_NAMES
    )

    def __init__(self, *args, **kwargs):
        """
        Saca de kwargs los campos que ahora viven en los sub-modelos antes de
        llamar a Model.__init__, que reventaria con TypeError por kwarg
        desconocido. Quedan guardados y se materializan en el primer save().
        """
        pending = {}
        for name in RentalRequest.MOVED_FIELD_NAMES:
            if name in kwargs:
                pending[name] = kwargs.pop(name)
        self._pending_submodel_values = pending
        super().__init__(*args, **kwargs)

    @staticmethod
    def _submodel_class(related_name):
        if related_name == 'location_info':
            return RentalRequestLocation
        if related_name == 'contact_info':
            return RentalRequestContact
        if related_name == 'costs_info':
            return RentalRequestCosts
        if related_name == 'payment_info':
            return RentalRequestPaymentInfo
        raise ValueError(f"Relacion de sub-modelo desconocida: {related_name}")

    def _submodel_instance(self, related_name):
        """Devuelve la fila hija o None si la solicitud aun no se ha guardado."""
        if self.pk is None:
            return None
        try:
            return getattr(self, related_name)
        except ObjectDoesNotExist:
            return None

    def _submodel_get(self, related_name, field_name, default=None):
        related = self._submodel_instance(related_name)
        if related is not None:
            return getattr(related, field_name)
        # Todavia sin guardar (o fila hija ausente): responde con lo que se
        # paso al constructor, si es que se paso algo.
        pending = getattr(self, '_pending_submodel_values', None) or {}
        if field_name in pending:
            return pending[field_name]
        return default

    def _submodel_set(self, related_name, field_name, value):
        related = self._submodel_instance(related_name)
        if related is None:
            if self.pk is None:
                # Sin PK no se puede crear la fila hija todavia: queda
                # pendiente para el primer save().
                if getattr(self, '_pending_submodel_values', None) is None:
                    self._pending_submodel_values = {}
                self._pending_submodel_values[field_name] = value
                return
            # Defensivo: la solicitud existe pero le falta la fila hija
            # (fila legacy, o borrado manual). Se crea al vuelo.
            self._submodel_class(related_name).objects.create(
                rental_request=self, **{field_name: value}
            )
            return
        setattr(related, field_name, value)
        related.save(update_fields=[field_name, 'updated_at'])

    def _materialize_submodels(self):
        """Crea las cuatro filas hijas tras el INSERT de la solicitud."""
        pending = getattr(self, '_pending_submodel_values', None) or {}
        for related_name, field_names in RentalRequest.SUBMODEL_RELATIONS:
            if self._submodel_instance(related_name) is not None:
                continue
            values = {
                name: pending[name] for name in field_names if name in pending
            }
            self._submodel_class(related_name).objects.create(
                rental_request=self, **values
            )
        self._pending_submodel_values = {}

    def save(self, *args, **kwargs):
        """
        Dos responsabilidades extra sobre el save() normal:

        1. update_fields: los nombres movidos ya no son campos de esta tabla,
           asi que Django lanzaria ValueError. Se filtran -- el valor ya quedo
           persistido por el setter correspondiente en el momento de la
           asignacion, asi que no se pierde nada.
        2. Primer INSERT: despues de que la solicitud tiene PK, se crean las
           cuatro filas hijas con lo que se haya pasado al constructor.
        """
        is_new = self.pk is None

        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            update_fields = list(update_fields)
            remaining = [
                name for name in update_fields
                if name not in RentalRequest.MOVED_FIELD_NAMES
            ]
            if len(remaining) != len(update_fields):
                # update_fields vacio hace que Django no guarde nada; se deja
                # updated_at para conservar el efecto de "esto se toco".
                kwargs['update_fields'] = remaining or ['updated_at']

        super().save(*args, **kwargs)

        if is_new:
            self._materialize_submodels()

    # -- Metodos get_FOO_display() que Django generaba por los campos con
    # -- choices y que desaparecieron junto con las columnas.

    def get_contact_doc_type_display(self):
        related = self._submodel_instance('contact_info')
        if related is None:
            return ''
        return related.get_contact_doc_type_display()

    def get_payment_method_display(self):
        related = self._submodel_instance('payment_info')
        if related is None:
            return ''
        return related.get_payment_method_display()

    # -- Paso 2: lugar de operacion (RentalRequestLocation) ------------------

    @property
    def location_address(self):
        return self._submodel_get('location_info', 'location_address', '')

    @location_address.setter
    def location_address(self, value):
        self._submodel_set('location_info', 'location_address', value)

    @property
    def location_city(self):
        return self._submodel_get('location_info', 'location_city', '')

    @location_city.setter
    def location_city(self, value):
        self._submodel_set('location_info', 'location_city', value)

    @property
    def location_department(self):
        return self._submodel_get('location_info', 'location_department', '')

    @location_department.setter
    def location_department(self, value):
        self._submodel_set('location_info', 'location_department', value)

    @property
    def location_coordinates(self):
        return self._submodel_get('location_info', 'location_coordinates', '')

    @location_coordinates.setter
    def location_coordinates(self, value):
        self._submodel_set('location_info', 'location_coordinates', value)

    @property
    def project_type(self):
        return self._submodel_get('location_info', 'project_type', '')

    @project_type.setter
    def project_type(self, value):
        self._submodel_set('location_info', 'project_type', value)

    @property
    def access_conditions(self):
        return self._submodel_get('location_info', 'access_conditions', '')

    @access_conditions.setter
    def access_conditions(self, value):
        self._submodel_set('location_info', 'access_conditions', value)

    @property
    def location_notes(self):
        return self._submodel_get('location_info', 'location_notes', '')

    @location_notes.setter
    def location_notes(self, value):
        self._submodel_set('location_info', 'location_notes', value)

    # -- Paso 3: responsable (RentalRequestContact) --------------------------

    @property
    def contact_full_name(self):
        return self._submodel_get('contact_info', 'contact_full_name', '')

    @contact_full_name.setter
    def contact_full_name(self, value):
        self._submodel_set('contact_info', 'contact_full_name', value)

    @property
    def contact_doc_type(self):
        return self._submodel_get('contact_info', 'contact_doc_type', RentalRequest.DOC_CC)

    @contact_doc_type.setter
    def contact_doc_type(self, value):
        self._submodel_set('contact_info', 'contact_doc_type', value)

    @property
    def contact_doc_number(self):
        return self._submodel_get('contact_info', 'contact_doc_number', '')

    @contact_doc_number.setter
    def contact_doc_number(self, value):
        self._submodel_set('contact_info', 'contact_doc_number', value)

    @property
    def contact_email(self):
        return self._submodel_get('contact_info', 'contact_email', '')

    @contact_email.setter
    def contact_email(self, value):
        self._submodel_set('contact_info', 'contact_email', value)

    @property
    def contact_phone(self):
        return self._submodel_get('contact_info', 'contact_phone', '')

    @contact_phone.setter
    def contact_phone(self, value):
        self._submodel_set('contact_info', 'contact_phone', value)

    @property
    def contact_company(self):
        return self._submodel_get('contact_info', 'contact_company', '')

    @contact_company.setter
    def contact_company(self, value):
        self._submodel_set('contact_info', 'contact_company', value)

    @property
    def contact_position(self):
        return self._submodel_get('contact_info', 'contact_position', '')

    @contact_position.setter
    def contact_position(self, value):
        self._submodel_set('contact_info', 'contact_position', value)

    # -- Paso 6 + totales (RentalRequestCosts) -------------------------------

    @property
    def delivery_cost(self):
        return self._submodel_get('costs_info', 'delivery_cost', Decimal('0'))

    @delivery_cost.setter
    def delivery_cost(self, value):
        self._submodel_set('costs_info', 'delivery_cost', value)

    @property
    def pickup_cost(self):
        return self._submodel_get('costs_info', 'pickup_cost', Decimal('0'))

    @pickup_cost.setter
    def pickup_cost(self, value):
        self._submodel_set('costs_info', 'pickup_cost', value)

    @property
    def distance_km(self):
        return self._submodel_get('costs_info', 'distance_km', None)

    @distance_km.setter
    def distance_km(self, value):
        self._submodel_set('costs_info', 'distance_km', value)

    @property
    def installation_cost(self):
        return self._submodel_get('costs_info', 'installation_cost', Decimal('0'))

    @installation_cost.setter
    def installation_cost(self, value):
        self._submodel_set('costs_info', 'installation_cost', value)

    @property
    def calibration_cost(self):
        return self._submodel_get('costs_info', 'calibration_cost', Decimal('0'))

    @calibration_cost.setter
    def calibration_cost(self, value):
        self._submodel_set('costs_info', 'calibration_cost', value)

    @property
    def training_cost(self):
        return self._submodel_get('costs_info', 'training_cost', Decimal('0'))

    @training_cost.setter
    def training_cost(self, value):
        self._submodel_set('costs_info', 'training_cost', value)

    @property
    def startup_cost(self):
        return self._submodel_get('costs_info', 'startup_cost', Decimal('0'))

    @startup_cost.setter
    def startup_cost(self, value):
        self._submodel_set('costs_info', 'startup_cost', value)

    @property
    def total_rental_days(self):
        return self._submodel_get('costs_info', 'total_rental_days', None)

    @total_rental_days.setter
    def total_rental_days(self, value):
        self._submodel_set('costs_info', 'total_rental_days', value)

    @property
    def base_cost(self):
        return self._submodel_get('costs_info', 'base_cost', None)

    @base_cost.setter
    def base_cost(self, value):
        self._submodel_set('costs_info', 'base_cost', value)

    @property
    def price_per_day_snapshot(self):
        return self._submodel_get('costs_info', 'price_per_day_snapshot', None)

    @price_per_day_snapshot.setter
    def price_per_day_snapshot(self, value):
        self._submodel_set('costs_info', 'price_per_day_snapshot', value)

    @property
    def price_per_hour_snapshot(self):
        return self._submodel_get('costs_info', 'price_per_hour_snapshot', None)

    @price_per_hour_snapshot.setter
    def price_per_hour_snapshot(self, value):
        self._submodel_set('costs_info', 'price_per_hour_snapshot', value)

    @property
    def labor_total(self):
        return self._submodel_get('costs_info', 'labor_total', Decimal('0'))

    @labor_total.setter
    def labor_total(self, value):
        self._submodel_set('costs_info', 'labor_total', value)

    @property
    def transport_total(self):
        return self._submodel_get('costs_info', 'transport_total', Decimal('0'))

    @transport_total.setter
    def transport_total(self, value):
        self._submodel_set('costs_info', 'transport_total', value)

    @property
    def setup_total(self):
        return self._submodel_get('costs_info', 'setup_total', Decimal('0'))

    @setup_total.setter
    def setup_total(self, value):
        self._submodel_set('costs_info', 'setup_total', value)

    @property
    def tax_amount(self):
        return self._submodel_get('costs_info', 'tax_amount', Decimal('0'))

    @tax_amount.setter
    def tax_amount(self, value):
        self._submodel_set('costs_info', 'tax_amount', value)

    @property
    def grand_total(self):
        return self._submodel_get('costs_info', 'grand_total', None)

    @grand_total.setter
    def grand_total(self, value):
        self._submodel_set('costs_info', 'grand_total', value)

    # -- Paso 8: pago (RentalRequestPaymentInfo) -----------------------------

    @property
    def payment_method(self):
        return self._submodel_get('payment_info', 'payment_method', RentalRequest.PAYMENT_WOMPI)

    @payment_method.setter
    def payment_method(self, value):
        self._submodel_set('payment_info', 'payment_method', value)

    @property
    def wompi_reference(self):
        return self._submodel_get('payment_info', 'wompi_reference', '')

    @wompi_reference.setter
    def wompi_reference(self, value):
        self._submodel_set('payment_info', 'wompi_reference', value)

    @property
    def wompi_transaction_id(self):
        return self._submodel_get('payment_info', 'wompi_transaction_id', '')

    @wompi_transaction_id.setter
    def wompi_transaction_id(self, value):
        self._submodel_set('payment_info', 'wompi_transaction_id', value)

    @property
    def payment_status(self):
        return self._submodel_get('payment_info', 'payment_status', '')

    @payment_status.setter
    def payment_status(self, value):
        self._submodel_set('payment_info', 'payment_status', value)

    @property
    def paid_at(self):
        return self._submodel_get('payment_info', 'paid_at', None)

    @paid_at.setter
    def paid_at(self, value):
        self._submodel_set('payment_info', 'paid_at', value)


# ---------------------------------------------------------------------------
# Sub-modelos de RentalRequest (hallazgo de auditoria DB-H1, 2026-07-27)
#
# RentalRequest habia crecido a ~50 columnas mezclando identidad/ciclo de vida
# con cuatro bloques de datos que en realidad son pasos del wizard. Cada bloque
# se movio a un OneToOneField propio. RentalRequest conserva su API de atributos
# en Python al 100% via @property/.setter (ver bloque "Delegacion" mas abajo),
# asi que serializers, selectors, commands y payloads del frontend siguen
# leyendo/escribiendo request.location_address, request.grand_total, etc.
#
# Regla: NO consultar estos campos por ORM sobre RentalRequest directamente
# (las properties no son campos, no funcionan en filter()/order_by()/values()).
# Para eso usar el lookup por relacion: location_info__location_city,
# contact_info__contact_doc_number, costs_info__grand_total,
# payment_info__payment_method.
# ---------------------------------------------------------------------------


class RentalRequestLocation(SintelBaseModel):
    """Paso 2 del wizard -- Lugar de operacion."""

    rental_request = models.OneToOneField(
        RentalRequest,
        on_delete=models.CASCADE,
        related_name='location_info',
    )
    location_address = models.CharField(max_length=500, blank=True, default='')
    location_city = models.CharField(max_length=100, blank=True, default='')
    location_department = models.CharField(max_length=100, blank=True, default='')
    location_coordinates = models.CharField(max_length=100, blank=True, default='')
    project_type = models.CharField(max_length=255, blank=True, default='')
    access_conditions = models.TextField(blank=True, default='')
    location_notes = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'lugar de operacion de solicitud'
        verbose_name_plural = 'lugares de operacion de solicitudes'

    def __str__(self):
        return f"Lugar de {self.rental_request_id}: {self.location_city}"


class RentalRequestContact(SintelBaseModel):
    """Paso 3 del wizard -- Responsable de la operacion."""

    rental_request = models.OneToOneField(
        RentalRequest,
        on_delete=models.CASCADE,
        related_name='contact_info',
    )
    contact_full_name = models.CharField(max_length=255, blank=True, default='')
    contact_doc_type = models.CharField(
        max_length=10, choices=RentalRequest.DOC_TYPE_CHOICES,
        default=RentalRequest.DOC_CC,
    )
    contact_doc_number = models.CharField(max_length=50, blank=True, default='')
    contact_email = models.EmailField(blank=True, default='')
    contact_phone = models.CharField(max_length=30, blank=True, default='')
    contact_company = models.CharField(max_length=255, blank=True, default='')
    contact_position = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        verbose_name = 'responsable de solicitud'
        verbose_name_plural = 'responsables de solicitudes'

    def __str__(self):
        return f"Responsable de {self.rental_request_id}: {self.contact_full_name}"


class RentalRequestCosts(SintelBaseModel):
    """Paso 6 del wizard (transporte y puesta en marcha) + totales calculados."""

    rental_request = models.OneToOneField(
        RentalRequest,
        on_delete=models.CASCADE,
        related_name='costs_info',
    )
    # Paso 6 -- Transporte y puesta en marcha
    delivery_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pickup_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    distance_km = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    installation_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    calibration_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    training_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    startup_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Totales calculados al confirmar
    total_rental_days = models.PositiveIntegerField(null=True, blank=True)
    base_cost = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    # R-07 (auditoria enterprise): snapshot inmutable del precio unitario del
    # EquipmentVariant vigente al momento de la reserva -- antes solo se
    # guardaban los totales derivados (base_cost/grand_total), no la tarifa
    # unitaria en si. Si el admin cambia rental_price_per_day/hour despues,
    # el historico de "cuanto costaba en ese momento" quedaba sin proteger,
    # a diferencia del mismo patron ya usado en Quotes/Orders/technical_services.
    # Nullable: filas ya existentes quedan None (no hay forma de reconstruir
    # el precio historico retroactivamente), solo las nuevas lo llenan.
    price_per_day_snapshot = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text='Snapshot de EquipmentVariant.rental_price_per_day al crear la solicitud.',
    )
    price_per_hour_snapshot = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text='Snapshot de EquipmentVariant.rental_price_per_hour al crear la solicitud.',
    )
    labor_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    transport_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    setup_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    grand_total = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )

    class Meta:
        verbose_name = 'costos de solicitud'
        verbose_name_plural = 'costos de solicitudes'

    def __str__(self):
        return f"Costos de {self.rental_request_id}: {self.grand_total}"


class RentalRequestPaymentInfo(SintelBaseModel):
    """
    Paso 8 del wizard -- metodo de pago y rastro de la pasarela.

    Se llama PaymentInfo y no Payment a proposito: la app `payment` tiene su
    propio modelo Payment/Transaction, y este solo guarda el eco de la pasarela
    dentro de la solicitud de alquiler.
    """

    rental_request = models.OneToOneField(
        RentalRequest,
        on_delete=models.CASCADE,
        related_name='payment_info',
    )
    payment_method = models.CharField(
        max_length=20,
        choices=RentalRequest.PAYMENT_METHOD_CHOICES,
        default=RentalRequest.PAYMENT_WOMPI,
    )
    wompi_reference = models.CharField(max_length=255, blank=True, default='')
    wompi_transaction_id = models.CharField(max_length=255, blank=True, default='')
    payment_status = models.CharField(max_length=50, blank=True, default='')
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'pago de solicitud'
        verbose_name_plural = 'pagos de solicitudes'

    def __str__(self):
        return f"Pago de {self.rental_request_id}: {self.payment_method}"


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
    # Denormalizado desde RentalRequest.commercial_type al crear el periodo
    # (_create_blocking_period()), mismo motivo que rental_mode/quantity ya
    # denormalizados aqui: AvailabilityEngine es hot-path y no debe hacer join
    # al padre solo para etiquetar un bloqueo como Renting o Comodato.
    commercial_type = models.CharField(
        max_length=10, choices=RentalRequest.COMMERCIAL_TYPE_CHOICES,
        default=RentalRequest.COMMERCIAL_RENTAL, db_index=True,
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


class EquipmentCommercialConfig(SintelBaseModel):
    """
    Que modalidades comerciales (Renting/Comodato) admite este Equipment.
    Mismo patron que EquipmentLogisticsConfig/EquipmentMarketing: OneToOne
    por Equipment, upsert via Commands.upsert(), sin tocar Equipment/
    EquipmentVariant. Default renting_enabled=True/comodato_enabled=False
    reproduce el comportamiento de "solo Renting" que ya tenia todo equipo
    existente antes de esta config existir.
    """
    equipment = models.OneToOneField(
        Equipment,
        on_delete=models.CASCADE,
        related_name='commercial_config'
    )
    renting_enabled = models.BooleanField(default=True, verbose_name='renting habilitado')
    comodato_enabled = models.BooleanField(default=False, verbose_name='comodato habilitado')
    comodato_notes = models.TextField(blank=True, default='', verbose_name='notas de comodato')

    class Meta:
        verbose_name = 'configuracion comercial'
        verbose_name_plural = 'configuraciones comerciales'

    def __str__(self):
        return f"Config comercial -- {self.equipment.name}"


class EquipmentCommercialOption(SintelBaseModel):
    """
    Plazos configurables por Equipment para una modalidad comercial (hoy solo
    Comodato los usa; el campo modality queda generico por si Renting algun
    dia tambien quiere ofrecer plazos fijos). Es catalogo de configuracion,
    no un registro de reserva -- no duplica RentalRequest/RentalPeriod.
    """
    TERM_6 = 6
    TERM_12 = 12
    TERM_18 = 18
    TERM_24 = 24
    TERM_36 = 36
    TERM_MONTHS_CHOICES = [
        (TERM_6, '6 meses'),
        (TERM_12, '12 meses'),
        (TERM_18, '18 meses'),
        (TERM_24, '24 meses'),
        (TERM_36, '36 meses'),
    ]

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name='commercial_options'
    )
    modality = models.CharField(
        max_length=10, choices=RentalRequest.COMMERCIAL_TYPE_CHOICES,
        default=RentalRequest.COMMERCIAL_COMODATO,
    )
    term_months = models.PositiveSmallIntegerField(choices=TERM_MONTHS_CHOICES)
    is_enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'opcion comercial'
        verbose_name_plural = 'opciones comerciales'
        constraints = [
            models.UniqueConstraint(
                fields=['equipment', 'modality', 'term_months'],
                name='renting_commercialoption_unique_term',
            ),
        ]
        ordering = ['modality', 'term_months']

    def __str__(self):
        return f"{self.equipment.name} -- {self.get_modality_display()} {self.term_months}m"


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
