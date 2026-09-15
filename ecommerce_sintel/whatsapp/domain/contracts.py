"""
whatsapp/domain/contracts.py

Mision "Refactorizacion Arquitectonica del Modulo WhatsApp", FASE 2
(2026-09-16). Representacion interna, independiente del proveedor real
(REST/Meta Cloud API hoy, QR en el futuro -- ver AUDITORIA/
WHATSAPP_CONNECTION_BASELINE.md para el hallazgo de que QR no existe hoy).

Ningun adapter puede devolver/recibir otra cosa -- este es el UNICO
lenguaje que el dominio (`whatsapp/domain/service.py`) conoce. Un adapter
que no pueda producir estos campos debe dejarlos en su default explicito
(nunca inventar un valor), nunca fallar silenciosamente (ver
ConnectionCapabilities en ports/connection.py).
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    TEXT = "text"
    MEDIA = "media"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class WhatsAppInboundMessage:
    """Un mensaje real recibido de un cliente, ya traducido por el adapter
    desde el formato especifico del proveedor (payload de Meta Cloud API
    hoy, evento de un gateway QR en el futuro)."""

    channel: str  # "rest" | "qr" -- que ADAPTER lo produjo, no que canal de negocio
    external_message_id: str
    external_conversation_id: str  # hoy: el telefono E.164 del cliente (Meta no da otro id de conversacion)

    sender_phone: str
    sender_name: str = ""

    message_type: MessageType = MessageType.TEXT
    text: str = ""
    media: dict | None = None  # {"url"/"media_id", "mime_type", ...} -- shape del proveedor, nunca interpretado por el dominio

    timestamp: datetime | None = None

    # Datos crudos del proveedor que el dominio NO interpreta pero que un
    # adapter puede necesitar reenviar (ej. waba_id/phone_number_id de
    # Meta) -- se persisten para auditoria/debug, nunca para decisiones de
    # negocio (esas viven en los campos tipados de arriba).
    provider_metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class WhatsAppOutboundMessage:
    """Lo que el dominio decide enviar -- el adapter decide COMO (texto
    libre vs. plantilla aprobada, ventana de servicio de 24h de Meta,
    formato del gateway QR, etc.), nunca el dominio."""

    external_conversation_id: str
    recipient: str  # telefono E.164 -- mismo valor que external_conversation_id hoy (Meta), separado a proposito por si un futuro proveedor los distingue
    text: str
    message_type: MessageType = MessageType.TEXT
    metadata: dict = field(default_factory=dict)
