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
from marketing.services.meta_selectors import MetaCampaignSelector
from marketing.integrations.meta.exceptions import (
    MetaApiError,
    MetaApiTransientError,
    MetaAuthError,
    MetaConfigError,
    MetaRateLimitError,
)
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


# --- FASE 9: Meta Ads READ (integracion Meta Business) ----------------------
#
# Expone MetaCampaignSelector (solo lectura) al ai_engine por la misma frontera
# /api/v1/internal/ai/* que el resto. Nginx no proxea /internal/ hacia afuera.
# Todas admin-only. Ninguna escritura aqui -- pause/resume/budget llegan en las
# FASE 16-18 detras de Policy Layer + aprobacion humana.

def _meta_error_response(exc: MetaApiError) -> Response:
    if isinstance(exc, MetaConfigError):
        return Response(
            {"error": "Meta Ads no esta configurado.", "detail": str(exc), "configured": False},
            status=503,
        )
    if isinstance(exc, MetaAuthError):
        return Response({"error": "Meta rechazo las credenciales de la cuenta publicitaria.", "detail": str(exc)}, status=502)
    if isinstance(exc, (MetaRateLimitError, MetaApiTransientError)):
        return Response({"error": "Meta no respondio a tiempo. Reintentar mas tarde.", "detail": str(exc)}, status=502)
    return Response({"error": "Error consultando Meta Ads.", "detail": str(exc)}, status=502)


class AiMetaCampaignsView(APIView):
    """GET /api/v1/internal/ai/marketing/meta/campaigns/ -> lista de campanas. Solo admin."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        limit = min(int(request.query_params.get("limit", 50)), 100)
        effective_status = request.query_params.getlist("effective_status") or None
        try:
            return Response(MetaCampaignSelector.get_campaigns(effective_status=effective_status, limit=limit))
        except MetaApiError as exc:
            return _meta_error_response(exc)


class AiMetaCampaignDetailView(APIView):
    """GET /api/v1/internal/ai/marketing/meta/campaign/<campaign_id>/ -> campana + adsets + insights. Solo admin."""
    permission_classes = [IsAdminUser]

    def get(self, request, campaign_id: str):
        try:
            return Response(MetaCampaignSelector.get_campaign_detail(campaign_id))
        except MetaApiError as exc:
            return _meta_error_response(exc)


class AiMetaInsightsView(APIView):
    """GET /api/v1/internal/ai/marketing/meta/insights/?object_id=&level=&date_preset= -> insights. Solo admin."""
    permission_classes = [IsAdminUser]

    _ALLOWED_LEVELS = {"account", "campaign", "adset", "ad"}
    _ALLOWED_PRESETS = {
        "today", "yesterday", "this_week_mon_today", "last_7d", "last_14d",
        "last_28d", "last_30d", "last_90d", "this_month", "last_month",
    }

    def get(self, request):
        object_id = request.query_params.get("object_id", "").strip()
        if not object_id:
            return Response({"error": "object_id es obligatorio."}, status=400)
        level = request.query_params.get("level", "campaign").strip()
        if level not in self._ALLOWED_LEVELS:
            return Response({"error": f"level invalido. Opciones: {sorted(self._ALLOWED_LEVELS)}"}, status=400)
        date_preset = request.query_params.get("date_preset", "last_30d").strip()
        if date_preset not in self._ALLOWED_PRESETS:
            return Response({"error": f"date_preset invalido. Opciones: {sorted(self._ALLOWED_PRESETS)}"}, status=400)
        try:
            return Response(MetaCampaignSelector.get_insights(
                object_id=object_id, level=level, date_preset=date_preset,
            ))
        except MetaApiError as exc:
            return _meta_error_response(exc)


class AiMetaAccountSummaryView(APIView):
    """GET /api/v1/internal/ai/marketing/meta/account-summary/?date_preset= -> resumen de la cuenta. Solo admin."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        date_preset = request.query_params.get("date_preset", "last_30d").strip()
        if date_preset not in AiMetaInsightsView._ALLOWED_PRESETS:
            return Response({"error": f"date_preset invalido. Opciones: {sorted(AiMetaInsightsView._ALLOWED_PRESETS)}"}, status=400)
        try:
            return Response(MetaCampaignSelector.get_account_summary(date_preset=date_preset))
        except MetaApiError as exc:
            return _meta_error_response(exc)
