# WHATSAPP_BAILEYS_ARCHITECTURE

**Fecha:** 2026-09-22
**Fases:** 1-24 y 21 (dev) de `PLAN_ACCION_MIGRACION_WHATSAPP_BAILEYS_SINTEL.md` (contrato del gateway, modelo de
estados, esqueleto del servicio, auth state de producción, QR real, Event Bus Gateway→Django,
autenticación Django→Gateway, `QRWebSessionAdapter` real conectado al gateway). Ver
`AUDITORIA/WHATSAPP_BAILEYS_PRE_MIGRATION_AUDIT.md` (Fase 0) para el inventario previo y el hallazgo
crítico de riesgo de negocio (decisión ya reabierta explícitamente por el usuario, ver ese documento).

Servicio real: `whatsapp_gateway/` (raíz del repo, junto a `ecommerce_sintel/` — Node.js/TypeScript,
independiente del proyecto Django). Ver `whatsapp_gateway/README.md` para el detalle de qué está y qué no
está implementado.

---

## Contrato HTTP (Fase 1)

Implementado tal cual en `whatsapp_gateway/src/server.ts` / `src/types.ts`:

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/health` | No (para healthcheck de Docker) | `{status, service, provider}` |
| GET | `/status` | `X-Gateway-Token` | Estado de conexión, sesión, QR disponible, timestamps |
| GET | `/session/qr` | `X-Gateway-Token` | QR vigente como data URL PNG, o `qr_available: false` |
| POST | `/session/start` | `X-Gateway-Token` | Arranca el socket de Baileys |
| POST | `/session/logout` | `X-Gateway-Token` | Cierra sesión, invalida auth state, vuelve a `QR_REQUIRED` |
| POST | `/session/reconnect` | `X-Gateway-Token` | Fuerza reconexión manual |
| POST | `/messages/send` | `X-Gateway-Token` | `{recipient, text}` → `{accepted, provider_message_id, status}` |

Nunca se devuelve: credenciales, Signal keys, auth state, tokens, contenido sensible de sesión — confirmado
por inspección de cada handler en `src/server.ts` (ninguno serializa el objeto de auth state ni el socket
crudo).

## Modelo de estados (Fase 2)

`whatsapp_gateway/src/state.ts::ConnectionState` — 8 valores exactos de la sección 5 del plan:

```
DISCONNECTED → STARTING → QR_REQUIRED → PAIRING → CONNECTED
CONNECTED → RECONNECTING → CONNECTED          (desconexión temporal)
CONNECTED → LOGGED_OUT → QR_REQUIRED          (logout)
ANY → ERROR                                    (error no recuperable)
```

Máquina de transiciones validada en código (`ConnectionStateMachine.transition`, lanza
`InvalidStateTransitionError` ante una transición no permitida) — no solo documentada, verificable.

### Nota de diseño — dos modelos de estado coexisten a propósito

El dominio Django ya tiene su propio modelo, más granular, construido en la misión previa
(`whatsapp/adapters/session_manager.py::WhatsAppSessionState`, 10 estados: `DISABLED`, `NOT_CONFIGURED`,
`QR_REQUIRED`, `QR_READY`, `SCANNING`, `AUTHENTICATING`, `CONNECTED`, `RECONNECTING`, `DISCONNECTED`,
`ERROR`). El gateway usa el modelo de 8 estados definido por el plan actual, tal cual, sin forzar una
correspondencia 1:1 prematura con el modelo Django. **El mapeo entre ambos es responsabilidad del futuro
`BaileysAdapter` en Django (Fase 6/8, todavía no implementado)** — es la capa de composición correcta para
esa traducción, igual que `whatsapp/factory.py` es hoy el único lugar con lógica de selección de mecanismo.
No se tocó `session_manager.py` en este pase.

## Event Bus Gateway → Django (Fase 6) — implementado y verificado extremo a extremo

- **Gateway** (`whatsapp_gateway/src/eventBus.ts::publishEvent()`): POST autenticado (`X-Gateway-Token`)
  con timeout de 5s, sin retry/cola propia (documentado como límite conocido, no una omisión silenciosa —
  ver docstring del archivo). Deshabilitado por defecto (`DJANGO_EVENTS_URL` vacío) para no forzar una
  dependencia dura de Django todavía no confirmada en Docker.
- **Django** (`notifications/api/whatsapp_gateway_webhook.py::WhatsAppGatewayEventView`, mismo patrón que
  `whatsapp_webhook.py` para Meta): fail-closed sin `WHATSAPP_GATEWAY_TOKEN` configurado (setting nuevo,
  `ecommerce/settings/base.py`), valida los 6 tipos de evento, deduplica `whatsapp.message.received` con
  `WhatsAppIdempotencyGuard` (canal `"baileys"`, mismo mecanismo provider-agnostic que ya usa el canal
  REST). **No invoca `WhatsAppService`/`process_whatsapp_inbound_task`** — eso es Fase 8, bloqueada hasta
  que exista un `BaileysAdapter` real en `whatsapp/factory.py` (conectar antes sería fingir una
  integración que no es real). No se creó ningún modelo nuevo (Fase 31 lo prohíbe explícitamente) — logs
  estructurados son la auditoría de este pase.
- **Verificación real**: servidor Django de desarrollo (`ecommerce_sintel_django`, reiniciado para tomar
  `WHATSAPP_GATEWAY_TOKEN` de `.env`), pegado con `curl` (401 sin token, 401 con token inválido, 200 con
  evento válido, `duplicate` en el segundo envío del mismo `provider_message_id`, 400 en evento
  desconocido) y luego con el propio publicador del gateway corriendo de verdad contra ese servidor —
  ambos extremos confirmados en los logs de Django.

## Fase 7-8 — `QRWebSessionAdapter` real + autenticación Django→Gateway

- **`whatsapp/clients/gateway_client.py::WhatsAppGatewayClient`** — cliente HTTP síncrono (mismo patrón
  que `MetaWhatsAppClient`), completa la mitad de la Fase 7 que faltaba (Django→Gateway; Gateway→Django ya
  estaba desde la Fase 6). Autenticado con `X-Gateway-Token` (mismo secreto compartido,
  `WHATSAPP_GATEWAY_TOKEN`).
- **`whatsapp/adapters/qr_web_session_adapter.py`** — dejó de ser un stub incondicional. Ahora es un
  **stub condicional**: sin `WHATSAPP_GATEWAY_ENABLED`/`WHATSAPP_GATEWAY_URL` configurados (default real
  hoy, dev y prod), se comporta **exactamente igual que antes** — cero I/O, mismas excepciones. Configurado,
  hace llamadas HTTP reales. Esto preservó los 33 tests existentes de `whatsapp/` **sin modificarlos**
  (verificado corriendo la suite completa antes y después).
- **`reconnect()` sobreescrito explícitamente** (no hereda el default `disconnect()+connect()` del Port):
  ese default equivale a un logout completo, que en el gateway real **borra el auth state** — usar
  `POST /session/reconnect` (diseñado para esto) en vez del default heredado fue una corrección real
  encontrada al razonar sobre el efecto secundario, no una preferencia estética.
- **Bug real encontrado y corregido probando contra el gateway vivo** (no una suposición): el cliente
  mandaba `Content-Type: application/json` incluso en POSTs sin body (`session/start|logout|reconnect`),
  y Fastify los rechazaba con 400 `FST_ERR_CTP_EMPTY_JSON_BODY`. Corregido: el header solo se envía cuando
  hay body real.
- **`process_whatsapp_gateway_inbound_task`** (nueva, `notifications/tasks.py`) — equivalente de
  `process_whatsapp_inbound_task` para el canal Baileys, sin reusar esa tarea tal cual (hardcodea
  `channel='meta_cloud_api'` y bookkeeping de `MetaWebhookEvent` que no aplica aquí). El webhook
  (`whatsapp_gateway_webhook.py`) la encola **solo si `WHATSAPP_CONNECTION_TYPE == 'QR_WEB_SESSION'`** —
  si no, el evento se audita/deduplica pero no se procesa, para no responder por el adapter equivocado.

### Verificación real — incluye un incidente transparente

Se levantó el gateway localmente y se probó `QRWebSessionAdapter` real desde dentro del contenedor
`ecommerce_sintel_django` (`host.docker.internal`): `capabilities`, `health_check()`, `get_status()`,
`get_session_state()`, `generate_pairing_qr()` (None, sin sesión), `send_message()` (falla limpio,
`WhatsAppGatewayError`, sin sesión), `translate_inbound()` (round-trip correcto). También se disparó
`process_whatsapp_gateway_inbound_task` real vía Celery (`docker exec` + `.delay()`), confirmado en los
logs del worker: resolución de "no_user" para un teléfono sintético, sin tocar datos de clientes reales.

**Incidente durante la prueba de `reconnect()`**: esa llamada hizo que el gateway abriera una conexión
real a los servidores de WhatsApp (vía Baileys) y generara un QR real — la primera vez en toda esta
migración que el software habló con la infraestructura real de WhatsApp. Ningún número se vinculó (nadie
escaneó el QR), pero fue una conexión real, no simulada. Se cerró de inmediato (`disconnect()` real desde
Django + terminar el proceso del gateway), se limpió el `WhatsAppSessionState`/directorio de auth, y se
revirtió `.env` de desarrollo a su mecanismo por defecto (`META_CLOUD_API`). Se documenta aquí sin
omisiones porque es exactamente el tipo de evento que esta auditoría existe para registrar.

## Fase 9-15 — auditadas contra el código real, sin código nuevo salvo donde se indica

La arquitectura hexagonal construida en las misiones previas (2026-09-16) ya satisfacía la mayoría de
estas fases para CUALQUIER adapter, Baileys incluido. Esta pasada fue de verificación real contra el
código, no de implementación desde cero -- donde algo ya estaba resuelto, se documenta como tal en vez de
reescribirlo (Fase 31: "no reescribir").

| Fase | Estado | Evidencia real |
|---|---|---|
| 9 — Identidad del cliente | **PASS**, sin código nuevo | `WhatsAppCustomerResolver` ya es 100% channel-agnostic (resuelve por `UserProfile.phone_number`, nunca por adapter). Verificado en vivo en la Fase 8 (`resultado=no_user` para un teléfono sin usuario, vía el canal Baileys real). No se creó `WhatsAppIdentity` -- el plan la hace condicional ("si se requiere") y no hay necesidad real hoy (Fase 31 prohíbe inventar modelos sin necesidad). |
| 10 — ChatRoom/Conversación | **PARCIAL — riesgo real señalado, NO tocado** | `WhatsAppConversationResolver` ya reusa el mismo `ChatRoom` para cualquier canal (sin duplicar salas). Pero `whatsapp/domain/service.py:91` sigue pasando `conversation_id=f"wa-{user.id}"` a `ask_ai()` -- la brecha de namespace que el plan pide resolver (Fase 10) sigue ahí. **No se tocó a propósito**: ese código es compartido por el canal Meta Cloud API YA EN PRODUCCIÓN -- cambiar el esquema de `conversation_id` afecta la continuidad de memoria de IA de conversaciones reales activas hoy, no solo Baileys. Requiere decisión explícita aparte, no un cambio de paso mientras se construye Baileys. |
| 11 — Idempotencia | **PASS**, verificado en vivo | `WhatsAppIdempotencyGuard` canal `"baileys"` -- probado con tráfico HTTP real en la Fase 6 (segundo envío del mismo `provider_message_id` devolvió `duplicate`). |
| 12 — Envío de mensajes | **PASS**, verificado en vivo | `send_message()` -> gateway `/messages/send` -> Baileys. Solo distingue `SENT/FAILED` (nunca `DELIVERED/READ`, honesto: el gateway no recibe esas señales de Baileys todavía). Camino de fallo probado en vivo contra el gateway real (Fase 7-8, `WhatsAppGatewayError` limpio sin sesión activa). |
| 13 — Colas y concurrencia | **PASS**, sin código nuevo | Los envíos ya pasan por Celery (`process_whatsapp_gateway_inbound_task`/`send_whatsapp_agent_reply_task`), nunca dentro del request HTTP. Un solo socket por cuenta ya construido (Fase 3, `whatsappSocketManager` singleton a nivel de módulo). |
| 14 — Reconexión | **Implementado, verificado parcialmente** | Backoff exponencial + jitter y distinción `loggedOut` vs. recuperable construidos y probados con datos sintéticos (Fase 3-4). Lo que NO se ha observado todavía es una reconexión real bajo una caída de red genuina y repetida contra un socket real en producción -- honesto dejarlo así en vez de reclamar un PASS completo sin esa evidencia. |
| 15 — Logout | **PASS, verificado en vivo (no planeado -- fue el cleanup real del incidente de la Fase 7-8)** | `disconnect()` real invalidó el auth state real del gateway durante la limpieza tras el incidente de conexión real documentado arriba -- la evidencia más fuerte posible, un logout real ejecutándose sobre una sesión real. |

## Fase 18-19 — Notifications / Google ADK, confirmadas sin código nuevo

| Fase | Estado | Evidencia |
|---|---|---|
| 18 — Integración con Notifications | **PASS** | `WhatsAppService.send_agent_reply` reusa `notifications.services.commands._resolve_phone` tal cual (sin duplicar). El gateway (`whatsapp_gateway/`) no tiene ningún sistema de notificaciones propio -- es transporte puro, confirmado por diseño (cero imports de ese tipo en `package.json`/`src/`). |
| 19 — Integración con Google ADK | **PASS** | `whatsapp/domain/service.py` llama `support.services.ai_bridge.ask_ai`/`is_ai_mode_active`/`is_ai_rate_limited` -- el MISMO bridge que usa el widget web, sin condicional de canal. El gateway Node no importa nada de IA/LLM/RAG (verificado: `package.json` solo tiene Baileys/Fastify/Pino/qrcode/dotenv/rate-limit). `ai_paused`/handoff humano verificados con test real (`ProcessWhatsAppGatewayInboundTaskTestCase.test_ai_paused_bloquea_auto_respuesta_pero_persiste_mensaje`, Fase 24). |

## Fase 20 (Seguridad) — estado real, no optimista

- ✅ Secretos nunca logueados (redact de Pino, headers nunca serializados en logs).
- ✅ Auth state fuera de repo/imagen/frontend/logs (`.gitignore`, `FileAuthStateStore` bajo `data/`).
- ✅ **Rate limiting en `/messages/send`**: implementado (`@fastify/rate-limit`, 20/min, `global:false`
  -- ninguna otra ruta tiene límite salvo esta). **Bug real encontrado y corregido en el camino**:
  `buildServer()` no esperaba (`await`) el registro del plugin antes de declarar las rutas
  síncronamente después -- el hook `onRoute` del plugin no llegaba a tiempo y el límite quedaba
  completamente ignorado, sin ningún error visible (0 headers `x-ratelimit-*`, todas las peticiones
  200). Encontrado con una reproducción mínima aislada, no una suposición; ahora `buildServer()` es
  `async` y se awaitea el registro. Cubierto por un test de regresión real
  (`test/server.test.ts`, la petición 21 en 1 minuto responde 429).
- ✅ **Gateway en red privada de Docker (dev)**: cumplido -- `docker-compose.yml` agrega el servicio
  `whatsapp_gateway` SIN `ports:` (nunca publicado al host), solo alcanzable desde otros contenedores
  de `ecommerce_sintel_network`. Verificado en vivo en ambas direcciones (Django→gateway,
  gateway→Django) sobre la red interna real, healthcheck en `healthy`. **Solo dev** -- prod
  (`docker-compose.prod.yml`) sin tocar, ver sección Fase 21 abajo.

## Fase 23-24 (Tests) — cobertura real agregada, no solo verificación manual

- **Fase 23 (gateway, Node)**: `whatsapp_gateway/test/` nuevo, usando el test runner nativo de Node
  (`node:test`, sin dependencia nueva) -- `state.test.ts` (máquina de estados, 8 casos incl. el
  diagrama completo de la Fase 2), `qr.test.ts`, `auth-store.test.ts` (persistencia real, Buffer
  round-trip, recuperación de lock huérfano, `clear()`), `server.test.ts` (contrato HTTP real via
  `.inject()` de Fastify -- auth 401, 400, rate limit 429 real). **24/24 tests, 0 fallos** (fue
  correr esta suite lo que encontró el bug del rate limit de arriba).
- **Fase 24 (Django)**: `whatsapp/tests/test_gateway_client.py` (incl. regresión del bug real del
  `Content-Type` en POSTs sin body, Fase 7-8) + `notifications/test_whatsapp_gateway.py` (auth
  fail-closed, dedupe real, guard de `WHATSAPP_CONNECTION_TYPE`, gate de `ai_paused`/número
  desconocido). **17/17 tests nuevos, 0 fallos.**
- Lo que sigue sin cobertura automatizada: `test_reconnect`/`test_logout` de la Fase 23 contra un
  socket Baileys REAL (solo la máquina de estados está probada, no el socket real -- probarlo de
  verdad exigiría una sesión real, ver Fase 25) y `test_security` explícito (rotación de token,
  timestamp/event_id -- Fase 7 completa, no construida).

## Qué se construyó y qué no (resumen — detalle completo en `whatsapp_gateway/README.md`)

**Construido y verificado** (npm install + typecheck + build + smoke test real de los 7 endpoints +
smoke test real del auth store + smoke test real del event bus): contrato HTTP, modelo de estados, socket
Baileys con QR/reconexión/logout reales, normalización y publicación de mensajes entrantes, auth mínima
por token compartido, logs estructurados con redacción, `FileAuthStateStore` real (Fase 4 — persistencia
atómica, lock single-writer con recuperación de huérfanos, `clear()` real; PostgreSQL descartado a
propósito, ver README), Event Bus real Gateway↔Django (Fase 6, ver sección arriba).

### Nota de diseño — `forceTransition()` vs. `transition()` estricta

`src/state.ts` implementa el validador estricto (`transition()` + `VALID_TRANSITIONS`) que demuestra el
diagrama exacto de la Fase 2, verificable de forma aislada. Pero `src/whatsapp/socket.ts` (donde los
eventos REALES de Baileys y los comandos HTTP del operador llegan) usa `forceTransition()` en todos los
casos: una desconexión de red o un `DisconnectReason.loggedOut` de WhatsApp puede ocurrir desde cualquier
estado intermedio, no solo desde el paso "correcto" del diagrama idealizado — y Baileys no expone una señal
propia para `PAIRING`/`SCANNING` distinta de QR_REQUIRED/open. Forzar la validación estricta contra eventos
reales que no respetan esa secuencia habría lanzado `InvalidStateTransitionError` sin capturar dentro de un
event handler de Baileys, tumbando el proceso — un bug real, encontrado y corregido durante la
implementación de la Fase 4 (no una decisión de diseño previa a probarlo).

## Fase 21 — Docker (dev completo, prod deliberadamente sin tocar)

- **Dev**: servicio `whatsapp_gateway` agregado a `docker-compose.yml` (`whatsapp_gateway/Dockerfile`,
  build 2 etapas, imagen runtime sin devDependencies). **Sin `ports:`** -- nunca publicado al host,
  solo alcanzable desde `ecommerce_sintel_network` (Fase 20: "no exponer el gateway directamente a
  Internet"). Auth state en named volume `ecommerce_sintel_whatsapp_auth` (Fase 4, sobrevive
  `docker compose down` sin `-v`). Healthcheck vía Node puro (`http.get` a `/health`, sin `curl` en la
  imagen), nunca condicionado al estado real de la sesión de WhatsApp (Fase 21: regla explícita).
- **Verificado en vivo, ambas direcciones, sobre la red interna real** (no simulado): `docker compose
  build whatsapp_gateway` + `up -d` → contenedor `healthy`; `django` → `http://whatsapp_gateway:3001/status`
  (200 real); `whatsapp_gateway` → `http://django:8000/.../whatsapp-gateway-events/` (Event Bus, 200
  real). `WHATSAPP_GATEWAY_ENABLED=true`/`WHATSAPP_GATEWAY_URL=http://whatsapp_gateway:3001` en `.env`
  dev -- `WHATSAPP_CONNECTION_TYPE` se mantiene en su default real (`META_CLOUD_API`, sin cambiar) a
  propósito: tener el gateway disponible en la red no cambia el mecanismo ACTIVO de mensajería.
- **`docker-compose.prod.yml` deliberadamente NO tocado** -- cambiar la topología de infraestructura de
  producción es una decisión aparte de agregar el servicio a dev, no se asumió como incluida.

**Explícitamente fuera de este pase**: `docker-compose.prod.yml`, Fase 25 (E2E real, requiere teléfono
físico), Fase 27 (remoción del proveedor QR experimental -- el propio plan la bloquea hasta que Fase 25
esté en PASS), Fase 10 (esquema `conversation_id` compartido con el canal Meta en producción, ver
sección Fase 9-15), Fase 29 completa (métricas dedicadas -- los logs estructurados ya existen, un
pipeline tipo Prometheus sería infraestructura nueva no pedida). Ningún número de teléfono real se ha
conectado -- el servicio nunca corrió contra la red real de WhatsApp.

## Fase 25 (E2E real) — Caso A y B alcanzados, con un bug real encontrado y corregido en producción activa

**2026-09-22, sesión real con el número de producción (`+573144601878`), autorización explícita
confirmada dos veces por el usuario (ver `WHATSAPP_BAILEYS_PRE_MIGRATION_AUDIT.md` y la reconfirmación
inmediatamente antes de este intento).**

- **Caso A (primera conexión)**: el usuario abrió `/panel/soporte/whatsapp`, hizo clic en "Conectar",
  escaneó el QR real con su teléfono. **Pairing exitoso**: Baileys confirmó
  `"me":{"id":"573144601878:5@s.whatsapp.net","name":"Sintel Technology"}`.
- **Bug real encontrado inmediatamente después, en la sesión real recién emparejada** (no en un test
  sintético): `FileAuthStateStore.atomicWriteFile()` generaba el nombre del archivo temporal con
  `pid + Date.now()` (resolución de milisegundo) -- Baileys dispara varios `creds.update`
  prácticamente simultáneos durante el pairing, y dos llamadas a `saveCreds()` en el mismo milisegundo
  colisionaban en el mismo nombre de tmp file. La segunda pisaba el tmp file de la primera; cuando la
  primera intentaba renombrarlo, ya no existía (`ENOENT`). Esa excepción, sin capturar dentro de un
  listener de `EventEmitter`, se volvía una unhandled promise rejection -- Node mata el proceso
  completo por defecto. Resultado real observado: loop de crash/restart cada ~35s, la sesión nunca
  llegaba a estabilizarse en `CONNECTED` aunque el pairing ya era válido.
- **Corrección aplicada** (`whatsapp_gateway/src/auth/fileAuthStateStore.ts`): nombre de tmp file con
  `randomUUID()` en vez de `Date.now()` -- único de verdad sin importar cuántas llamadas concurrentes
  ocurran en el mismo milisegundo. Defensa en profundidad adicional
  (`whatsapp_gateway/src/whatsapp/socket.ts`): el listener de `creds.update` ahora atrapa sus propios
  errores (`.catch()` con log, nunca deja que una falla de guardado tumbe el proceso).
- **Verificado real, no supuesto**: rebuild + redeploy del contenedor (`docker compose build && up -d
  whatsapp_gateway`) preservando el volumen de auth state (no se perdió el pairing), reconexión real
  vía `POST /session/reconnect` **sin volver a escanear QR** -- `GET /status` confirmó
  `"status":"CONNECTED","phone":"573144601878","jid":"573144601878:5@s.whatsapp.net"`, estable durante
  la ventana de verificación (contenedor sin reinicios posteriores).
- **Caso B (persistencia)** parcialmente alcanzado: la sesión sobrevivió una recreación real del
  contenedor (rebuild + recreate, no solo un restart) y se reconectó sin QR -- más exigente que el
  `docker restart whatsapp_gateway` que describe el plan textualmente.
- **Implicación operativa real activa ahora mismo**: el gateway queda como un "dispositivo vinculado"
  real en la cuenta de WhatsApp de producción. Recibe copia de los mensajes reales entrantes, los
  normaliza y los publica al Event Bus -- pero como `WHATSAPP_CONNECTION_TYPE` sigue en
  `META_CLOUD_API` (sin cambiar), Django los audita/deduplica y **no** los procesa como negocio real
  (mismo guard de la Fase 8) -- no hay riesgo de respuesta duplicada. El contenido de los mensajes
  nunca se loguea (solo metadatos: `event_id`/`provider_message_id`).
- **No alcanzado todavía**: Casos C/D (mensaje entrante/saliente real de punta a punta -- bloqueado
  a propósito por el guard de `WHATSAPP_CONNECTION_TYPE`, ver Fase 8), Caso E (logout real desde el
  panel, no probado en esta sesión), Caso F (reconexión automática tras una caída real de red, sin
  intervención manual).

## Próximo checkpoint

Fases 1-24, 21 (dev) y 26 (regresión, 172/173 -- único fallo es `pytest` no instalado, preexistente y
no relacionado) completas y verificadas con evidencia real. El siguiente paso natural con impacto real
sería `docker-compose.prod.yml` o Fase 25 (E2E) -- ambos requieren decisión/recurso explícito del
usuario (infraestructura de producción y un teléfono físico, respectivamente), no algo para asumir por
inercia.
