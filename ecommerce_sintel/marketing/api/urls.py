from django.urls import path, include
from rest_framework.routers import DefaultRouter
from marketing.api.views import (
    MarketingCampaignViewSet, 
    FlashOfferViewSet, 
    AgentRunViewSet,
    DashboardViewSet
)

router = DefaultRouter()
router.register(r'campaigns', MarketingCampaignViewSet, basename='marketing-campaign')
router.register(r'offers', FlashOfferViewSet, basename='flash-offer')
router.register(r'agent-runs', AgentRunViewSet, basename='agent-run')
router.register(r'dashboard', DashboardViewSet, basename='marketing-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]
