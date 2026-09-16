"""
whatsapp/adapters/qr_web_session_adapter.py

Mision "Migracion Arquitectonica de WhatsApp -- QR Web Session Experimental
+ Meta Cloud API Futura" (2026-09-16). Renombrado desde `qr_adapter.py`/
`QRConnectionAdapter` (mision anterior, FASE 5).

## EXPERIMENTAL / THIRD-PARTY / NON-OFFICIAL (Regla dura de esta mision, FASE 7)

Este adapter, si algun dia se conecta a un gateway real, representaria una
sesion tipo WhatsApp Web via un mecanismo QR de TERCERO (ej. Baileys,
whatsapp-web.js) -- NUNCA la API oficial de Meta. Prohibido explicitamente
por la mision usar lenguaje como "API oficial por QR": no lo es, y este
docstring lo deja explicito para cualquiera que lea este archivo despues.

## Estado real, FASE 8 de esta mision (AUDITORIA/WHATSAPP_QR_PROVIDER_EVALUATION.md)

Evaluados Baileys/whatsapp-web.js/alternativas -- conclusion: BLOQUEADO
para el numero de produccion real de SINTEL. Conectar el mismo numero que
ya usa Meta Cloud API oficialmente a una libreria no oficial viola los
Terminos de Servicio de WhatsApp Business y arriesga perder TAMBIEN la
integracion oficial que ya funciona, por una capacidad que no aporta nada
que Meta Cloud API no cubra ya. Este adapter existe para probar que la
arquitectura hexagonal es real (mismo contrato que MetaCloudAPIAdapter,
sin que el dominio necesite saberlo) -- no para simular un producto
terminado. `WhatsAppQRNotImplementedError` en cada metodo real, fail-loud
explicito, nunca una simulacion.
"""
import logging

from whatsapp.adapters.session_manager import WhatsAppSessionManager, WhatsAppSessionState
from whatsapp.domain.contracts import WhatsAppInboundMessage, WhatsAppOutboundMessage
from whatsapp.ports.connection import ConnectionCapabilities, ConnectionStatus, WhatsAppConnectionPort

logger = logging.getLogger("whatsapp.qr_web_session_adapter")

# Capacidades declaradas de un gateway QR TIPICO (Baileys/whatsapp-web.js y
# similares) -- documentadas como referencia de lo que un gateway real
# probablemente soportaria, NO como capacidades reales de este adapter hoy
# (que no tiene ningun gateway conectado). Ver get_status()/health_check():
# siempre reportan el estado real (NOT_CONFIGURED/False), nunca estas
# capacidades como si ya funcionaran.
_CAPABILITIES = ConnectionCapabilities(
    send_text=False,
    receive_text=False,
    send_media=False,
    receive_media=False,
    webhook=False,
    polling=True,         # tipico de estos gateways (long-polling/WebSocket de eventos), no confirmado
    qr_pairing=True,       # la razon de ser de este adapter -- tampoco implementado todavia
    session_persistence=False,  # una sesion de navegador tipicamente NO sobrevive un reinicio sin trabajo adicional
    delivery_status=False,
)

# ConnectionStatus (Port, generico) <- WhatsAppSessionState (interno, granular).
# El Port solo necesita saber "funciona / no funciona / no configurado" --
# el detalle de QR_REQUIRED/SCANNING/etc. es interno de este adapter (ver
# get_session_state(), expuesto aparte para quien lo necesite, ej. la UI).
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


class WhatsAppQRNotImplementedError(Exception):
    """Se lanza por cada operacion real del QR adapter -- fail-loud
    explicito (Regla de la mision: "no fallar silenciosamente"), nunca un
    no-op silencioso ni una simulacion."""


class QRWebSessionAdapter(WhatsAppConnectionPort):
    """Ver docstring del modulo. Ningun metodo hace I/O real de un gateway
    -- todos devuelven/lanzan un estado honesto de "no implementado
    todavia", con la maquina de estados real de WhatsAppSessionManager
    detras (hoy siempre NOT_CONFIGURED)."""

    def __init__(self):
        self._session = WhatsAppSessionManager(initial=WhatsAppSessionState.NOT_CONFIGURED)

    @property
    def capabilities(self) -> ConnectionCapabilities:
        return _CAPABILITIES

    def get_session_state(self) -> WhatsAppSessionState:
        """Estado granular real (QR_REQUIRED/SCANNING/etc.) -- expuesto
        aparte de `get_status()` (Port generico) para que la UI pueda
        mostrar el detalle real que pide la mision (FASE 19/20), sin que
        el Port/dominio necesiten conocer estos valores."""
        return self._session.state

    def connect(self) -> ConnectionStatus:
        logger.warning("[whatsapp.qr] connect() llamado -- ningun gateway QR real esta integrado todavia.")
        return ConnectionStatus.NOT_IMPLEMENTED

    def disconnect(self) -> None:
        return None

    def get_status(self) -> ConnectionStatus:
        return _SESSION_TO_CONNECTION_STATUS[self._session.state]

    def send_message(self, message: WhatsAppOutboundMessage) -> str:
        raise WhatsAppQRNotImplementedError(
            "QRWebSessionAdapter.send_message: ningun gateway QR real esta integrado. "
            "Ver AUDITORIA/WHATSAPP_QR_PROVIDER_EVALUATION.md -- bloqueado para el numero "
            "de produccion real, requiere decision explicita de negocio para reabrirse."
        )

    def generate_pairing_qr(self) -> str | None:
        raise WhatsAppQRNotImplementedError(
            "QRWebSessionAdapter.generate_pairing_qr: sin gateway real, no hay nada que emparejar."
        )

    def health_check(self) -> bool:
        return False

    def translate_inbound(self, raw_event: dict) -> WhatsAppInboundMessage | None:
        raise WhatsAppQRNotImplementedError(
            "QRWebSessionAdapter.translate_inbound: sin gateway real, no hay formato de evento que traducir."
        )
