import logging
from django.db import transaction
from payment.models import CodTransaction
from orders.models import Order
from payment.shared.commands import _deduct_inventory_for_order

logger = logging.getLogger(__name__)


class CodCommands:

    @staticmethod
    @transaction.atomic
    def confirm_order(order: Order) -> CodTransaction:
        """
        Confirma una orden COD: descuenta inventario, crea CodTransaction,
        marca la orden como STATUS_PAID (mismo gate que desbloquea fulfillment
        para Wompi/Nequi via confirm_order_payment()) y notifica al panel de
        administracion y al cliente via notifications.
        Debe llamarse dentro del mismo atomic block de create_from_cart.
        """
        from notifications.services.commands import NotificationCommands

        _deduct_inventory_for_order(order, reference=f"COD Order {order.uuid}")
        cod_tx = CodTransaction.objects.create(order=order)

        order.status = Order.STATUS_PAID
        order.save(update_fields=['status', 'updated_at'])

        from operations.services.commands import OperationCommands
        OperationCommands.ensure_tickets_for_order(order)

        from orders.services.fulfillment.commands import FulfillmentCommands
        FulfillmentCommands.ensure_shipment_for_order(order)

        _user  = order.user
        _uuid  = str(order.uuid)
        _total = str(order.total_amount)
        transaction.on_commit(
            lambda: NotificationCommands.dispatch_notification(
                user=_user,
                template_slug='order_cod_confirmed',
                context={
                    'order_uuid': _uuid,
                    'user_email': _user.email,
                    'total':      _total,
                    'user_name':  _user.get_short_name(),
                },
                ws_group='admin',
            )
        )

        logger.info("COD order confirmed | order=%s cod_tx=%s", order.uuid, cod_tx.uuid)
        return cod_tx

    @staticmethod
    @transaction.atomic
    def mark_delivered(cod_transaction: CodTransaction) -> CodTransaction:
        from django.utils import timezone

        cod_transaction.status       = CodTransaction.STATUS_DELIVERED
        cod_transaction.delivered_at = timezone.now()
        cod_transaction.save(update_fields=['status', 'delivered_at'])

        order = cod_transaction.order
        order.status = 'delivered'
        order.save(update_fields=['status'])

        logger.info("COD delivered | order=%s", order.uuid)
        return cod_transaction

    @staticmethod
    @transaction.atomic
    def cancel(cod_transaction: CodTransaction, notes: str = '') -> CodTransaction:
        cod_transaction.status = CodTransaction.STATUS_CANCELLED
        cod_transaction.notes  = notes
        cod_transaction.save(update_fields=['status', 'notes'])

        order = cod_transaction.order
        order.status = 'cancelled'
        order.save(update_fields=['status'])

        logger.info("COD cancelled | order=%s", order.uuid)
        return cod_transaction
