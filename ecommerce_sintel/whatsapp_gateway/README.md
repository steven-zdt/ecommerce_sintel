# whatsapp_gateway

Gateway de transporte WhatsApp basado en Baileys, para Sintel Support. Construido en el marco de
`PLAN_ACCION_MIGRACION_WHATSAPP_BAILEYS_SINTEL.md` (Fases 1-6: contrato, modelo de estados, esqueleto del
servicio, auth state de producción, QR real, Event Bus hacia Django). Ver
`AUDITORIA/WHATSAPP_BAILEYS_PRE_MIGRATION_AUDIT.md` para la auditoría previa completa y
`AUDITORIA/WHATSAPP_BAILEYS_ARCHITECTURE.md` para el contrato y modelo de estados documentados en detalle.

## Principio de diseño

```
BAILEYS = TRANSPORTE
DJANGO  = DOMINIO
```

Este servicio NUNCA:
- accede al ORM/PostgreSQL de Django directamente;
- decide identidad de cliente, permisos, `ChatRoom`, ni nada de negocio;
- ejecuta lógica de IA/LLM/RAG;
- se expone públicamente a Internet (debe vivir detrás de Nginx/Django, en red privada de Docker).

## Decisión de negocio — LEER ANTES DE CONECTAR ESTO A UN NÚMERO REAL

`AUDITORIA/WHATSAPP_QR_PROVIDER_EVALUATION.md` (2026-09-16) evaluó Baileys contra el número de producción
real de SINTEL y concluyó **BLOQUEADO** por riesgo de violar los Términos de Servicio de WhatsApp Business y
de perder la integración oficial de Meta Cloud API ya activa en ese mismo número. Esa decisión fue reabierta
explícitamente por el usuario el 2026-09-22 (ver `AUDITORIA/WHATSAPP_BAILEYS_PRE_MIGRATION_AUDIT.md`,
sección RISKS) **aceptando ese riesgo para el número de producción real**. Cualquiera que retome este
código debe conocer esa decisión antes de continuar — no es un detalle técnico, es una decisión de negocio
con riesgo real de perder el canal de soporte oficial.

## Versión de Baileys — evidencia (Fase 2 del plan: "fijar versión exacta y registrar evidencia")

Consultado `https://registry.npmjs.org/@whiskeysockets/baileys` el 2026-09-22:

- `dist-tags`: `{"latest": "7.0.0-rc14", "legacy": "6.7.24"}`
- Se fijó **`6.7.24`** (no `7.0.0-rc14`) porque es un release-candidate de la siguiente major (no estable,
  puede tener breaking changes antes de su release final) — `6.7.24` es la última versión estable de la
  línea v6, no está deprecada, `engines.node >=20.0.0` (cumplido, Node instalado: v24.18.0).
- Fijada exacta en `package.json` (sin `^`/`~`) — no se actualiza sola con `npm install`.

## Auth state de producción (Fase 4) — implementado

`src/auth/fileAuthStateStore.ts::FileAuthStateStore` reemplaza `useMultiFileAuthState`. Persistencia
atómica en disco (write-tmp + rename), lock de single-writer con recuperación de lock huérfano (PID
muerto), permisos restrictivos (0700/0600), `clear()` real para logout. **No usa PostgreSQL** — ver el
docstring del archivo para la justificación completa (violaría la Decisión #4 de la Fase 0: "el gateway NO
accede directamente a PostgreSQL de Django"; levantar un Postgres nuevo solo para esto no está justificado
mientras el servicio siga sin Docker real, Fase 21). El directorio (`WA_AUTH_STORAGE_DIR`, default
`data/auth-store`) es el punto de montaje candidato para un named volume cuando llegue la Fase 21.
Verificado con un smoke test real: round-trip de credenciales y de claves con `Buffer` real, recuperación
de lock huérfano, `clear()`.

## Qué SÍ incluye este esqueleto (Fases 1-6)

- Contrato HTTP completo de la Fase 1: `GET /health`, `GET /status`, `GET /session/qr`,
  `POST /session/start|logout|reconnect`, `POST /messages/send` — ver `src/server.ts`, `src/types.ts`.
- Modelo de estados de la Fase 2 (`DISCONNECTED/STARTING/QR_REQUIRED/PAIRING/CONNECTED/RECONNECTING/
  LOGGED_OUT/ERROR`), con máquina de transiciones validada — `src/state.ts`.
- Socket de Baileys real (`src/whatsapp/socket.ts`): un único socket por cuenta (Fase 13), captura y
  codifica el QR como data URL PNG (Fase 5), reconexión con backoff exponencial + jitter distinguiendo
  `loggedOut` de errores recuperables (Fase 14), normalización de `messages.upsert` al contrato interno
  (Fase 9).
- Autenticación mínima `X-Gateway-Token` fail-closed (el proceso no arranca sin
  `WA_GATEWAY_INTERNAL_TOKEN`) — versión reducida de la Fase 7.
- Logs estructurados con redacción de campos sensibles (Pino) — Fase 29.
- **Event Bus real (Fase 6)** — `src/eventBus.ts::publishEvent()` publica los 6 tipos de evento
  (`whatsapp.connection.status/qr/logged_out`, `whatsapp.message.received/sent/failed`) a
  `notifications/api/whatsapp_gateway_webhook.py` en Django, autenticado con el mismo
  `X-Gateway-Token`. Verificado extremo a extremo con tráfico HTTP real contra el Django de desarrollo
  corriendo (auth 401 sin token, evento aceptado y logueado, deduplicación real de
  `whatsapp.message.received` vía `WhatsAppIdempotencyGuard` canal `"baileys"`).
- Verificado: `npm install`, `npm run typecheck`, `npm run build`, smoke test real de los 7 endpoints
  del contrato, smoke test real del auth store, y smoke test real del Event Bus contra Django.

## Qué NO incluye todavía (fases explícitamente futuras, no ejecutadas en este pase)

- **Fase 8 — procesamiento real de negocio**: `notifications/api/whatsapp_gateway_webhook.py` recibe,
  autentica y deduplica `whatsapp.message.received`, pero **no** invoca
  `whatsapp.domain.service.WhatsAppService` ni `process_whatsapp_inbound_task` — eso requiere un
  `BaileysAdapter` real en `whatsapp/factory.py` (Fase 8/9), que no existe todavía. Conectar esto antes
  sería fingir una integración que no es real.
- **Fase 7 completa** — solo el token compartido; faltan rotación, validación de timestamp/event_id e
  idempotencia a nivel de transporte.
- **Fase 16-18 — Frontend real / WebSocket del panel**: no se tocó `WhatsAppConnectionStatusView.vue` ni
  se creó ningún flujo de QR en el panel todavía — Django recibe y loguea `whatsapp.connection.qr` pero no
  lo distribuye a nadie.
- **Fase 21 — Docker producción**: agregado a `docker-compose.yml` (dev, ver abajo) y verificado en
  vivo. **NO agregado a `docker-compose.prod.yml`** — cambiar infraestructura de producción es una
  decisión aparte, deliberadamente no tomada en este pase.
- **whatsapp/factory.py (Django)**: no se agregó ningún `BaileysAdapter` ni tercer
  `CONNECTION_TYPE_BAILEYS` — el dominio Django sigue sin conocer este servicio.
- Ningún número de teléfono real se ha conectado — este servicio nunca se ha ejecutado contra la red real
  de WhatsApp, solo probado localmente (health/status/qr/event bus, sin `session/start` real).

## Desarrollo local (sin Docker)

```bash
cp .env.example .env   # completar WA_GATEWAY_INTERNAL_TOKEN
npm install
npm run dev             # tsx watch
npm run typecheck
npm test                # Fase 23 -- node:test, sin dependencia nueva
npm run build && npm start
```

## Docker (Fase 21 — dev, verificado en vivo)

Servicio `whatsapp_gateway` en `docker-compose.yml` (raíz de `ecommerce_sintel/`). Build en 2 etapas
(`Dockerfile`), **sin `ports:`** (nunca expuesto al host/Internet -- solo alcanzable desde otros
contenedores de `ecommerce_sintel_network`, ej. Django vía `http://whatsapp_gateway:3001`). Auth state
en el named volume `ecommerce_sintel_whatsapp_auth` (sobrevive `docker compose down` sin `-v`).
Healthcheck vía Node puro (`http.get` a `/health`, sin `curl` en la imagen) -- nunca depende del
estado real de la sesión de WhatsApp.

```bash
docker compose build whatsapp_gateway
docker compose up -d whatsapp_gateway
docker compose logs -f whatsapp_gateway
```

Verificado con tráfico real entre contenedores: Django → gateway (`/status`, `/health`) y gateway →
Django (Event Bus) ambos confirmados por la red interna de Docker, sin publicar ningún puerto al
host. **NO agregado a `docker-compose.prod.yml`** -- ver `AUDITORIA/WHATSAPP_BAILEYS_ARCHITECTURE.md`.

## Variables de entorno

Ver `.env.example` — todas documentadas ahí (`WA_GATEWAY_PORT`, `WA_GATEWAY_INTERNAL_TOKEN`,
`WA_SESSION_STORAGE`, `WA_AUTH_STORAGE_DIR`, `WA_LOG_LEVEL`, `WA_RECONNECT_*`, `DJANGO_EVENTS_URL`).

Del lado Django (`.env` de `ecommerce_sintel/`, dev-only, nunca `.env.production` sin decidirlo
explícitamente): `WHATSAPP_GATEWAY_TOKEN` debe tener **el mismo valor** que `WA_GATEWAY_INTERNAL_TOKEN`
de este servicio — un solo secreto compartido para todo el canal Gateway↔Django en este pase.
