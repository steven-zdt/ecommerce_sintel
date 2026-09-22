/**
 * src/whatsapp/socket.ts
 *
 * Fase 3/8/13/14 del plan. Unico modulo que importa Baileys directamente --
 * "one active socket per WhatsApp account" (Fase 13): un solo socket
 * modulo-nivel, nunca uno por request. Traduce eventos crudos de Baileys al
 * modelo de estados propio (src/state.ts) y al contrato normalizado
 * (src/types.ts), y publica esos eventos a Django via src/eventBus.ts
 * (Fase 6) -- el receptor real (Django) todavia no actua sobre
 * `message.received` para logica de negocio (Fase 8 pendiente, requiere
 * un BaileysAdapter en whatsapp/factory.py que no existe todavia; ver
 * notifications/api/whatsapp_gateway_webhook.py).
 *
 * Auth state: FileAuthStateStore real (Fase 4, src/auth/fileAuthStateStore.ts)
 * -- persistencia atomica en disco, lock de single-writer, recuperacion de
 * lock huerfano. Reemplaza useMultiFileAuthState (que el plan marca
 * explicitamente como no apto para produccion) desde este pase.
 *
 * Nota de diseno -- state.ts::forceTransition() en vez de transition():
 * `transition()` (con VALID_TRANSITIONS) es el validador estricto que
 * demuestra el diagrama exacto de la Fase 2 -- vive intacto en state.ts y
 * es lo verificable/testeable independientemente. Este archivo, en cambio,
 * reacciona a eventos REALES de Baileys y a comandos HTTP del operador, que
 * pueden llegar desde cualquier estado (una desconexion de red no espera a
 * que el proceso este en el estado "correcto" para ocurrir; PAIRING en
 * particular no tiene una senal propia y distinta en el `connection.update`
 * real de Baileys -- WhatsApp no notifica "escaneando" por separado de
 * QR_REQUIRED/open). Forzar el modelo idealizado de 8 estados contra
 * eventos que no respetan esa secuencia (ver DisconnectReason.loggedOut,
 * que puede ocurrir en cualquier punto, no solo desde CONNECTED) causaria
 * `InvalidStateTransitionError` sin capturar dentro de un event handler de
 * Baileys -- tumbaria el proceso. `forceTransition()` es el escape
 * deliberado para esto (mismo principio que ya aplicaba ANY -> ERROR).
 */
import makeWASocket, {
  DisconnectReason,
  fetchLatestBaileysVersion,
  type WASocket,
} from "@whiskeysockets/baileys";
import { Boom } from "@hapi/boom";
import { randomUUID } from "node:crypto";

import { FileAuthStateStore, toBaileysAuthState } from "../auth/fileAuthStateStore.js";
import { config } from "../config.js";
import { publishEvent } from "../eventBus.js";
import { logger } from "../logger.js";
import { encodeQrAsDataUrl } from "../qr.js";
import { ConnectionState, ConnectionStateMachine } from "../state.js";
import type { NormalizedInboundMessage, SendMessageResponse } from "../types.js";

const authStore = new FileAuthStateStore(config.authStorageDir);

class WhatsAppSocketManager {
  private socket: WASocket | null = null;
  private readonly stateMachine = new ConnectionStateMachine();
  private currentQrDataUrl: string | null = null;
  private reconnectAttempts = 0;
  private phone: string | null = null;
  private jid: string | null = null;

  get state(): ConnectionState {
    return this.stateMachine.state;
  }

  get lastConnectedAt(): string | null {
    return this.stateMachine.lastConnectedAt;
  }

  get lastDisconnectAt(): string | null {
    return this.stateMachine.lastDisconnectAt;
  }

  get qrDataUrl(): string | null {
    return this.currentQrDataUrl;
  }

  get sessionInfo(): { phone: string | null; jid: string | null } {
    return { phone: this.phone, jid: this.jid };
  }

  /** Sesion viva en ESTE proceso (socket conectado con user.id resuelto). */
  get hasSession(): boolean {
    return this.jid !== null;
  }

  /** Credenciales persistidas en disco -- true incluso si el proceso
   * todavia no llamo start() en este arranque (ej. justo despues de un
   * `docker restart`, antes de que /session/start se invoque). */
  async hasPersistedSession(): Promise<boolean> {
    return authStore.exists();
  }

  /** Fase 6: publica whatsapp.connection.status con el snapshot actual. */
  private _publishStatus(): void {
    void publishEvent({
      event: "whatsapp.connection.status",
      event_id: randomUUID(),
      occurred_at: new Date().toISOString(),
      provider: "baileys",
      status: this.state,
      phone: this.phone,
      jid: this.jid,
    });
  }

  async start(): Promise<void> {
    if (this.socket) {
      logger.warn("start() llamado con un socket ya activo -- ignorado (one socket per account, Fase 13)");
      return;
    }
    await authStore.acquireLock();
    // forceTransition, no transition(): start() es un comando de operador
    // (POST /session/start) que debe funcionar sin importar el estado de
    // partida -- ej. tras un logout previo el estado queda en QR_REQUIRED
    // con socket=null, y pedir un QR nuevo desde ahi es un flujo real y
    // valido (mismo razonamiento que logout()/reconnect(), ver arriba).
    this.stateMachine.forceTransition(ConnectionState.STARTING);
    await this._connect();
  }

  private async _connect(): Promise<void> {
    const { state: authState, saveCreds } = await toBaileysAuthState(authStore);
    const { version } = await fetchLatestBaileysVersion();

    const socket = makeWASocket({
      version,
      auth: authState,
      // printQRInTerminal deprecated (ver plan, seccion 2) -- el QR se
      // captura via el evento connection.update de abajo, nunca se imprime.
    });
    this.socket = socket;

    // Defensa en profundidad real (incidente 2026-09-22): Baileys no
    // captura errores de este listener -- una excepcion aqui se vuelve una
    // unhandled promise rejection y tumba TODO el proceso por defecto en
    // Node. Un fallo puntual guardando credenciales (disco, permisos) debe
    // logearse, nunca matar la sesion completa.
    socket.ev.on("creds.update", () => {
      saveCreds().catch((err) => {
        logger.error({ event: "save_creds_failed", error: String(err) }, "fallo guardando credenciales -- sesion sigue viva, se reintentara en el proximo creds.update");
      });
    });

    socket.ev.on("connection.update", (update) => {
      const { connection, lastDisconnect, qr } = update;

      if (qr) {
        void this._handleQr(qr);
      }

      if (connection === "open") {
        this.reconnectAttempts = 0;
        this.currentQrDataUrl = null;
        this.jid = socket.user?.id ?? null;
        this.phone = this.jid ? this.jid.split(":")[0]?.split("@")[0] ?? null : null;
        this.stateMachine.forceTransition(ConnectionState.CONNECTED);
        logger.info({ event: "connection_status", status: "CONNECTED" }, "socket conectado");
        this._publishStatus();
        return;
      }

      if (connection === "close") {
        this._handleClose(lastDisconnect);
      }
    });

    socket.ev.on("messages.upsert", (payload) => {
      for (const raw of payload.messages) {
        const normalized = this._normalizeInbound(raw);
        if (normalized) {
          logger.info(
            { event: "whatsapp.message.received", event_id: normalized.event_id },
            "mensaje entrante normalizado -- publicando a Django (Fase 6)",
          );
          // Envelope exacto de la seccion 9 del plan -- "message" anidado,
          // no el shape plano de NormalizedInboundMessage (ese es interno).
          void publishEvent({
            event: normalized.event,
            event_id: normalized.event_id,
            occurred_at: normalized.occurred_at,
            provider: normalized.provider,
            message: {
              provider_message_id: normalized.provider_message_id,
              remote_jid: normalized.remote_jid,
              sender_phone: normalized.sender_phone,
              text: normalized.text,
              timestamp: normalized.timestamp,
            },
          });
        }
      }
    });
  }

  private async _handleQr(rawQr: string): Promise<void> {
    this.currentQrDataUrl = await encodeQrAsDataUrl(rawQr);
    if (this.state !== ConnectionState.QR_REQUIRED) {
      this.stateMachine.forceTransition(ConnectionState.QR_REQUIRED);
    }
    logger.info({ event: "connection_status", status: "QR_REQUIRED" }, "QR generado");
    this._publishStatus();
    void publishEvent({
      event: "whatsapp.connection.qr",
      event_id: randomUUID(),
      occurred_at: new Date().toISOString(),
      provider: "baileys",
      qr_image: this.currentQrDataUrl,
    });
  }

  private _handleClose(lastDisconnect: { error?: Error } | undefined): void {
    const boom = lastDisconnect?.error as Boom | undefined;
    const statusCode = boom?.output?.statusCode;

    if (statusCode === DisconnectReason.loggedOut) {
      // Fase 14, regla dura: loggedOut NUNCA es un loop de reconexion.
      logger.warn({ event: "connection_status", status: "LOGGED_OUT" }, "sesion cerrada por WhatsApp -- requiere nuevo QR");
      this.currentQrDataUrl = null;
      this.jid = null;
      this.phone = null;
      this.socket = null;
      this.stateMachine.forceTransition(ConnectionState.LOGGED_OUT);
      void publishEvent({
        event: "whatsapp.connection.logged_out",
        event_id: randomUUID(),
        occurred_at: new Date().toISOString(),
        provider: "baileys",
      });
      this.stateMachine.forceTransition(ConnectionState.QR_REQUIRED);
      this._publishStatus();
      return;
    }

    if (!config.reconnect.enabled || this.reconnectAttempts >= config.reconnect.maxAttempts) {
      logger.error(
        { event: "connection_status", status: "ERROR", attempts: this.reconnectAttempts },
        "reconexion agotada o deshabilitada -- ERROR terminal, requiere intervencion manual (session/reconnect)",
      );
      this.socket = null;
      this.stateMachine.forceTransition(ConnectionState.ERROR);
      this._publishStatus();
      return;
    }

    this.stateMachine.forceTransition(ConnectionState.RECONNECTING);
    this._publishStatus();
    const attempt = ++this.reconnectAttempts;
    // Backoff exponencial con jitter (Fase 14). base * 2^(n-1) +- 20%.
    const jitter = 0.8 + Math.random() * 0.4;
    const delayMs = Math.round(config.reconnect.baseDelayMs * 2 ** (attempt - 1) * jitter);
    logger.warn(
      { event: "connection_status", status: "RECONNECTING", attempt, delayMs },
      "conexion cerrada -- reintentando",
    );
    this.socket = null;
    setTimeout(() => {
      void this._connect();
    }, delayMs);
  }

  private _normalizeInbound(raw: unknown): NormalizedInboundMessage | null {
    // Traduccion best-effort del shape crudo de Baileys -- deliberadamente
    // defensiva (campos opcionales via optional chaining): el objetivo de
    // este pase es demostrar la forma del contrato (Fase 1/9), no cubrir
    // cada variante de mensaje de WhatsApp todavia.
    const msg = raw as {
      key?: { remoteJid?: string; id?: string; fromMe?: boolean };
      message?: { conversation?: string; extendedTextMessage?: { text?: string } };
      messageTimestamp?: number | { toNumber(): number };
    };
    if (!msg.key || msg.key.fromMe) return null;
    const remoteJid = msg.key.remoteJid ?? "";
    const text = msg.message?.conversation ?? msg.message?.extendedTextMessage?.text ?? "";
    if (!text) return null;

    return {
      event: "whatsapp.message.received",
      event_id: randomUUID(),
      occurred_at: new Date().toISOString(),
      provider: "baileys",
      provider_message_id: msg.key.id ?? randomUUID(),
      remote_jid: remoteJid,
      sender_phone: remoteJid.split("@")[0] ?? "",
      text,
      timestamp: new Date(
        typeof msg.messageTimestamp === "number"
          ? msg.messageTimestamp * 1000
          : msg.messageTimestamp
            ? msg.messageTimestamp.toNumber() * 1000
            : Date.now(),
      ).toISOString(),
    };
  }

  /**
   * Comando explicito del operador (Fase 15 -- boton "Desconectar" del
   * panel). Debe funcionar y terminar en QR_REQUIRED sin importar el
   * estado de partida (a diferencia de la transicion LOGGED_OUT automatica
   * que dispara `_handleClose` cuando WhatsApp cierra la sesion del lado
   * del protocolo -- esa SI esta restringida a partir de CONNECTED/
   * RECONNECTING, ver state.ts). Idempotente: llamarlo sin sesion activa
   * no debe fallar.
   */
  async logout(): Promise<void> {
    if (this.socket) {
      try {
        await this.socket.logout();
      } catch (err) {
        logger.warn({ event: "logout_error", error: String(err) }, "socket.logout() fallo -- se limpia el estado local igual");
      }
    }
    this.socket = null;
    this.currentQrDataUrl = null;
    this.jid = null;
    this.phone = null;
    this.reconnectAttempts = 0;
    await authStore.clear(); // Fase 15/20: invalida el auth state real, nunca deja material huerfano
    this.stateMachine.forceTransition(ConnectionState.LOGGED_OUT);
    void publishEvent({
      event: "whatsapp.connection.logged_out",
      event_id: randomUUID(),
      occurred_at: new Date().toISOString(),
      provider: "baileys",
      reason: "operator_command",
    });
    this.stateMachine.forceTransition(ConnectionState.QR_REQUIRED);
    this._publishStatus();
  }

  async reconnect(): Promise<void> {
    this.reconnectAttempts = 0;
    if (this.socket) {
      this.socket.end(undefined);
      this.socket = null;
    }
    this.stateMachine.forceTransition(ConnectionState.STARTING);
    await authStore.acquireLock(); // no-op real si este mismo proceso ya lo sostiene (mismo PID)
    await this._connect();
  }

  async sendMessage(recipient: string, text: string): Promise<SendMessageResponse> {
    if (!this.socket || this.state !== ConnectionState.CONNECTED) {
      return { accepted: false, provider_message_id: null, status: "FAILED", error: "socket no conectado" };
    }
    try {
      const jid = recipient.includes("@") ? recipient : `${recipient}@s.whatsapp.net`;
      const result = await this.socket.sendMessage(jid, { text });
      const providerMessageId = result?.key?.id ?? null;
      void publishEvent({
        event: "whatsapp.message.sent",
        event_id: randomUUID(),
        occurred_at: new Date().toISOString(),
        provider: "baileys",
        message: { provider_message_id: providerMessageId, recipient },
      });
      return { accepted: true, provider_message_id: providerMessageId, status: "SENT" };
    } catch (err) {
      logger.error({ event: "whatsapp.message.failed", error: String(err) }, "fallo el envio");
      void publishEvent({
        event: "whatsapp.message.failed",
        event_id: randomUUID(),
        occurred_at: new Date().toISOString(),
        provider: "baileys",
        message: { recipient, error: String(err) },
      });
      return { accepted: false, provider_message_id: null, status: "FAILED", error: String(err) };
    }
  }
}

export const whatsappSocketManager = new WhatsAppSocketManager();
