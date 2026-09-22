/**
 * src/state.ts
 *
 * Fase 2 del plan de migracion -- estado unico de conexion, exactamente los
 * 8 valores definidos en PLAN_ACCION_MIGRACION_WHATSAPP_BAILEYS_SINTEL.md
 * seccion 5, con las transiciones ahi documentadas. Constantes tipadas --
 * "no utilizar strings diferentes en cada capa" (regla dura de la fase).
 *
 * Nota de diseno (registrar en AUDITORIA/WHATSAPP_BAILEYS_ARCHITECTURE.md):
 * el dominio Django (`whatsapp/adapters/session_manager.py::WhatsAppSessionState`)
 * usa un modelo de 10 estados mas granular (QR_READY/SCANNING/AUTHENTICATING
 * separados) construido en la mision anterior. Este gateway usa el modelo de
 * 8 estados tal cual lo define el plan actual -- el mapeo entre ambos es
 * responsabilidad del futuro BaileysAdapter en Django (Fase 6/8, todavia no
 * implementado), no de este archivo. No se colapsan ni se inventan estados
 * intermedios aqui para forzar una correspondencia 1:1 prematura.
 */

export enum ConnectionState {
  DISCONNECTED = "DISCONNECTED",
  STARTING = "STARTING",
  QR_REQUIRED = "QR_REQUIRED",
  PAIRING = "PAIRING",
  CONNECTED = "CONNECTED",
  RECONNECTING = "RECONNECTING",
  LOGGED_OUT = "LOGGED_OUT",
  ERROR = "ERROR",
}

// Transiciones validas reales (seccion 5 del plan). ERROR es alcanzable
// desde cualquier estado (ANY -> ERROR), modelado aparte abajo en
// isValidTransition en vez de repetirlo en cada fila.
const VALID_TRANSITIONS: Record<ConnectionState, ReadonlySet<ConnectionState>> = {
  [ConnectionState.DISCONNECTED]: new Set([ConnectionState.STARTING]),
  [ConnectionState.STARTING]: new Set([ConnectionState.QR_REQUIRED, ConnectionState.CONNECTED]),
  [ConnectionState.QR_REQUIRED]: new Set([ConnectionState.PAIRING]),
  [ConnectionState.PAIRING]: new Set([ConnectionState.CONNECTED, ConnectionState.QR_REQUIRED]),
  [ConnectionState.CONNECTED]: new Set([ConnectionState.RECONNECTING, ConnectionState.LOGGED_OUT]),
  [ConnectionState.RECONNECTING]: new Set([ConnectionState.CONNECTED, ConnectionState.DISCONNECTED]),
  [ConnectionState.LOGGED_OUT]: new Set([ConnectionState.QR_REQUIRED]),
  [ConnectionState.ERROR]: new Set([ConnectionState.STARTING, ConnectionState.DISCONNECTED]),
};

export class InvalidStateTransitionError extends Error {
  constructor(from: ConnectionState, to: ConnectionState) {
    super(`Transicion de estado invalida: ${from} -> ${to}`);
    this.name = "InvalidStateTransitionError";
  }
}

export class ConnectionStateMachine {
  private _state: ConnectionState = ConnectionState.DISCONNECTED;
  private _lastConnectedAt: string | null = null;
  private _lastDisconnectAt: string | null = null;

  get state(): ConnectionState {
    return this._state;
  }

  get lastConnectedAt(): string | null {
    return this._lastConnectedAt;
  }

  get lastDisconnectAt(): string | null {
    return this._lastDisconnectAt;
  }

  /**
   * ANY -> ERROR siempre permitido (seccion 5 del plan: "Error no
   * recuperable: ANY -> ERROR"). Todo lo demas debe seguir
   * VALID_TRANSITIONS -- fail-loud si no, nunca forzar un estado
   * inconsistente silenciosamente.
   */
  transition(next: ConnectionState): void {
    if (next === ConnectionState.ERROR || this._state === next) {
      this._apply(next);
      return;
    }
    const allowed = VALID_TRANSITIONS[this._state];
    if (!allowed.has(next)) {
      throw new InvalidStateTransitionError(this._state, next);
    }
    this._apply(next);
  }

  /**
   * Escape hatch deliberado, distinto de `transition()`: un comando externo
   * (ej. `POST /session/logout` pedido por un admin desde el panel) debe
   * poder llevar la maquina a QR_REQUIRED/DISCONNECTED sin importar en que
   * estado intermedio estaba -- no es un evento del protocolo de Baileys
   * (esos SI deben seguir VALID_TRANSITIONS via `transition()`, ver
   * socket.ts::_handleClose). Mismo principio que ya aplica ANY -> ERROR,
   * generalizado a comandos explicitos del operador humano.
   */
  forceTransition(next: ConnectionState): void {
    this._apply(next);
  }

  private _apply(next: ConnectionState): void {
    if (next === ConnectionState.CONNECTED) {
      this._lastConnectedAt = new Date().toISOString();
    }
    if (
      next === ConnectionState.DISCONNECTED ||
      next === ConnectionState.RECONNECTING ||
      next === ConnectionState.LOGGED_OUT
    ) {
      this._lastDisconnectAt = new Date().toISOString();
    }
    this._state = next;
  }
}
