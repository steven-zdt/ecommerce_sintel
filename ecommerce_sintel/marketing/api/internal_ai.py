"""
Endpoints internos de Marketing para el AI Engine (Fases 2 y 8 AI Core).

Fase 2 (read, cualquier usuario activo):
  - AiActivePromosView: ofertas flash activas.

Fase 8 (read, solo admin):
  - AiMarketingDashboardView: dashboard consolidado del negocio.
  - AiStaleStockAlertsView: alertas de stock inactivo por dominio.
  - AiCampaignTargetsView: usuarios objetivo para campanas de reactivacion.
  - AiPersonalRecommendationView: perfil + recomendacion personalizada del
    usuario autenticado (cross-selling / up-selling basado en CRM context).

Restriccion: PersonalOffer queda fuera (gap #5 del plan).
"""
from rest_framework.views import APIView
from rest_framework.response import Response

from marketing.services.selectors import MarketingSelector
from users.api.permissions import IsAuthenticatedActiveUser, IsAdminUser

MAX_LIST_LIMIT = 20


def _offer_target(offer) -> dict | None:
    if offer.variant_id:
        return {"type": "product", "uuid": str(offer.variant.uuid), "name": offer.variant.product.name}
    if offer.service_variant_id:
        return {"type": "service", "uuid": str(offer.service_variant.uuid), "name": offer.service_variant.service.name}
    if offer.equipment_variant_id:
        return {"type": "equipment", "uuid": str(offer.equipment_variant.uuid), "name": offer.equipment_variant.equipment.name}
    return None


class AiActivePromosView(APIView):
    """GET /api/v1/internal/ai/marketing/promos/ -> flash offers activas ahora."""
    permission_classes = [IsAuthenticatedActiveUser]

    def get(self, request):
        limit = min(int(request.query_params.get("limit", 10)), MAX_LIST_LIMIT)
        offers = MarketingSelector.list_active_flash_offers()[:limit]
        return Response({"promotions": [
            {
                "uuid": str(offer.uuid),
                "name": offer.name,
                "description": offer.description,
                "discount_percentage": str(offer.discount_percentage),
                "start_time": offer.start_time.isoformat(),
                "end_time": offer.end_time.isoformat(),
                "target": _offer_target(offer),
            }
            for offer in offers
        ]})


# --- Fase 8: admin-only ------------------------------------------------------

class AiMarketingDashboardView(APIView):
    """GET /api/v1/internal/ai/marketing/dashboard/ -> dashboard consolidado. Solo admin."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        data = MarketingSelector.get_consolidated_dashboard()
        return Response(data)


class AiStaleStockAlertsView(APIView):
    """GET /api/v1/internal/ai/marketing/stale-stock/ -> alertas stock inactivo. Solo admin."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get("days", 30))
        data = MarketingSelector.get_stale_stock_alerts(days=days)
        return Response({"days": days, **data})


class AiCampaignTargetsView(APIView):
    """GET /api/v1/internal/ai/marketing/campaign-targets/ -> usuarios objetivo. Solo admin."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        targets = MarketingSelector.get_campaign_targets_for_stale_products()
        return Response({"count": len(targets), "targets": targets})


class AiPersonalRecommendationView(APIView):
    """
    GET /api/v1/internal/ai/marketing/recommendation/
    Perfil de marketing del usuario autenticado + recomendacion basada en su preferencia.
    """
    permission_classes = [IsAuthenticatedActiveUser]

    _PREFERENCE_HINT = {
        "products":  "El cliente prefiere comprar productos. Ofrecer novedades de shop y flash offers de variantes.",
        "services":  "El cliente contrata servicios tecnicos. Ofrecer paquetes o servicios complementarios.",
        "renting":   "El cliente alquila equipos frecuentemente. Ofrecer disponibilidad de nuevos equipos o tarifas preferenciales.",
    }

    def get(self, request):
        profile = MarketingSelector.get_user_marketing_profile(request.user)
        preference = profile.get("preference", "products")
        profile["recommendation_hint"] = self._PREFERENCE_HINT.get(preference, "")
        active_offers = MarketingSelector.list_active_flash_offers()
        type_map = {"products": "product", "services": "service", "renting": "equipment"}
        target_type = type_map.get(preference, "product")
        relevant = []
        for offer in active_offers[:5]:
            target = _offer_target(offer)
            if target and target["type"] == target_type:
                relevant.append({"name": offer.name, "discount": str(offer.discount_percentage)})
        profile["relevant_offers"] = relevant
        return Response(profile)
