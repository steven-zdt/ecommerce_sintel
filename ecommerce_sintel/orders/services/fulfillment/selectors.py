from django.db.models import Q, QuerySet
from django.utils import timezone
from orders.models import Order, Shipment, ShipmentTimeline

class FulfillmentSelector:
    @staticmethod
    def list_fulfillment_orders() -> QuerySet:
        return Order.objects.filter(status__in=[
            Order.STATUS_PREPARING,
            Order.STATUS_READY_FOR_DISPATCH,
            Order.STATUS_ASSIGNED,
            Order.STATUS_PICKED_UP,
            Order.STATUS_IN_TRANSIT,
            Order.STATUS_OUT_FOR_DELIVERY,
        ], is_deleted=False)

    @staticmethod
    def get_order_timeline(order: Order) -> QuerySet:
        return ShipmentTimeline.objects.filter(order=order).order_by('created_at')

    # ── Bandeja operativa de Shop Operations (2026-07-09) ────────────────────

    @staticmethod
    def shipment_queryset() -> QuerySet:
        return (
            Shipment.objects.filter(is_deleted=False)
            .select_related(
                'order__user', 'order__shipping_address',
                'dispatch_center', 'carrier', 'driver',
                'assigned_dispatcher__user',
            )
            .prefetch_related('order__items', 'timeline__created_by')
        )

    @staticmethod
    def list_shipments_for_admin(*, status='', search='', date_from=None, date_to=None) -> QuerySet:
        """
        Bandeja operativa (Fase 4): solo ordenes con Shipment ya existen porque
        ensure_shipment_for_order() solo se llama tras pago confirmado -- nunca
        hay que filtrar manualmente "pendientes de pago", ya estan excluidas por
        construccion (no tienen Shipment).
        """
        qs = FulfillmentSelector.shipment_queryset()
        if status:
            qs = qs.filter(status=status)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        if search:
            qs = qs.filter(
                Q(shipment_number__icontains=search)
                | Q(tracking_code__icontains=search)
                | Q(order__uuid__icontains=search)
                | Q(order__user__email__icontains=search)
            )
        return qs.order_by('-created_at')

    @staticmethod
    def get_shipment_by_uuid(uuid):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(FulfillmentSelector.shipment_queryset(), uuid=uuid)

    @staticmethod
    def dashboard_metrics() -> dict:
        today = timezone.localdate()
        qs = Shipment.objects.filter(is_deleted=False)
        active_statuses = [
            Shipment.STATUS_PREPARING, Shipment.STATUS_READY_FOR_DISPATCH,
            Shipment.STATUS_ASSIGNED, Shipment.STATUS_PICKED_UP,
            Shipment.STATUS_IN_TRANSIT, Shipment.STATUS_OUT_FOR_DELIVERY,
        ]
        completed_qs = qs.filter(
            status__in=[Shipment.STATUS_DELIVERED, Shipment.STATUS_COMPLETED],
            actual_delivery__isnull=False,
        ).only('actual_delivery', 'created_at')
        durations = [
            (s.actual_delivery - s.created_at).total_seconds() / 3600 for s in completed_qs
        ]
        avg_hours = round(sum(durations) / len(durations), 1) if durations else None
        sla_target_hours = 72
        within_sla = len([d for d in durations if d <= sla_target_hours])
        sla_pct = round((within_sla / len(durations)) * 100, 1) if durations else None

        from operations.models import DispatcherProfile
        return {
            'pending_preparation': qs.filter(status=Shipment.STATUS_PREPARING).count(),
            'pending_packing': qs.filter(status=Shipment.STATUS_READY_FOR_DISPATCH).count(),
            'dispatches_today': qs.filter(
                status__in=[Shipment.STATUS_PICKED_UP, Shipment.STATUS_IN_TRANSIT],
                updated_at__date=today,
            ).count(),
            'deliveries_today': qs.filter(status=Shipment.STATUS_DELIVERED, actual_delivery__date=today).count(),
            'dispatchers_active': DispatcherProfile.objects.filter(is_available=True, is_active=True).count(),
            'delayed': qs.filter(
                status__in=active_statuses, estimated_delivery__lt=timezone.now(),
            ).count(),
            'avg_fulfillment_hours': avg_hours,
            'sla_percentage': sla_pct,
            'incidents': qs.filter(status__in=[Shipment.STATUS_FAILED_DELIVERY, Shipment.STATUS_LOST]).count(),
        }
