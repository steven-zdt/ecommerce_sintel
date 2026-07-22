"""
Endpoint interno read-only para el AI Engine (Fase 2 AI Core).

Envuelve InventorySelector.get_stock_for_variant (fuente de verdad:
InventoryTransaction.balance_after con cache de 5 min -- NO el campo
variant.stock legacy). La variante se resuelve por tipo via el selector
get_by_uuid de la app duena correspondiente.
"""
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response

from inventory.services.selectors import InventorySelector
from users.api.permissions import IsAuthenticatedActiveUser


def _resolve_variant(variant_type: str, variant_uuid: str):
    if variant_type == 'product':
        from shop.services.selectors import ProductVariantSelector
        return ProductVariantSelector.get_by_uuid(variant_uuid)
    if variant_type == 'equipment':
        from renting.services.selectors import EquipmentVariantSelector
        return EquipmentVariantSelector.get_by_uuid(variant_uuid)
    if variant_type == 'service':
        from technical_services.services.selectors import ServiceVariantSelector
        return ServiceVariantSelector.get_by_uuid(variant_uuid)
    return None


class AiStockCheckView(APIView):
    """
    GET /api/v1/internal/ai/inventory/stock/?variant=<uuid>&type=product|equipment|service
    """
    permission_classes = [IsAuthenticatedActiveUser]

    def get(self, request):
        variant_uuid = request.query_params.get('variant', '').strip()
        variant_type = request.query_params.get('type', 'product').strip().lower()
        if not variant_uuid:
            return Response({'error': 'Parametro variant (uuid) requerido.'}, status=400)
        try:
            variant = _resolve_variant(variant_type, variant_uuid)
        except Exception:
            raise Http404('Variante no encontrada.')
        if variant is None:
            return Response({'error': "Parametro type debe ser 'product', 'equipment' o 'service'."}, status=400)

        stock = InventorySelector.get_stock_for_variant(variant)
        return Response({
            'variant_uuid': variant_uuid,
            'type': variant_type,
            'sku': getattr(variant, 'sku', None),
            'stock': stock,
        })
