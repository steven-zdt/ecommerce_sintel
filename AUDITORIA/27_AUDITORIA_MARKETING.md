# 27 — Auditoría Enterprise: Marketing/CRM (Fase 13)

> **Fase 13 completada y cerrada 2026-08-03** — continúa el plan de
> [15](15_AUDITORIA_SUPPORT_OMNICANAL.md)-[26](26_AUDITORIA_CORE.md). `marketing/` está bien
> aislado de `support/` (patrón Pull correcto vía `ShopSummaryProvider`/`RentingSummaryProvider`/
> `ServicesSummaryProvider`, cero imports directos) — sin acoplamiento arquitectónico peligroso.
> Alcance aprobado por el usuario: P1 + P2. Los 2 P3 (Customer360 sin campañas por falta de FK a
> usuario en `CampaignLog`; sin supresión de campañas para clientes con ticket abierto) quedan
> documentados como pendientes.

## P0 real, no reportado por la auditoría inicial — el agente autónomo nunca pudo ejecutarse

Al escribir el primer test que realmente **importa** `marketing/agent/brain.py` (los hallazgos
de la auditoría se basaron en lectura de código, no en ejecución), apareció un `ImportError` a
nivel de módulo: tanto `marketing/agent/brain.py` como `marketing/tasks.py::send_via_channel_task`
importaban `CampaignCommands` de `marketing.services.commands` — una clase que **nunca existió
ahí** (el nombre real, desde el commit inicial del repositorio, siempre fue `MarketingCommands`).

Impacto real: el agente autónomo de marketing (`run_marketing_agent_task`, disparado manual o
por Celery Beat) **jamás pudo completar un solo ciclo** sin fallar en el import, antes de llegar
a cualquier lógica de negocio — ni siquiera al bloque `try/except` que loggea errores en
`AgentRun`, porque el `ImportError` ocurre al cargar el módulo, no al ejecutar `run()`. Y aunque
ese import se hubiera arreglado sin tocar `tasks.py`, cualquier `CampaignLog` que llegara a
encolarse habría fallado igual en `send_via_channel_task` por el mismo motivo. Es decir: **el
pipeline completo de envío de campañas, en cualquier camino posible, estaba roto desde el
commit inicial.**

**Resuelto:** renombrado el import/uso a `MarketingCommands` (el nombre real de la clase) en
ambos archivos.

## P1 — El agente rompía silenciosamente email/WhatsApp con un destinatario falso

`MarketingAgent.run()` despachaba siempre con `recipient="broadcast"` — un string literal, sin
importar qué canal eligiera el LLM. Los 6 canales sociales (facebook, instagram, youtube, tiktok,
x, google_business) ignoran `recipient` (publican a nivel de página/cuenta), así que no fallan.
Pero `email_channel.py` (`to=[message.recipient]`) y `whatsapp_channel.py`
(`"to": message.recipient`) usan ese string como dirección real — si el LLM elegía `email` o
`whatsapp`, el envío fallaba **siempre**, sin ninguna alerta sobre esa tasa de fallo sistemática.

**Resuelto:** se filtran los canales elegidos por el LLM a los realmente broadcast
(`marketing/channels/registry.py::BROADCAST_CHANNELS`) antes de crear la campaña y despachar.
Si el LLM elige únicamente canales que requieren destinatario real (email/whatsapp), el ciclo
se marca `completed_no_action` y no se despacha nada — en vez de fallar en silencio. Se decidió
**no** intentar resolver una audiencia real para email/whatsapp en este fix: el flujo actual del
agente es de un solo disparo sin lista de destinatarios, y construir esa resolución de audiencia
es una feature mayor, desproporcionada para un fix incremental (mismo criterio ya aplicado en la
[Fase 7](21_AUDITORIA_CUSTOMER360.md) al declinar unificar módulos sin un selector limpio).

## P2 — Sin rate-limit propio, comparte cuota de Meta con soporte transaccional

`marketing/channels/whatsapp_channel.py` usa el mismo `phone_number_id`/token de Meta que
`notifications/clients/whatsapp.py` (envío transaccional de soporte, OTPs) — confirmado vía
`OrganizationSelector.get_integration_settings()`. Sin ningún límite propio, una ráfaga de
campañas de marketing podía consumir la cuota de mensajería de esa cuenta y degradar/bloquear
mensajes transaccionales de soporte que comparten el mismo número.

**Resuelto:** límite de 20 envíos/hora para el canal `whatsapp` en `MarketingCommands.dispatch()`,
mismo patrón atómico `cache.add()`/`cache.incr()` ya usado en
`notifications/services/commands.py::_channel_rate_limited` y
`support/services/commands.py::is_message_flood_limited`. Los demás canales no se ven afectados.

## Pendiente (P3, no implementado en esta fase)

- `CampaignLog.recipient` es un `CharField` libre (email/teléfono/page_id), sin `ForeignKey` a
  usuario — Customer 360 no puede mostrar "el cliente recibió N promociones esta semana" sin un
  join por string. A diferencia de la Fase 7 (decisión explícita por falta de selector), aquí sí
  hay un `MarketingSelector` limpio, pero el modelo no permite el join.
- Sin supresión de campañas para clientes con `ChatRoom` abierto — un cliente reclamando en
  soporte puede recibir una campaña promocional en paralelo sin ningún check.

## Verificación

- 4 tests nuevos: filtro de canales broadcast (con y sin canales dispatchable), rate-limit de
  whatsapp (bloquea tras el límite, no afecta otros canales).
- `marketing/tests.py`: **13/13** (9 preexistentes + 4 nuevos) — y por primera vez, estos tests
  realmente ejecutan `MarketingAgent.run()` en vez de solo tocar permisos/modelos, lo que
  destapó el `ImportError` P0 de arriba.
- `manage.py check`: limpio (solo el warning preexistente no relacionado).

## Resumen ejecutivo

El hallazgo más importante de esta fase no estaba en la lista original de la auditoría: el
pipeline completo de envío de campañas de marketing (agente autónomo + task de Celery) llevaba
roto por un `ImportError` desde el commit inicial del repositorio, invisible porque ningún test
existente importaba realmente esos módulos. El P1 (destinatario falso en email/WhatsApp) y el P2
(cuota de Meta compartida con soporte) eran hallazgos reales pero secundarios frente a esto —
ambos quedan corregidos en el mismo cambio, y ahora sí son alcanzables porque el import ya no
rompe antes de llegar a esa lógica.

## Roadmap — estado actualizado

| Fase | Estado |
|------|--------|
| 1-10 | Hechas — ver documentos 15-25 |
| 12 | Hecha — ver [26](26_AUDITORIA_CORE.md) (sin hallazgos) |
| 13 — Marketing/CRM | **Hecha (este documento) — ImportError P0 + P1 + P2 cerrados, 2 P3 documentados** |
| 14 | Hecha — ver [28](28_AUDITORIA_OPERATIONS.md) |
| 15-16 | Fuera de alcance de esta sesión |
