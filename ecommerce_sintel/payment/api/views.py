# Shim de compatibilidad — implementación movida a wompi/online/api/views.py
from payment.online.api.views import WompiPaymentViewSet, _verify_wompi_event_signature  # noqa: F401

__all__ = ['WompiPaymentViewSet', '_verify_wompi_event_signature']
