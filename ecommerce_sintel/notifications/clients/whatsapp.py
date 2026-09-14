"""
Shim de compatibilidad. El transporte real de WhatsApp Cloud API se movio a
marketing/integrations/meta/ (FASE 3 del plan de integracion Meta Business,
Documentacion/Arquitectura_general/META_BUSINESS_INTEGRATION_MASTER_PLAN.md).

Este modulo se mantiene porque notifications/tasks.py y ~20 tests importan
`WhatsAppClient` y sus excepciones desde aqui. El nombre y el contrato publico
(send_template / send_text -> message_id) no cambian; lo que cambio es que
ahora hay UN solo cliente HTTP hacia graph.facebook.com (MetaGraphClient) en
lugar de una requests.Session propia por cada consumidor.

Mapeo de excepciones (la jerarquia nueva es equivalente a la vieja):
  WhatsAppApiError    == MetaApiError     (base)
  WhatsAppAuthError   == MetaAuthError    (subclase de MetaApiError)
  WhatsAppConfigError == MetaConfigError  (subclase de MetaApiError)
"""
from marketing.integrations.meta.exceptions import (
    MetaApiError as WhatsAppApiError,
    MetaAuthError as WhatsAppAuthError,
    MetaConfigError as WhatsAppConfigError,
)
from marketing.integrations.meta.whatsapp import MetaWhatsAppClient

__all__ = [
    "WhatsAppClient",
    "WhatsAppApiError",
    "WhatsAppAuthError",
    "WhatsAppConfigError",
]


class WhatsAppClient(MetaWhatsAppClient):
    """Alias historico de MetaWhatsAppClient. No agrega comportamiento -- existe
    solo para no romper los imports de notifications/*."""
