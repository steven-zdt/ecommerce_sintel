/**
 * src/config.ts
 *
 * Fase 3/22 del plan de migracion (AUDITORIA/WHATSAPP_BAILEYS_PRE_MIGRATION_AUDIT.md).
 * Lee y valida las variables de entorno del gateway. Fail-closed: si falta
 * WA_GATEWAY_INTERNAL_TOKEN el proceso no arranca -- nunca correr el gateway
 * sin autenticacion (Fase 7/20 del plan: "nunca exponer el gateway sin
 * autenticacion").
 */
import "dotenv/config";

function required(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Falta la variable de entorno obligatoria: ${name}`);
  }
  return value;
}

function optional(name: string, fallback: string): string {
  return process.env[name] ?? fallback;
}

export const config = {
  port: Number(optional("WA_GATEWAY_PORT", "3001")),
  internalToken: required("WA_GATEWAY_INTERNAL_TOKEN"),
  sessionStorage: optional("WA_SESSION_STORAGE", "file"),
  // Directorio raiz del FileAuthStateStore real (Fase 4). En Docker (Fase
  // 21, todavia no ejecutada) este path debe ser un named volume dedicado
  // -- ver AUDITORIA/WHATSAPP_BAILEYS_ARCHITECTURE.md.
  authStorageDir: optional("WA_AUTH_STORAGE_DIR", "data/auth-store"),
  // Fase 6: URL del Event Bus receptor en Django
  // (notifications/api/whatsapp_gateway_webhook.py). Opcional a proposito
  // -- ver docstring de src/eventBus.ts.
  djangoEventsUrl: optional("DJANGO_EVENTS_URL", ""),
  logLevel: optional("WA_LOG_LEVEL", "info"),
  reconnect: {
    enabled: optional("WA_RECONNECT_ENABLED", "true") === "true",
    maxAttempts: Number(optional("WA_RECONNECT_MAX_ATTEMPTS", "10")),
    baseDelayMs: Number(optional("WA_RECONNECT_BASE_DELAY_MS", "2000")),
  },
} as const;

if (config.sessionStorage !== "file") {
  throw new Error(
    `WA_SESSION_STORAGE=${config.sessionStorage} no soportado. Unico valor valido: "file" ` +
      `(FileAuthStateStore real, Fase 4 -- ver src/auth/fileAuthStateStore.ts). PostgreSQL se ` +
      `descarto deliberadamente, ver docstring de ese archivo.`,
  );
}
