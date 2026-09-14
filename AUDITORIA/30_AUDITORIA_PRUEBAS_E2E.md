# 30 — Auditoría Enterprise: Pruebas / Cobertura E2E (Fase 16, final)

> **Fase 16 completada y cerrada 2026-08-03** — última fase del plan de
> [15](15_AUDITORIA_SUPPORT_OMNICANAL.md)-[29](29_AUDITORIA_OBSERVABILIDAD.md). Foco: cobertura
> de pruebas sobre todo lo tocado en las 15 fases anteriores, y verificación de imports en vivo
> (lección de la [Fase 13](27_AUDITORIA_MARKETING.md)) para descartar más `ImportError` ocultos.

## Hallazgo real más importante: bug funcional, no solo gap de cobertura

Al investigar si existía un test que cubriera el flujo omnicanal completo (cliente por
WhatsApp → IA responde → escalamiento a humano → agente responde → cliente ve la respuesta),
se confirmó que **no existe**, y al investigar por qué, se descubrió que **no puede existir
porque el flujo mismo está roto**: `WhatsAppClient().send_text()` solo se invocaba desde
`process_whatsapp_inbound_task` (la respuesta automática de la IA) — grep exhaustivo de
`send_text|WhatsAppClient()` en todo el repo confirmó que **ningún otro código** llamaba a ese
cliente. La rama de respuesta del agente humano en `support/consumers.py::receive()` únicamente
hacía `group_send` por WebSocket.

**Impacto real**: un cliente que escribe exclusivamente por WhatsApp (sin abrir nunca el widget
web, por tanto sin conexión WS activa) que llega a tener su ticket escalado a un humano
(`ai_paused=True`) y recibe una respuesta de un agente desde `/panel/soporte`, **nunca la
recibe** — la respuesta solo existe en el broadcast WS, que no tiene ningún destinatario
conectado. El cliente se queda esperando indefinidamente en WhatsApp.

**Resuelto:** `notifications/tasks.py::send_whatsapp_agent_reply_task` (nuevo) — cuando un
agente responde desde el panel, además del `group_send` existente, se reenvía el texto por
WhatsApp si el usuario tiene un teléfono colombiano válido (misma resolución —`_resolve_phone`—
que ya usa `dispatch_notification` para el canal WhatsApp transaccional). Sujeto a la ventana de
servicio de 24h de Meta: si Meta la rechaza (`WhatsAppApiError`), se registra como fallo no
bloqueante, mismo criterio que el resto de envíos WhatsApp del proyecto — no se inventa manejo
nuevo. Conectado desde `support/consumers.py` vía un helper `_dispatch_whatsapp_agent_reply`
(`@database_sync_to_async`, mismo patrón que el resto de llamadas sync-desde-async ya
establecido en ese archivo, ej. `_message_flood_limited`).

**Decisión de alcance explícita (elegida por el usuario):** reenviar siempre que el usuario
tenga teléfono válido, sin agregar un campo de canal/origen a `ChatRoom` — la alternativa más
correcta a largo plazo (rastrear explícitamente si la conversación se originó por WhatsApp)
queda fuera de esta fase, documentada como mejora futura si el volumen de falsos positivos
(reenviar por WhatsApp una respuesta a un ticket 100% web) resulta molesto en la práctica.

## Otros hallazgos de cobertura (P2-P3, documentados, no corregidos en esta fase)

- **`notifications/clients/sms.py`/`send_sms_notification_task`**: import verificado limpio en
  vivo (no es un `ImportError`), pero nunca se ejecuta en ningún test — las 3 rutas de error
  (`SmsConfigError`, `SmsBridgeUnreachableError`, `SmsApiError`) y el flujo de éxito no tienen
  cobertura. El mismo patrón de import diferido (`from ... import SmsClient` dentro del cuerpo
  de la función) que ocultó el bug de Fase 13 está presente aquí también.
- **`operations/consumers.py`/`routing.py`** (WS de tracking en tiempo real): import verificado
  limpio, pero `operations/tests.py` no usa `WebsocketCommunicator` en absoluto — cobertura cero
  para el consumer de tracking, asimetría notable frente a `support/tests.py`.
- **`ai_engine/`**: sin ningún `tests.py`/`test_*.py` en Python — el "cerebro" que decide qué le
  responde al cliente no tiene cobertura automatizada más allá de scripts `.ps1` manuales. Import
  verificado limpio dentro de su propio contenedor (`ecommerce_sintel_ai`, namespace de import
  distinto al de Django). No es un `ImportError`, pero es el componente más crítico del sistema
  sin ningún test Python.
- **`notifications/management/commands/audit_notifications.py`**: nunca invocado vía
  `call_command` en ningún test.

## Verificación de imports en vivo (obligatoria, lección de Fase 13)

Se importaron activamente todos los módulos candidatos a "nunca tocados por un test" —
**ningún `ImportError` nuevo encontrado**. `operations.consumers`, `operations.routing`,
`notifications.clients.sms`, `notifications.management.commands.audit_notifications`,
`ai_engine.main`, `ai_engine.tools.support_tools` — todos importan limpio.

## Corrida combinada de las 7 suites tocadas en toda la sesión

```
support/tests.py notifications/tests.py organization/tests.py operations/tests.py
marketing/tests.py security/tests.py ecommerce/tests.py
```

**103 passed, 0 failed** en la primera corrida (antes del fix de esta fase) — sin colisión de
nombres de usuario, sin efecto de orden entre apps. Tras agregar los 4 tests de esta fase, la
corrida combinada de `support/tests.py` + `notifications/tests.py` se repitió limpia (ver
sección Verificación abajo).

Único punto menor (P4): un warning de teardown de BD ("being accessed by other users") tras
`ecommerce/tests.py::ProductionSettingsDebugFailSafeTestCase` al correr junto con las demás
suites — no rompe la corrida, ya visto como comportamiento benigno en fases anteriores (Fase 11).

## Verificación

- 3 tests nuevos para `send_whatsapp_agent_reply_task` (reenvía si hay teléfono válido; no
  reenvía si no hay teléfono; un rechazo de Meta no propaga excepción).
- 1 test de integración WS nuevo (`test_respuesta_de_admin_dispara_reenvio_por_whatsapp`) —
  cliente conecta, admin conecta, cliente escribe, admin responde, se verifica que el bridge a
  WhatsApp se dispara con el `user_id` y texto correctos.
- `manage.py check`: limpio.

## Resumen ejecutivo

La Fase 16 se planteó como "cobertura de pruebas" pero, siguiendo la misma metodología que
destapó el `ImportError` de Marketing en la Fase 13 (verificar en vivo en vez de solo leer
código), llevó a descubrir el hallazgo funcional más importante de las últimas fases: la promesa
central de todo este plan de 16 fases — un "centro de servicio al cliente inteligente
omnicanal" — tenía una brecha real en su flujo más importante (WhatsApp → humano → WhatsApp).
Se cerró reusando exactamente la infraestructura ya validada en fases anteriores
(`_resolve_phone`, `WhatsAppClient`, patrón de tarea Celery con `autoretry_for`), sin inventar
arquitectura nueva.

## Roadmap — estado final

| Fase | Estado |
|------|--------|
| 1-10 | Hechas — ver documentos 15-25 |
| 11 — Seguridad | Hecha — ver [23](23_AUDITORIA_SEGURIDAD.md) |
| 12 — Core | Hecha — ver [26](26_AUDITORIA_CORE.md) (sin hallazgos) |
| 13 — Marketing/CRM | Hecha — ver [27](27_AUDITORIA_MARKETING.md) (ImportError P0 + P1 + P2) |
| 14 — Operations | Hecha — ver [28](28_AUDITORIA_OPERATIONS.md) |
| 15 — Observabilidad | Hecha — ver [29](29_AUDITORIA_OBSERVABILIDAD.md) |
| 16 — Pruebas | **Hecha (este documento) — bug funcional real cerrado (bridge WhatsApp↔agente)** |

**Las 16 fases del plan quedan completas.**
