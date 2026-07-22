"""
Marketing Selector - Intelligence Dashboard
Consumes SummaryProviders from each business app using the explicit "Pull" pattern.
No signals, no direct model imports from multiple apps in commands — only via Providers.
"""
from django.conf import settings
from django.db.models import QuerySet, Sum, Count
from django.utils import timezone
from marketing.models import MarketingCampaign, FlashOffer, PersonalOffer, AgentRun
from orders.models import Order, OrderItem

# Pull-based imports: each app exposes its own SummaryProvider
from shop.services.summary import ShopSummaryProvider
from renting.services.summary import RentingSummaryProvider
from technical_services.services.summary import ServicesSummaryProvider


class MarketingSelector:
    CAMPAIGN_LIST_FIELDS = ('id', 'uuid', 'title', 'scheduled_at', 'is_completed', 'created_at')
    OFFER_LIST_FIELDS = ('id', 'uuid', 'name', 'discount_percentage', 'start_time', 'end_time', 'is_active')

    @staticmethod
    def list_campaigns_for_admin() -> QuerySet:
        return MarketingCampaign.objects.all().order_by('-created_at')

    @staticmethod
    def get_campaign_by_uuid(uuid: str) -> MarketingCampaign:
        return MarketingCampaign.objects.prefetch_related('logs').get(uuid=uuid)

    @staticmethod
    def list_flash_offers() -> QuerySet:
        return FlashOffer.objects.filter(is_active=True)

    @staticmethod
    def list_active_flash_offers() -> QuerySet:
        """Flash offers activas dentro de su ventana de tiempo, con datos de variante incluidos."""
        now = timezone.now()
        return (
            FlashOffer.objects
            .filter(is_active=True, start_time__lte=now, end_time__gte=now)
            .select_related(
                'variant__product',
                'service_variant__service',
                'equipment_variant__equipment',
            )
            .prefetch_related('variant__product__images')
            .order_by('end_time')
        )

    @staticmethod
    def list_agent_runs() -> QuerySet:
        return AgentRun.objects.all().order_by('-created_at')

    @staticmethod
    def get_consolidated_dashboard() -> dict:
        """
        Consolidates statistics from all business apps.
        Designed for the Marketing Dashboard and Campaign Decision Engine.
        """
        total_revenue = (
            Order.objects.filter(status='paid')
            .aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        )
        total_orders = Order.objects.count()
        paid_orders = Order.objects.filter(status='paid').count()
        conversion_rate = round((paid_orders / total_orders) * 100, 2) if total_orders > 0 else 0

        return {
            'platform_overview': {
                'total_revenue': total_revenue,
                'total_orders': total_orders,
                'paid_orders': paid_orders,
                'conversion_rate_pct': conversion_rate,
            },
            'shop': ShopSummaryProvider.get_summary(),
            'renting': RentingSummaryProvider.get_summary(),
            'technical_services': ServicesSummaryProvider.get_summary(),
        }

    @staticmethod
    def get_stale_stock_alerts(days: int = 30) -> dict:
        """
        Aggregates stale stock signals from all apps for campaign triggers.
        """
        shop_data = ShopSummaryProvider.get_summary()
        renting_data = RentingSummaryProvider.get_summary()
        services_data = ServicesSummaryProvider.get_summary()

        return {
            'shop_stale_count': shop_data['stale_stock_count'],
            'shop_stale_ids': shop_data['stale_stock_record_ids'],
            'renting_stale_count': renting_data['stale_equipment_count'],
            'renting_stale_ids': renting_data['stale_equipment_record_ids'],
            'services_stale_count': services_data['stale_services_count'],
            'services_stale_ids': services_data['stale_service_record_ids'],
        }

    @staticmethod
    def get_user_marketing_profile(user) -> dict:
        """
        Analiza el historial completo de un usuario para personalización.
        """
        orders = Order.objects.filter(user=user, status='paid')
        total_spent = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

        product_count = OrderItem.objects.filter(order__user=user, variant__isnull=False).count()
        service_count = OrderItem.objects.filter(order__user=user, service_variant__isnull=False).count()
        rental_count = OrderItem.objects.filter(order__user=user, equipment_variant__isnull=False).count()

        preference = max(
            [('products', product_count), ('services', service_count), ('renting', rental_count)],
            key=lambda x: x[1]
        )[0]

        return {
            'user_uuid': str(user.uuid),
            'total_spent': total_spent,
            'orders_count': orders.count(),
            'preference': preference,
            'product_purchases': product_count,
            'service_purchases': service_count,
            'rental_purchases': rental_count,
        }

    @staticmethod
    def get_campaign_targets_for_stale_products() -> list:
        """
        Returns users who have shown interest in stale product categories.
        Useful for triggering targeted discounts or flash offers.
        """
        # Identify users who bought products that are now stale
        stale_data = MarketingSelector.get_stale_stock_alerts()
        stale_shop_ids = stale_data['shop_stale_ids']
        stale_renting_ids = stale_data['renting_stale_ids']

        # Get users who interacted with those stale stock records
        targeted_users = (
            OrderItem.objects.filter(
                order__status='paid',
                variant__isnull=False
            ).values('order__user__email', 'order__user__uuid')
            .distinct()
            .annotate(count=Count('order__user__uuid'))
        )
        return list(targeted_users)
