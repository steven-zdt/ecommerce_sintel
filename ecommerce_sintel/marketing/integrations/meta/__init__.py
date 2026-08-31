"""
Frontera HTTP unica hacia Meta (Graph API / WhatsApp Cloud API / Marketing API).

FASE 3 del plan de integracion Meta Business
(Documentacion/Arquitectura_general/META_BUSINESS_INTEGRATION_MASTER_PLAN.md).

Regla: NINGUN otro punto del backend hace requests.* directo a
graph.facebook.com. Todo pasa por MetaGraphClient (transporte puro, sin logica
de negocio de Sintel) o por uno de los subclientes de dominio construidos
encima (whatsapp.py hoy; marketing.py / instagram.py / pages.py / conversions.py
/ catalog.py en fases posteriores).

Vive bajo marketing/ porque marketing es el dominio dueno de Meta/Ads; los
demas consumidores (notifications, support, shop) importan el subcliente que
necesitan desde aqui.
"""
from marketing.integrations.meta.client import MetaGraphClient
from marketing.integrations.meta.exceptions import (
    MetaApiError,
    MetaApiTransientError,
    MetaAuthError,
    MetaConfigError,
    MetaRateLimitError,
)
from marketing.integrations.meta.signatures import verify_meta_webhook_signature
from marketing.integrations.meta.whatsapp import MetaWhatsAppClient

__all__ = [
    "MetaGraphClient",
    "MetaWhatsAppClient",
    "MetaApiError",
    "MetaApiTransientError",
    "MetaAuthError",
    "MetaConfigError",
    "MetaRateLimitError",
    "verify_meta_webhook_signature",
]
