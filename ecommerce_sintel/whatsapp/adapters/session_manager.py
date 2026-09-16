"""
whatsapp/adapters/session_manager.py

Mision "Migracion Arquitectonica de WhatsApp", FASE 9 (2026-09-16).
Estados de sesion reales para mecanismos CON sesion persistente propia
(hoy: `QRWebSessionAdapter` -- Meta Cloud API es stateless por token, no
necesita este nivel de detalle, ver `ConnectionStatus` simple del Port).

Clasificacion (ver AUDITORIA/WHATSAPP_CONNECTION_MIGRATION_BASELINE.md):
APPLICATION, especifico del adapter que lo usa -- el dominio
(`whatsapp/domain/`) NUNCA conoce estos estados, solo conoce
`ConnectionStatus` (el contrato generico del Port). Mezclar esto en el
dominio violaria la regla dura de la mision (seccion 1).

No hay persistencia real implementada todavia (Regla FASE 9: "la sesion
debe sobrevivir reinicios siempre que el proveedor lo permita") -- sin un
proveedor real (ver AUDITORIA/WHATSAPP_QR_PROVIDER_EVALUATION.md,
conclusion BLOCKED), no hay sesion real que persistir. La maquina de
estados queda lista para cuando exista.
"""
from enum import Enum


class WhatsAppSessionState(str, Enum):
    DISABLED = "DISABLED"                # el mecanismo QR ni siquiera esta seleccionado (WHATSAPP_CONNECTION_TYPE != QR_WEB_SESSION)
    NOT_CONFIGURED = "NOT_CONFIGURED"     # seleccionado, pero sin gateway/proveedor real integrado (estado real HOY)
    QR_REQUIRED = "QR_REQUIRED"           # gateway real disponible, esperando que se solicite un QR
    QR_READY = "QR_READY"                 # QR real generado, esperando escaneo
    SCANNING = "SCANNING"                 # el telefono inicio el escaneo, esperando confirmacion
    AUTHENTICATING = "AUTHENTICATING"     # escaneo confirmado, estableciendo la sesion
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


# Transiciones validas reales -- documentadas explicitamente para que un
# futuro gateway real no pueda saltarse pasos (ej. ir de QR_REQUIRED
# directo a CONNECTED sin pasar por QR_READY/SCANNING/AUTHENTICATING).
_VALID_TRANSITIONS: dict[WhatsAppSessionState, set[WhatsAppSessionState]] = {
    WhatsAppSessionState.DISABLED: {WhatsAppSessionState.NOT_CONFIGURED},
    WhatsAppSessionState.NOT_CONFIGURED: {WhatsAppSessionState.DISABLED, WhatsAppSessionState.QR_REQUIRED},
    WhatsAppSessionState.QR_REQUIRED: {WhatsAppSessionState.QR_READY, WhatsAppSessionState.ERROR, WhatsAppSessionState.DISABLED},
    WhatsAppSessionState.QR_READY: {WhatsAppSessionState.SCANNING, WhatsAppSessionState.QR_REQUIRED, WhatsAppSessionState.ERROR, WhatsAppSessionState.DISABLED},
    WhatsAppSessionState.SCANNING: {WhatsAppSessionState.AUTHENTICATING, WhatsAppSessionState.QR_REQUIRED, WhatsAppSessionState.ERROR},
    WhatsAppSessionState.AUTHENTICATING: {WhatsAppSessionState.CONNECTED, WhatsAppSessionState.ERROR, WhatsAppSessionState.QR_REQUIRED},
    WhatsAppSessionState.CONNECTED: {WhatsAppSessionState.RECONNECTING, WhatsAppSessionState.DISCONNECTED, WhatsAppSessionState.ERROR},
    WhatsAppSessionState.RECONNECTING: {WhatsAppSessionState.CONNECTED, WhatsAppSessionState.QR_REQUIRED, WhatsAppSessionState.ERROR, WhatsAppSessionState.DISCONNECTED},
    WhatsAppSessionState.DISCONNECTED: {WhatsAppSessionState.QR_REQUIRED, WhatsAppSessionState.RECONNECTING, WhatsAppSessionState.DISABLED},
    WhatsAppSessionState.ERROR: {WhatsAppSessionState.QR_REQUIRED, WhatsAppSessionState.DISABLED},
}


class InvalidSessionTransitionError(Exception):
    pass


class WhatsAppSessionManager:
    """Guarda el estado real de la sesion QR en memoria de proceso HOY
    (sin proveedor real, no hay nada persistente que guardar -- ver
    docstring del modulo). Cuando exista un gateway real, este manager es
    el punto real donde conectar persistencia (Redis/DB), sin que
    `QRWebSessionAdapter` ni el dominio deban cambiar."""

    def __init__(self, *, initial: WhatsAppSessionState = WhatsAppSessionState.NOT_CONFIGURED):
        self._state = initial

    @property
    def state(self) -> WhatsAppSessionState:
        return self._state

    def transition(self, new_state: WhatsAppSessionState) -> None:
        allowed = _VALID_TRANSITIONS.get(self._state, set())
        if new_state not in allowed and new_state != self._state:
            raise InvalidSessionTransitionError(
                f"Transicion invalida: {self._state.value} -> {new_state.value} "
                f"(permitidas desde {self._state.value}: {sorted(s.value for s in allowed)})"
            )
        self._state = new_state
