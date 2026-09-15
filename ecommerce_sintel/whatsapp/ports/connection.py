"""
whatsapp/ports/connection.py

Mision "Refactorizacion Arquitectonica del Modulo WhatsApp", FASE 3-4
(2026-09-16). Contrato abstracto de TRANSPORTE -- solo capacidades de
conexion/envio/recepcion. Ningun metodo de negocio (abrir_ticket,
resolver_cliente, crear_sala, pausar_ia) pertenece aqui -- esos viven en
`whatsapp/domain/service.py::WhatsAppService`, que RECIBE un adapter, nunca
lo construye.

Regla dura de la mision (seccion 1): el dominio nunca hace
`if connection_type == "qr": ... elif == "rest": ...` -- ese condicional
solo puede existir en la capa de composicion (`whatsapp/factory.py`).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from whatsapp.domain.contracts import WhatsAppInboundMessage, WhatsAppOutboundMessage


class ConnectionStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"
    PAIRING_REQUIRED = "PAIRING_REQUIRED"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"  # FASE 6/9 de la mision: un mecanismo declarado pero sin gateway real integrado -- nunca se finge CONNECTED


@dataclass(frozen=True)
class ConnectionCapabilities:
    """Mision, FASE 4: "no asumir que QR y REST tendran exactamente las
    mismas capacidades... si una capacidad no esta disponible, debe
    declararse explicitamente y no fallar silenciosamente." El dominio
    consulta esto ANTES de pedirle algo a un adapter que no lo soporta."""

    send_text: bool = False
    receive_text: bool = False
    send_media: bool = False
    receive_media: bool = False
    webhook: bool = False
    polling: bool = False
    qr_pairing: bool = False
    session_persistence: bool = False
    delivery_status: bool = False


class UnsupportedCapabilityError(Exception):
    """El dominio pidio una operacion que el adapter activo declara no
    soportar -- fail-loud, nunca un no-op silencioso."""


class WhatsAppConnectionPort(ABC):
    """Contrato real que TODO adapter (REST hoy, QR cuando exista un
    gateway real) debe cumplir identico. Ver whatsapp/tests/test_contract.py
    -- se corre parametrizado contra cada adapter real, no es solo un
    acuerdo de interfaz en papel.

    SINCRONO a proposito (2026-09-16, decision de diseño real): el prompt
    maestro de esta mision no exige async/sync -- el contexto de ejecucion
    REAL del dominio WhatsApp en este proyecto es 100% sincrono (Celery
    worker `notifications`, Django ORM sincrono, `MetaWhatsAppClient` usa
    `requests`, no hay ningun event loop asyncio corriendo ahi). Hacer este
    contrato async habria significado envolver codigo sincrono real con
    `sync_to_async`/`asgiref` sin ningun beneficio real -- complejidad sin
    evidencia de necesidad (Regla 1 de la mision: no sobrearquitecturar).
    Si en el futuro WhatsApp se sirve desde un proceso async real (ej. un
    gateway QR con su propio loop de eventos), ese adapter puede ejecutar
    su propio I/O async internamente y exponer estos metodos sincronos de
    todas formas (via `asyncio.run()`/una cola), sin cambiar el contrato."""

    @property
    @abstractmethod
    def capabilities(self) -> ConnectionCapabilities:
        """Declaracion real, no aspiracional -- lo que este adapter
        concreto puede hacer HOY, verificado contra su implementacion."""

    @abstractmethod
    def connect(self) -> ConnectionStatus:
        ...

    @abstractmethod
    def disconnect(self) -> None:
        ...

    @abstractmethod
    def get_status(self) -> ConnectionStatus:
        ...

    @abstractmethod
    def send_message(self, message: WhatsAppOutboundMessage) -> str:
        """Devuelve el external_message_id real del proveedor. Lanza
        UnsupportedCapabilityError si capabilities.send_text/send_media es
        False para el tipo de mensaje pedido."""

    @abstractmethod
    def generate_pairing_qr(self) -> str | None:
        """Solo tiene sentido si capabilities.qr_pairing es True -- un
        adapter REST real devuelve None sin lanzar (no es un error pedirle
        esto a REST, simplemente no aplica)."""

    @abstractmethod
    def health_check(self) -> bool:
        ...

    def translate_inbound(self, raw_event: dict) -> WhatsAppInboundMessage | None:
        """Traduce un evento crudo del proveedor (payload ya parseado por
        la capa de transporte real -- webhook view para REST, evento del
        gateway para QR) al contrato canonico. None si el evento no es un
        mensaje procesable (ej. un callback de estado 'delivered', no un
        mensaje entrante). Sync a proposito -- es una traduccion pura de
        datos, sin I/O."""
        raise NotImplementedError
