# 15 — Auditoría Enterprise del módulo Support (rumbo a Centro de Atención Omnicanal)

> **Fase 1 completada 2026-07-31** — diagnóstico global de solo lectura, cero cambios de código.
> Origen: el mismo día se encontró y corrigió en producción un bug real de desconexión permanente
> del chat de soporte (WebSocket nunca refrescaba el JWT antes de conectar — ver §0). A partir de
> ahí el usuario solicitó una auditoría Enterprise de 16 fases para preparar `support` como Centro
> Inteligente de Atención Omnicanal. Esta Fase 1 (auditoría global, sin tocar lógica de negocio) ya
> se ejecutó y es la base de las fases siguientes, que se ejecutarán de forma incremental — el plan
> completo (Fases 2-16: sync AI Engine, omnicanalidad, Customer 360, reconexión enterprise,
> escalabilidad, seguridad, observabilidad, pruebas) **no se ha ejecutado todavía**, solo esta
> Fase 1. Ver §Roadmap al final.

## §0. Contexto inmediato — bug de producción resuelto el mismo día

Antes de esta auditoría, el chat de soporte quedaba en "Desconectado" permanente en producción: el
WebSocket (`support/channels_auth.py`) se autentica una sola vez al conectar, y como
`ACCESS_TOKEN_LIFETIME=15min` y el interceptor de Axios que refresca sola el token nunca corre para
conexiones WS, cualquier pestaña abierta más de 15 min quedaba reintentando para siempre con un
token vencido. Corregido en `SupportChatWidget.vue` y `SupportDashboardView.vue` (refresco
proactivo antes de cada intento de conexión) más manejo explícito de sesión muerta (logout +
aviso, en vez de loop infinito silencioso). Se agregó logging real en `channels_auth.py`
(antes tragaba la excepción en silencio — exactamente el mismo patrón detectado de nuevo en
§C3 de esta auditoría, en otro archivo). Desplegado y verificado en producción.

---

## A. Documentación desactualizada — `support/.AGENT/docs/ARQUITECTURA_COMPLETA_SUPPORT.md`

**A1. El doc afirma que `support` no tiene REST API pública — falso.** (P3)
Líneas 22-24 y 285-289 del doc dicen que no existe y que asumir lo contrario es un anti-patrón.
Realidad: `ecommerce/urls.py:69` registra `api/v1/support/` → `RateConversationView` (CSAT),
consumido activamente por `SupportChatWidget.vue:223`. Ya detectado antes en
`Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md:1204-1236,1554` (2026-07-23) como
pendiente — nunca se corrigió.

**A2. Sección "Notificaciones" (líneas 265-271) desactualizada.** (P3)
Dice que `support` nunca llama a `NotificationCommands.dispatch_notification()`. Realidad:
`support/tasks.py:38` sí lo hace (`dispatch_notification_once`, Fase 11 Proactividad, cron horaria
vía migración `0007_seed_notify_stale_tickets_periodic_task.py`).

**A3. Estructura de directorios (líneas 28-48) incompleta.** (P3)
Faltan `services/customer360.py`, `tasks.py`, `api/views.py`, `api/urls.py`.

**A4. Modelos documentados incompletos.** (P3)
Falta `ChatRoom.csat_rating/csat_comment/csat_rated_at` (migración `0008`) y `ChatRoomContext`
(constraint `chatroomcontext_exactly_one_target`, FKs a `orders.Order`/`renting.RentalRequest`).

**A5. Servicios documentados incompletos.** (P3)
Falta `ChatAnalyticsSelector` (Fase 9, KPIs de fallback/handoff/tokens en `SupportDashboardView.vue`).

---

## B. Bugs de correctitud

**B1. Los mensajes del bot IA se atribuyen al CLIENTE en el panel admin vía REST — inconsistente con el WebSocket.** (P2)
`support/api/serializers.py:41-42`:
```python
def get_is_admin(self, obj):
    return bool(obj.sender.is_staff and obj.sender.is_superuser)
```
El usuario-bot (`ai_bridge.py::get_ai_bot_user`) se crea con `is_active=False` pero
`is_staff`/`is_superuser` en su default `False` → este serializer devuelve `is_admin=False` para
cualquier mensaje del bot. Pero `consumers.py:151-155` (broadcast en vivo por WS) sí marca
`'is_admin': True` explícitamente para el bot. Impacto real: `SupportDashboardView.vue::selectRoom()`
carga el historial vía REST (`ChatRoomSerializer`), así que cualquier mensaje histórico de la IA se
renderiza con el **email del cliente** como remitente y burbuja de estilo "cliente"
(`SupportDashboardView.vue:144`, `bubble-user`) — un agente humano puede creer que el cliente
escribió algo que en realidad generó el asistente.
*Sugerencia:* extraer la regla "es el bot" a un único lugar (selector o método de modelo) reusado
por el serializer y por `consumers.py`.

**B2. El cliente puede seguir escribiendo por WS en una sala ya `CLOSED`.** (P3)
`consumers.py:75-97` (rama cliente de `receive()`) no vuelve a chequear `room.status` antes de
guardar el mensaje; la rama admin sí filtra `status=OPEN` (`_get_room_and_client_uuid`). Hoy la
única protección es de UI (el widget oculta el input tras `room_closed`). Un tab desactualizado o
un cliente WS no oficial puede insertar mensajes en una sala cerrada que quedan sin respuesta (la
IA tampoco responde ahí) y sin ruta de reapertura.
*Sugerencia:* replicar en la rama cliente la misma validación de estado que ya existe del lado admin.

---

## C. Seguridad y observabilidad

**C1. El throttling de IA se aplicó al endpoint interno secundario, no al canal WS primario que realmente dispara el costo del LLM.** (P2)
`support/api/internal_ai.py:70-75` tiene `ScopedRateThrottle` con comentario explícito sobre el
riesgo de costo (D-03, auditoría enterprise previa). Pero el punto de entrada real —
`SupportChatConsumer.receive()` (dispara `_ai_reply` en cada mensaje si `is_ai_mode_active`) — no
tiene ningún throttling. Hoy `AI_SUPPORT_CHAT_ENABLED` está apagado en producción, pero es
exactamente el gap que hay que cerrar antes de activar IA ahí.
*Sugerencia:* throttling por usuario/sala en `receive()` antes de invocar `_ai_reply`.

**C2. Una caída total del AI Engine es invisible — no queda ninguna señal ni para el agente admin ni para el cliente.** (P2)
`ChatAnalyticsSelector.get_summary()` calcula sus métricas solo desde `ai_metrics` ya persistidos.
Cuando `ask_ai()` devuelve `None` (motor caído o timeout, `ai_bridge.py:64-69`), `_ai_reply`
simplemente retorna sin guardar nada (`consumers.py:145-150`); una excepción inesperada solo se
loguea (`consumers.py:168-170`). No se crea ningún registro, así que ni el dashboard muestra un
contador de "motor no disponible" ni el cliente recibe ningún mensaje de degradación — el chat
queda en silencio total.
*Sugerencia:* persistir un marcador cuando `ask_ai()` degrada a `None`, y exponer un contador
dedicado en `ChatAnalyticsSelector.get_summary`.

**C3. `except Exception` genérico en `customer360.py:11-15` oculta errores reales.** (P4)
```python
def _shipment_status(order):
    try:
        return order.shipment.status
    except Exception:
        return None
```
El único fallo esperado es `Shipment.DoesNotExist`. Mismo patrón corregido hoy en
`channels_auth.py` (§0) — vale aplicar el mismo criterio aquí.

---

## D. Duplicación (DRY)

**D1. Lógica "contexto → label" duplicada entre WS y REST.** (P3)
`consumers.py:243-253` (`_get_room_contexts`) y `serializers.py:13-30`
(`ChatRoomContextSerializer`) implementan por separado la misma rama
`ORDER → "Pedido #{id}"` / `RENTAL → "Alquiler #{id}"`. Cualquier cambio de formato debe hacerse en
dos sitios o divergen.
*Sugerencia:* extraer un único helper (método de modelo o función en `selectors.py`).

---

## E. Cobertura de tests

**E1. `RateConversationView` (CSAT REST) sin cobertura HTTP.** (P2)
El único test existente prueba `ChatCommands.rate_conversation` directo, nunca la vista/URL/permisos
reales. El propio comentario del view documenta un fix de disclosure de seguridad (D-04, auditoría
previa: antes cualquier usuario autenticado podía distinguir 200/400 vs 404 para un `room_uuid`
ajeno) que hoy no tiene ningún test de regresión.

**E2. `AiOpenSupportTicketView` (Human Handoff interno) sin ningún test en todo el repo.** (P2)
Cubre transcript dump, flip de `ai_paused`, notificación a `support_admins` vía Channels,
`attach_context`, y `SecurityEvent.AI_ACTION_EXECUTED` — todo sin probar.

**E3. `support/tasks.py::notify_unattended_escalated_tickets` sin ningún test.** (P3)

---

## Lo que SÍ está bien (no re-litigar en fases siguientes)

- Service Layer respetado: toda escritura pasa por `ChatCommands`, toda lectura por
  `ChatSelector`/`ChatAnalyticsSelector`/`Customer360Selector` — sin lógica de negocio embebida en
  `consumers.py`/`views.py`.
- `dashboard.SupportAdminOrchestrator` es un passthrough delgado real, sin duplicar Commands/Selectors.
- Un solo consumer WS (`SupportChatConsumer`) — sin duplicación de canales.
- Contrato `ai_bridge.py::ask_ai()` (`{message, conversation_id}` + `Authorization: Bearer`) coincide
  exactamente con lo que expone `ai_engine/main.py` (`ChatRequest`/`get_validated_token`) — sin
  mismatch de contrato con el AI Engine.
- Communication Center (`useCommunication.js`, deep-link directo a WhatsApp) y `support` (chat vía
  Channels) son deliberadamente sistemas separados, sin solapamiento de código real.

---

## Matriz de prioridad (P0-P4)

**Actualizado 2026-07-31 (mismo día): los 5 hallazgos P2 se cerraron como lote incremental,
verificados con 17/17 tests pasando (11 preexistentes + 6 nuevos) y confirmación visual en vivo
en dev antes de desplegar a producción.**

| # | Hallazgo | Severidad | Módulos | Estado |
|---|----------|-----------|---------|--------|
| B1 | Bot IA atribuido al cliente en REST | **P2** | support/api, frontend dashboard | **Resuelto** — `ChatMessage.is_from_agent` como única fuente de verdad, reusado por serializer y consumer |
| C1 | Sin throttle en el canal WS que dispara IA | **P2** | support/consumers.py | **Resuelto** — `ai_bridge.is_ai_rate_limited()`, 20 turnos/10min por sala vía cache atómico |
| C2 | Caída del AI Engine invisible en métricas | **P2** | support/services, ai_bridge | **Resuelto** — marcador `ai_metrics.engine_unavailable`, aviso real al cliente, KPI nuevo "Motor IA no disponible" en el dashboard |
| E1 | CSAT REST sin test de regresión del fix de disclosure | **P2** | support/tests.py | **Resuelto** — 3 tests nuevos (anónimo, sala ajena→404, éxito+validación) |
| E2 | Human Handoff interno sin ningún test | **P2** | support/tests.py | **Resuelto** — 3 tests nuevos (sin mensaje→400, éxito con transcript+pausa+SecurityEvent, orden ajena→404) |
| A1 | Doc dice que no existe REST API (sí existe) | P3 | doc | **Resuelto** |
| A2-A5 | Doc desincronizado (notifs, estructura, modelos, servicios) | P3 | doc | **Resuelto** |
| B2 | Cliente puede escribir en sala CLOSED por WS | P3 | support/consumers.py | **Resuelto** — `_room_is_open()` + test de regresión |
| D1 | Lógica de contexto duplicada WS/REST | P3 | support | **Resuelto** — `ChatRoomContext.target_uuid`/`.label` |
| E3 | Cron de tickets sin escalar sin test | P3 | support/tests.py | **Resuelto** — test con 4 salas (candidata + 3 exclusiones) + dedupe |
| C3 | `except Exception` genérico en customer360.py | P4 | support/services | **Resuelto** — excepción específica `Shipment.DoesNotExist` |

**Los 11 hallazgos de esta Fase 1 (5 P2 + 6 P3/P4) están cerrados.** Verificado con 19/19 tests
pasando, `manage.py check` limpio, sin migraciones pendientes, y desplegado a producción en 2
lotes el mismo día (2026-07-31).

---

## Resumen ejecutivo

El módulo `support` tiene una base arquitectónica sólida (Service Layer respetado, un solo
consumer, contrato AI Engine correcto) — nada de lo encontrado exige reescritura, todo es
corrección incremental. El hallazgo más serio es funcional, no cosmético: los mensajes del bot IA
se muestran atribuidos al cliente en el panel admin vía REST mientras que por WebSocket se
muestran correctamente como agente (B1) — impacta directamente la confianza del historial que ve
un agente humano. Hay dos gaps de seguridad/costo concretos: el throttling de IA se aplicó al
endpoint interno secundario pero no al canal WS primario que realmente dispara las llamadas al LLM
(C1), y una caída completa del AI Engine no deja ninguna señal ni al agente ni al cliente (C2).
Dos superficies con implicancias de seguridad/costo real — CSAT (fix de disclosure ya aplicado
pero sin test) y Human Handoff interno — no tienen ninguna prueba de regresión (E1, E2). La
documentación de arquitectura del módulo está desincronizada del código en 5 puntos, uno de ellos
(A1) ya detectado y dejado pendiente en `IMPLEMENTATION_SUMMARY.md` desde 2026-07-23 sin corregirse.
Ninguno de estos hallazgos es crítico hoy (IA deshabilitada en producción), pero P2 (B1, C1, C2,
E1, E2) debería cerrarse antes de activar el chat con IA de forma amplia o de avanzar hacia
omnicanalidad (Fases 2+).

---

## Roadmap — estado de las 16 fases solicitadas

| Fase | Contenido | Estado |
|------|-----------|--------|
| 1 | Auditoría global | **Hecha (este documento)** |
| 2 | Sincronización con AI Engine | Pendiente |
| 3 | Sincronización documental cross-módulo | Pendiente (A1-A5 de este doc son el punto de partida) |
| 4 | Producción (WS, proxy, JWT) | Bug crítico ya resuelto el mismo día (§0); resto pendiente |
| 5 | Communication Center | Pendiente (confirmado: hoy sin solapamiento real) |
| 6 | Omnicanalidad | Pendiente |
| 7 | Customer 360 | Pendiente (`Customer360Selector` ya existe como base) |
| 8 | AI (ai_bridge, RAG, observabilidad) | Pendiente |
| 9 | Reconexión automática enterprise | Pendiente |
| 10 | Escalabilidad (100-10000 usuarios) | Pendiente |
| 11 | Seguridad | Parcialmente cubierta por C1/E1/E2 de este doc |
| 12 | Observabilidad | Parcialmente cubierta por C2 de este doc |
| 13 | Frontend (design system, a11y, dark mode) | Pendiente |
| 14 | Documentación | Pendiente (A1-A5 son el punto de partida) |
| 15 | Plan de corrección priorizado | Matriz P0-P4 de este doc es la primera versión |
| 16 | Pruebas (unit/integration/stress/chaos) | Pendiente (E1-E3 son los gaps ya identificados) |

Siguiente paso sugerido: cerrar los 5 hallazgos P2 (B1, C1, C2, E1, E2) como un lote incremental
antes de avanzar a Fase 2 (sync AI Engine) — son de bajo riesgo de regresión y cierran exactamente
los gaps que las fases de omnicanalidad/escalabilidad asumirían ya resueltos.
