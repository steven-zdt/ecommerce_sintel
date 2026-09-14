from django.db import transaction
from django.shortcuts import get_object_or_404
from .timeline import ShipmentTimelineCommands
from .events import FulfillmentEvents
from orders.models import Order, Shipment, DispatchCenter, Carrier, DeliveryDriver

class AssignmentCommands:
    @staticmethod
    def _set_dispatcher_availability(dispatcher, is_available):
        """Mantiene operations.DispatcherProfile.is_available sincronizada con
        la asignacion real via Shipment. Cross-domain audit FASE B
        (2026-08-14, ver
        technical_services/.AGENT/CROSS_DOMAIN_ASSIGNMENT_AUDIT_FINAL.md):
        mismo patron que RentalOperationCommands._set_dispatcher_availability()/
        ServiceOperationCommands._set_technician_availability()."""
        if dispatcher is None:
            return
        if dispatcher.is_available != is_available:
            dispatcher.is_available = is_available
            dispatcher.save(update_fields=['is_available', 'updated_at'])

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
        same_dispatcher = shipment.assigned_dispatcher_id == dispatcher.id
        if not dispatcher.is_active or (not same_dispatcher and not dispatcher.is_available):
            raise ValueError('El despachador seleccionado no esta disponible.')

        # Cross-domain audit FASE B (2026-08-14, ver
        # technical_services/.AGENT/CROSS_DOMAIN_ASSIGNMENT_AUDIT_FINAL.md):
        # este es ahora el unico lugar que marca al despachador ocupado para
        # envios de Shop -- antes ningun escritor lo hacia (mismo gap que
        # tenia RentalOperationCommands.assign_dispatcher() hasta esa
        # auditoria), y luego operations.OperationCommands.assign_resource()
        # lo hacia de forma aislada, sin relacion con este Shipment.
        previous_dispatcher = shipment.assigned_dispatcher
        if previous_dispatcher and previous_dispatcher.id != dispatcher.id:
            AssignmentCommands._set_dispatcher_availability(previous_dispatcher, True)
        AssignmentCommands._set_dispatcher_availability(dispatcher, False)

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
