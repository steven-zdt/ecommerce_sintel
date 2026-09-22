/**
 * src/server.ts
 *
 * Fase 1 del plan: implementa el contrato HTTP exacto de la seccion 4
 * (health, status, session/start|logout|reconnect, session/qr, messages/send).
 *
 * Autenticacion: verificacion de `X-Gateway-Token` contra
 * WA_GATEWAY_INTERNAL_TOKEN -- version minima de la Fase 7 (un secreto
 * compartido estatico). La Fase 7 completa (rotacion, validacion de
 * timestamp/event_id/idempotencia) queda fuera de alcance de este pase; se
 * deja este guard porque un servidor HTTP capaz de enviar mensajes de
 * WhatsApp sin ninguna autenticacion, ni siquiera en un esqueleto, no es
 * una omision aceptable (Fase 20: "nunca exponer el gateway sin
 * autenticacion").
 */
import Fastify from "fastify";
import rateLimit from "@fastify/rate-limit";

import { config } from "./config.js";
import { logger } from "./logger.js";
import { whatsappSocketManager } from "./whatsapp/socket.js";
import type {
  HealthResponse,
  QrResponse,
  SendMessageRequest,
  SendMessageResponse,
  SessionActionResponse,
  StatusResponse,
} from "./types.js";

export async function buildServer() {
  const app = Fastify({ loggerInstance: logger });

  // Fase 20 del plan: "Aplicar rate limiting al endpoint interno de envio".
  // global:false -- por defecto NINGUNA ruta tiene limite salvo las que lo
  // declaren explicitamente via `config.rateLimit` (solo /messages/send,
  // ver abajo). No es una defensa contra abuso externo real (el gateway no
  // deberia ser alcanzable desde Internet, ver Fase 20/21) -- es una
  // segunda capa honesta contra un bug interno (un loop de reintento mal
  // hecho en Django, por ejemplo) que intente mandar cientos de mensajes
  // por segundo.
  //
  // AWAIT real y necesario, no cosmetico -- bug encontrado probando esto
  // de verdad (ver test/server.test.ts): sin `await` aqui, las rutas
  // declaradas synchronamente despues (app.post(...) mas abajo) se
  // registran antes de que el hook `onRoute` del plugin este activo, y
  // `config.rateLimit` en la ruta queda completamente ignorado -- sin
  // ningun error, sin ningun header, 0 limite real aplicado. Confirmado
  // con una reproduccion minima aislada antes de aplicar el fix.
  await app.register(rateLimit, { global: false });

  // /health queda fuera del guard de token a proposito -- es lo que un
  // healthcheck de Docker (Fase 21) debe poder pegarle sin credenciales.
  app.get<{ Reply: HealthResponse }>("/health", async () => ({
    status: "ok",
    service: "whatsapp_gateway",
    provider: "baileys",
  }));

  app.addHook("onRequest", async (request, reply) => {
    if (request.url === "/health") return;
    const token = request.headers["x-gateway-token"];
    if (token !== config.internalToken) {
      await reply.code(401).send({ error: "token invalido o ausente (X-Gateway-Token)" });
    }
  });

  app.get<{ Reply: StatusResponse }>("/status", async () => {
    const { phone, jid } = whatsappSocketManager.sessionInfo;
    // has_session refleja credenciales PERSISTIDAS (sobreviven restart),
    // no solo el socket vivo de este proceso -- ver
    // WhatsAppSocketManager.hasPersistedSession().
    const hasSession = whatsappSocketManager.hasSession || (await whatsappSocketManager.hasPersistedSession());
    return {
      provider: "baileys",
      status: whatsappSocketManager.state,
      phone,
      jid,
      has_session: hasSession,
      qr_available: whatsappSocketManager.qrDataUrl !== null,
      last_connected_at: whatsappSocketManager.lastConnectedAt,
      last_disconnect_at: whatsappSocketManager.lastDisconnectAt,
    };
  });

  app.get<{ Reply: QrResponse }>("/session/qr", async () => ({
    qr_available: whatsappSocketManager.qrDataUrl !== null,
    qr_image: whatsappSocketManager.qrDataUrl,
    // Baileys rota el QR cada ~20s mientras QR_REQUIRED -- no se rastrea un
    // expires_at exacto en este pase (el frontend real deberia re-consultar
    // /session/qr periodicamente mientras el estado sea QR_REQUIRED).
    expires_at: null,
  }));

  app.post<{ Reply: SessionActionResponse }>("/session/start", async () => {
    await whatsappSocketManager.start();
    return { status: whatsappSocketManager.state };
  });

  app.post<{ Reply: SessionActionResponse }>("/session/logout", async () => {
    await whatsappSocketManager.logout();
    return { status: whatsappSocketManager.state };
  });

  app.post<{ Reply: SessionActionResponse }>("/session/reconnect", async () => {
    await whatsappSocketManager.reconnect();
    return { status: whatsappSocketManager.state };
  });

  app.post<{ Body: SendMessageRequest; Reply: SendMessageResponse }>(
    "/messages/send",
    {
      // 20/min es holgado para respuestas de soporte reales (un agente/IA
      // respondiendo mensajes uno a uno), pero corta de raiz un loop de
      // envio masivo -- exactamente el escenario que Fase 20 pide prevenir
      // ("No implementar bulk spam / automatic unsolicited messaging").
      config: { rateLimit: { max: 20, timeWindow: "1 minute" } },
    },
    async (request, reply) => {
      const { recipient, text } = request.body ?? ({} as SendMessageRequest);
      if (!recipient || !text) {
        return reply.code(400).send({
          accepted: false,
          provider_message_id: null,
          status: "FAILED",
          error: "recipient y text son obligatorios",
        });
      }
      return whatsappSocketManager.sendMessage(recipient, text);
    },
  );

  return app;
}
