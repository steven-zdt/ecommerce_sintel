# 19 — Auditoría Enterprise: Communication Center, canales y evaluación de "Conversation Manager" (Fase 5)

> **Fase 5 completada 2026-08-01** — continúa el plan iniciado en
> [15](15_AUDITORIA_SUPPORT_OMNICANAL.md)-[18](18_AUDITORIA_PRODUCCION_RESILIENCIA_WS.md), todas
> cerradas el mismo día. A diferencia de las fases anteriores (buscar y corregir bugs), esta fase
> es principalmente una EVALUACIÓN de arquitectura — el brief original pedía sincronizar `support`
> con todos los canales de comunicación bajo "un único Conversation Manager". Se investigó a fondo
> y **se decidió NO implementar la fusión** (ver §2) — es prematura dado el estado real del
> código. Sí se encontró un gap operativo real y de bajo riesgo (M2) que vale la pena cerrar.

## §1 Verificación de completitud

**Email — ya conectado, sin gap.** La plantilla `ticket_soporte_sin_seguimiento` (que `support/tasks.py`
dispara) tiene `email_body` poblado y `dispatch_notification()` no restringe canales — el cliente
YA recibe un email real cuando su ticket escalado queda sin seguimiento 2h+, sin código adicional.
No existe (ni se esperaba) un flujo de email ENTRANTE que reabra una `ChatRoom` — confirmado por
ausencia total de parsing IMAP/inbound en el repo.

**Tickets — colisión de nombre, no de datos.** `operations.OperationTicket` (despacho/logística
de campo) y el uso coloquial de "ticket" en `support` (una `ChatRoom` con `ai_paused=True`) son
conceptos completamente distintos, sin ninguna FK cruzada ni acoplamiento real. Cosmético — vale
una nota aclaratoria en la doc de `support`, no una corrección de código.

**Customer 360 — sí está enganchado de verdad, con 2 campos calculados y nunca mostrados.**
Confirmado el trigger exacto: seleccionar una sala en `SupportDashboardView.vue` cambia el
`user-uuid` del panel, que dispara el fetch real (`watch(..., {immediate:true})`). Gap real: el
selector calcula `addresses` y `notifications` (últimas 15 `NotificationLog`) pero
`Customer360Panel.vue` nunca los renderiza — trabajo de backend ya pagado sin explotar en la UI.
(M1, P3, no implementado esta fase — ver "Pendiente" abajo.)

## §2 Evaluación: "Conversation Manager" único — recomendación clara

**No perseguirlo ahora.** Evidencia concreta: hoy existen 3 implementaciones de "conversación"
completamente aisladas, sin ningún modelo compartido (`grep` confirma cero clases
`Conversation`/`ConversationManager` genéricas en todo el repo):

| | `support` (chat WS) | WhatsApp entrante (Meta Cloud API) | `CommunicationCenter` (deep-link) |
|---|---|---|---|
| Persistencia | `ChatRoom`/`ChatMessage` real | **Ninguna** | **Ninguna** |
| IA | `ask_ai(..., conversation_id=f'room-{uuid}')` | `ask_ai(..., conversation_id=f'wa-{user_id}')` — **namespace distinto, memoria aislada** | No aplica |
| Visible para un agente humano | Sí, total | **No, nunca** | No, por diseño (fuera de Sintel) |

El hallazgo más concreto: el mismo `ask_ai()` se llama con `conversation_id` en namespaces
completamente distintos según el canal — un cliente que escribe por el widget web y luego por
WhatsApp obtiene dos memorias de IA totalmente aisladas, y **la conversación de WhatsApp con IA
no deja ningún rastro en BD** (ni `ChatMessage`, ni `NotificationLog` de la respuesta saliente) —
invisible para cualquier agente humano o auditoría, a diferencia de todo lo demás en el proyecto.

Fusionar de verdad exigiría: generalizar `ChatRoom` con un campo `channel`, reescribir
`process_whatsapp_inbound_task` para pasar por `ChatCommands`, resolver identidad cross-canal de
forma robusta (hoy WhatsApp matchea por los últimos 10 dígitos del teléfono, más débil que el JWT
del WS), y decidir qué hacer con `CommunicationCenter` (estructuralmente sin servidor en el
mensaje). Todo esto sobre modelos que las Fases 1-4 acaban de endurecer con 20+ tests, para un
chat con IA que **hoy está apagado en producción** y con volumen bajo — el ROI no lo justifica
todavía.

**Recomendación concreta:** en vez de la fusión completa, cerrar primero **M2** — que
`process_whatsapp_inbound_task` también escriba en la `ChatRoom` del usuario (reusando
`ChatCommands`, el mismo patrón que ya usa `ai_proactive_room_message_task` en sentido inverso).
Resuelve el riesgo operativo real (invisibilidad) con una función tocada, sin re-arquitectura. La
unificación del `conversation_id` de IA quedaría como una fase separada, solo si el volumen de
WhatsApp automatizado crece lo suficiente para justificarlo.

## Hallazgos menores

| # | Hallazgo | Severidad | Estado |
|---|---|---|---|
| M1 | `Customer360Panel.vue` no renderiza `addresses`/`notifications` que el selector ya calcula | P3 | Pendiente |
| M2 | Respuestas de IA vía WhatsApp entrante no dejan ningún rastro en BD — invisibles para agentes/auditoría | **P2** | **Resuelto** |
| M3 | Colisión de nombre "ticket" entre `operations.OperationTicket` y el uso coloquial en `support` | P4 | Pendiente (cosmético) |

## M2 — Resuelto (2026-08-01, mismo día)

`process_whatsapp_inbound_task` (`notifications/tasks.py`) ahora persiste ambos lados de la
conversación (mensaje del cliente + respuesta de la IA) en la `ChatRoom` real del usuario, reusando
`ChatCommands` — mismo patrón que `ai_proactive_room_message_task` ya usaba en sentido inverso.
Además hace `group_send` a `chat_{user.uuid}` y `support_admins` para que un agente con el
dashboard/widget abierto vea el mensaje en vivo, no solo al reabrir la sala.

**Deliberadamente fuera de alcance** (evaluado y pospuesto arriba, no un olvido): el
`conversation_id` de IA sigue siendo `wa-{user_id}` (namespace separado de `room-{uuid}` del canal
web — unificarlo es la fusión completa que esta fase recomendó NO hacer todavía), y este canal
sigue sin respetar `is_ai_mode_active`/`ai_paused` de la sala (coordinación cross-canal de Human
Handoff, mismo motivo).

Verificado: 2 tests nuevos (mensaje+respuesta persisten correctamente con métricas; si la IA no
responde, el mensaje del cliente igual se persiste, no se pierde solo porque el motor falló) +
suite completa de `notifications` y `support` sin regresiones (43/43 pasando). Desplegado a
producción.

## Resumen ejecutivo

Email y Tickets se verificaron sin gaps reales (email ya conectado vía el pipeline genérico;
"tickets" es solo colisión de nombre, sin acoplamiento de datos). Customer 360 está genuinamente
enganchado al dashboard, con 2 campos calculados y nunca mostrados (M1). El hallazgo central es
de arquitectura: "único Conversation Manager" es prematuro — 3 implementaciones de conversación
aisladas, sin modelo compartido, y fusionarlas tocaría modelos recién endurecidos para un canal
con IA hoy apagada en producción. El gap real y accionable es M2: las conversaciones de WhatsApp
con IA no dejan ningún rastro visible para un humano — un problema de visibilidad operativa, no
de arquitectura elegante, resoluble con una función tocada en vez de una re-arquitectura completa.

## Roadmap — estado actualizado

| Fase | Estado |
|------|--------|
| 1 — Auditoría global de `support` | Hecha, 11/11 cerrados |
| 2 — Sincronización con AI Engine | Hecha, 7/8 cerrados |
| 3 — Sincronización documental cross-módulo | Hecha, 4/4 cerrados |
| 4 — Producción y resiliencia WS | Hecha, 3/12 cerrados |
| 5 — Communication Center y canales | **Hecha, M2 cerrado (P2, el único accionable) — recomendación de NO fusionar canales se mantiene** |
| 6-16 | Pendientes |
