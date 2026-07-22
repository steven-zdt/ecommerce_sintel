from django.db import transaction
from orders.models import Order, Shipment, ShipmentTimeline
from .events import FulfillmentEvents

# Fase 13/14: notificaciones y correos al cliente por hito operativo. Solo los
# eventos realmente visibles para el cliente disparan notificacion -- eventos
# internos (asignar centro de despacho, etc.) no la necesitan.
CUSTOMER_NOTIFICATION_BY_EVENT = {
    FulfillmentEvents.PAYMENT_RECEIVED:      'shop_order_received',
    FulfillmentEvents.PREPARATION_STARTED:   'shop_preparing_order',
    FulfillmentEvents.DISPATCHER_ASSIGNED:   'shop_dispatch_assigned',
    FulfillmentEvents.DISPATCHED:            'shop_order_shipped',
    FulfillmentEvents.OUT_FOR_DELIVERY:      'shop_delivery_scheduled',
    FulfillmentEvents.DELIVERED:             'shop_order_delivered',
    FulfillmentEvents.CUSTOMER_CONFIRMED:    'shop_delivery_confirmed',
}


class ShipmentTimelineCommands:
    @staticmethod
    @transaction.atomic
    def add_event(
        order: Order,
        shipment: Shipment | None,
        event_type: str,
        comment: str = '',
        location: str = '',
        ip_address: str | None = None,
        created_by=None,
        metadata: dict | None = None,
    ) -> ShipmentTimeline:
        event = ShipmentTimeline.objects.create(
            order=order,
            shipment=shipment,
            event_type=event_type,
            comment=comment,
            location=location,
            ip_address=ip_address,
            created_by=created_by,
            metadata=metadata or {},
        )

        template_slug = CUSTOMER_NOTIFICATION_BY_EVENT.get(event_type)
        if template_slug:
            dispatcher = getattr(shipment, 'assigned_dispatcher', None) if shipment else None
            context = {
                'order_uuid': str(order.uuid),
                'tracking_code': (shipment.tracking_code or '') if shipment else '',
                'carrier_name': (shipment.carrier.name if shipment and shipment.carrier else ''),
                'dispatcher_name': (dispatcher.user.get_full_name() or dispatcher.user.email) if dispatcher else '',
                'estimated_delivery': str(shipment.estimated_delivery or '') if shipment else '',
            }
            from notifications.services.commands import NotificationCommands
            _user = order.user
            transaction.on_commit(lambda: NotificationCommands.dispatch_notification(
                user=_user, template_slug=template_slug, context=context,
            ))
        return event

    @staticmethod
    def get_timeline(order: Order):
        return ShipmentTimeline.objects.filter(order=order).order_by('created_at')
