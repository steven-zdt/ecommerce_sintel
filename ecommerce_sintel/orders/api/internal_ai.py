"""
Endpoint interno read-only para el AI Engine (Fase 2 AI Core).

Envuelve OrderSelector -- cero logica de negocio nueva, solo seleccion de
campos para respuestas compactas (presupuesto de tokens del LLM). Ruteado
bajo /api/v1/internal/ai/ (ver ecommerce/internal_ai_urls.py); exige JWT de
un usuario activo como todo endpoint del puente (Fase 1).
"""
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response

from orders.services.selectors import OrderSelector
from users.api.permissions import IsAuthenticatedActiveUser

MAX_LIST_LIMIT = 20


def _order_to_dict(order) -> dict:
    shipment = getattr(order, 'shipment', None)
    return {
        'uuid': str(order.uuid),
        'status': order.status,
        'status_label': order.get_status_display(),
        'total_amount': str(order.total_amount),
        'discount_amount': str(order.discount_amount),
        'payment_method': order.payment_method,
        'created_at': order.created_at.isoformat(),
        'items': [
            {
                'item_name': item.item_name,
                'sku': item.sku,
                'quantity': item.quantity,
                'price': str(item.price),
            }
            for item in order.items.all()
        ],
        'tracking_number': getattr(shipment, 'tracking_number', None),
        'shipment_status': getattr(shipment, 'status', None),
    }


class AiOrderStatusView(APIView):
    """
    GET /api/v1/internal/ai/orders/            -> ultimas ordenes del usuario
    GET /api/v1/internal/ai/orders/?uuid=<u>   -> una orden (owner-check manual,
                                                  OrderSelector.get_by_uuid no filtra por dueno)
    """
    permission_classes = [IsAuthenticatedActiveUser]

    def get(self, request):
        order_uuid = request.query_params.get('uuid', '').strip()
        if order_uuid:
            try:
                order = OrderSelector.get_by_uuid(order_uuid)
            except Exception:
                raise Http404('Orden no encontrada.')
            if order.user_id != request.user.id:
                # Owner-check manual exigido por el plan (Fase 2, tabla de Tools)
                raise Http404('Orden no encontrada.')
            return Response({'order': _order_to_dict(order)})

        limit = min(int(request.query_params.get('limit', 5)), MAX_LIST_LIMIT)
        orders = OrderSelector.list_for_user(request.user)[:limit]
        return Response({'orders': [_order_to_dict(o) for o in orders]})
