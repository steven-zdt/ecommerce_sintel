"""
whatsapp/adapters/meta_cloud_api_adapter.py

Mision "Migracion Arquitectonica de WhatsApp -- QR Web Session Experimental
+ Meta Cloud API Futura" (2026-09-16). Renombrado desde `rest_adapter.py`/
`RestConnectionAdapter` (mision anterior, FASE 6) -- mismo adapter real,
nombre mas explicito: esto es especificamente la integracion OFICIAL de
Meta (WhatsApp Business Platform / Cloud API), no un termino generico
"REST" que podria confundirse con cualquier transporte HTTP.

Envuelve la integracion de Meta Cloud API que ya existe y funciona en
produccion (`marketing/integrations/meta/`, ver AUDITORIA/
WHATSAPP_CONNECTION_BASELINE.md). NO reescribe el transporte --
`MetaWhatsAppClient`/`MetaGraphClient` siguen siendo el unico cliente HTTP
real hacia graph.facebook.com, este adapter solo lo expone detras del
contrato `WhatsAppConnectionPort`.

Cero logica de negocio aqui -- solo traduccion de formato + transporte.
"""
import logging
from datetime import datetime, timezone as dt_timezone

from django.conf import settings

from whatsapp.domain.contracts import MessageType, WhatsAppInboundMessage, WhatsAppOutboundMessage
from whatsapp.ports.connection import (
    ConnectionCapabilities,
    ConnectionStatus,
    UnsupportedCapabilityError,
    WhatsAppConnectionPort,
)

logger = logging.getLogger("whatsapp.meta_cloud_api_adapter")

_CAPABILITIES = ConnectionCapabilities(
    send_text=True,
    receive_text=True,
    send_media=False,       # MetaWhatsAppClient hoy solo implementa send_text/send_template -- declarado explicito, no se finge soporte
    receive_media=False,    # el webhook descarta explicitamente mensajes no-text (ver notifications/api/whatsapp_webhook.py)
    webhook=True,
    polling=False,
    qr_pairing=False,
    session_persistence=True,   # la "sesion" de Meta Cloud API es el token de acceso, no expira por reinicio de contenedor
    delivery_status=True,       # MetaWebhookEvent ya persiste callbacks de status (delivered/read/failed)
)


class MetaCloudAPIAdapter(WhatsAppConnectionPort):
    """Adapter real contra la API oficial de WhatsApp Business Platform
    (Meta Cloud API). `connect()`/`disconnect()` son conceptualmente
    triviales aqui (no hay sesion persistente que abrir/cerrar, es HTTP
    request/response puro autenticado por token) -- se implementan igual
    para cumplir el contrato, documentado explicito en vez de dejarlos
    vacios sin explicacion.

    NOT_CONFIGURED vs DISCONNECTED vs CONNECTED (Regla FASE 10/21 de la
    mision, verificado explicito, no confundido): si faltan credenciales
    (`META_ACCESS_TOKEN`/`WHATSAPP_PHONE_NUMBER_ID`), el estado real es
    NOT_CONFIGURED -- nunca ERROR (eso implicaria que algo se intento y
    fallo) ni DISCONNECTED (eso implicaria que alguna vez estuvo
    conectado)."""

    def __init__(self, *, client=None):
        # notifications.clients.whatsapp.WhatsAppClient (shim historico,
        # subclase identica de MetaWhatsAppClient) -- NO se usa
        # MetaWhatsAppClient directo a proposito: ~20 tests reales
        # preexistentes (notifications/tests.py) mockean
        # 'notifications.clients.whatsapp.WhatsAppClient.send_text', un
        # patch sobre la SUBCLASE no intercepta llamadas hechas contra la
        # clase padre. Usar el mismo punto de entrada real que ya usaba
        # notifications/tasks.py preserva esos tests sin tocarlos (Regla de
        # migracion incremental sin breaking change).
        from notifications.clients.whatsapp import WhatsAppClient
        self._client_factory = client or WhatsAppClient
        self._connected = False

    @property
    def capabilities(self) -> ConnectionCapabilities:
        return _CAPABILITIES

    def _is_configured(self) -> bool:
        return bool(settings.META_ACCESS_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID)

    def connect(self) -> ConnectionStatus:
        if not self._is_configured():
            return ConnectionStatus.NOT_CONFIGURED
        self._connected = True
        return ConnectionStatus.CONNECTED

    def disconnect(self) -> None:
        self._connected = False

    def get_status(self) -> ConnectionStatus:
        if not self._is_configured():
            return ConnectionStatus.NOT_CONFIGURED
        return ConnectionStatus.CONNECTED if self._connected else ConnectionStatus.DISCONNECTED

    def send_message(self, message: WhatsAppOutboundMessage) -> str:
        if message.message_type != MessageType.TEXT:
            raise UnsupportedCapabilityError(
                f"MetaCloudAPIAdapter no soporta send de tipo {message.message_type!r} "
                "(capabilities.send_media=False -- MetaWhatsAppClient no implementa envio de media hoy)."
            )
        # Sincrono real (requests, via MetaGraphClient) -- se ejecuta dentro
        # de una tarea Celery (notifications/tasks.py), mismo criterio que
        # ya aplicaba el codigo que este adapter reemplaza.
        client = self._client_factory()
        return client.send_text(message.recipient, message.text)

    def generate_pairing_qr(self) -> str | None:
        # No aplica a Meta Cloud API -- no es un error pedirlo, simplemente
        # no hay nada que emparejar (autenticacion por token, no por QR).
        return None

    def health_check(self) -> bool:
        # Verificacion de configuracion, deliberadamente SIN una llamada
        # HTTP real a Meta (evita gastar cuota/latencia en cada health
        # check) -- un chequeo mas profundo (ping real a graph.facebook.com)
        # queda documentado como mejora futura si se necesita, no se
        # implementa sin evidencia de que la verificacion de config no
        # alcanza.
        return self._is_configured()

    def translate_inbound(self, raw_event: dict) -> WhatsAppInboundMessage | None:
        """`raw_event` es el dict `message` ya extraido por
        notifications/api/whatsapp_webhook.py del payload de Meta
        (`value['messages'][i]`) -- mismo shape real que Meta entrega,
        no reinventado aqui."""
        if not raw_event:
            return None
        msg_type = raw_event.get("type")
        if msg_type != "text":
            return None  # mismo criterio real que el webhook ya aplicaba -- tipos no soportados se descartan, logueados por el caller

        wa_id = str(raw_event.get("from", "")).strip()
        text = str((raw_event.get("text") or {}).get("body", "")).strip()
        if not (wa_id and text):
            return None

        ts_raw = raw_event.get("timestamp")
        timestamp = None
        if ts_raw:
            try:
                timestamp = datetime.fromtimestamp(int(ts_raw), tz=dt_timezone.utc)
            except (ValueError, TypeError):
                timestamp = None

        return WhatsAppInboundMessage(
            channel="meta_cloud_api",
            external_message_id=str(raw_event.get("id", "")).strip(),
            external_conversation_id=wa_id,
            sender_phone=wa_id,
            message_type=MessageType.TEXT,
            text=text,
            timestamp=timestamp,
            provider_metadata={"raw_type": msg_type},
        )
