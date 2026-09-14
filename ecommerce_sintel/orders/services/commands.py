import logging
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from orders.models import Order, OrderItem, ShippingAddress, Coupon
from cart.models import Cart
from inventory.services.selectors import InventorySelector, check_variant_or_service_availability

logger = logging.getLogger(__name__)


def _check_item_stock(item):
    """
    DUP-B4 (auditoria, doc 03): delega el calculo de disponibilidad a
    inventory.services.selectors.check_variant_or_service_availability()
    (mismo helper que usa cart.services.commands._check_availability()), pero
    conserva el mensaje de error propio de esta app (con el SKU) en vez del
    mensaje generico del helper compartido -- el texto que ve el usuario no
    cambio, solo el calculo/comparacion de stock que estaba duplicado.
    """
    try:
        check_variant_or_service_availability(item.variant, item.service_variant, item.quantity)
    except ValidationError:
        if item.variant:
            raise ValidationError(f"Sin existencias suficientes para: {item.variant.sku}")
        sv = item.service_variant
        raise ValidationError(f"El servicio {sv.sku} ya no esta disponible.")


def _item_unit_price(item) -> Decimal:
    if item.variant:
        from shop.services.pricing_service import PricingService
        return PricingService.calculate_variant_price(
            item.variant, include_active_taxes=True
        )
    if item.service_variant:
        sv = item.service_variant
        if sv.fixed_price is not None:
            return Decimal(str(sv.fixed_price))
        from technical_services.services.selectors import ServiceSelector
        return Decimal(str(ServiceSelector.get_variant_quotation(sv)['total_price']))
    return Decimal('0.00')


class OrderCommands:
    @staticmethod
    def create_from_cart(
        user,
        shipping_address: ShippingAddress,
        coupon_code: str = None,
        payment_method: str = 'WOMPI',
    ) -> Order:
        # Validacion (solo lectura) deliberadamente FUERA del bloque atomico de abajo:
        # un cupon invalido debe dejar su SecurityEvent(COUPON_REJECTED) escrito de
        # verdad -- si esta validacion viviera dentro del @transaction.atomic, el
        # ValidationError que aborta la creacion de la orden tambien hacia rollback
        # del evento de auditoria (bug real encontrado al verificar esta integracion).
        cart = Cart.objects.prefetch_related(
            'items__variant__product',
            'items__service_variant__service',
        ).filter(user=user).first()

        if not cart or not cart.items.exists():
            raise ValidationError("El carrito esta vacio.")

        items = list(cart.items.all())

        for item in items:
            _check_item_stock(item)

        total_items_price = Decimal('0.00')
        for item in items:
            total_items_price += _item_unit_price(item) * item.quantity

        discount = Decimal('0.00')
        if coupon_code:
            now = timezone.now()
            coupon = Coupon.objects.filter(
                code=coupon_code,
                active=True,
                valid_from__lte=now,
                valid_to__gte=now,
            ).first()
            if not coupon:
                from security.models import SecurityEvent
                from security.services.commands import SecurityCommands
                SecurityCommands.log_event(
                    SecurityEvent.COUPON_REJECTED, user=user, severity=SecurityEvent.SEVERITY_WARNING,
                    metadata={'code': coupon_code},
                )
                raise ValidationError("El cupon no es valido o ha expirado.")
            if coupon.is_percentage:
                discount = (total_items_price * coupon.discount_value) / 100
            else:
                discount = coupon.discount_value
            discount = min(discount, total_items_price)

        total = total_items_price - discount

        return OrderCommands._create_order_atomic(
            user=user, shipping_address=shipping_address, payment_method=payment_method,
            items=items, total=total, discount=discount, cart=cart,
        )

    @staticmethod
    @transaction.atomic
    def _create_order_atomic(user, shipping_address, payment_method, items, total, discount, cart) -> Order:
        # Idempotencia por carrito (O-01): serializa dos checkouts concurrentes
        # del mismo usuario (doble clic / reintento de red). El select_for_update
        # bloquea las filas del carrito; el segundo request espera aqui hasta que
        # el primero commitea (y vacia el carrito con cart.items.all().delete()),
        # luego re-verifica y encuentra el carrito vacio -> aborta sin crear una
        # segunda orden del mismo carrito. El carrito es el ancla de idempotencia
        # natural, sin necesidad de un idempotency-key del cliente ni migracion.
        locked_item_ids = list(cart.items.select_for_update().values_list('id', flat=True))
        if not locked_item_ids:
            raise ValidationError("El carrito ya fue procesado o esta vacio.")

        # En el nuevo flujo de fulfillment, la orden se crea en estado de pago pendiente.
        # El paso de confirmación de pago ocurre luego, fuera de create_from_cart().
        initial_status = Order.STATUS_PENDING_PAYMENT

        order = Order.objects.create(
            user=user,
            shipping_address=shipping_address,
            total_amount=total,
            discount_amount=discount,
            status=initial_status,
            payment_method=payment_method,
        )

        for item in items:
            unit_price = _item_unit_price(item)
            if item.variant:
                OrderItem.objects.create(
                    order=order,
                    variant=item.variant,
                    item_name=item.variant.product.name,
                    sku=item.variant.sku,
                    quantity=item.quantity,
                    price=unit_price,
                )
            elif item.service_variant:
                sv = item.service_variant
                OrderItem.objects.create(
                    order=order,
                    service_variant=sv,
                    item_name=f"{sv.service.name} ({sv.sku})",
                    sku=sv.sku,
                    quantity=item.quantity,
                    price=unit_price,
                )

        cart.items.all().delete()

        from notifications.services.commands import NotificationCommands

        _user = user
        _ctx = {
            'order_uuid': str(order.uuid),
            'status': order.status,
            'total': str(order.total_amount),
            'user_name': _user.get_short_name(),
        }
        transaction.on_commit(
            lambda: NotificationCommands.dispatch_notification(
                user=_user,
                template_slug='order_created',
                context=_ctx,
                ws_group=f'user_{_user.uuid}',
            )
        )

        if payment_method == 'COD':
            from payment.cod.services.commands import CodCommands
            CodCommands.confirm_order(order)

        return order

    @staticmethod
    def create_from_rental(rental_request) -> Order:
        """
        Crea el Order+OrderItem oficiales de un alquiler ya pagado/aprobado.

        A diferencia de create_from_cart(), este metodo NO se llama en la
        creacion de la solicitud sino unicamente desde
        RentalRequestCommands.confirm_payment()/approve_manual_validation()
        (es decir, con el pago ya resuelto) -- por eso el Order nace
        directamente en STATUS_PAID y no dispara 'order_created' ni ninguna
        otra notificacion propia: la unica comunicacion al cliente para este
        evento es la que ya envia el flujo de renting (rental_payment_confirmed/
        rental_cod_confirmed), evitando un correo/WhatsApp duplicado.
        """
        variant = rental_request.equipment_variant
        order = Order.objects.create(
            user=rental_request.user,
            shipping_address=None,
            total_amount=rental_request.grand_total,
            status=Order.STATUS_PAID,
            payment_method=rental_request.payment_method or 'WOMPI',
        )
        OrderItem.objects.create(
            order=order,
            equipment_variant=variant,
            item_name=f"{variant.equipment.name} (Alquiler {rental_request.start_date} al {rental_request.end_date})",
            sku=variant.sku,
            quantity=rental_request.quantity,
            price=rental_request.grand_total,
        )
        return order


class ShippingAddressCommands:
    """
    Unica direccion `is_default=True` por usuario, sin importar por donde entre
    el dato (create, update, o el action set-default) -- antes ShippingAddressViewSet
    era un ModelViewSet puro sin Commands, nada garantizaba esta invariante.
    """

    @staticmethod
    @transaction.atomic
    def create(user, **data) -> ShippingAddress:
        is_first = not ShippingAddress.objects.filter(user=user, is_deleted=False).exists()
        requested_default = data.pop('is_default', False)
        address = ShippingAddress.objects.create(user=user, is_default=is_first or requested_default, **data)
        if address.is_default:
            ShippingAddress.objects.filter(user=user, is_deleted=False).exclude(pk=address.pk).update(is_default=False)
        return address

    @staticmethod
    @transaction.atomic
    def update(address: ShippingAddress, **data) -> ShippingAddress:
        make_default = data.pop('is_default', None)
        for field, value in data.items():
            setattr(address, field, value)
        if make_default:
            ShippingAddress.objects.filter(user=address.user, is_deleted=False).exclude(pk=address.pk).update(is_default=False)
            address.is_default = True
        address.save()
        return address

    @staticmethod
    @transaction.atomic
    def set_as_default(user, address: ShippingAddress) -> ShippingAddress:
        ShippingAddress.objects.filter(user=user, is_deleted=False).exclude(pk=address.pk).update(is_default=False)
        address.is_default = True
        address.save(update_fields=['is_default'])
        return address

    @staticmethod
    @transaction.atomic
    def delete(address: ShippingAddress) -> None:
        # Soft-delete: un hard delete() choca con el PROTECT de Order.shipping_address
        # en cuanto la direccion ya fue usada en algun pedido (ProtectedError -> 500).
        # Si era la predeterminada, otra direccion restante toma su lugar para no
        # dejar al usuario sin direccion predeterminada.
        was_default = address.is_default
        address.is_deleted = True
        address.is_default = False
        address.save(update_fields=['is_deleted', 'is_default', 'updated_at'])
        if was_default:
            fallback = ShippingAddress.objects.filter(user=address.user, is_deleted=False).order_by('-created_at').first()
            if fallback:
                fallback.is_default = True
                fallback.save(update_fields=['is_default'])
