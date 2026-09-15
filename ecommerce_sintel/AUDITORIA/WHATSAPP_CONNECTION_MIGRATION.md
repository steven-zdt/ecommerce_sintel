# WHATSAPP_CONNECTION_MIGRATION

**Misión "Refactorización Arquitectónica del Módulo WhatsApp", 2026-09-16.** Migración
incremental real, sin breaking change (FASE 25).

## Pasos reales ejecutados (en orden)

1. Auditoría real (FASE 0) — `AUDITORIA/WHATSAPP_CONNECTION_BASELINE.md`.
2. Extracción del dominio (`whatsapp/domain/`) — lógica idéntica a la que vivía inline en
   `notifications/tasks.py`, sin cambiar comportamiento.
3. Contrato canónico + Port (`whatsapp/domain/contracts.py`, `whatsapp/ports/connection.py`).
4. `RestConnectionAdapter` envolviendo la integración REAL ya existente (`MetaWhatsAppClient` vía
   el shim `notifications.clients.whatsapp.WhatsAppClient` — no la clase de `marketing`
   directamente, ver hallazgo de compatibilidad de tests abajo).
5. `QRConnectionAdapter` estructural, `NOT_IMPLEMENTED` honesto.
6. `WhatsAppConnectionFactory` + `settings.WHATSAPP_CONNECTION_TYPE` (default `REST`).
7. `notifications/tasks.py::process_whatsapp_inbound_task`/`send_whatsapp_agent_reply_task`
   reducidas a wrappers delgados que delegan en `WhatsAppService`.
8. `notifications/api/whatsapp_webhook.py` — deduplicación movida a
   `WhatsAppIdempotencyGuard` (mismo mecanismo, generalizado), resto sin cambios.
9. Tests de contrato/aislamiento/inversión/fallos (FASE 20-23).
10. Regresión completa de `notifications` (44/44) y `whatsapp` (31/31).

## Compatibilidad preservada — hallazgo real durante la migración

`RestConnectionAdapter` inicialmente usaba `marketing.integrations.meta.whatsapp.
MetaWhatsAppClient` directo. **Corregido**: ~20 tests reales preexistentes
(`notifications/tests.py`) mockean `notifications.clients.whatsapp.WhatsAppClient.send_text`/
`send_template` — un `patch` sobre la subclase (`WhatsAppClient`) no intercepta llamadas hechas
contra la clase padre (`MetaWhatsAppClient`) si el código instancia la clase padre directamente.
El adapter ahora usa `notifications.clients.whatsapp.WhatsAppClient` (el shim histórico, subclase
idéntica), el mismo punto de entrada que el código real siempre usó — cero tests rotos,
confirmado con la regresión completa.

## Nombres/firmas de tareas Celery preservados

`process_whatsapp_inbound_task` y `send_whatsapp_agent_reply_task` mantienen su `name=` registrado
en Celery, sus argumentos (`process_whatsapp_inbound_task` gana `message_id: str = ''`, aditivo
con default — no rompe ninguna llamada existente que no lo pase) y su comportamiento observable
exacto (mismo guard de reintento, mismo respeto de `ai_paused`, mismo manejo de errores).

## Deduplicación — cambio de mecanismo, no de comportamiento

Antes: `cache.add('whatsapp_inbound_msg:{message_id}', ...)` inline en el webhook.
Después: `WhatsAppIdempotencyGuard.is_duplicate('rest', message_id)` — mismo backend (Django
cache/Redis), mismo TTL (24h), mismo criterio atómico — namespace ahora incluye el `channel` para
que un futuro adapter QR nunca pueda colisionar con IDs de mensaje de REST.

## Rollback

Si algo falla en producción: `WHATSAPP_CONNECTION_TYPE` no tiene ningún efecto de rollback útil
hoy (solo existe REST funcional) — el rollback real es de **código**, no de configuración:
`git revert` de los commits de esta misión. `notifications/tasks.py`/`whatsapp_webhook.py`
quedan como wrappers delgados; revertir el commit que los modificó restaura el código inline
anterior sin tocar `MetaWebhookEvent`/`ChatRoom`/ningún dato persistido (la migración no tocó
ningún modelo ni migración de base de datos).

## Checklist de aceptación (ver criterios completos en la certificación final)

Ver `AUDITORIA/WHATSAPP_CONNECTION_FINAL_CERTIFICATION.md`.
