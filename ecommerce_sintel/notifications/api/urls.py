from django.urls import path, include
from rest_framework.routers import DefaultRouter
from notifications.api.views import NotificationLogViewSet, UserNotificationPreferenceViewSet
from notifications.api.whatsapp_webhook import WhatsAppInboundWebhookView
from notifications.api.whatsapp_gateway_webhook import WhatsAppGatewayEventView

router = DefaultRouter()
router.register(r'logs',        NotificationLogViewSet,            basename='notification-logs')
router.register(r'preferences', UserNotificationPreferenceViewSet, basename='notification-preferences')

urlpatterns = [
    # Fase 7 AI Core: webhook entrante de WhatsApp (Meta Cloud API).
    # AllowAny como el webhook de Wompi; GET verifica, POST procesa async.
    path('whatsapp-webhook/', WhatsAppInboundWebhookView.as_view(), name='whatsapp-inbound-webhook'),
    # Fase 6 migracion Baileys: Event Bus whatsapp_gateway/ -> Django (auth
    # por X-Gateway-Token, no por usuario -- ver whatsapp_gateway_webhook.py).
    path('whatsapp-gateway-events/', WhatsAppGatewayEventView.as_view(), name='whatsapp-gateway-events'),
    path('', include(router.urls)),
]
