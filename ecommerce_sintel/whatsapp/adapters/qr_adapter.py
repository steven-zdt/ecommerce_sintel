"""
whatsapp/adapters/qr_adapter.py

Mision "Refactorizacion Arquitectonica del Modulo WhatsApp", FASE 5
(2026-09-16). Adapter QR -- estructuralmente completo (cumple el mismo
`WhatsAppConnectionPort` que `RestConnectionAdapter`), funcionalmente
`NOT_IMPLEMENTED`.

Hallazgo real de FASE 0 (ver AUDITORIA/WHATSAPP_CONNECTION_BASELINE.md):
no existe en este repositorio, ni existio nunca, ningun mecanismo QR para
WhatsApp -- ninguna libreria de pairing (Baileys/whatsapp-web.js o
equivalente), ninguna automatizacion de navegador, ningun gateway real.
Regla 36 de la mision ("no inventes capacidades") prohibe fingir que esto
funciona. Este adapter existe para PROBAR que la arquitectura hexagonal es
real (un segundo adapter que cumple el contrato sin que
`WhatsAppService`/Support/ChatRoom necesiten saberlo) -- no para simular
un producto terminado.

Cuando se elija una libreria/gateway QR real, la implementacion entra AQUI
-- `capabilities` pasa a declarar lo que ese gateway real soporte, los
metodos dejan de lanzar `NotImplementedError` uno por uno, y NINGUN otro
archivo del dominio necesita cambiar (esa es la prueba de la mision, ver
whatsapp/tests/test_isolation.py).
"""
import logging

from whatsapp.domain.contracts import WhatsAppInboundMessage, WhatsAppOutboundMessage
from whatsapp.ports.connection import ConnectionCapabilities, ConnectionStatus, WhatsAppConnectionPort

logger = logging.getLogger("whatsapp.qr_adapter")

# Capacidades declaradas de un gateway QR TIPICO (Baileys/whatsapp-web.js y
# similares) -- documentadas como referencia de lo que un gateway real
# probablemente soportaria, NO como capacidades reales de este adapter hoy
# (que no tiene ningun gateway conectado). Ver get_status()/health_check():
# siempre reportan el estado real (NOT_IMPLEMENTED/False), nunca estas
# capacidades como si ya funcionaran.
_CAPABILITIES = ConnectionCapabilities(
    send_text=False,
    receive_text=False,
    send_media=False,
    receive_media=False,
    webhook=False,
    polling=True,         # tipico de estos gateways (long-polling de eventos), no confirmado
    qr_pairing=True,       # la razon de ser de este adapter -- tampoco implementado todavia
    session_persistence=False,  # una sesion de navegador tipicamente NO sobrevive un reinicio sin trabajo adicional
    delivery_status=False,
)


class WhatsAppQRNotImplementedError(Exception):
    """Se lanza por cada operacion real del QR adapter -- fail-loud
    explicito (Regla de la mision, FASE 4: "no fallar silenciosamente"),
    nunca un no-op silencioso ni una simulacion."""


class QRConnectionAdapter(WhatsAppConnectionPort):
    """Ver docstring del modulo. Ningun metodo hace I/O real -- todos
    devuelven/lanzan un estado honesto de "no implementado todavia"."""

    @property
    def capabilities(self) -> ConnectionCapabilities:
        return _CAPABILITIES

    def connect(self) -> ConnectionStatus:
        logger.warning("[whatsapp.qr] connect() llamado -- ningun gateway QR real esta integrado todavia.")
        return ConnectionStatus.NOT_IMPLEMENTED

    def disconnect(self) -> None:
        return None

    def get_status(self) -> ConnectionStatus:
        return ConnectionStatus.NOT_IMPLEMENTED

    def send_message(self, message: WhatsAppOutboundMessage) -> str:
        raise WhatsAppQRNotImplementedError(
            "QRConnectionAdapter.send_message: ningun gateway QR real esta integrado. "
            "Elegir/integrar una libreria de pairing real antes de activar WHATSAPP_CONNECTION_TYPE=QR."
        )

    def generate_pairing_qr(self) -> str | None:
        raise WhatsAppQRNotImplementedError(
            "QRConnectionAdapter.generate_pairing_qr: sin gateway real, no hay nada que emparejar."
        )

    def health_check(self) -> bool:
        return False

    def translate_inbound(self, raw_event: dict) -> WhatsAppInboundMessage | None:
        raise WhatsAppQRNotImplementedError(
            "QRConnectionAdapter.translate_inbound: sin gateway real, no hay formato de evento que traducir."
        )
