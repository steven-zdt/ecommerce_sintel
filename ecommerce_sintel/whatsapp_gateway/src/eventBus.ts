/**
 * src/eventBus.ts
 *
 * Fase 6 del plan -- publica los eventos normalizados a Django
 * (`notifications/api/whatsapp_gateway_webhook.py`) via webhook HTTP
 * interno, autenticado con el mismo `X-Gateway-Token` que protege las
 * rutas entrantes de este servicio (un solo secreto compartido para todo
 * el canal Gateway<->Django en este pase -- Fase 7 completa, con rotacion
 * y validacion de timestamp/idempotencia a nivel de transporte, queda
 * pendiente).
 *
 * Deliberadamente SIN cola/retry propio: un intento, se loguea el
 * resultado. El plan no exige un outbox persistente en la Fase 6 -- la
 * evidencia del evento sigue existiendo en los logs de este proceso aunque
 * la publicacion falle (Django caido, red, etc.), y `messages.upsert` no se
 * pierde para efectos de negocio real porque ese flujo todavia no depende
 * de este bus (ver whatsapp_gateway_webhook.py: Fase 8 pendiente). Si en el
 * futuro esto debe ser confiable de verdad, ese es trabajo de una fase
 * posterior explicita, no una suposicion silenciosa aqui.
 *
 * `DJANGO_EVENTS_URL` es opcional a proposito: si no esta configurada, el
 * bus queda deshabilitado (solo logs locales) -- permite correr el gateway
 * de forma aislada, como en las Fases 1-4, sin forzar una dependencia dura
 * de Django todavia no confirmada en Docker (Fase 21).
 */
import { config } from "./config.js";
import { logger } from "./logger.js";

export type GatewayEvent = Record<string, unknown> & { event: string; event_id: string };

export async function publishEvent(event: GatewayEvent): Promise<void> {
  if (!config.djangoEventsUrl) {
    logger.debug({ event: event.event, event_id: event.event_id }, "event bus deshabilitado (DJANGO_EVENTS_URL no configurada) -- solo log local");
    return;
  }
  try {
    const response = await fetch(config.djangoEventsUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Gateway-Token": config.internalToken,
      },
      body: JSON.stringify(event),
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) {
      logger.warn(
        { event: event.event, event_id: event.event_id, http_status: response.status },
        "Django rechazo el evento del gateway",
      );
      return;
    }
    logger.debug({ event: event.event, event_id: event.event_id }, "evento publicado a Django");
  } catch (err) {
    logger.warn(
      { event: event.event, event_id: event.event_id, error: String(err) },
      "no se pudo publicar el evento a Django (sin retry en este pase, ver docstring del modulo)",
    );
  }
}
