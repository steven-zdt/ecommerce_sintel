from django.db import transaction
from django.utils import timezone
from orders.models import Order, Shipment, ShipmentTrackingEvent

class ShipmentTrackingCommands:
    @staticmethod
    @transaction.atomic
    def create_tracking_point(
        order: Order,
        lat: float,
        lng: float,
        accuracy: float = 0.0,
        created_by=None,
        shipment: Shipment | None = None,
        timestamp=None,
        metadata: dict | None = None,
    ) -> ShipmentTrackingEvent:
        return ShipmentTrackingEvent.objects.create(
            order=order,
            shipment=shipment,
            lat=lat,
            lng=lng,
            accuracy=accuracy,
            timestamp=timestamp or timezone.now(),
            created_by=created_by,
            metadata=metadata or {},
        )

    @staticmethod
    def list_tracking_points(order: Order):
        return ShipmentTrackingEvent.objects.filter(order=order).order_by('timestamp')
