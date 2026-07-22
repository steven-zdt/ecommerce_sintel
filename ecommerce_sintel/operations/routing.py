from django.urls import re_path
from operations.consumers import OperationTrackingConsumer

operations_websocket_patterns = [
    re_path(
        r'^ws/operations/(?P<ticket_uuid>[0-9a-f-]+)/$',
        OperationTrackingConsumer.as_asgi(),
    ),
]
