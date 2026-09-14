import uuid
from decimal import Decimal
from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from ecommerce.base_models import SintelBaseModel
from shared.models import AbstractCostRule, AbstractCostAssignment, AbstractReview

class Category(SintelBaseModel):
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL, related_name='children', null=True, blank=True
    )
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=150, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True) # UI Moderna
    is_active = models.BooleanField(default=True)
    
    # SEO
    meta_title = models.CharField(max_length=70, blank=True, default='')
    meta_description = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'categoria'
        verbose_name_plural = 'categorias'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Brand(SintelBaseModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=150, unique=True, db_index=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True) # UI Moderna
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(SintelBaseModel):
    class Condition(models.TextChoices):
        NEW = "new", "Nuevo"
        USED = "used", "Usado"
        REFURBISHED = "refurbished", "Reacondicionado"

    vendor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="products", null=True, blank=True)
    
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    short_description = models.CharField(max_length=255, blank=True, null=True, help_text="Resumen para tarjetas de producto") # UI & SEO
    description = models.TextField(blank=True, null=True)
    video_url = models.URLField(blank=True, null=True, help_text="URL de YouTube o Vimeo del producto") # Conversión
    # Bloques "Alcance"/"Garantia" de la Fase 2 de reingenieria PDP (2026-08-05) -- texto
    # unico, mismo patron que description, no ameritan modelo hijo propio (no son listas).
    scope = models.TextField(blank=True, default='')
    warranty = models.TextField(blank=True, default='')

    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.NEW)
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    
    # SEO
    meta_title = models.CharField(max_length=70, blank=True, default='')
    meta_description = models.TextField(blank=True, default='')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)


class ProductVariant(SintelBaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    sku = models.CharField(max_length=100, unique=True, db_index=True)

    # Precios
    price = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    discounted_price = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    discount_start_date = models.DateTimeField(null=True, blank=True)
    discount_end_date = models.DateTimeField(null=True, blank=True)

    stock = models.PositiveIntegerField(default=0)
    is_default = models.BooleanField(default=False)

    # Especificaciones dinamicas
    attributes = models.JSONField(default=dict, blank=True)

    # Logistica (max_digits=12 para compatibilidad con valores grandes de exportacion)
    weight = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Peso en kg")
    length = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Largo en cm")
    width  = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Ancho en cm")
    height = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Alto en cm")

    def __str__(self):
        return f"{self.product.name} - {self.sku}"


class ProductImage(SintelBaseModel):
    TYPE_PRINCIPAL = 'PRINCIPAL'
    TYPE_GALLERY = 'GALERIA'
    TYPE_DETAIL = 'DETALLE'
    TYPE_EXAMPLE = 'EJEMPLO'
    IMAGE_TYPE_CHOICES = [
        (TYPE_PRINCIPAL, 'Principal'),
        (TYPE_GALLERY, 'Galeria'),
        (TYPE_DETAIL, 'Detalle'),
        (TYPE_EXAMPLE, 'Ejemplo'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='images', null=True, blank=True)
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    # Paridad con renting.EquipmentImage (2026-08-03) -- subconjunto reducido de tipos,
    # sin INSTALACION/VISTA_360/PLANO (no aplican a un producto de venta directa).
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPE_CHOICES, default=TYPE_GALLERY, db_index=True)
    display_order = models.PositiveIntegerField(default=0) # Control del UI

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return f"Imagen de {self.product.name}"


class ProductReview(AbstractReview):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    is_verified_purchase = models.BooleanField(default=False) # Prueba Social

    class Meta:
        # "Ya has calificado este producto" en ProductReviewSerializer.validate() solo lo
        # aplicaba a nivel de aplicacion -- sin constraint de BD, una condicion de carrera
        # (dos submits simultaneos) o cualquier codigo que cree ProductReview directamente
        # podia dejar reseñas duplicadas. Verificado 2026-07-03: no habia duplicados existentes.
        unique_together = ('user', 'product')

    def __str__(self):
        return f"Reseña de {self.user.email} para {self.product.name}"


class Tax(SintelBaseModel):
    class TaxType(models.TextChoices):
        PERCENTAGE = "percentage", "Porcentaje"
        FIXED = "fixed", "Fijo"

    name = models.CharField(max_length=100)
    tax_type = models.CharField(max_length=20, choices=TaxType.choices, default=TaxType.PERCENTAGE)
    value = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ProductCostRule(AbstractCostRule):
    CTX_TAX = 'TAX'
    CTX_DISCOUNT = 'DISCOUNT'
    CONTEXT_CHOICES = [
        (CTX_TAX, 'Impuesto'),
        (CTX_DISCOUNT, 'Descuento'),
    ]

    context = models.CharField(max_length=20, choices=CONTEXT_CHOICES, db_index=True)
    applies_globally = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name = 'regla de costo de producto'
        verbose_name_plural = 'reglas de costo de producto'


class ProductCostAssignment(AbstractCostAssignment):
    rule = models.ForeignKey(
        ProductCostRule, on_delete=models.CASCADE, related_name='assignments'
    )
    variant = models.ForeignKey(
        'shop.ProductVariant', on_delete=models.CASCADE, related_name='cost_assignments'
    )

    class Meta:
        verbose_name = 'asignacion de regla de costo'
        verbose_name_plural = 'asignaciones de reglas de costo'
        unique_together = ('rule', 'variant')


# ── Catalogo enriquecido de Product (2026-08-03) ──────────────────────────────
# Espejo de renting.Equipment (migracion 0022_catalog_detail_models, 2026-07-16, ver
# renting/CLAUDE.md) -- mismo patron 1-a-muchos que ProductImage, con position para
# reordenar y is_active para activar/desactivar sin borrar (el borrado real usa
# is_deleted de SintelBaseModel). NO se mirroriza RentalServiceIncluded/RentalOptionalService/
# EquipmentLogisticsConfig/EquipmentCommercialConfig -- esos son de pricing/logistica de
# alquiler, fuera del alcance de esta fase (descripcion/componentes/documentacion).
# Ver shop/.AGENT/docs/ARQUITECTURA_COMPLETA_SHOP.md §13 para el detalle completo.

class ProductFeature(SintelBaseModel):
    """Caracteristica destacada del producto (titulo + valor), ej. 'Resolucion: 4MP'."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='features')
    title = models.CharField(max_length=255)
    value = models.CharField(max_length=255, blank=True, default='')
    icon = models.CharField(max_length=100, blank=True, default='')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'caracteristica de producto'
        verbose_name_plural = 'caracteristicas de producto'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.product.name} -- {self.title}: {self.value}"


class ProductIncludedItem(SintelBaseModel):
    """Que trae la caja / que incluye el producto -- fila administrable."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='included_items')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=100, blank=True, default='')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'item incluido en el producto'
        verbose_name_plural = 'items incluidos en el producto'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.product.name} incluye: {self.title}"


class ProductExcludedItem(SintelBaseModel):
    """Que NO incluye el producto -- fila administrable."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='excluded_items')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=100, blank=True, default='')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'item no incluido en el producto'
        verbose_name_plural = 'items no incluidos en el producto'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.product.name} no incluye: {self.title}"


class ProductSpecificationGroup(SintelBaseModel):
    """Agrupador de especificaciones tecnicas (ej. 'Camara', 'Grabador')."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='specification_groups')
    name = models.CharField(max_length=150)
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'grupo de especificaciones'
        verbose_name_plural = 'grupos de especificaciones'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.product.name} -- grupo {self.name}"


class ProductSpecification(SintelBaseModel):
    """
    Fila de ficha tecnica. product se mantiene denormalizado ademas de group (mismo
    patron que renting.RentalSpecification) para listar/optimizar todas las specs de un
    producto sin pasar por el join de group.
    """
    group = models.ForeignKey(ProductSpecificationGroup, on_delete=models.CASCADE, related_name='specifications')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='specifications')
    name = models.CharField(max_length=150)
    value = models.CharField(max_length=255)
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'especificacion tecnica'
        verbose_name_plural = 'especificaciones tecnicas'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.product.name} -- {self.name}: {self.value}"


class ProductRequirement(SintelBaseModel):
    """Requisito de instalacion/uso del producto (ej. punto electrico, conexion a internet)."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='requirements')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'requisito de producto'
        verbose_name_plural = 'requisitos de producto'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.product.name} -- requiere: {self.title}"


class ProductServiceIncluded(SintelBaseModel):
    """Servicio que ya viene incluido en el precio del producto (ej. instalacion basica)."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='services_included')
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
        return f"{self.product.name} -- servicio incluido: {self.title}"


class ProductOptionalService(SintelBaseModel):
    """Servicio adicional que el cliente puede contratar por un costo extra (ej. instalacion profesional)."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='optional_services')
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
        return f"{self.product.name} -- servicio opcional: {self.title}"


class ProductFAQ(SintelBaseModel):
    """Pregunta frecuente del producto, mostrada en el detalle publico."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=500)
    answer = models.TextField()
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'pregunta frecuente'
        verbose_name_plural = 'preguntas frecuentes'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.product.name} -- FAQ: {self.question[:50]}"


class ProductVideo(SintelBaseModel):
    """
    Video del producto (lista, a diferencia del campo unico legacy Product.video_url --
    ese campo se conserva por compatibilidad, sin migrar datos automaticamente).
    source_type distingue el origen porque cada uno se resuelve distinto en el
    frontend: YOUTUBE/VIMEO usan video_url (embed), MP4 usa video_file (subido).
    """
    SOURCE_YOUTUBE = 'YOUTUBE'
    SOURCE_VIMEO = 'VIMEO'
    SOURCE_MP4 = 'MP4'
    SOURCE_TYPE_CHOICES = [
        (SOURCE_YOUTUBE, 'YouTube'),
        (SOURCE_VIMEO, 'Vimeo'),
        (SOURCE_MP4, 'Archivo MP4'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='videos')
    title = models.CharField(max_length=255, blank=True, default='')
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPE_CHOICES, default=SOURCE_YOUTUBE)
    video_url = models.URLField(blank=True, default='')
    video_file = models.FileField(upload_to='products/videos/', blank=True, null=True)
    thumbnail = models.ImageField(upload_to='products/videos/thumbs/', blank=True, null=True)
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'video de producto'
        verbose_name_plural = 'videos de producto'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.product.name} -- video: {self.title or self.source_type}"


class ProductDocument(SintelBaseModel):
    """
    Documento descargable del producto: manual, ficha tecnica, guia, certificado,
    catalogo. is_public controla visibilidad en el detalle del cliente (documentos
    internos pueden quedar is_public=False).
    """
    TYPE_MANUAL = 'MANUAL'
    TYPE_FICHA_TECNICA = 'FICHA_TECNICA'
    TYPE_GUIA = 'GUIA'
    TYPE_CERTIFICADO = 'CERTIFICADO'
    TYPE_CATALOGO = 'CATALOGO'
    TYPE_OTRO = 'OTRO'
    DOCUMENT_TYPE_CHOICES = [
        (TYPE_MANUAL, 'Manual'),
        (TYPE_FICHA_TECNICA, 'Ficha tecnica'),
        (TYPE_GUIA, 'Guia'),
        (TYPE_CERTIFICADO, 'Certificado'),
        (TYPE_CATALOGO, 'Catalogo'),
        (TYPE_OTRO, 'Otro'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES, default=TYPE_OTRO, db_index=True)
    version = models.CharField(max_length=50, blank=True, default='')
    language = models.CharField(max_length=10, blank=True, default='es')
    file = models.FileField(upload_to='products/documents/')
    cover_image = models.ImageField(upload_to='products/documents/covers/', blank=True, null=True)
    downloads = models.PositiveIntegerField(default=0)
    position = models.PositiveIntegerField(default=0)
    is_public = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'documento de producto'
        verbose_name_plural = 'documentos de producto'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.product.name} -- {self.get_document_type_display()}: {self.title}"


class ProductFunctioningStep(SintelBaseModel):
    """
    Paso de "como funciona" el producto (mirror de technical_services.ServiceProcessStep,
    2026-08-06) -- sin equivalente previo en Shop. step_number es editable (no se infiere
    de position) por la misma razon que en ServiceProcessStep: el admin puede querer un
    numero visible distinto del orden de arrastre.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='functioning_steps')
    step_number = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    image = models.ImageField(upload_to='products/functioning/', blank=True, null=True)
    estimated_time = models.CharField(max_length=100, blank=True, default='', help_text='Ej: 30 min, 1-2 horas')
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'paso de funcionamiento de producto'
        verbose_name_plural = 'pasos de funcionamiento de producto'
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.product.name} -- paso {self.step_number}: {self.title}"