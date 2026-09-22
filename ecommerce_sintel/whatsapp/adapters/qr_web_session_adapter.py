"""
whatsapp/adapters/qr_web_session_adapter.py

Mision "Migracion Arquitectonica de WhatsApp -- QR Web Session Experimental
+ Meta Cloud API Futura" (2026-09-16). Renombrado desde `qr_adapter.py`/
`QRConnectionAdapter` (mision anterior, FASE 5).

## EXPERIMENTAL / THIRD-PARTY / NON-OFFICIAL (Regla dura de esta mision, FASE 7)

Este adapter representa una sesion tipo WhatsApp Web via Baileys
(`whatsapp_gateway/`, Node/TypeScript) -- NUNCA la API oficial de Meta.
Prohibido explicitamente por la mision usar lenguaje como "API oficial por
QR": no lo es.

## Estado real (Fase 0-8 de PLAN_ACCION_MIGRACION_WHATSAPP_BAILEYS_SINTEL.md,
## AUDITORIA/WHATSAPP_BAILEYS_PRE_MIGRATION_AUDIT.md)

`AUDITORIA/WHATSAPP_QR_PROVIDER_EVALUATION.md` evaluo Baileys/whatsapp-web.js
-- BLOQUEADO para el numero de produccion real de SINTEL salvo autorizacion
explicita de negocio (riesgo real de violar TOS de WhatsApp Business y de
perder la integracion oficial Meta Cloud API ya activa en el mismo numero).
Esa autorizacion se obtuvo explicitamente el 2026-09-22 (ver
AUDITORIA/WHATSAPP_BAILEYS_PRE_MIGRATION_AUDIT.md, seccion RISKS) para el
numero de produccion real -- esto NO reduce el riesgo, solo documenta que
fue aceptado a proposito.

Este adapter YA NO es un stub incondicional. Ahora es un stub CONDICIONAL:

- `WHATSAPP_GATEWAY_ENABLED=False` (default) o `WHATSAPP_GATEWAY_URL` vacio
  -> comportamiento IDENTICO al original: cada metodo real lanza
  `WhatsAppQRNotImplementedError`, fail-loud explicito, cero llamadas de
  red. Esto preserva sin cambios el comportamiento de dev/produccion
  existente (ninguno de los dos configura estas variables hoy) y los tests
  existentes de `whatsapp/tests/` sin modificarlos.
- Ambas configuradas -> llamadas HTTP reales a `whatsapp_gateway/` via
  `whatsapp/clients/gateway_client.py::WhatsAppGatewayClient`. Sigue sin
  haber ningun numero de telefono real conectado solo por escribir este
  codigo -- eso requiere ademas levantar el gateway y escanear un QR real,
  fuera del alcance de este pase (ver whatsapp_gateway/README.md).
"""
import logging
from datetime import datetime

from django.conf import settings

from whatsapp.adapters.session_manager import WhatsAppSessionManager, WhatsAppSessionState
from whatsapp.clients.gateway_client import WhatsAppGatewayClient, WhatsAppGatewayError
from whatsapp.domain.contracts import MessageType, WhatsAppInboundMessage, WhatsAppOutboundMessage
from whatsapp.ports.connection import ConnectionCapabilities, ConnectionStatus, WhatsAppConnectionPort

logger = logging.getLogger("whatsapp.qr_web_session_adapter")

# Capacidades del stub SIN gateway configurado -- documentadas como
# referencia de lo que un gateway QR tipico probablemente soportaria, NO
# como capacidades reales (no hay ninguna conexion). Sin cambios respecto
# al comportamiento original.
_STUB_CAPABILITIES = ConnectionCapabilities(
    send_text=False,
    receive_text=False,
    send_media=False,
    receive_media=False,
    webhook=False,
    polling=True,
    qr_pairing=True,
    session_persistence=False,
    delivery_status=False,
)

# Capacidades REALES de whatsapp_gateway/ (Fase 1-6, ver whatsapp_gateway/README.md)
# cuando esta configurado -- verificadas contra lo que el gateway realmente
# implementa hoy, no aspiracional.
_REAL_CAPABILITIES = ConnectionCapabilities(
    send_text=True,
    receive_text=True,
    send_media=False,        # whatsapp_gateway/src/server.ts solo implementa texto (Fase 3)
    receive_media=False,     # idem, translate_inbound de abajo solo produce MessageType.TEXT
    webhook=True,            # eventos llegan por push (Event Bus, Fase 6), no polling
    polling=False,
    qr_pairing=True,
    session_persistence=True,   # FileAuthStateStore real (Fase 4)
    delivery_status=False,      # el gateway no reporta delivered/read todavia
)

# Stub sin gateway: ConnectionStatus <- WhatsAppSessionState (10 estados
# granulares, ver session_manager.py). Sin cambios.
_SESSION_TO_CONNECTION_STATUS = {
    WhatsAppSessionState.DISABLED: ConnectionStatus.NOT_IMPLEMENTED,
    WhatsAppSessionState.NOT_CONFIGURED: ConnectionStatus.NOT_IMPLEMENTED,
    WhatsAppSessionState.QR_REQUIRED: ConnectionStatus.PAIRING_REQUIRED,
    WhatsAppSessionState.QR_READY: ConnectionStatus.PAIRING_REQUIRED,
    WhatsAppSessionState.SCANNING: ConnectionStatus.PAIRING_REQUIRED,
    WhatsAppSessionState.AUTHENTICATING: ConnectionStatus.PAIRING_REQUIRED,
    WhatsAppSessionState.CONNECTED: ConnectionStatus.CONNECTED,
    WhatsAppSessionState.RECONNECTING: ConnectionStatus.DISCONNECTED,
    WhatsAppSessionState.DISCONNECTED: ConnectionStatus.DISCONNECTED,
    WhatsAppSessionState.ERROR: ConnectionStatus.ERROR,
}

# Gateway real configurado: ConnectionState (8 estados, whatsapp_gateway/
# src/state.ts) -> ConnectionStatus (Port generico, 6 valores).
_GATEWAY_TO_CONNECTION_STATUS = {
    "DISCONNECTED": ConnectionStatus.DISCONNECTED,
    "STARTING": ConnectionStatus.PAIRING_REQUIRED,
    "QR_REQUIRED": ConnectionStatus.PAIRING_REQUIRED,
    "PAIRING": ConnectionStatus.PAIRING_REQUIRED,
    "CONNECTED": ConnectionStatus.CONNECTED,
    "RECONNECTING": ConnectionStatus.DISCONNECTED,
    "LOGGED_OUT": ConnectionStatus.DISCONNECTED,
    "ERROR": ConnectionStatus.ERROR,
}

# Gateway real configurado: ConnectionState (8 estados) -> WhatsAppSessionState
# (10 estados granulares de Django, ver session_manager.py). Vocabularios
# DISTINTOS a proposito (ver AUDITORIA/WHATSAPP_BAILEYS_ARCHITECTURE.md,
# "Nota de diseno") -- esta funcion ES la capa de composicion que los
# traduce. El gateway no distingue QR_READY/SCANNING/AUTHENTICATING como
# eventos separados (WhatsApp Web no expone esas senales por separado via
# Baileys) -- se aproxima con el estado granular MAS CERCANO semanticamente,
# documentado explicito, nunca inventado sin justificacion:
#   - gateway STARTING ("arrancando, todavia sin QR") ~ Django QR_REQUIRED
#     ("esperando que se solicite un QR")
#   - gateway QR_REQUIRED ("QR generado, esperando escaneo" -- MISMO NOMBRE,
#     SIGNIFICADO DISTINTO) ~ Django QR_READY ("QR real generado, esperando
#     escaneo") -- la colision de nombres es real, no un error de este mapeo
#   - gateway PAIRING (cubre "escaneo iniciado" + "estableciendo sesion" en
#     un solo estado) ~ Django AUTHENTICATING (el mas avanzado de los dos
#     que Django distingue, SCANNING nunca se alcanza via este gateway)
#   - gateway LOGGED_OUT es transitorio (el gateway mismo pasa a QR_REQUIRED
#     de inmediato, ver whatsapp_gateway/src/whatsapp/socket.ts::logout())
#     ~ Django DISCONNECTED
_GATEWAY_TO_SESSION_STATE = {
    "DISCONNECTED": WhatsAppSessionState.DISCONNECTED,
    "STARTING": WhatsAppSessionState.QR_REQUIRED,
    "QR_REQUIRED": WhatsAppSessionState.QR_READY,
    "PAIRING": WhatsAppSessionState.AUTHENTICATING,
    "CONNECTED": WhatsAppSessionState.CONNECTED,
    "RECONNECTING": WhatsAppSessionState.RECONNECTING,
    "LOGGED_OUT": WhatsAppSessionState.DISCONNECTED,
    "ERROR": WhatsAppSessionState.ERROR,
}


class WhatsAppQRNotImplementedError(Exception):
    """Se lanza cuando NO hay gateway configurado (WHATSAPP_GATEWAY_ENABLED/
    WHATSAPP_GATEWAY_URL) -- fail-loud explicito, nunca un no-op silencioso
    ni una simulacion. Distinto de WhatsAppGatewayError (fallo operacional
    real con un gateway SI configurado, ver whatsapp/clients/gateway_client.py)."""


def _gateway_configured() -> bool:
    return bool(getattr(settings, "WHATSAPP_GATEWAY_ENABLED", False) and getattr(settings, "WHATSAPP_GATEWAY_URL", ""))


class QRWebSessionAdapter(WhatsAppConnectionPort):
    """Ver docstring del modulo. Sin gateway configurado: identico al
    stub original (ningun I/O real). Con gateway configurado: transporte
    HTTP real hacia whatsapp_gateway/, vocabulario propio de estados
    traducido explicitamente al Port y a WhatsAppSessionState."""

    def __init__(self):
        self._session = WhatsAppSessionManager(initial=WhatsAppSessionState.NOT_CONFIGURED)
        self._client = WhatsAppGatewayClient() if _gateway_configured() else None
        # Ultimo `status` textual real devuelto por el gateway (uno de sus
        # 8 valores) -- fuente de verdad para get_session_state() cuando
        # hay gateway. NUNCA se conduce via WhatsAppSessionManager.transition()
        # en este modo: el gateway es la fuente de verdad remota, replicar
        # sus saltos de estado contra la maquina de transiciones ESTRICTA
        # de Django (pensada para un adapter que gestiona su propio estado
        # local) lanzaria InvalidSessionTransitionError ante saltos legitimos
        # que Django no modela por separado (ver mapeo de arriba) -- mismo
        # bug real ya encontrado y corregido del lado del gateway
        # (whatsapp_gateway/src/whatsapp/socket.ts, ver AUDITORIA/
        # WHATSAPP_BAILEYS_ARCHITECTURE.md).
        self._last_gateway_status: str | None = None

    @property
    def capabilities(self) -> ConnectionCapabilities:
        return _REAL_CAPABILITIES if self._client else _STUB_CAPABILITIES

    def get_session_state(self) -> WhatsAppSessionState:
        if not self._client:
            return self._session.state
        if self._last_gateway_status is None:
            # Configurado pero todavia no se consulto el gateway ni una vez
            # en este proceso -- DISCONNECTED es honesto ("sin sesion activa
            # conocida"), NOT_CONFIGURED se reserva para el modo stub.
            return WhatsAppSessionState.DISCONNECTED
        return _GATEWAY_TO_SESSION_STATE.get(self._last_gateway_status, WhatsAppSessionState.ERROR)

    def connect(self) -> ConnectionStatus:
        if not self._client:
            logger.warning("[whatsapp.qr] connect() llamado -- ningun gateway QR real esta configurado (WHATSAPP_GATEWAY_ENABLED/WHATSAPP_GATEWAY_URL).")
            return ConnectionStatus.NOT_IMPLEMENTED
        try:
            data = self._client.session_start()
        except WhatsAppGatewayError as exc:
            logger.error("[whatsapp.qr] session_start fallo: %s", exc)
            self._last_gateway_status = "ERROR"
            return ConnectionStatus.ERROR
        self._last_gateway_status = data.get("status")
        return _GATEWAY_TO_CONNECTION_STATUS.get(self._last_gateway_status, ConnectionStatus.ERROR)

    def disconnect(self) -> None:
        if not self._client:
            return None
        try:
            self._client.session_logout()
        except WhatsAppGatewayError as exc:
            # disconnect() nunca lanza (Regla del Port, ver ports/connection.py
            # y whatsapp/tests/test_contract.py::test_ambos_disconnect_no_lanza)
            # -- se loguea y se sigue.
            logger.warning("[whatsapp.qr] session_logout fallo (ignorado, disconnect() no lanza): %s", exc)
        self._last_gateway_status = "LOGGED_OUT"
        return None

    def reconnect(self) -> ConnectionStatus:
        """Sobreescribe el default del Port (disconnect()+connect()) a
        proposito -- ese default equivale a un logout completo seguido de
        un login nuevo, lo que en whatsapp_gateway/ BORRA el auth state real
        (ver whatsapp_gateway/src/whatsapp/socket.ts::logout()::authStore.clear()).
        El gateway expone POST /session/reconnect exactamente para evitar
        eso (reconexion de socket, sesion/credenciales intactas). Sin
        gateway configurado, se preserva el default heredado del Port
        (identico al comportamiento original: siempre NOT_IMPLEMENTED)."""
        if not self._client:
            return super().reconnect()
        try:
            data = self._client.session_reconnect()
        except WhatsAppGatewayError as exc:
            logger.error("[whatsapp.qr] session_reconnect fallo: %s", exc)
            self._last_gateway_status = "ERROR"
            return ConnectionStatus.ERROR
        self._last_gateway_status = data.get("status")
        return _GATEWAY_TO_CONNECTION_STATUS.get(self._last_gateway_status, ConnectionStatus.ERROR)

    def get_status(self) -> ConnectionStatus:
        if not self._client:
            return _SESSION_TO_CONNECTION_STATUS[self._session.state]
        try:
            data = self._client.status()
        except WhatsAppGatewayError as exc:
            logger.error("[whatsapp.qr] status fallo: %s", exc)
            self._last_gateway_status = "ERROR"
            return ConnectionStatus.ERROR
        self._last_gateway_status = data.get("status")
        return _GATEWAY_TO_CONNECTION_STATUS.get(self._last_gateway_status, ConnectionStatus.ERROR)

    def send_message(self, message: WhatsAppOutboundMessage) -> str:
        if not self._client:
            raise WhatsAppQRNotImplementedError(
                "QRWebSessionAdapter.send_message: ningun gateway QR real esta configurado. "
                "Ver AUDITORIA/WHATSAPP_QR_PROVIDER_EVALUATION.md -- bloqueado para el numero "
                "de produccion real, requiere decision explicita de negocio para reabrirse."
            )
        data = self._client.send_message(recipient=message.recipient, text=message.text)
        if not data.get("accepted"):
            raise WhatsAppGatewayError(f"el gateway rechazo el envio: {data.get('error', 'motivo desconocido')}")
        return data.get("provider_message_id") or ""

    def generate_pairing_qr(self) -> str | None:
        if not self._client:
            raise WhatsAppQRNotImplementedError(
                "QRWebSessionAdapter.generate_pairing_qr: sin gateway real, no hay nada que emparejar."
            )
        data = self._client.qr()
        return data.get("qr_image")

    def health_check(self) -> bool:
        if not self._client:
            return False
        return self._client.health()

    def translate_inbound(self, raw_event: dict) -> WhatsAppInboundMessage | None:
        """`raw_event` es el sub-objeto "message" del envelope
        whatsapp.message.received (ver whatsapp_gateway/src/types.ts::
        NormalizedInboundMessage y notifications/api/whatsapp_gateway_webhook.py)
        -- NO el envelope completo (ese incluye "event"/"event_id" que no
        son parte del mensaje en si)."""
        if not self._client:
            raise WhatsAppQRNotImplementedError(
                "QRWebSessionAdapter.translate_inbound: sin gateway real, no hay formato de evento que traducir."
            )
        text = (raw_event.get("text") or "").strip()
        if not text:
            return None
        timestamp = None
        raw_ts = raw_event.get("timestamp")
        if raw_ts:
            try:
                timestamp = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
            except ValueError:
                timestamp = None
        return WhatsAppInboundMessage(
            channel="baileys",
            external_message_id=raw_event.get("provider_message_id", ""),
            external_conversation_id=raw_event.get("remote_jid", ""),
            sender_phone=raw_event.get("sender_phone", ""),
            message_type=MessageType.TEXT,
            text=text,
            timestamp=timestamp,
        )
