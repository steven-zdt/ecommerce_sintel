from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from users.api.permissions import IsAdminUser
from orders.models import Order
from users.models import User
from shop.models import Product


class DashboardMetricsView(APIView):
    """
    Retorna las metricas principales del dashboard administrativo.

    Migrado desde coreui.api.views (2026-05-14).
    Endpoint: GET /api/v1/dashboard/metrics/
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        summary="Metricas del dashboard administrativo",
        responses={200: {
            'type': 'object',
            'properties': {
                'total_sales':     {'type': 'number'},
                'orders_count':    {'type': 'integer'},
                'customers_count': {'type': 'integer'},
                'products_count':  {'type': 'integer'},
                'recent_orders':   {'type': 'array'},
            }
        }}
    )
    def get(self, request):
        total_sales = (
            Order.objects
            .filter(status__in=['paid', 'delivered'])
            .aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        )
        orders_count    = Order.objects.count()
        customers_count = User.objects.filter(is_active=True, is_staff=False).count()
        products_count  = Product.objects.filter(is_active=True).count()

        recent_orders = list(
            Order.objects
            .order_by('-created_at')
            .values('id', 'uuid', 'status', 'total_amount', 'created_at')[:5]
        )
        for o in recent_orders:
            o['uuid']         = str(o['uuid'])
            o['created_at']   = o['created_at'].isoformat()
            o['total_amount'] = str(o['total_amount'])

        return Response({
            'total_sales':     total_sales,
            'orders_count':    orders_count,
            'customers_count': customers_count,
            'products_count':  products_count,
            'recent_orders':   recent_orders,
        })
