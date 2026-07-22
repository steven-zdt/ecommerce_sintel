"""
Renting Summary Provider
Exposes business statistics for consumption by marketing and other apps.
Pattern: Pull-based, decoupled. No signals. No external app dependencies.
"""
from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from orders.models import OrderItem
from renting.models import EquipmentVariant, RentalPeriod


class RentingSummaryProvider:

    @staticmethod
    def get_summary() -> dict:
        today = timezone.now().date()
        threshold = today - timedelta(days=30)

        # Variantes con stock fisico > 0
        total_variants = (
            EquipmentVariant.objects
            .filter(is_deleted=False, stock__gt=0)
            .count()
        )

        # Unidades actualmente en renta (periodo 'active')
        currently_rented = (
            RentalPeriod.objects
            .filter(status=RentalPeriod.STATUS_ACTIVE, is_deleted=False)
            .count()
        )

        # Variantes con stock pero sin ningun periodo en los ultimos 30 dias (obsoletas)
        stale_variant_ids = list(
            EquipmentVariant.objects
            .filter(is_deleted=False, stock__gt=0)
            .exclude(
                rental_periods__end_date__gte=threshold,
                rental_periods__is_deleted=False,
            )
            .values_list('id', flat=True)
        )

        # Top 5 equipos mas rentados (ordenes pagadas)
        top_rented = list(
            OrderItem.objects
            .filter(equipment_variant__isnull=False, order__status='paid')
            .values('sku', 'item_name')
            .annotate(units_rented=Sum('quantity'))
            .order_by('-units_rented')[:5]
        )

        return {
            'app': 'renting',
            'total_equipment_variants': total_variants,
            'currently_rented_out': currently_rented,
            'stale_equipment_count': len(stale_variant_ids),
            'stale_equipment_variant_ids': stale_variant_ids,
            'top_rented_equipment': top_rented,
        }
