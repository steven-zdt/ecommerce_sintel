/**
 * src/logger.ts
 *
 * Fase 29 del plan: logs estructurados, nunca auth state / Signal keys /
 * tokens / QR completo / contenido sensible innecesario. `redact` cubre los
 * campos que un log accidental (ej. serializar un objeto de Baileys
 * completo) podria filtrar.
 */
import pino from "pino";
import { config } from "./config.js";

export const logger = pino({
  level: config.logLevel,
  redact: {
    paths: [
      "*.creds",
      "*.keys",
      "*.token",
      "*.authState",
      "*.qr",
      "req.headers['x-gateway-token']",
      "req.headers.authorization",
    ],
    censor: "[REDACTED]",
  },
  base: { service: "whatsapp_gateway" },
});
