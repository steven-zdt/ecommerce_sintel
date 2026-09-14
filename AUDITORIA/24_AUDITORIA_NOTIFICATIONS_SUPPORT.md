# 24 — Auditoría Enterprise: Notifications × Support (Fase 9)

> **Fase 9 completada y cerrada 2026-08-01** — continúa el plan de
> [15](15_AUDITORIA_SUPPORT_OMNICANAL.md)-[23](23_AUDITORIA_SEGURIDAD.md). El módulo
> `notifications/` solo había tenido un ajuste documental (Fase 3), nunca una auditoría real de
> su integración con `support/` (recordatorios de tickets, WhatsApp inbound, Event Bus proactivo
> de IA). Alcance aprobado por el usuario: el hallazgo P1 más los 3 P2. Los 3 P3 restantes
> (índices de `NotificationLog`/`ChatRoom`, bypass de `UserNotificationPreference` en el mensaje
> proactivo de IA) quedan documentados como pendientes de menor prioridad.

## P1 — Ticket escalado a humano y sin atender solo notificaba al cliente, nunca al staff

`support/tasks.py::notify_unattended_escalated_tickets` (ChatRoom abierta, `ai_paused=True`,
2h sin actividad) llama `dispatch_notification_once(user=room.user, ...)`, que dispara el Event
Bus de IA (`ai_proactive_room_message_task`) — el bot deja un mensaje de tranquilidad en la sala
("Seguimos con tu caso..."). Ese mensaje solo se difundía por WS al grupo `chat_{user.uuid}`
(el cliente). **Ningún canal alertaba al staff** de que un ticket llevaba 2+ horas escalado a un
humano sin que nadie respondiera — el mecanismo de escalamiento no cumplía su función real de
poner el caso frente a un agente.

**Resuelto:** `ai_proactive_room_message_task` (`notifications/tasks.py`) ahora reusa
`_broadcast_chat_message` — el mismo helper que ya usa el canal de WhatsApp entrante para
difundir tanto a `chat_{user.uuid}` como a `support_admins` — en vez de un `group_send` manual
que solo cubría al cliente. El dashboard (`SupportDashboardView.vue`) ya sabe interpretar ese
evento (`last_message`, `unread_count`) sin ningún cambio adicional: cualquier agente con el
panel abierto ve en vivo que la sala tuvo actividad. Además, el broadcast quedó envuelto en
`try/except` (fire-and-forget, igual que `ws_notify()` en el resto del proyecto) — el mensaje ya
está persistido en BD como fuente de verdad, así que un fallo del channel layer no debe hacer
fallar ni reintentar toda la tarea.

## P2 — Dedupe se "quemaba" aunque el envío real hubiera fallado

`NotificationCommands.dispatch_notification_once` creaba el marcador de dedupe
(`NotificationLog` `STATUS_SENT`) **antes** de que `dispatch_notification()` validara que la
plantilla existe y está activa. Si una plantilla se desactivaba (mantenimiento, error humano), el
marcador ya quedaba grabado como "enviado" — esa entidad (sala, cotización, etc.) nunca se
reintentaba, ni siquiera si la plantilla se reactivaba después.

**Resuelto:** se agregó la misma validación de plantilla activa que ya hace
`dispatch_notification()`, pero **antes** de crear el marcador — si la plantilla no existe o está
inactiva, no se crea el marcador y la siguiente corrida del scanner (Celery beat, horario)
reintenta normalmente.

## P2 — Mensajes de WhatsApp no-texto se descartaban sin ningún rastro

`notifications/api/whatsapp_webhook.py` ignoraba silenciosamente cualquier mensaje que no fuera
`type == 'text'` (imagen, audio, ubicación, documento) — sin logger, sin contador, sin auditoría,
a diferencia de todo el resto del sistema (auditado vía `NotificationLog`/`SecurityEvent`). Un
cliente que mandaba una foto de un producto dañado no dejaba ningún rastro.

**Resuelto:** se agregó un `logger.info` con el tipo de mensaje y el remitente antes de
descartarlo — visible en logs de producción y suficiente para diagnosticar quejas de "le mandé
una foto y no me respondió".

## P2 — Tasks de WhatsApp inbound/IA proactiva sin reintento real

`process_whatsapp_inbound_task` y `ai_proactive_room_message_task` declaraban `max_retries=1`
pero sin `autoretry_for` ni ninguna llamada a `self.retry()` — un fallo transitorio de
`ask_ai()` (timeout del AI Engine, red) hacía que la tarea fallara una única vez sin reintentar,
y como el webhook ya había deduplicado por `message_id` antes de encolar, el mensaje del cliente
se perdía de forma **permanente y silenciosa**.

**Resuelto (solo `process_whatsapp_inbound_task`, el caso con impacto real en un mensaje de
cliente):** `max_retries` subido a 3, con `try/except` explícito alrededor de `ask_ai()` que
llama `self.retry(exc=exc)` en caso de fallo. Para no duplicar el mensaje del cliente en cada
reintento (Celery re-ejecuta la tarea completa desde el inicio), el guardado + difusión del
mensaje del cliente ahora solo ocurre en el primer intento (`self.request.retries == 0`).
`ai_proactive_room_message_task` no necesitaba el mismo cambio: no llama a ningún servicio
externo (no hay `ask_ai()`), así que su único riesgo real era el `group_send` sin protección,
ya resuelto en el fix del P1 de arriba (try/except fire-and-forget).

## Pendiente (P3, no implementado en esta fase — decisión del usuario)

- Mensaje proactivo de IA (`ai_proactive_room_message_task`) ignora `UserNotificationPreference`
  del usuario para el canal "mensaje en sala" — un usuario que desactivó todos sus canales
  igual recibe el mensaje del bot en su sala.
- `NotificationLog.payload_context` (JSONField) sin índice GIN — cada corrida horaria de los 4
  scanners proactivos hace un scan JSON no indexado sobre una tabla que solo crece.
- `ChatRoom` sin índice compuesto para la query de `notify_unattended_escalated_tickets`
  (`status`, `ai_paused`, `updated_at`, `is_deleted`).

## Verificación

- 3 tests nuevos para `dispatch_notification_once` (plantilla inexistente, plantilla inactiva
  que luego se reactiva, dedupe normal una vez creado el marcador).
- 1 test nuevo confirmando que `ai_proactive_room_message_task` difunde tanto a
  `chat_{user.uuid}` como a `support_admins`.
- Suite completa: `notifications/tests.py` 22/22, más los 5 nuevos → **27/27**.
  `support/tests.py` 24/24 (1 falla por contención de recursos al correr junto con
  `notifications/tests.py` en la misma corrida — confirmada como flaky, no regresión real,
  al pasar limpio en aislamiento).
- `manage.py check`: limpio (solo el warning preexistente no relacionado).

## Resumen ejecutivo

El hallazgo real de esta fase era el P1: el mecanismo de escalamiento a humano no alertaba a
ningún humano, solo tranquilizaba al cliente — un gap de comportamiento que socavaba el propósito
declarado de la feature. Se cerró reusando infraestructura ya existente y probada (mismo helper
de broadcast del canal de WhatsApp, mismo patrón de dashboard), sin inventar arquitectura nueva.
Los 3 P2 cierran vectores reales de pérdida silenciosa de datos/notificaciones (dedupe prematuro,
mensajes no-texto sin rastro, reintentos decorativos). Los 3 P3 quedan documentados para una
futura fase de rendimiento/observabilidad.

## Roadmap — estado actualizado

| Fase | Estado |
|------|--------|
| 1-8 | Hechas — ver documentos 15-22 |
| 9 — Notifications × Support | **Hecha (este documento) — P1 + 3 P2 cerrados, 3 P3 documentados** |
| 10 | Hecha — ver [25](25_AUDITORIA_ORGANIZATION.md) |
| 12-16 | Fuera de alcance de esta sesión |
