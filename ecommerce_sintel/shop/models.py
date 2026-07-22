import uuid
from decimal import Decimal
from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from ecommerce.base_models import SintelBaseModel

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
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='images', null=True, blank=True)
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0) # Control del UI

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return f"Imagen de {self.product.name}"


class ProductReview(SintelBaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
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


class ProductCostRule(SintelBaseModel):
    TYPE_FIXED = 'FIXED'
    TYPE_PERCENTAGE = 'PERCENTAGE'
    COST_TYPE_CHOICES = [
        (TYPE_FIXED, 'Valor fijo (COP)'),
        (TYPE_PERCENTAGE, 'Porcentaje (%)'),
    ]

    CTX_TAX = 'TAX'
    CTX_DISCOUNT = 'DISCOUNT'
    CONTEXT_CHOICES = [
        (CTX_TAX, 'Impuesto'),
        (CTX_DISCOUNT, 'Descuento'),
    ]

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    cost_type = models.CharField(max_length=10, choices=COST_TYPE_CHOICES, db_index=True)
    context = models.CharField(max_length=20, choices=CONTEXT_CHOICES, db_index=True)
    value = models.DecimalField(max_digits=12, decimal_places=4)
    applies_globally = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = 'regla de costo de producto'
        verbose_name_plural = 'reglas de costo de producto'

    def __str__(self):
        return f"{self.name} ({self.context})"


class ProductCostAssignment(SintelBaseModel):
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

    def __str__(self):
        return f"{self.rule.name} -> {self.variant.sku}"