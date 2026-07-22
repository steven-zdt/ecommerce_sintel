from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from users.api.permissions import IsAdminUser
from marketing.models import MarketingCampaign, FlashOffer, AgentRun
from marketing.services import MarketingSelector
from marketing.api.serializers import (
    MarketingCampaignSerializer,
    FlashOfferSerializer,
    AgentRunSerializer,
    ConsolidatedDashboardSerializer
)

class MarketingCampaignViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    queryset = MarketingSelector.list_campaigns_for_admin()
    serializer_class = MarketingCampaignSerializer
    lookup_field = 'uuid'

class FlashOfferViewSet(viewsets.ReadOnlyModelViewSet):
    """Ofertas flash activas. Lectura publica (vitrina de la tienda)."""
    permission_classes = [permissions.AllowAny]
    queryset = MarketingSelector.list_flash_offers()
    serializer_class = FlashOfferSerializer
    lookup_field = 'uuid'

class AgentRunViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminUser]
    queryset = MarketingSelector.list_agent_runs()
    serializer_class = AgentRunSerializer
    lookup_field = 'uuid'

class DashboardViewSet(viewsets.ViewSet):
    """
    Consolidated Intelligence Dashboard for Marketing.
    """
    permission_classes = [IsAdminUser]

    @extend_schema(responses={200: ConsolidatedDashboardSerializer})
    def list(self, request):
        data = MarketingSelector.get_consolidated_dashboard()
        serializer = ConsolidatedDashboardSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)
