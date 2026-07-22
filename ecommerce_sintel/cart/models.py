from django.db import models
from django.conf import settings
from shop.models import ProductVariant
from technical_services.models import ServiceVariant
from ecommerce.base_models import SintelBaseModel

class Cart(SintelBaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart',
        null=True,
        blank=True,
        unique=True,
    )
    guest_id = models.UUIDField(null=True, blank=True, db_index=True)

    def __str__(self):
        return f"Carrito {self.uuid}"

class CartItem(SintelBaseModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    service_variant = models.ForeignKey(ServiceVariant, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(variant__isnull=False, service_variant__isnull=True) |
                    models.Q(variant__isnull=True, service_variant__isnull=False)
                ),
                name='cart_cartitem_exactly_one_target',
            ),
            models.UniqueConstraint(
                fields=['cart', 'variant'],
                condition=models.Q(variant__isnull=False),
                name='cart_cartitem_unique_variant_per_cart',
            ),
            models.UniqueConstraint(
                fields=['cart', 'service_variant'],
                condition=models.Q(service_variant__isnull=False),
                name='cart_cartitem_unique_service_variant_per_cart',
            ),
        ]

    def __str__(self):
        item_name = self.variant.sku if self.variant else self.service_variant.sku
        return f"{item_name} x {self.quantity}"

class WishlistItem(SintelBaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('user', 'variant')
