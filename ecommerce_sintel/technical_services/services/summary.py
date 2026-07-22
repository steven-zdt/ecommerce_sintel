"""
Technical Services Summary Provider
Exposes business statistics for consumption by marketing and other apps.
Pattern: Pull-based, decoupled. No signals, no inventory dependency.
Disponibilidad temporal gestionada via ServiceBooking.
"""
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from technical_services.models import ServiceVariant, ServiceBooking
from orders.models import OrderItem


class ServicesSummaryProvider:

    @staticmethod
    def get_summary() -> dict:
        base_qs = ServiceVariant.objects.filter(is_deleted=False)

        total_service_variants: int = base_qs.count()
        available: int = base_qs.filter(is_active=True, service__is_active=True).count()
        unavailable: int = base_qs.filter(is_active=False).count()

        now = timezone.now()
        active_bookings: int = ServiceBooking.objects.filter(
            status__in=[ServiceBooking.STATUS_SCHEDULED, ServiceBooking.STATUS_ACTIVE],
            start_time__lte=now,
            end_time__gt=now,
        ).count()

        top_services = (
            OrderItem.objects.filter(service_variant__isnull=False, order__status='paid')
            .values('sku', 'item_name')
            .annotate(units_sold=Sum('quantity'))
            .order_by('-units_sold')[:5]
        )

        cutoff_date = now - timedelta(days=30)
        recent_variant_uuids = OrderItem.objects.filter(
            service_variant__isnull=False,
            created_at__gt=cutoff_date,
        ).values_list('service_variant__uuid', flat=True).distinct()

        stale_variants = base_qs.filter(
            is_active=True,
            service__is_active=True,
        ).exclude(uuid__in=recent_variant_uuids)

        return {
            'app': 'technical_services',
            'total_service_variants': total_service_variants,
            'available': available,
            'unavailable': unavailable,
            'active_bookings': active_bookings,
            'top_selling_services': list(top_services),
            'stale_services_count': stale_variants.count(),
            'stale_service_record_ids': list(stale_variants.values_list('uuid', flat=True)),
        }
