import logging
import uuid
from django.db import transaction
from django.utils import timezone
from orders.models import Order, Shipment
from .timeline import ShipmentTimelineCommands
from .events import FulfillmentEvents
from .assignment import AssignmentCommands

logger = logging.getLogger(__name__)


def _has_sufficient_stock_for_dispatch(order: Order) -> bool:
    """
    Chequeo de SOLO LECTURA de disponibilidad antes de despachar (Fase 5/18). El
    stock ya fue descontado al confirmarse el pago (ver
    payment/shared/commands.py::_deduct_inventory_for_order) -- esto NUNCA vuelve
    a descontar, solo valida que no haya quedado en negativo por otro motivo
    (ajuste manual, orden concurrente, etc.) antes de dejar salir el pedido.
    """
    from django.contrib.contenttypes.models import ContentType
    from inventory.models import StockRecord
    from inventory.services.selectors import InventorySelector

    for item in order.items.filter(variant__isnull=False).select_related('variant'):
        try:
            ct = ContentType.objects.get_for_model(type(item.variant))
            record = StockRecord.objects.filter(
                content_type=ct, object_id=item.variant.uuid, is_active=True
            ).first()
        except Exception:
            record = None
        if record is None:
            continue
        if InventorySelector.get_current_stock(record.id) < 0:
            return False
    return True


class FulfillmentCommands:
    @staticmethod
    def _get_shipment(order: Order) -> Shipment | None:
        try:
            return order.shipment
        except Shipment.DoesNotExist:
            return None

    @staticmethod
    def _create_shipment(order: Order) -> Shipment:
        shipment_number = f"SHP-{order.uuid.hex[:8]}-{uuid.uuid4().hex[:6]}"
        return Shipment.objects.create(
            order=order,
            shipment_number=shipment_number,
            status=Shipment.STATUS_PREPARING,
        )

    @staticmethod
    @transaction.atomic
    def ensure_shipment_for_order(order: Order, actor=None) -> Shipment | None:
        """
        Crea el Shipment automaticamente al confirmarse el pago (Wompi/Nequi
        aprobado o COD confirmado) -- unico punto de entrada al dominio operativo
        de Shop, analogo a ServiceOperationCommands.ensure_for_order /
        RentalOperationCommands.ensure_for_request. Solo aplica a ordenes con al
        menos un item de producto fisico (shop.ProductVariant); ordenes puramente
        de servicio/renting no generan Shipment.
        """
        if not order.items.filter(variant__isnull=False).exists():
            return None

        shipment = FulfillmentCommands._get_shipment(order)
        created = shipment is None
        if created:
            shipment = FulfillmentCommands._create_shipment(order)

        if created:
            ShipmentTimelineCommands.add_event(
                order=order, shipment=shipment,
                event_type=FulfillmentEvents.PAYMENT_RECEIVED,
                comment='Pago confirmado -- pedido listo para preparar.',
                created_by=actor,
            )
        return shipment

    @staticmethod
    @transaction.atomic
    def confirm_delivery_by_customer(order: Order, actor=None) -> Order:
        """Confirmacion del cliente de que recibio el pedido (Fase 3/14)."""
        shipment = FulfillmentCommands._get_shipment(order)
        if not shipment:
            raise ValueError('No existe un shipment para confirmar entrega.')
        if shipment.status != Shipment.STATUS_DELIVERED:
            raise ValueError('Solo se puede confirmar la entrega de un pedido ya entregado.')

        shipment.customer_confirmed_at = timezone.now()
        shipment.save(update_fields=['customer_confirmed_at', 'updated_at'])

        ShipmentTimelineCommands.add_event(
            order=order, shipment=shipment,
            event_type=FulfillmentEvents.CUSTOMER_CONFIRMED,
            comment='Cliente confirmo la recepcion del pedido.',
            created_by=actor,
        )
        return order

    @staticmethod
    @transaction.atomic
    def start_preparation(order: Order, created_by=None, comment: str = '') -> Order:
        shipment = FulfillmentCommands._get_shipment(order) or FulfillmentCommands._create_shipment(order)
        shipment.status = Shipment.STATUS_PREPARING
        shipment.save(update_fields=['status', 'updated_at'])

        order.status = Order.STATUS_PREPARING
        order.save(update_fields=['status', 'updated_at'])

        ShipmentTimelineCommands.add_event(
            order=order,
            shipment=shipment,
            event_type=FulfillmentEvents.PREPARATION_STARTED,
            comment=comment,
            created_by=created_by,
        )
        return order

    @staticmethod
    @transaction.atomic
    def complete_packing(order: Order, created_by=None, comment: str = '', **package_fields) -> Order:
        shipment = FulfillmentCommands._get_shipment(order)
        if not shipment:
            raise ValueError('No existe un shipment asociado para completar el empaque.')

        update_fields = ['status', 'updated_at']
        for field in ('package_type', 'package_weight', 'package_volume', 'package_dimensions', 'evidence_photos'):
            if field in package_fields and package_fields[field] not in (None, ''):
                setattr(shipment, field, package_fields[field])
                update_fields.append(field)

        shipment.status = Shipment.STATUS_READY_FOR_DISPATCH
        shipment.save(update_fields=update_fields)

        order.status = Order.STATUS_READY_FOR_DISPATCH
        order.save(update_fields=['status', 'updated_at'])

        ShipmentTimelineCommands.add_event(
            order=order,
            shipment=shipment,
            event_type=FulfillmentEvents.PACKING_COMPLETED,
            comment=comment,
            created_by=created_by,
        )
        return order

    @staticmethod
    @transaction.atomic
    def schedule_dispatch(order: Order, created_by=None, **schedule_fields) -> Order:
        """Programacion logistica (Fase 8/9): metodo de envio, fecha estimada y ruta, sin transicion de estado."""
        shipment = FulfillmentCommands._get_shipment(order)
        if not shipment:
            raise ValueError('No existe un shipment asociado para programar.')

        update_fields = ['updated_at']
        for field in ('shipping_method', 'dispatch_scheduled_at', 'estimated_delivery', 'route'):
            if field in schedule_fields and schedule_fields[field] not in (None, ''):
                setattr(shipment, field, schedule_fields[field])
                update_fields.append(field)
        shipment.save(update_fields=update_fields)

        ShipmentTimelineCommands.add_event(
            order=order,
            shipment=shipment,
            event_type=FulfillmentEvents.SCHEDULED,
            comment='Programacion logistica actualizada.',
            created_by=created_by,
        )
        return order

    @staticmethod
    @transaction.atomic
    def assign_dispatch_center(order: Order, dispatch_center_uuid: str, assigned_by=None) -> Order:
        shipment = FulfillmentCommands._get_shipment(order) or FulfillmentCommands._create_shipment(order)
        shipment = AssignmentCommands.assign_dispatch_center(order, shipment, dispatch_center_uuid, assigned_by)

        if order.status not in {Order.STATUS_ASSIGNED, Order.STATUS_PICKED_UP, Order.STATUS_IN_TRANSIT, Order.STATUS_OUT_FOR_DELIVERY, Order.STATUS_DELIVERED, Order.STATUS_COMPLETED}:
            order.status = Order.STATUS_READY_FOR_DISPATCH
            order.save(update_fields=['status', 'updated_at'])

        return order

    @staticmethod
    @transaction.atomic
    def assign_carrier(order: Order, carrier_uuid: str, assigned_by=None) -> Order:
        shipment = FulfillmentCommands._get_shipment(order)
        if not shipment:
            raise ValueError('Debe iniciar la preparación antes de asignar una transportadora.')

        shipment = AssignmentCommands.assign_carrier(order, shipment, carrier_uuid, assigned_by)
        order.status = Order.STATUS_ASSIGNED
        order.save(update_fields=['status', 'updated_at'])
        return order

    @staticmethod
    @transaction.atomic
    def assign_driver(order: Order, driver_uuid: str, assigned_by=None) -> Order:
        shipment = FulfillmentCommands._get_shipment(order)
        if not shipment:
            raise ValueError('Debe iniciar la preparación antes de asignar un repartidor.')

        shipment = AssignmentCommands.assign_driver(order, shipment, driver_uuid, assigned_by)
        order.status = Order.STATUS_ASSIGNED
        order.save(update_fields=['status', 'updated_at'])
        return order

    @staticmethod
    @transaction.atomic
    def assign_dispatcher(order: Order, dispatcher_profile_uuid: str, assigned_by=None) -> Order:
        shipment = FulfillmentCommands._get_shipment(order)
        if not shipment:
            raise ValueError('Debe iniciar la preparación antes de asignar un despachador.')

        AssignmentCommands.assign_dispatcher(order, shipment, dispatcher_profile_uuid, assigned_by)
        return order

    @staticmethod
    @transaction.atomic
    def dispatch(order: Order, created_by=None, comment: str = '') -> Order:
        shipment = FulfillmentCommands._get_shipment(order)
        if not shipment:
            raise ValueError('No existe un shipment para despachar.')
        if not _has_sufficient_stock_for_dispatch(order):
            raise ValueError('No se puede despachar: hay productos sin disponibilidad en inventario.')

        shipment.status = Shipment.STATUS_PICKED_UP
        shipment.save(update_fields=['status', 'updated_at'])

        order.status = Order.STATUS_PICKED_UP
        order.save(update_fields=['status', 'updated_at'])

        ShipmentTimelineCommands.add_event(
            order=order,
            shipment=shipment,
            event_type=FulfillmentEvents.DISPATCHED,
            comment=comment,
            created_by=created_by,
        )
        return order

    @staticmethod
    @transaction.atomic
    def mark_in_transit(order: Order, created_by=None, comment: str = '') -> Order:
        shipment = FulfillmentCommands._get_shipment(order)
        if not shipment:
            raise ValueError('No existe un shipment para actualizar a en tránsito.')

        shipment.status = Shipment.STATUS_IN_TRANSIT
        shipment.save(update_fields=['status', 'updated_at'])

        order.status = Order.STATUS_IN_TRANSIT
        order.save(update_fields=['status', 'updated_at'])

        ShipmentTimelineCommands.add_event(
            order=order,
            shipment=shipment,
            event_type=FulfillmentEvents.IN_TRANSIT,
            comment=comment,
            created_by=created_by,
        )
        return order

    @staticmethod
    @transaction.atomic
    def mark_out_for_delivery(order: Order, created_by=None, comment: str = '') -> Order:
        shipment = FulfillmentCommands._get_shipment(order)
        if not shipment:
            raise ValueError('No existe un shipment para marcar en reparto.')

        shipment.status = Shipment.STATUS_OUT_FOR_DELIVERY
        shipment.save(update_fields=['status', 'updated_at'])

        order.status = Order.STATUS_OUT_FOR_DELIVERY
        order.save(update_fields=['status', 'updated_at'])

        ShipmentTimelineCommands.add_event(
            order=order,
            shipment=shipment,
            event_type=FulfillmentEvents.OUT_FOR_DELIVERY,
            comment=comment,
            created_by=created_by,
        )
        return order

    @staticmethod
    @transaction.atomic
    def deliver(order: Order, created_by=None, comment: str = '') -> Order:
        shipment = FulfillmentCommands._get_shipment(order)
        if not shipment:
            raise ValueError('No existe un shipment para marcar como entregado.')

        shipment.status = Shipment.STATUS_DELIVERED
        shipment.actual_delivery = timezone.now()
        shipment.save(update_fields=['status', 'actual_delivery', 'updated_at'])

        order.status = Order.STATUS_DELIVERED
        order.save(update_fields=['status', 'updated_at'])

        ShipmentTimelineCommands.add_event(
            order=order,
            shipment=shipment,
            event_type=FulfillmentEvents.DELIVERED,
            comment=comment,
            created_by=created_by,
        )
        return order

    @staticmethod
    @transaction.atomic
    def complete_order(order: Order, created_by=None, comment: str = '') -> Order:
        shipment = FulfillmentCommands._get_shipment(order)
        if shipment and shipment.status != Shipment.STATUS_COMPLETED:
            shipment.status = Shipment.STATUS_COMPLETED
            shipment.save(update_fields=['status', 'updated_at'])

        order.status = Order.STATUS_COMPLETED
        order.save(update_fields=['status', 'updated_at'])

        ShipmentTimelineCommands.add_event(
            order=order,
            shipment=shipment,
            event_type=FulfillmentEvents.COMPLETED,
            comment=comment,
            created_by=created_by,
        )
        return order
