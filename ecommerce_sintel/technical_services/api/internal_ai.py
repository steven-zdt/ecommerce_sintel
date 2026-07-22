"""
Endpoint interno read-only para el AI Engine (Fase 2 AI Core).

ServiceOperationSelector NO filtra por dueno (gap #4 del plan) -- este
endpoint agrega el owner-check el mismo (filter(order__user=...) /
verificacion de order.user_id), exactamente como exige la tabla de Tools
de la Fase 2 (`[owner-check manual]`).
"""
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response

from orders.services.selectors import OrderSelector
from technical_services.services.operations import ServiceOperationSelector
from users.api.permissions import IsAuthenticatedActiveUser

MAX_LIST_LIMIT = 20


def _operation_to_dict(operation) -> dict:
    technician = operation.technician
    return {
        'order_uuid': str(operation.order.uuid),
        'status': operation.status,
        'status_label': operation.get_status_display(),
        'scheduled_date': operation.scheduled_date.isoformat() if operation.scheduled_date else None,
        'scheduled_time': operation.scheduled_time.isoformat() if operation.scheduled_time else None,
        'technician': technician.get_full_name() if technician else None,
        'completed_at': operation.completed_at.isoformat() if operation.completed_at else None,
    }


class AiServiceStatusView(APIView):
    """
    GET /api/v1/internal/ai/services/              -> operaciones de servicio del usuario
    GET /api/v1/internal/ai/services/?order=<uuid> -> la operacion de esa orden
    """
    permission_classes = [IsAuthenticatedActiveUser]

    def get(self, request):
        order_uuid = request.query_params.get('order', '').strip()
        if order_uuid:
            try:
                order = OrderSelector.get_by_uuid(order_uuid)
            except Exception:
                raise Http404('Orden no encontrada.')
            if order.user_id != request.user.id:
                raise Http404('Orden no encontrada.')
            operation = getattr(order, 'service_operation', None)
            if operation is None:
                return Response({'operation': None, 'detail': 'La orden no tiene servicio tecnico asociado.'})
            return Response({'operation': _operation_to_dict(operation)})

        limit = min(int(request.query_params.get('limit', 5)), MAX_LIST_LIMIT)
        operations = (
            ServiceOperationSelector.queryset()
            .filter(order__user=request.user)
            .order_by('-created_at')[:limit]
        )
        return Response({'operations': [_operation_to_dict(op) for op in operations]})
