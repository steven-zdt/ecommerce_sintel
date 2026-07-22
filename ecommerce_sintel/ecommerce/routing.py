from django.urls import path
from ecommerce.consumers import NotificationConsumer
from support.routing import support_websocket_patterns
from operations.routing import operations_websocket_patterns

websocket_urlpatterns = [
    path('ws/', NotificationConsumer.as_asgi()),
    path('ws', NotificationConsumer.as_asgi()),
] + support_websocket_patterns + operations_websocket_patterns
