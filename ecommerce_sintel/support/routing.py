from django.urls import path
from support.consumers import SupportChatConsumer

support_websocket_patterns = [
    path('ws/support/chat/', SupportChatConsumer.as_asgi()),
]
