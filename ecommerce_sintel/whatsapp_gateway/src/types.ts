/**
 * src/types.ts
 *
 * Fase 1 del plan -- contrato interno estable del gateway. Formas de
 * request/response de cada endpoint del contrato (seccion 4 del plan) mas
 * las formas de evento normalizado (seccion 9) que el gateway ya produce
 * internamente aunque todavia no las publique a Django (Fase 6/8: "Event
 * Bus Gateway -> Django", fuera de alcance de este pase -- ver README).
 */
import type { ConnectionState } from "./state.js";

export interface HealthResponse {
  status: "ok";
  service: "whatsapp_gateway";
  provider: "baileys";
}

export interface StatusResponse {
  provider: "baileys";
  status: ConnectionState;
  phone: string | null;
  jid: string | null;
  has_session: boolean;
  qr_available: boolean;
  last_connected_at: string | null;
  last_disconnect_at: string | null;
}

export interface QrResponse {
  qr_available: boolean;
  /** Data URL PNG (data:image/png;base64,...) -- nunca el string crudo de
   * Baileys sin codificar (seccion 5 del plan: "generar una representacion
   * adecuada para frontend"). null si no hay QR vigente. */
  qr_image: string | null;
  expires_at: string | null;
}

export interface SendMessageRequest {
  recipient: string; // telefono E.164, mismo campo que WhatsAppOutboundMessage.recipient en Django
  text: string;
}

export interface SendMessageResponse {
  accepted: boolean;
  provider_message_id: string | null;
  status: "SENT" | "FAILED";
  error?: string;
}

export interface SessionActionResponse {
  status: ConnectionState;
}

/**
 * Evento normalizado (seccion 9 del plan). Producido internamente por el
 * socket manager al traducir `messages.upsert` de Baileys -- todavia no se
 * publica a ningun lado (ese es el Event Bus de la Fase 6/8, fuera de
 * alcance de este pase). Mismo espiritu que
 * `whatsapp/domain/contracts.py::WhatsAppInboundMessage` en Django, sin
 * intentar ser el mismo tipo (son procesos y lenguajes distintos).
 */
export interface NormalizedInboundMessage {
  event: "whatsapp.message.received";
  event_id: string;
  occurred_at: string;
  provider: "baileys";
  provider_message_id: string;
  remote_jid: string;
  sender_phone: string;
  text: string;
  timestamp: string;
}
