/**
 * src/index.ts
 *
 * Entrypoint. Fase 3 del plan -- levanta el servidor HTTP del contrato.
 * NO arranca el socket de Baileys automaticamente: la conexion real se
 * dispara explicitamente via `POST /session/start` (Fase 1), nunca al boot
 * del proceso -- evita que un simple `docker restart` intente reautenticar
 * sin que nadie lo haya pedido.
 */
import { config } from "./config.js";
import { logger } from "./logger.js";
import { buildServer } from "./server.js";

async function main(): Promise<void> {
  const app = await buildServer();
  await app.listen({ port: config.port, host: "0.0.0.0" });
  logger.info({ event: "startup", port: config.port }, "whatsapp_gateway escuchando");
}

main().catch((err) => {
  logger.error({ event: "startup_failed", error: String(err) }, "no se pudo arrancar el gateway");
  process.exit(1);
});
