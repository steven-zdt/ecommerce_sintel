from django.shortcuts import get_object_or_404
from django.db.models import QuerySet
from cart.models import Cart

class CartSelector:
    @staticmethod
    def get_for_user(user) -> Cart:
        """Obtiene o crea un carrito para un usuario autenticado con prefetches optimizados."""
        cart, _ = Cart.objects.get_or_create(user=user)
        # Refetch with prefetches
        return (
            Cart.objects
            .prefetch_related(
                'items__variant__product',
                'items__service_variant__service'
            )
            .get(id=cart.id)
        )

    @staticmethod
    def get_by_guest_id(guest_id: str) -> Cart:
        """Obtiene un carrito por guest_id con prefetches."""
        return (
            Cart.objects
            .prefetch_related(
                'items__variant__product',
                'items__service_variant__service'
            )
            .get(guest_id=guest_id)
        )

    @staticmethod
    def get_cart_queryset(cart_id: int) -> QuerySet:
        return Cart.objects.filter(id=cart_id).prefetch_related('items__variant__product', 'items__service_variant__service')
