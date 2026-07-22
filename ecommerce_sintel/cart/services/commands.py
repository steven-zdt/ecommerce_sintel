from decimal import Decimal
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from cart.models import Cart, CartItem, WishlistItem
from shop.models import ProductVariant
from technical_services.models import ServiceVariant
from inventory.services.selectors import InventorySelector


def _check_availability(variant, service_variant, quantity_requested, existing_qty=0):
    """
    Returns available stock (int) for products, or raises ValidationError for services.
    Services use is_active as availability signal (stock is unlimited when active).
    """
    if service_variant is not None:
        if not service_variant.is_active or not service_variant.service.is_active:
            raise ValidationError("El servicio no esta disponible en este momento.")
        return 9999  # servicios no tienen stock fisico

    stock = InventorySelector.get_current_stock(variant)
    total_requested = existing_qty + quantity_requested
    if total_requested > stock:
        raise ValidationError(
            f"Stock insuficiente. Stock disponible: {stock}, solicitado: {total_requested}."
        )
    return stock


class CartCommands:
    @staticmethod
    @transaction.atomic
    def add_item(cart: Cart, variant: ProductVariant = None,
                 service_variant: ServiceVariant = None, quantity: int = 1) -> CartItem:
        if not variant and not service_variant:
            raise ValueError("Debe proporcionar un variant o un service_variant.")

        lookup = {'cart': cart, 'variant': variant, 'service_variant': service_variant}
        existing_item = CartItem.objects.select_for_update().filter(**lookup).first()
        existing_qty = existing_item.quantity if existing_item else 0

        _check_availability(variant, service_variant, quantity, existing_qty)

        if existing_item:
            existing_item.quantity += quantity
            existing_item.save()
            return existing_item

        try:
            with transaction.atomic():
                return CartItem.objects.create(**lookup, quantity=quantity)
        except IntegrityError:
            # Condicion de carrera: dos altas simultaneas para el mismo (cart, variant)
            # pasaron el filter() de arriba antes de que cualquiera confirmara. La
            # UniqueConstraint en BD bloquea el segundo INSERT; nos recuperamos
            # fusionando la cantidad en el item que gano la carrera, en vez de fallar.
            item = CartItem.objects.select_for_update().get(**lookup)
            item.quantity += quantity
            item.save()
            return item

    @staticmethod
    @transaction.atomic
    def update_item_quantity(cart: Cart, variant: ProductVariant = None,
                             service_variant: ServiceVariant = None, quantity: int = 0) -> CartItem:
        lookup = {'cart': cart, 'variant': variant, 'service_variant': service_variant}
        if quantity <= 0:
            CartItem.objects.filter(**lookup).delete()
            return None

        _check_availability(variant, service_variant, quantity)

        item = CartItem.objects.select_for_update().get(**lookup)
        item.quantity = quantity
        item.save()
        return item

    @staticmethod
    @transaction.atomic
    def remove_item(cart: Cart, item_uuid: str):
        """Soft-delete de un item puntual del carrito (nunca DELETE fisico)."""
        item = CartItem.objects.get(cart=cart, uuid=item_uuid, is_deleted=False)
        item.is_deleted = True
        item.save(update_fields=['is_deleted', 'updated_at'])

    @staticmethod
    @transaction.atomic
    def clear_cart(cart: Cart):
        cart.items.all().delete()

    @staticmethod
    @transaction.atomic
    def checkout_cart(user, cart: Cart) -> dict:
        from shop.services.pricing_service import PricingService

        items = cart.items.select_for_update().prefetch_related(
            'variant__product', 'service_variant__service'
        ).all()
        if not items.exists():
            raise ValidationError("El carrito esta vacio.")

        items_payload = []
        subtotal = Decimal('0.00')
        total_amount = Decimal('0.00')

        for item in items:
            if item.variant:
                stock = InventorySelector.get_current_stock(item.variant)
                if item.quantity > stock:
                    raise ValidationError(
                        f"Stock insuficiente para {item.variant.sku}. "
                        f"Disponible: {stock}, Requerido: {item.quantity}"
                    )
                unit_price = PricingService.calculate_variant_price(
                    item.variant, include_active_taxes=False
                )
                unit_price_with_tax = PricingService.calculate_variant_price(
                    item.variant, include_active_taxes=True
                )
                final_price = unit_price_with_tax * item.quantity
                items_payload.append({
                    'item_type': 'product',
                    'variant_uuid': str(item.variant.uuid),
                    'sku': item.variant.sku,
                    'item_name': item.variant.product.name,
                    'quantity': item.quantity,
                    'unit_price': str(unit_price.quantize(Decimal('0.01'))),
                    'unit_price_with_tax': str(unit_price_with_tax.quantize(Decimal('0.01'))),
                    'final_price': str(final_price.quantize(Decimal('0.01'))),
                })
                subtotal += unit_price * item.quantity
                total_amount += final_price

            elif item.service_variant:
                sv = item.service_variant
                if not sv.is_active or not sv.service.is_active:
                    raise ValidationError(
                        f"El servicio {sv.sku} ya no esta disponible."
                    )
                if sv.fixed_price is not None:
                    unit_price = Decimal(str(sv.fixed_price))
                else:
                    from technical_services.services.selectors import ServiceSelector
                    unit_price = Decimal(str(
                        ServiceSelector.get_variant_quotation(sv)['total_price']
                    ))
                final_price = unit_price * item.quantity
                items_payload.append({
                    'item_type': 'service',
                    'service_variant_uuid': str(sv.uuid),
                    'sku': sv.sku,
                    'item_name': f"{sv.service.name} ({sv.sku})",
                    'quantity': item.quantity,
                    'unit_price': str(unit_price.quantize(Decimal('0.01'))),
                    'unit_price_with_tax': str(unit_price.quantize(Decimal('0.01'))),
                    'final_price': str(final_price.quantize(Decimal('0.01'))),
                })
                subtotal += unit_price * item.quantity
                total_amount += final_price

        return {
            'items': items_payload,
            'subtotal': str(subtotal.quantize(Decimal('0.01'))),
            'total_tax': str((total_amount - subtotal).quantize(Decimal('0.01'))),
            'total_amount': str(total_amount.quantize(Decimal('0.01'))),
            'total_items': sum(item.quantity for item in items)
        }


class WishlistCommands:
    """Write-side commands for the user wishlist."""

    @staticmethod
    @transaction.atomic
    def add_to_wishlist(user, variant: ProductVariant) -> tuple:
        """
        Add a product variant to the user's wishlist.
        Uses get_or_create to handle duplicates; restores soft-deleted entries.
        Returns (WishlistItem, created: bool).
        """
        item, created = WishlistItem.objects.get_or_create(
            user=user,
            variant=variant,
        )
        if not created and item.is_deleted:
            item.is_deleted = False
            item.save(update_fields=['is_deleted', 'updated_at'])
        return item, created

    @staticmethod
    @transaction.atomic
    def remove_from_wishlist(user, item_uuid) -> None:
        """Soft-delete a wishlist item. 404 if not found or already removed."""
        from django.shortcuts import get_object_or_404
        item = get_object_or_404(WishlistItem, uuid=item_uuid, user=user, is_deleted=False)
        item.is_deleted = True
        item.save(update_fields=['is_deleted', 'updated_at'])
