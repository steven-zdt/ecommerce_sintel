import logging
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from orders.models import Order
from inventory.models import StockRecord
from inventory.services.commands import InventoryCommands
from inventory.services.selectors import InventorySelector

logger = logging.getLogger(__name__)


# ── Helpers de inventario ─────────────────────────────────────────────────────

def _get_stock_record(variant) -> StockRecord | None:
    try:
        ct = ContentType.objects.get_for_model(type(variant))
        return StockRecord.objects.filter(
            content_type=ct, object_id=variant.uuid, is_active=True
        ).first()
    except Exception:
        return None


def _has_sufficient_stock(variant, quantity: int) -> bool:
    record = _get_stock_record(variant)
    if record is None:
        return False
    return InventorySelector.get_current_stock(record.id) >= quantity


def _deduct_inventory_for_order(order: Order, reference: str) -> None:
    """
    Descuenta stock fisico para todos los items de la orden.
    Omite ServiceVariant (sin StockRecord fisico).
    Compartido por Wompi Online, Nequi y COD.
    """
    from inventory.services.dtos import StockAdjustmentDTO

    for item in order.items.select_for_update().all():
        variant = item.variant or item.equipment_variant
        if variant is None:
            continue
        record = _get_stock_record(variant)
        if record:
            InventoryCommands.register_exit(
                StockAdjustmentDTO(
                    stock_record_uuid=record.uuid,
                    quantity=item.quantity,
                    reference=reference,
                )
            )


# ── Funcion compartida post-aprobacion ────────────────────────────────────────

@transaction.atomic
def confirm_order_payment(order: Order, reference: str) -> None:
    """
    SSoT: logica post-aprobacion compartida por todos los metodos de pago online
    (Wompi Online, Nequi Push, y futuros). Marca la orden como 'paid', confirma slots
    de servicios, descuenta inventario y despacha notificaciones multicanal.

    El llamador debe verificar que el pago fue aprobado antes de invocar esta funcion.
    """
    from technical_services.services.commands import ServiceCommands
    from notifications.services.commands import NotificationCommands

    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status == Order.STATUS_PAID:
        logger.info(
            "Pago ya confirmado, no se descuenta inventario de nuevo | order=%s reference=%s",
            order.uuid,
            reference,
        )
        return

    order.status = Order.STATUS_PAID
    order.save(update_fields=['status', 'updated_at'])

    ServiceCommands.confirm_slot_on_payment(order)
    _deduct_inventory_for_order(order, reference=f"Order {order.uuid} - {reference}")

    from operations.services.commands import OperationCommands
    OperationCommands.ensure_tickets_for_order(order)

    from orders.services.fulfillment.commands import FulfillmentCommands
    FulfillmentCommands.ensure_shipment_for_order(order)

    logger.info("Pago confirmado | order=%s reference=%s", order.uuid, reference)

    _user  = order.user
    _uuid  = str(order.uuid)
    _total = str(order.total_amount)
    transaction.on_commit(
        lambda: NotificationCommands.dispatch_notification(
            user=_user,
            template_slug='order_paid',
            context={
                'order_uuid': _uuid,
                'status':     'paid',
                'total':      _total,
                'user_name':  _user.get_short_name(),
            },
            ws_group=f'user_{_user.uuid}',
        )
    )
