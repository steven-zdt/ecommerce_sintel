from rest_framework import viewsets, status, permissions, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError

from cart.models import Cart, CartItem, WishlistItem
from cart.services import CartSelector, CartCommands
from cart.services.commands import WishlistCommands
from cart.api.serializers import (
    CartSerializer,
    AddCartItemSerializer,
    CartItemSerializer,
    UpdateCartItemSerializer,
)
from shop.models import ProductVariant
from technical_services.models import ServiceVariant
from users.api.permissions import IsBuyerOrAdmin

class CartViewSet(viewsets.ViewSet):
    """
    ViewSet for managing the current user's cart.
    This is not a ModelViewSet because actions are primarily session-based.
    """
    permission_classes = [IsBuyerOrAdmin]

    # S-04 (auditoria enterprise): sin ningun throttle en las 5 acciones de
    # mutacion del carrito.
    ACTION_THROTTLE_SCOPES = {
        'add_item': 'cart_mutate',
        'update_item': 'cart_mutate',
        'clear': 'cart_mutate',
        'remove_item': 'cart_mutate',
        'checkout': 'cart_checkout',
    }

    def get_throttles(self):
        scope = self.ACTION_THROTTLE_SCOPES.get(self.action)
        if not scope:
            return []
        self.throttle_scope = scope
        return [ScopedRateThrottle()]

    def get_cart(self):
        return CartSelector.get_for_user(self.request.user)

    def list(self, request):
        """Returns the current user's cart details."""
        cart = self.get_cart()
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        request=AddCartItemSerializer,
        responses={201: CartItemSerializer}
    )
    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Adds an item to the cart."""
        cart = self.get_cart()
        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        variant_uuid = data.get('variant_uuid')
        service_uuid = data.get('service_variant_uuid')
        quantity = data['quantity']
        
        variant = None
        service_variant = None
        
        if variant_uuid:
            variant = get_object_or_404(ProductVariant, uuid=variant_uuid)
        if service_uuid:
            service_variant = get_object_or_404(ServiceVariant, uuid=service_uuid)
            
        try:
            item = CartCommands.add_item(
                cart=cart, 
                variant=variant, 
                service_variant=service_variant, 
                quantity=quantity
            )
        except (ValidationError, ValueError) as e:
            raise serializers.ValidationError({"detail": str(e)})

        output_serializer = CartItemSerializer(item, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=UpdateCartItemSerializer,
        responses={200: CartItemSerializer}
    )
    @action(detail=False, methods=['post'])
    def update_item(self, request):
        """Updates an item quantity in the cart."""
        cart = self.get_cart()
        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        variant_uuid = data.get('variant_uuid')
        service_uuid = data.get('service_variant_uuid')
        quantity = data['quantity']

        variant = None
        service_variant = None

        if variant_uuid:
            variant = get_object_or_404(ProductVariant, uuid=variant_uuid)
        if service_uuid:
            service_variant = get_object_or_404(ServiceVariant, uuid=service_uuid)

        try:
            item = CartCommands.update_item_quantity(
                cart=cart,
                variant=variant,
                service_variant=service_variant,
                quantity=quantity
            )
        except (ValidationError, ValueError) as e:
            raise serializers.ValidationError({"detail": str(e)})

        if item is None:
            return Response({"detail": "Item eliminado del carrito."}, status=status.HTTP_200_OK)

        output_serializer = CartItemSerializer(item, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def clear(self, request):
        """Empties the current user's cart."""
        cart = self.get_cart()
        CartCommands.clear_cart(cart)
        return Response({"detail": "Carrito vaciado."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='remove-item/(?P<item_uuid>[^/.]+)')
    def remove_item(self, request, item_uuid=None):
        """Removes a specific item from the cart by its UUID."""
        cart = self.get_cart()
        get_object_or_404(CartItem, cart=cart, uuid=item_uuid, is_deleted=False)
        CartCommands.remove_item(cart, item_uuid)
        return Response({"detail": "Item eliminado."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def checkout(self, request):
        """Calculates checkout payload with frozen pricing and stock verification."""
        cart = self.get_cart()
        try:
            payload = CartCommands.checkout_cart(request.user, cart)
        except (ValidationError, ValueError) as e:
            raise serializers.ValidationError({"detail": str(e)})
        return Response(payload, status=status.HTTP_200_OK)


class WishlistViewSet(viewsets.ViewSet):
    """
    Gestiona la lista de deseos del usuario autenticado.
    GET    /api/v1/cart/wishlist/          - listar items
    POST   /api/v1/cart/wishlist/          - agregar variante (body: {variant_uuid})
    DELETE /api/v1/cart/wishlist/{uuid}/   - eliminar item
    """
    permission_classes = [IsBuyerOrAdmin]
    lookup_field = 'uuid'

    @staticmethod
    def _primary_image_url(request, product):
        images = list(product.images.all())
        if not images:
            return None
        primary = next((img for img in images if img.is_primary), images[0])
        url = primary.image.url
        return request.build_absolute_uri(url) if request else url

    def list(self, request):
        items = (
            WishlistItem.objects
            .filter(user=request.user, is_deleted=False)
            .select_related('variant__product')
            .prefetch_related('variant__product__images')
            .order_by('-created_at')
        )
        data = [
            {
                'uuid': str(item.uuid),
                'variant_uuid': str(item.variant.uuid),
                'sku': item.variant.sku,
                'product_name': item.variant.product.name,
                'price': str(item.variant.price),
                'image': self._primary_image_url(request, item.variant.product),
                'added_at': item.created_at.isoformat(),
            }
            for item in items
        ]
        return Response(data)

    def create(self, request):
        variant_uuid = request.data.get('variant_uuid')
        if not variant_uuid:
            return Response({'detail': 'variant_uuid es requerido.'}, status=status.HTTP_400_BAD_REQUEST)

        variant = get_object_or_404(ProductVariant, uuid=variant_uuid)

        item, _ = WishlistCommands.add_to_wishlist(user=request.user, variant=variant)

        return Response(
            {
                'uuid': str(item.uuid),
                'variant_uuid': str(variant.uuid),
                'sku': variant.sku,
                'product_name': variant.product.name,
                'price': str(variant.price),
                'image': self._primary_image_url(request, variant.product),
            },
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, uuid=None):
        WishlistCommands.remove_from_wishlist(user=request.user, item_uuid=uuid)
        return Response(status=status.HTTP_204_NO_CONTENT)

