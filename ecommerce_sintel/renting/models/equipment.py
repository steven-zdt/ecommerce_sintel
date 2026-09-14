# Extracted from the former renting.models module. Public imports remain in __init__.py.

import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from ecommerce.base_models import SintelBaseModel
from shared.models import AbstractReview

from .common import RentingBrand, RentingCategory

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

class EquipmentReview(AbstractReview):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='equipment_reviews')
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='reviews')

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

