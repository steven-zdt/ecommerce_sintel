"""
Shop Summary Provider
Exposes business statistics for consumption by marketing and other apps.
Pattern: Pull-based, decoupled. No signals used.
"""
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from shop.models import Product, ProductVariant
from orders.models import OrderItem
from inventory.models import StockRecord
from django.contrib.contenttypes.models import ContentType


class ShopSummaryProvider:
    """
    Provides aggregated statistics about shop products for marketing.
    Called explicitly by marketing.services.selectors — never via signals.
    """

    @staticmethod
    def get_summary() -> dict:
        """
        Returns a comprehensive summary of the shop module.
        """
        product_ct = ContentType.objects.get_for_model(ProductVariant)
        stock_records = StockRecord.objects.filter(
            content_type=product_ct, is_active=True, is_deleted=False
        )

        total_variants = stock_records.count()
        in_stock = stock_records.filter(stock__gt=0).count()
        out_of_stock = stock_records.filter(stock=0).count()
        total_stock_units = stock_records.aggregate(total=Sum('stock'))['total'] or 0

        # Stale stock: variants with no EXIT transaction in the last 30 days
        threshold = timezone.now() - timedelta(days=30)
        stale_stock_ids = []
        for record in stock_records.filter(stock__gt=0):
            last_exit = record.transactions.filter(movement_type='EXIT').order_by('-created_at').first()
            if not last_exit or last_exit.created_at < threshold:
                stale_stock_ids.append(record.id)

        # Top selling products
        top_selling = (
            OrderItem.objects.filter(variant__isnull=False, order__status='paid')
            .values('sku', 'item_name')
            .annotate(units_sold=Sum('quantity'))
            .order_by('-units_sold')[:5]
        )

        return {
            'app': 'shop',
            'total_active_variants': total_variants,
            'in_stock': in_stock,
            'out_of_stock': out_of_stock,
            'total_stock_units': total_stock_units,
            'stale_stock_count': len(stale_stock_ids),
            'stale_stock_record_ids': stale_stock_ids,
            'top_selling_products': list(top_selling),
        }
