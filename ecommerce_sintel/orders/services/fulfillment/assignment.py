from django.db import transaction
from django.shortcuts import get_object_or_404
from .timeline import ShipmentTimelineCommands
from .events import FulfillmentEvents
from orders.models import Order, Shipment, DispatchCenter, Carrier, DeliveryDriver

class AssignmentCommands:
    @staticmethod
    @transaction.atomic
    def assign_dispatch_center(order: Order, shipment: Shipment, dispatch_center_uuid: str, assigned_by=None) -> Shipment:
        dispatch_center = get_object_or_404(DispatchCenter, uuid=dispatch_center_uuid, is_deleted=False)
        shipment.dispatch_center = dispatch_center
        shipment.save(update_fields=['dispatch_center', 'updated_at'])

        ShipmentTimelineCommands.add_event(
            order=order,
            shipment=shipment,
            event_type=FulfillmentEvents.DISPATCH_CENTER_ASSIGNED,
            comment=f"Centro de despacho asignado: {dispatch_center.name}",
            created_by=assigned_by,
        )
        return shipment

    @staticmethod
    @transaction.atomic
    def assign_carrier(order: Order, shipment: Shipment, carrier_uuid: str, assigned_by=None) -> Shipment:
        carrier = get_object_or_404(Carrier, uuid=carrier_uuid, is_deleted=False)
        shipment.carrier = carrier
        shipment.save(update_fields=['carrier', 'updated_at'])

        ShipmentTimelineCommands.add_event(
            order=order,
            shipment=shipment,
            event_type=FulfillmentEvents.CARRIER_ASSIGNED,
            comment=f"Transportadora asignada: {carrier.name}",
            created_by=assigned_by,
        )
        return shipment

    @staticmethod
    @transaction.atomic
    def assign_driver(order: Order, shipment: Shipment, driver_uuid: str, assigned_by=None) -> Shipment:
        driver = get_object_or_404(DeliveryDriver, uuid=driver_uuid, is_deleted=False)
        shipment.driver = driver
        shipment.vehicle = driver.vehicle or shipment.vehicle
        shipment.save(update_fields=['driver', 'vehicle', 'updated_at'])

        ShipmentTimelineCommands.add_event(
            order=order,
            shipment=shipment,
            event_type=FulfillmentEvents.DRIVER_ASSIGNED,
            comment=f"Repartidor asignado: {driver.name}",
            created_by=assigned_by,
        )
        return shipment

    @staticmethod
    @transaction.atomic
    def assign_dispatcher(order: Order, shipment: Shipment, dispatcher_profile_uuid: str, assigned_by=None) -> Shipment:
        """
        Camino NUEVO de asignacion (2026-07-09): usa operations.DispatcherProfile
        (mismo pool de despachadores registrados que ya usa Renting, gestionado en
        /panel/despachadores) en vez de orders.DeliveryDriver (standalone, sin FK a
        User). No reemplaza assign_driver/assign_carrier -- coexiste.
        """
        from operations.models import DispatcherProfile
        dispatcher = get_object_or_404(DispatcherProfile, uuid=dispatcher_profile_uuid, is_deleted=False)
        if not dispatcher.is_active or not dispatcher.is_available:
            raise ValueError('El despachador seleccionado no esta disponible.')

        shipment.assigned_dispatcher = dispatcher
        shipment.vehicle = dispatcher.vehicle_plate or shipment.vehicle
        update_fields = ['assigned_dispatcher', 'vehicle', 'updated_at']
        if shipment.status == Shipment.STATUS_READY_FOR_DISPATCH:
            shipment.status = Shipment.STATUS_ASSIGNED
            update_fields.append('status')
        shipment.save(update_fields=update_fields)

        if order.status not in {Order.STATUS_ASSIGNED, Order.STATUS_PICKED_UP, Order.STATUS_IN_TRANSIT, Order.STATUS_OUT_FOR_DELIVERY, Order.STATUS_DELIVERED, Order.STATUS_COMPLETED}:
            order.status = Order.STATUS_ASSIGNED
            order.save(update_fields=['status', 'updated_at'])

        ShipmentTimelineCommands.add_event(
            order=order,
            shipment=shipment,
            event_type=FulfillmentEvents.DISPATCHER_ASSIGNED,
            comment=f"Despachador asignado: {dispatcher.user.get_full_name() or dispatcher.user.email}",
            created_by=assigned_by,
        )
        return shipment
