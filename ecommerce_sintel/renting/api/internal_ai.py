"""
Endpoints internos para el AI Engine (Fases 2, 4 y 8 AI Core).

Lectura: envuelven RentalRequestSelector / RentingSelector /
EquipmentVariantSelector / EquipmentBlockSelector. Escritura (Fase 4): envuelven
RentalRequestCommands.create_request/cancel_request reusando
RentalRequestInputSerializer (misma validacion que el wizard publico) y
las permission classes reales (IsBuyerOrAdmin). Toda escritura queda
auditada en security.SecurityEvent (AI_ACTION_EXECUTED). Ruteados bajo
/api/v1/internal/ai/ (ecommerce/internal_ai_urls.py).
"""
from datetime import date

from rest_framework import status as http_status
from rest_framework.views import APIView
from rest_framework.response import Response

from renting.api.serializers import RentalRequestInputSerializer
from renting.models import RentalRequest
from renting.services.commands import RentalRequestCommands
from renting.services.selectors import (
    EquipmentBlockSelector,
    EquipmentVariantSelector,
    RentalRequestSelector,
    RentingSelector,
)
from users.api.permissions import IsAuthenticatedActiveUser, IsBuyerOrAdmin, IsAdminUser

MAX_LIST_LIMIT = 20


from ecommerce.internal_ai_utils import log_ai_action as _log_ai_action


def _rental_to_dict(rental) -> dict:
    equipment = rental.equipment_variant.equipment
    return {
        'uuid': str(rental.uuid),
        'status': rental.status,
        'status_label': rental.get_status_display(),
        'equipment': equipment.name,
        'sku': rental.equipment_variant.sku,
        'start_date': rental.start_date.isoformat() if rental.start_date else None,
        'end_date': rental.end_date.isoformat() if rental.end_date else None,
        'quantity': rental.quantity,
        'rental_mode': rental.rental_mode,
        'grand_total': str(rental.grand_total) if rental.grand_total is not None else None,
        'created_at': rental.created_at.isoformat(),
    }


class AiRentalStatusView(APIView):
    """
    GET /api/v1/internal/ai/rentals/            -> ultimas solicitudes del usuario
    GET /api/v1/internal/ai/rentals/?uuid=<u>   -> una solicitud (el selector ya
                                                   filtra por dueno: get_by_uuid_for_user)
    """
    permission_classes = [IsAuthenticatedActiveUser]

    def get(self, request):
        rental_uuid = request.query_params.get('uuid', '').strip()
        if rental_uuid:
            rental = RentalRequestSelector.get_by_uuid_for_user(rental_uuid, request.user)
            return Response({'rental': _rental_to_dict(rental)})

        limit = min(int(request.query_params.get('limit', 5)), MAX_LIST_LIMIT)
        rentals = RentalRequestSelector.list_for_user(request.user)[:limit]
        return Response({'rentals': [_rental_to_dict(r) for r in rentals]})


class AiRentalAvailabilityView(APIView):
    """
    GET /api/v1/internal/ai/renting/availability/?variant=<uuid>&start=YYYY-MM-DD&end=YYYY-MM-DD&quantity=N

    Envuelve RentingSelector.check_availability (wrapper de AvailabilityEngine,
    modo dias). Solo lectura, sin PII.
    """
    permission_classes = [IsAuthenticatedActiveUser]

    def get(self, request):
        variant_uuid = request.query_params.get('variant', '').strip()
        start_raw = request.query_params.get('start', '').strip()
        end_raw = request.query_params.get('end', '').strip()
        if not (variant_uuid and start_raw and end_raw):
            return Response({'error': 'Parametros variant, start y end son requeridos.'}, status=400)
        try:
            start_date = date.fromisoformat(start_raw)
            end_date = date.fromisoformat(end_raw)
            quantity = int(request.query_params.get('quantity', 1))
        except ValueError:
            return Response({'error': 'Fechas YYYY-MM-DD y quantity entero.'}, status=400)

        variant = EquipmentVariantSelector.get_by_uuid(variant_uuid)
        available = RentingSelector.check_availability(variant.id, start_date, end_date, quantity)
        return Response({
            'variant_uuid': variant_uuid,
            'equipment': variant.equipment.name,
            'sku': variant.sku,
            'start_date': start_raw,
            'end_date': end_raw,
            'quantity': quantity,
            'available': available,
        })


class AiEquipmentSearchView(APIView):
    """
    GET /api/v1/internal/ai/renting/equipment/?q=<texto>&limit=N

    Envuelve RentingSelector.list_available_equipment(). El filtro por nombre
    y el select_related extra son presentacion (evitar N+1 al armar el dict),
    no logica de negocio.
    """
    permission_classes = [IsAuthenticatedActiveUser]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        limit = min(int(request.query_params.get('limit', 10)), MAX_LIST_LIMIT)
        equipments = RentingSelector.list_available_equipment().select_related('category', 'brand')
        if query:
            equipments = equipments.filter(name__icontains=query)
        results = []
        for equipment in equipments[:limit]:
            results.append({
                'uuid': str(equipment.uuid),
                'name': equipment.name,
                'category': equipment.category.name if equipment.category_id else None,
                'brand': equipment.brand.name if equipment.brand_id else None,
                'variants': [
                    {
                        'uuid': str(v.uuid),
                        'sku': v.sku,
                        'rental_price_per_day': str(v.rental_price_per_day) if v.rental_price_per_day is not None else None,
                        'rental_price_per_hour': str(v.rental_price_per_hour) if v.rental_price_per_hour is not None else None,
                        'stock': v.stock,
                    }
                    for v in equipment.variants.all()
                    if v.is_active and not v.is_deleted
                ],
            })
        return Response({'equipment': results})


class AiCreateRentalRequestView(APIView):
    """
    POST /api/v1/internal/ai/rentals/create/ (Fase 4)

    Envuelve RentalRequestCommands.create_request() con la MISMA validacion
    del wizard publico (RentalRequestInputSerializer) -- si faltan campos,
    el 400 lista exactamente cuales, y el AI se los pide al cliente.
    La solicitud queda en pending_payment (nunca bloquea agenda).
    """
    permission_classes = [IsBuyerOrAdmin]

    def post(self, request):
        serializer = RentalRequestInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            rental = RentalRequestCommands.create_request(
                user=request.user, validated_data=serializer.validated_data,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=http_status.HTTP_400_BAD_REQUEST)
        _log_ai_action(request, 'CreateRentalRequestTool', {'rental_uuid': str(rental.uuid)})
        rental = RentalRequestSelector.get_by_uuid_for_user(rental.uuid, request.user)
        return Response({'rental': _rental_to_dict(rental)}, status=http_status.HTTP_201_CREATED)


class AiCancelRentalView(APIView):
    """
    POST /api/v1/internal/ai/rentals/cancel/ {uuid} (Fase 4)

    Mismo guard de estados que RentalRequestViewSet.cancel: nunca se cancela
    una solicitud pagada/aprobada/en operacion (eso escala a soporte).
    """
    permission_classes = [IsBuyerOrAdmin]

    def post(self, request):
        rental_uuid = str(request.data.get('uuid', '')).strip()
        if not rental_uuid:
            return Response({'error': 'Parametro uuid requerido.'}, status=http_status.HTTP_400_BAD_REQUEST)
        rental = RentalRequestSelector.get_by_uuid_for_user(rental_uuid, request.user)
        if rental.status in (
            RentalRequest.STATUS_PAID, RentalRequest.STATUS_CONFIRMED, RentalRequest.STATUS_IN_OPERATION,
        ):
            return Response(
                {'error': 'No se puede cancelar una solicitud pagada, aprobada o en operacion. Escalar a soporte.'},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        rental = RentalRequestCommands.cancel_request(rental)
        _log_ai_action(request, 'CancelRentalTool', {'rental_uuid': str(rental.uuid)})
        return Response({'rental': _rental_to_dict(rental)})


# ─── Fase 8: mantenimiento preventivo (admin) ────────────────────────────────

class AiEquipmentMaintenanceView(APIView):
    """
    GET /api/v1/internal/ai/renting/maintenance/?equipment_uuid=<uuid>
    Lista los bloqueos activos de un equipo -- util para que el AI Core
    informe sobre mantenimiento preventivo/correctivo programado.
    Solo admin (informacion operativa interna, no visible al cliente).
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        equipment_uuid = request.query_params.get('equipment_uuid', '').strip()
        if not equipment_uuid:
            return Response({'error': 'equipment_uuid requerido.'}, status=400)

        blocks_qs = EquipmentBlockSelector.list_for_equipment(
            equipment_uuid=equipment_uuid,
            active_only=True,
        )
        return Response({
            'equipment_uuid': equipment_uuid,
            'active_blocks': [
                {
                    'uuid': str(b.uuid),
                    'status': b.status,
                    'reason': b.reason,
                    'created_at': b.created_at.isoformat(),
                    'variant_uuid': str(b.equipment_variant.uuid),
                    'variant_name': b.equipment_variant.name if hasattr(b.equipment_variant, 'name') else '',
                }
                for b in blocks_qs
            ],
            'count': blocks_qs.count(),
        })
