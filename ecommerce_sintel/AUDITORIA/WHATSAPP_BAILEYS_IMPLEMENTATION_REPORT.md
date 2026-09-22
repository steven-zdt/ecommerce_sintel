# WhatsApp Baileys Implementation Report

**Fecha de cierre de esta sesión de trabajo:** 2026-09-22
**Plan de referencia:** `PLAN_ACCION_MIGRACION_WHATSAPP_BAILEYS_SINTEL.md`
**Documentos relacionados:** `AUDITORIA/WHATSAPP_BAILEYS_PRE_MIGRATION_AUDIT.md` (Fase 0),
`AUDITORIA/WHATSAPP_BAILEYS_ARCHITECTURE.md` (detalle técnico Fase 1-24 + 21 dev, con evidencia
completa de cada verificación — este documento es el resumen ejecutivo, no lo reemplaza).

## Estado

**PARCIAL — EN PROGRESO, no COMPLETED.** Fases 1-20, 21 (solo dev), 22, 23, 24, 26 en `PASS`
verificado con evidencia real. **Fase 25 (E2E real) con avance real y significativo, agregado
después del cierre original de esta sesión**: el 2026-09-22, con autorización explícita del usuario,
se conectó el número de producción real (`+573144601878`) al gateway Baileys por primera vez —
pairing real exitoso, un bug real de condición de carrera encontrado en la sesión real recién
emparejada (`FileAuthStateStore`, crash loop tras cada `creds.update`) y corregido en caliente,
reconexión real sin re-escanear QR tras recrear el contenedor. Ver sección dedicada en
`AUDITORIA/WHATSAPP_BAILEYS_ARCHITECTURE.md` para el detalle completo. Fases 10, 21 (prod), 27, 29
(completa) siguen deliberadamente sin ejecutar. El plan exige `E2E = PASS` completo (Casos A-F) y
`LEGACY_REMOVED = PASS` para declarar `COMPLETED` — Casos A/B alcanzados, C-F no, así que este
reporte sigue sin declararlo.

## Versiones

| Componente | Versión | Evidencia |
|---|---|---|
| Baileys (`@whiskeysockets/baileys`) | **6.7.24** (fijada exacta) | Consultado en npm registry 2026-09-22; se descartó `7.0.0-rc14` (release candidate, no estable) |
| Node.js | v24.18.0 (host) / `node:24-bookworm-slim` (imagen Docker) | `engines.node >=20.0.0` cumplido |
| TypeScript | ^5.7.2 | — |
| Django | 5.2.13 | Ya en producción, sin cambios de versión |
| PostgreSQL | `pgvector/pgvector:pg16` | Ya en producción, sin cambios de versión ni de esquema para esta migración |

## Arquitectura

- **Gateway**: `whatsapp_gateway/` — Node.js + TypeScript + Fastify + Baileys. Servicio independiente,
  transporte puro (`BAILEYS = TRANSPORTE`). Contrato HTTP completo (Fase 1), modelo de 8 estados
  (Fase 2), `FileAuthStateStore` real (Fase 4, sin PostgreSQL — ver justificación en el archivo),
  Event Bus real hacia Django (Fase 6), rate limiting real en `/messages/send` (Fase 20).
- **Django**: `whatsapp/adapters/qr_web_session_adapter.py` — dejó de ser un stub incondicional; ahora
  es un stub *condicional* (`WHATSAPP_GATEWAY_ENABLED`/`WHATSAPP_GATEWAY_URL`), preservando el
  comportamiento original al 100% cuando no está configurado. `whatsapp/clients/gateway_client.py`
  (cliente HTTP Django→Gateway), `notifications/api/whatsapp_gateway_webhook.py` (receptor
  Gateway→Django), `notifications.tasks.process_whatsapp_gateway_inbound_task` (Celery, canal
  Baileys). Ningún cambio en `whatsapp/domain/*` (el dominio sigue sin conocer el mecanismo de
  conexión, verificado por los tests AST existentes).
- **Frontend**: `WhatsAppConnectionStatusView.vue` — QR real en vivo, acciones
  Conectar/Reconectar/Desconectar, estado distribuido por WebSocket (reusa `ws/support/chat/`
  existente). Build de producción verificado; **sin verificación visual en navegador real** (sin esa
  herramienta disponible en esta sesión).
- **Docker**: servicio `whatsapp_gateway` en `docker-compose.yml` (dev), sin `ports:` publicados,
  named volume para auth state, healthcheck real. **`docker-compose.prod.yml` sin tocar.**

## Sesión

- **QR**: `PASS`. Captura real de Baileys, codificado a data URL PNG, distribuido por el Event Bus y
  por WebSocket al panel.
- **Persistence**: `PASS`. `FileAuthStateStore` verificado con smoke test real (round-trip de
  credenciales y de una clave con `Buffer` real, recuperación de lock huérfano, `clear()`).
- **Reconnect**: `PARCIAL, con evidencia real fuerte`. Backoff exponencial + jitter probado con datos
  sintéticos. Además, verificado real: la sesión sobrevivió una recreación completa del contenedor
  (rebuild + recreate, no solo restart) y se reconectó vía `POST /session/reconnect` **sin volver a
  escanear QR**. No observada todavía bajo una caída de red real y repetida en el tiempo (horas/días).
- **Logout**: `PASS`, verificado en vivo dos veces — primero como cleanup del incidente de la Fase
  7-8, y otra vez cerrando la conexión real accidental descrita abajo.

## Mensajería

- **Receive**: `PASS` hasta el punto donde el plan lo permite en este pase — el evento llega
  normalizado, autenticado, deduplicado, y se encola `process_whatsapp_gateway_inbound_task` (solo si
  `WHATSAPP_CONNECTION_TYPE=QR_WEB_SESSION`, verificado con test real). El flujo completo hasta una
  respuesta real de WhatsApp requiere una sesión real conectada (Fase 25).
- **Send**: `PASS`. Camino de éxito y de fallo (`WhatsAppGatewayError`) verificados en vivo contra el
  gateway real, sin sesión activa.
- **Idempotency**: `PASS`, verificado con tráfico HTTP real (`WhatsAppIdempotencyGuard`, canal
  `"baileys"`).

## Integración

- **Customer**: `PASS`. `WhatsAppCustomerResolver` reutilizado tal cual, channel-agnostic.
- **ChatRoom**: `PASS` con una salvedad documentada — `WhatsAppConversationResolver` reutiliza el
  mismo `ChatRoom` sin duplicar salas, pero `conversation_id=f"wa-{user.id}"` (pasado a `ask_ai`) es
  compartido con el canal Meta ya en producción y **no se tocó** — requiere decisión explícita aparte
  (Fase 10, ver Riesgos).
- **Notifications**: `PASS`. Sin sistema de notificaciones propio en el gateway.
- **Google ADK**: `PASS`. Mismo `support.services.ai_bridge.ask_ai` que el canal web; el gateway Node
  no importa nada de IA/LLM/RAG.

## Tests

| Suite | Resultado |
|---|---|
| Gateway (Node, `whatsapp_gateway/test/`, Fase 23) | **24/24**, 0 fallos |
| Django nuevo (`whatsapp/tests/test_gateway_client.py` + `notifications/test_whatsapp_gateway.py`, Fase 24) | **17/17**, 0 fallos |
| Regresión completa (`whatsapp notifications dashboard support`, Fase 26) | **172/173** — único error es `ModuleNotFoundError: pytest` en `support/tests.py`, preexistente y documentado antes de esta sesión, no relacionado |
| Integration | Cubierta por los tests de arriba (webhook + task + cliente HTTP, todos con aserciones de integración real, no solo unitarias) |
| E2E (Fase 25) | **Casos A/B alcanzados con el número real de producción** (pairing real + reconexión real sin re-escanear tras recrear el contenedor). Casos C/D/E/F sin ejecutar. |

## Evidencia (resumen — detalle completo con comandos/timestamps en `AUDITORIA/WHATSAPP_BAILEYS_ARCHITECTURE.md`)

- Auditoría previa (Fase 0) con hallazgo crítico de riesgo de negocio, autorización explícita del
  usuario registrada con fecha.
- Smoke tests reales del contrato HTTP, del auth store, del event bus (ambas direcciones), del cliente
  Django→Gateway, y del WebSocket (`channels.testing.WebsocketCommunicator` real).
- Verificación en vivo con `curl`, `docker exec`, Celery real (`.delay()` + logs del worker), y
  contenedores Docker reales (`docker compose build/up`, healthcheck `healthy`).
- 4 bugs reales encontrados y corregidos probando contra el sistema vivo (no supuestos):
  1. Content-Type enviado en POSTs sin body → 400 de Fastify (cliente HTTP Django→Gateway).
  2. `app.register(rateLimit, ...)` sin `await` → rate limit completamente ignorado, sin error visible.
  3. `.env` compartido entre runtime y tests → un test que solo comprobaba el tipo de retorno
     (`reconnect()`) disparó una conexión real a WhatsApp durante una corrida de tests automatizada.
  4. **Condición de carrera real en `FileAuthStateStore.atomicWriteFile()`** (nombre de tmp file con
     resolución de milisegundo) → crash loop del proceso completo justo después de un pairing real
     exitoso con el número de producción. Corregido con `randomUUID()` + manejo de errores en el
     listener de `creds.update` (ver Fase 25 en `AUDITORIA/WHATSAPP_BAILEYS_ARCHITECTURE.md`).

## Riesgos conocidos

1. **`conversation_id` compartido con el canal Meta en producción** (Fase 10) — no resuelto,
   deliberadamente, por el riesgo de afectar continuidad de memoria de IA de conversaciones reales
   activas hoy. Requiere decisión explícita del usuario antes de tocarlo.
2. **Gateway sin aislar en red de producción** — solo dev tiene el servicio en Docker con red privada;
   producción no se tocó.
3. **Sin rotación de token / validación de timestamp-idempotencia a nivel de transporte** (Fase 7
   completa) — solo el secreto compartido estático.
4. **Incidente de conexión real** (dos veces, documentado con transparencia completa en
   `AUDITORIA/WHATSAPP_BAILEYS_ARCHITECTURE.md`): probar código real contra un gateway real y
   alcanzable puede generar tráfico real hacia los servidores de WhatsApp si algún test/acción llama
   `connect()`/`reconnect()` sin que el entorno esté explícitamente aislado. Mitigado para el punto
   encontrado; no hay garantía de que sea el único vector posible en código futuro que no siga el
   mismo cuidado.
5. **Sin observabilidad dedicada** (Fase 29) — solo logs estructurados, sin métricas ni dashboards.
6. **Conexión real activa ahora mismo, dejada así a petición explícita del usuario** ("déjalo
   conectado", 2026-09-22, tras confirmarle el estado real y la implicación operativa). El gateway
   está conectado como dispositivo vinculado real al número de producción (`+573144601878`) — ver
   Fase 25 en `AUDITORIA/WHATSAPP_BAILEYS_ARCHITECTURE.md`. No procesa mensajes como negocio real
   (`WHATSAPP_CONNECTION_TYPE` sigue en `META_CLOUD_API`), pero SÍ recibe una copia de cada mensaje
   real entrante mientras el contenedor siga corriendo. Quien retome este trabajo debe saber que esta
   conexión sigue viva salvo que se desconecte explícitamente (panel → "Desconectar", o
   `docker compose stop whatsapp_gateway`). Última verificación de estabilidad antes del cierre de
   esta sesión: `CONNECTED`, contenedor `healthy`, sin reinicios desde el fix del bug de la Fase 25.

## Rollback

- **Dev**: `docker compose stop whatsapp_gateway` (o `down`, el named volume de auth state sobrevive
  sin `-v`). Poner `WHATSAPP_GATEWAY_ENABLED=false` en `.env` revierte el adapter a su comportamiento
  de stub original, sin tocar código.
- **Prod**: no aplica — nunca se tocó `docker-compose.prod.yml` ni `.env.production`. El mecanismo
  activo real (`WHATSAPP_CONNECTION_TYPE=META_CLOUD_API`) nunca cambió durante esta migración.
- **Reversión total de código**: todo el trabajo vive en archivos nuevos o en cambios aditivos
  (ningún archivo del dominio `whatsapp/` preexistente perdió funcionalidad; los 172 tests de
  regresión lo confirman) — revertir es tan simple como no desplegar estos commits.

## Qué falta para un cierre real (`COMPLETED`)

1. Decisión explícita sobre `conversation_id` (Fase 10).
2. `docker-compose.prod.yml` (Fase 21 prod) — decisión aparte, infraestructura de producción real.
3. Fase 25 (E2E real) — requiere un teléfono físico y, probablemente, un número de WhatsApp separado
   del de producción real (ver `AUDITORIA/WHATSAPP_BAILEYS_PRE_MIGRATION_AUDIT.md` para el riesgo de
   negocio ya documentado sobre usar el número real).
4. Fase 7 completa (rotación de token, timestamp/event_id a nivel de transporte).
5. Fase 27 (remoción del proveedor QR experimental) — bloqueada explícitamente por el plan hasta que
   Fase 25 esté en `PASS`.
6. Fase 29 completa (métricas dedicadas).

Este documento se cierra aquí como resumen de la sesión de trabajo del 2026-09-22. El siguiente
trabajador (humano o IA) debe leer esta sección antes de continuar — no asumir que "la migración a
Baileys ya está lista" solo porque la mayoría de las fases numeradas están en `PASS`.
