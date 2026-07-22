"""
Endpoint interno read-only para el AI Engine (Fase 2 AI Core).

Reusa la MISMA query owner-safe de WompiPaymentViewSet.transaction_status
(Q(order__user) | Q(rental_request__user)) pero SIN el side-effect de
_sync_wompi_status -- decision explicita del plan ("reusar la misma query,
no el endpoint HTTP"): una consulta del AI nunca dispara llamadas a Wompi.

NOTA (gap #2 del plan, NO resuelto aqui por diseno): solo se expone
status/status_label -- el motivo real de un rechazo vive en
TransactionEvent.raw_payload (admin-only) y no se filtra al cliente.
"""
from django.db.models import Q
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response

from payment.models import Transaction
from users.api.permissions import IsAuthenticatedActiveUser

MAX_LIST_LIMIT = 10

_STATUS_LABELS = dict(Transaction.STATUS_CHOICES)


def _tx_to_dict(tx) -> dict:
    return {
        'transaction_uuid': str(tx.uuid),
        'status': tx.status,
        'status_label': _STATUS_LABELS.get(tx.status, tx.status),
        'payment_method_type': tx.payment_method_type,
        'amount_in_cents': tx.amount_in_cents,
        'currency': tx.currency,
        'created_at': tx.created_at.isoformat(),
        'order_uuid': str(tx.order.uuid) if tx.order_id else None,
        'rental_uuid': str(tx.rental_request.uuid) if tx.rental_request_id else None,
    }


class AiPaymentStatusView(APIView):
    """
    GET /api/v1/internal/ai/payments/           -> ultimas transacciones del usuario
    GET /api/v1/internal/ai/payments/?tx=<uuid> -> una transaccion (owner-safe)
    """
    permission_classes = [IsAuthenticatedActiveUser]

    def get(self, request):
        owner_filter = Q(order__user=request.user) | Q(rental_request__user=request.user)
        tx_uuid = request.query_params.get('tx', '').strip()
        if tx_uuid:
            try:
                tx = (
                    Transaction.objects
                    .select_related('order', 'rental_request')
                    .get(owner_filter, uuid=tx_uuid)
                )
            except Transaction.DoesNotExist:
                raise Http404('Transaccion no encontrada.')
            return Response({'transaction': _tx_to_dict(tx)})

        limit = min(int(request.query_params.get('limit', 5)), MAX_LIST_LIMIT)
        txs = (
            Transaction.objects
            .select_related('order', 'rental_request')
            .filter(owner_filter)
            .order_by('-created_at')[:limit]
        )
        return Response({'transactions': [_tx_to_dict(t) for t in txs]})
