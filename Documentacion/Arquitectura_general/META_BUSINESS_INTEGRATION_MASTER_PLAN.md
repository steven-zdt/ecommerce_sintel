# Integracion Meta Business en SINTEL - Plan Maestro de Implementacion

> Estado: **FASE 0 bloqueada en el usuario (credenciales reales pendientes, ver seccion 3 -- `META_ACCESS_TOKEN` de dev confirmado INVALIDO contra Meta real el 2026-09-15, `debug_token` -> code 190)** | **FASE 1-4, 6, 6.1, 7, 9, 10 DONE + DESPLEGADAS A PRODUCCION (2026-08-31)** | FASE 5 ya cubierta | **FASE 11 PARCIAL (2026-09-15, camino corto sin MCP -- ver seccion 6)** | FASE 8, 12-26 PENDIENTES
> FASE 10: codigo desplegado pero DORMIDO (`MCP_META_ADS_ENABLED=false`) -- falta crear el App de Meta y la autorizacion OAuth (`python -m mcp_client.authorize`). Ver seccion 9.
> Deploy 2026-08-31: `./deploy/backup.sh` + `./deploy/deploy.sh`; migraciones `notifications.0008/0009` aplicadas a la BD de prod; `ecommerce_sintel_ai:prod` reconstruida aparte.
> Rama de la fundacion: `fix/audit-p0-remediation`
> Documento vivo. Cada fase se marca DONE con fecha + commit cuando pasa su checkpoint.

---

## 0. Objetivo y filosofia

Integrar Meta Business (WhatsApp Cloud API, Graph API, Marketing API, Conversions
API, Catalog, y **Meta Ads MCP**) sin reemplazar nada de lo que ya funciona.

Tres capas, frontera estricta entre ellas:

```
CAPA 1 - Meta Channel Infrastructure   WhatsApp / Graph / Webhooks / CAPI / Catalog
CAPA 2 - SINTEL Business Core           Django / Commands / Selectors / PostgreSQL
CAPA 3 - Agentic Intelligence           ai_engine / LangGraph / Agents / MCP / Human Approval
```

Reglas arquitectonicas que NO se negocian:

| Regla | Por que |
|---|---|
| `Meta API -> Django -> Commands/Selectors -> PostgreSQL` | La API oficial es la integracion de produccion (determinista, Celery, webhooks). |
| `Usuario/Admin -> ai_engine -> Agent Profile -> Capability -> Policy Layer -> Meta MCP / internal_ai` | El MCP es la interfaz *agentic*, se anade POR ENCIMA. |
| `ai_engine` NUNCA toca el ORM | Ya hay ~30 endpoints `/api/v1/internal/ai/*` para eso (`ecommerce/internal_ai_urls.py`). Meta extiende esa misma frontera. |
| Prohibido: `Meta MCP -> ORM`, `Meta MCP -> PostgreSQL`, `Meta webhook -> ai_engine -> ORM` | Rompe la frontera. |
| El LLM nunca ve Tools/MCP directamente | Pasa por `capabilities/registry.py` -> `tools/registry.py` -> Policy Layer. |
| Toda escritura publicitaria pasa por Policy Layer (`deny`/`confirm`/`allow`) + `interrupt()` de LangGraph para aprobacion humana | Nunca "LLM cree que es buena idea -> modificacion financiera". |
| SINTEL es SSoT. Meta Catalog / CAPI son proyecciones. Nunca al reves. | |
| WhatsApp inbound sigue por `notifications` -> `support.ai_bridge` -> `ai_engine /chat`, misma `ChatRoom`, mismo handoff humano | Tocar esa frontera seria una regresion. |

**API oficial** para: WhatsApp, webhooks, Conversions API, catalogo, sincronizacion,
eventos, procesos Celery, operaciones deterministas.
**Meta Ads MCP** (`https://mcp.facebook.com/ads`, OAuth de Meta) para: explorar
campanas, analizar resultados, diagnosticar, comparar metricas, crear propuestas,
acciones administrativas supervisadas. Los MCP comunitarios de "Meta Business/
WhatsApp" NO entran al camino critico.

---

## 1. Estado del codigo al arrancar (verificado contra el repo, 2026-08-31)

| Pieza | Donde | Estado |
|---|---|---|
| Env vars Meta | `ecommerce/settings/base.py` | `META_ACCESS_TOKEN`, `META_APP_SECRET`, `WHATSAPP_PHONE_NUMBER_ID`, `FACEBOOK_PAGE_ID`, `INSTAGRAM_BUSINESS_ACCOUNT_ID`, `WHATSAPP_WEBHOOK_VERIFY_TOKEN` ya existian |
| Fachada de solo lectura sobre settings | `organization/services/selectors.py::OrganizationSelector.get_integration_settings()` | ya existia; consumida por `marketing/channels/*` |
| Patron de cliente HTTP aislado | `payment/online/wompi_client.py::WompiApiClient` | referencia: excepciones tipadas (definitivo vs transitorio), `_request()` con mapeo de status |
| Cliente WhatsApp transaccional | `notifications/clients/whatsapp.py` | tenia `requests.Session` propia + clases de error propias |
| Adapters de campana | `marketing/channels/{whatsapp,facebook,instagram}_channel.py` | `requests.post` crudo a Graph API |
| Webhook WhatsApp inbound | `notifications/api/whatsapp_webhook.py` | firma HMAC fail-closed, `hub.challenge`, dedupe Redis `cache.add`, 200 rapido, handoff a Celery -- ya cumple FASE 5/8 |
| Flujo webhook -> IA | `notifications/tasks.py::process_whatsapp_inbound_task` -> `support.services.ai_bridge` -> ai_engine `/chat` | correcto, respeta `ai_paused`/handoff/rate-limit |
| Endpoints internos IA | `ecommerce/internal_ai_urls.py` | ~30 vistas, patron: vista en la app duena envuelve Selector/Command, permisos reales, consumidas via `ai_engine/tools/http_bridge.py` |
| Capability Registry | `ai_engine/capabilities/registry.py` | 29 capabilities |
| Tool Registry + bridge | `ai_engine/tools/registry.py`, `ai_engine/tools/http_bridge.py` (`django_internal_get/post`) | |
| Policy Layer | `ai_engine/action_graph.py::node_evaluate_policy` (`allow`/`deny`/`confirm`) + `node_await_confirmation` (`interrupt`) + rate limit Redis | |
| Agentes | `ai_engine/agents/profiles/*.yaml` | 9: account, admin, marketing, order, payment, rental, sales, service, support |
| MarketingAgent | `ai_engine/agents/profiles/marketing_agent.yaml`, `marketing/agent/brain.py` | existe |
| MCP client | `ai_engine/mcp/` | NO existe (directorio vacio) |

---

## 2. Decisiones tomadas para la fundacion (usuario, 2026-08-31)

1. **Alcance de la primera pasada:** solo FASE 1-3 + 6 + refactor del cliente WhatsApp. Aditivo, sin cambio de comportamiento.
2. **Ubicacion de la frontera HTTP:** `marketing/integrations/meta/` (marketing es el dominio dueno; `notifications` importa el subcliente de WhatsApp desde ahi).
3. **Config de activos Meta:** `settings`/`.env` + selector de solo lectura. **Sin modelo, sin migracion de config.** Coherente con `FACEBOOK_PAGE_ID` etc. que ya son env vars, y con la regla explicita de `organization` de que las credenciales de integracion viven en `.env`, nunca en BD.

---

## 3. FASE 0 - Inventario Meta Business (BLOQUEADA EN EL USUARIO)

No tocar codigo. Obtener y registrar en el secret manager / `.env.production`:

| Variable | Donde se saca | Obligatoria desde |
|---|---|---|
| `META_BUSINESS_ID` | Business Manager > Informacion del negocio | **PROVISTO: `3054417098283269`** (en `.env` dev) |
| `META_APP_ID` | Meta for Developers > App (tipo Business) > Basic | **FASE 10 (MCP OAuth) -- OBLIGATORIO, el MCP no permite dynamic registration.** Ver seccion 9.1 |
| `META_APP_SECRET` | Meta for Developers > App > Config basica | **YA** (firma de webhooks) |
| `META_WABA_ID` | Business Manager > Cuentas de WhatsApp | FASE 4 (plantillas / estados) |
| `META_PHONE_NUMBER_ID` (`WHATSAPP_PHONE_NUMBER_ID`) | WhatsApp Manager | **YA** |
| `META_WHATSAPP_ACCESS_TOKEN` (`META_ACCESS_TOKEN`) | System User token permanente | **YA** |
| `META_PAGE_ID` (`FACEBOOK_PAGE_ID`) | Pagina de Facebook > Acerca de | FASE 21 |
| `META_INSTAGRAM_BUSINESS_ID` (`INSTAGRAM_BUSINESS_ACCOUNT_ID`) | IG conectada a la Pagina | FASE 21 |
| `META_AD_ACCOUNT_ID` | Administrador de anuncios > Config (numero SIN `act_`) | FASE 7 |
| `META_PIXEL_ID` / `META_DATASET_ID` | Events Manager | FASE 19 |
| `META_CATALOG_ID` | Commerce Manager | FASE 20 |
| `META_WEBHOOK_VERIFY_TOKEN` (`WHATSAPP_WEBHOOK_VERIFY_TOKEN`) | lo defines tu | **YA** |

Empezar solo con: Business + WhatsApp Business Account + Facebook Page + Instagram
Business + Ad Account. Pixel/CAPI/Catalog despues.

---

## 4. FASE 1-3 + 6 - Fundacion (DONE 2026-08-31)

### FASE 1+2 - Superficie de config Meta
- `ecommerce/settings/base.py`: +`META_GRAPH_API_VERSION` (`v20.0`), `META_BUSINESS_ID`, `META_WABA_ID`, `META_AD_ACCOUNT_ID`, `META_CATALOG_ID`, `META_PIXEL_ID`, `META_DATASET_ID`.
- `ecommerce/.env.production.example`: mismas claves documentadas.
- `organization/services/selectors.py::get_integration_settings()`: extendido con esas claves + `meta_app_secret`, `meta_graph_api_version`, `whatsapp_webhook_verify_token`. Sigue siendo la unica puerta de lectura. Nada se movio a BD.

### FASE 3 - `marketing/integrations/meta/`
```
marketing/integrations/meta/
  exceptions.py   MetaApiError / MetaApiTransientError / MetaAuthError / MetaConfigError / MetaRateLimitError
  client.py       MetaGraphClient  -- transporte puro (get/post/delete/paginate), version de Graph API,
                  timeout, clasificacion de errores (429 y codes 4/17/32/613/80004 -> RateLimit;
                  401/403 y codes 190/102/... -> Auth; 5xx/red -> Transient), envelope de error de Graph
                  parseado (message/code/subcode/fbtrace). CERO logica de negocio.
  signatures.py   verify_meta_webhook_signature(app_secret, raw_body, header) -- funcion pura, fail-closed
  whatsapp.py     MetaWhatsAppClient(send_template, send_text) sobre MetaGraphClient
  tests/          test_client.py (23 casos), test_signatures.py, test_whatsapp.py -- SimpleTestCase, mock de requests.request
```
- `MetaGraphClient` lee la config via `OrganizationSelector.get_integration_settings()` (parametrizable para tests con `integration_settings=`).

### Refactor del cliente WhatsApp
- `notifications/clients/whatsapp.py` reducido a shim: `class WhatsAppClient(MetaWhatsAppClient)` + alias de excepciones (`WhatsAppApiError = MetaApiError`, `WhatsAppAuthError = MetaAuthError`, `WhatsAppConfigError = MetaConfigError`). Modulo, nombre de clase y API publica intactos -> los 5 call sites en `notifications/tasks.py` y los ~20 `@patch` en tests siguen validos. Solo se actualizaron 3 tests que mockeaban `requests.Session.post` (detalle de transporte que se movio) para mockear `marketing.integrations.meta.client.requests.request`.

### FASE 6 - `MetaWebhookEvent`
- Modelo nuevo en `notifications/models.py` (misma app que el webhook productor). Campos: `object_type`, `event_type`, `business_id`, `waba_id`, `phone_number_id`, `external_message_id`, `payload_hash` (sha256 del body crudo), `signature_valid`, `status` (`RECEIVED`/`PROCESSING`/`PROCESSED`/`FAILED`/`DUPLICATE`/`REJECTED`), `received_at`, `processed_at`, `retry_count`, `error_code`, `payload` (JSON). Migracion `0008_metawebhookevent.py` (verificada con `makemigrations --check`).
- `notifications/api/whatsapp_webhook.py`: usa `verify_meta_webhook_signature`; persiste **una fila por evento**, incluidos los rechazados por firma (`status=REJECTED`, 403) y los callbacks de estado `statuses` (delivered/read/failed); marca `DUPLICATE` en colision de dedupe; pasa `event_id` a la tarea.
- `notifications/tasks.py::process_whatsapp_inbound_task(..., event_id=None)`: helper `_mark_meta_webhook_event()` avanza el ciclo de vida (`PROCESSED` con `error_code` de contexto en las salidas benignas, `FAILED` + `retry_count++` en fallo de `ask_ai`, `FAILED` en fallo de envio).
- `notifications/admin.py`: `MetaWebhookEventAdmin` de solo lectura.
- **Pendiente FASE 6.1:** tarea Celery de retencion/purga de `MetaWebhookEvent.payload` (contiene texto de cliente) alineada con la politica de `NotificationLog`/`ChatMessage`.

**Checkpoint FASE 1-3+6 (PASS):** `manage.py test marketing.integrations.meta` (23 OK) + `manage.py test notifications` sin regresiones + `makemigrations --check` limpio + `py_compile` de todos los .py.

---

## 5. FASE 4, 6.1, 7, 9 - Capa READ (DONE 2026-08-31)

### FASE 4 - Normalizacion de adapters de canal (DONE)
- `marketing/channels/whatsapp_channel.py` -> `MetaWhatsAppClient.send_template`.
- `marketing/channels/facebook_channel.py` -> `MetaGraphClient().post("/{page_id}/feed", data=...)`.
- `marketing/channels/instagram_channel.py` -> `MetaGraphClient().post` en los 2 pasos (media / media_publish).
- Interfaz `AbstractChannelAdapter.send()` intacta (mismo dict `{success, channel, response}`).
- Tests: `marketing/integrations/meta/tests/test_channels.py` (6).
- **PASS verificado:** `grep -rn "graph.facebook.com" --include=*.py` solo aparece en `marketing/integrations/meta/` (mas `tiktok_channel.py`, que no es Meta).

### FASE 5 - Webhook Gateway (YA CUMPLE via FASE 6)
`notifications/api/whatsapp_webhook.py` hace solo challenge / firma / persistir evento /
dedupe / `Celery.delay()`. Cero Selector/Command de negocio, cero IA. Opcional futuro:
renombrar la ruta a `/api/v1/webhooks/meta/` (hoy `/api/v1/notifications/whatsapp-webhook/`)
-- requiere reconfigurar el webhook en Meta, en ventana controlada.

### FASE 6.1 - Retencion de MetaWebhookEvent (DONE)
- `notifications/tasks.py::purge_meta_webhook_events_task` + seed `0009_seed_purge_meta_webhook_events_task.py` (PeriodicTask diaria 03:30, cola `notifications`).
- Politica: `payload` sanitizado (`{}`) a los 30 dias; fila borrada a los 180.

### FASE 7 - Meta Marketing READ API (DONE)
- `marketing/integrations/meta/marketing.py` - `MetaMarketingClient` sobre `MetaGraphClient`: `list_campaigns` / `get_campaign` / `list_adsets` / `list_ads` / `get_insights` (soporta `time_range` o `date_preset`) / `get_account_summary`. `_act()` normaliza el ad account id (antepone `act_`). **Solo GET.**
- `marketing/services/meta_selectors.py` - `MetaCampaignSelector`: normaliza (presupuestos de unidad minima -> decimal string, `purchase_roas` lista -> numero) y devuelve estructuras planas. Propaga las excepciones tipadas de la frontera Meta sin envolver (cada vista las mapea).
- Tests: `test_marketing.py` (6), `test_selectors.py` (4).

### FASE 9 - Endpoints internos internal_ai Meta READ (DONE)
- `marketing/api/internal_ai.py` - `AiMetaCampaignsView`, `AiMetaCampaignDetailView`, `AiMetaInsightsView`, `AiMetaAccountSummaryView`. `IsAdminUser`. Helper `_meta_error_response()`: `MetaConfigError` -> 503 (`configured: false`), auth/rate/transient/api -> 502. Validacion de `level` y `date_preset` contra allowlist.
- Registradas en `ecommerce/internal_ai_urls.py` bajo `marketing/meta/...`. Nginx no proxea `/internal/`.
- Tests: `marketing/tests.py::MetaAdsInternalAiViewsTestCase` (6).

**Checkpoint FASE 4/6.1/7/9 (PASS):** `manage.py test marketing` (57 OK), `manage.py test notifications` (sin regresiones), `makemigrations --check` limpio (`notifications` sin cambios pendientes).

---

## 6. Fases pendientes

Notacion: **Goal** / **Archivos** / **Reglas** / **Tests** / **PASS/FAIL**.

### FASE 8 - Dashboard Meta READ (BFF)
- **Goal:** panel `/panel/marketing/meta/*`.
- **Archivos:** `dashboard/api/views.py` (+ViewSet Meta), `dashboard/services/*`, rutas `/api/v1/dashboard/marketing/meta/...`. Frontend `frontend/src/apps/admin/...`.
- **Reglas:** operaciones administrativas pasan por el BFF `dashboard`, no por el endpoint publico ni por `internal_ai`. Permiso admin.
- **Tests:** `manage.py test dashboard` - contrato del endpoint; permiso denegado a no-admin.
- **PASS:** un admin ve resumen/campanas/rendimiento; un no-admin recibe 403.

### FASE 10 - MCP Client en ai_engine (DONE 2026-08-31, falta la autorizacion del usuario)

**Meta lanzo el 2026-04-29 un MCP remoto de primera parte** en `https://mcp.facebook.com/ads`
(gratis en beta; ~125 tools incl. WhatsApp Business management).

OAuth real, **verificado contra el endpoint 2026-08-31** (`.well-known/oauth-authorization-server/ads`):
- `authorization_endpoint`: `https://www.facebook.com/v26.0/dialog/oauth` (el dialogo de Facebook Login).
- `token_endpoint`: `https://graph.facebook.com/v26.0/oauth/access_token`.
- `token_endpoint_auth_methods_supported: ["none"]`, `code_challenge_methods_supported: ["S256"]` -> cliente publico + PKCE, sin secret.
- `scopes_supported`: `ads_read, ads_management, catalog_management, business_management, pages_show_list, instagram_basic, ads_mcp_management`.
- **Dynamic client registration NO disponible** (`/register/ads` -> 400 `"Dynamic registration is not available for this client"`). **Hace falta un App de Meta** (developers.facebook.com): su App ID es el `client_id`, y el App necesita `http://localhost:{MCP_OAUTH_CALLBACK_PORT}/callback` en sus Valid OAuth Redirect URIs. `mcp_client/storage.py::seed_client_info()` siembra ese client_id para que el SDK salte el `/register`.

- **Paquete `ai_engine/mcp_client/`** (NO `mcp/` -- ai_engine pone su raiz al frente de
  `sys.path`, un paquete `mcp` ensombreceria el SDK oficial que se importa como `import mcp`):
  - `client.py` - `MetaAdsMCPClient`: `list_tools()` / `call_tool(name, args)` / `ping()`.
    Solo habla el protocolo (transporte streamable-HTTP + OAuth). Contrato de errores como
    `tools/http_bridge.py`: nunca propaga excepciones, todo vuelve dict. El refresh token
    nunca sale de este modulo. Imports del SDK `mcp` perezosos.
  - `policy.py` - `classify_mcp_tool()` -> `allow`/`confirm`/`deny`, espeja
    `action_graph.py::node_evaluate_policy`. Con `MCP_META_ADS_ALLOW_WRITES=False` (FASE 10)
    **cualquier tool que no sea lectura clara se deniega**; dinero/facturacion/cuenta -> deny
    siempre.
  - `registry.py` - `MCPServerRegistry` (hoy solo `meta_ads`).
  - `storage.py` - `FileTokenStorage` (Protocol `TokenStorage` del SDK) -> `/data/mcp/*.json`,
    0600, volumen `*_mcp_tokens`.
  - `authorize.py` - CLI one-shot: `python -m mcp_client.authorize` (arranca callback HTTP
    local, imprime la URL de Meta, el usuario inicia sesion, guarda el refresh token).
- **`ai_engine/config.py`**: `MCP_META_ADS_URL` / `MCP_META_ADS_ENABLED` (default False) /
  `MCP_META_ADS_ALLOW_WRITES` (default False) / `MCP_META_ADS_CLIENT_ID` (cae a `META_APP_ID`) /
  `MCP_META_ADS_SCOPE` (default `ads_read,business_management,pages_show_list,ads_mcp_management`) /
  `MCP_TOKEN_STORE_DIR` / `MCP_OAUTH_CALLBACK_PORT` (default 8766 -- 8765 lo usa el SMS bridge) /
  `MCP_CALL_TIMEOUT_S`.
- **`ai_engine/requirements.txt`**: `mcp>=1.24,<1.25` (mcp >=1.25 arrastra starlette 1.x,
  incompatible con el fastapi 0.115 del engine; 1.24.0 resuelve con starlette 0.46.2 y
  `main.py` sigue importando). **Requiere `docker compose build sintel_ai`.**
- **`docker-compose(.prod).yml`**: volumen `*_mcp_tokens:/data/mcp` en el servicio `sintel_ai`.
- **`gateway/router.py`**: `GET /api/v1/ai/mcp/status` y `POST /api/v1/ai/mcp/ping` (dev,
  detras de `AI_TOOLS_DEBUG`; ping solo admin) para verificar la conexion.
- **Tests:** `ai_engine/tests/test_mcp_{policy,client,registry,storage}.py` (24), + suite
  completa `pytest tests/` 158 passed / 16 skipped con `mcp` instalado.
- **PASS verificado:** cliente lista/llama tools contra sesion MCP falsa; escrituras
  denegadas sin abrir sesion; `mcp_client` no importa Django/ORM; el token no aparece en
  ningun dict de salida ni log.
- **Pendiente (usuario):** `docker compose build sintel_ai` -> `docker compose run --rm
  -p 8765:8765 sintel_ai python -m mcp_client.authorize` -> login en el navegador -> poner
  `MCP_META_ADS_ENABLED=true` y reiniciar. Ver seccion 9.

### FASE 11 - Capabilities Meta Ads (READ) -- PARCIAL (camino corto, 2026-09-15)

**Estado real: mecanismo cerrado y verificado contra el runtime ADK real (dev); routing/intents
dedicados (originalmente planeados para FASE 12) NO estan hechos; el path MCP sigue sin
autorizar.** No declarar esta fase `DONE` -- ver honestidad de alcance abajo.

- **Archivos reales (distintos de lo planeado originalmente):**
  - `ai_engine/tools/marketing_tools.py`: 4 Tools nuevas (`MetaCampaignsTool`,
    `MetaCampaignDetailTool`, `MetaInsightsTool` -- cubre account/campaign/adset/ad via el
    parametro `level`, `MetaAccountSummaryTool`), todas envolviendo las vistas `AiMeta*View` de
    FASE 9 (`internal_ai`, Django) via `django_internal_get` -- **NO tocan el MCP** (FASE 10
    sigue sin OAuth real, el volumen `*_mcp_tokens` esta vacio en dev y prod, verificado).
  - `ai_engine/capabilities/registry.py`: 4 capabilities nuevas, nombradas en espanol siguiendo
    la convencion REAL ya usada en el archivo (`consultar_campanas_meta`,
    `consultar_detalle_campana_meta`, `consultar_insights_meta`, `consultar_resumen_cuenta_meta`)
    -- **no son los IDs `meta_ads_*` que este plan proponia originalmente**, se prefirio
    consistencia con las ~20 capabilities ya existentes sobre el nombre propuesto en el plan.
  - `ai_engine/agents/profiles/marketing_agent.yaml`: las 4 Tools + 4 capabilities agregadas a
    `herramientas`/`capacidades` de `MarketingAgent` (perfil ya existente, no se creo un
    `MetaAgent` nuevo -- coherente con la regla de FASE 12 de abajo).
  - No se toco `meta_ads_performance_diagnosis` (analisis compuesto, no un wrap 1:1 de una vista
    -- fuera de alcance del camino corto) ni ninguna capability sobre MCP.

- **Verificado real contra `ecommerce_sintel_ai_adk` (dev, rebuild + restart, nunca produccion):**
  - `_load_profiles()` valida las 9 `herramientas`/9 `capacidades` de `MarketingAgent` sin error
    (import directo de `agents` dentro del contenedor, los 9 perfiles cargan).
  - `sintel_adapter.adapt_sintel_tool()` envuelve las 4 Tools nuevas en `FunctionTool` real de
    ADK sin error.
  - Round-trip real end-to-end con un JWT real de un admin de dev: `tools.invoke("MetaCampaignsTool", ...)`
    -> `http_bridge` -> Django `internal_ai` real -> `MetaCampaignSelector` -> `MetaGraphClient`
    -> degrada correctamente a `503 {"configured": false}` (falta `META_AD_ACCOUNT_ID` real) --
    **nunca inventa datos**, tal como exige la regla de honestidad de este plan.
  - Regresion: **correccion 2026-09-15 (misma tarea, verificacion inicial estaba mal)** -- la
    primera corrida de regresion de `ai_engine` (OLD) uso la imagen Docker vieja sin rebuild
    (`docker compose run` no reconstruye sola), asi que en realidad NO habia probado este cambio
    -- daba 104/16 identico al baseline solo porque corria codigo previo a este commit. Rehecho
    con `docker compose build sintel_ai` primero: **112 passed/16 skipped** (+8 tests nuevos, 4
    capabilities x 2 casos del `test_tool_policy_matrix.py` generico -- ver abajo). `ai_engine_adk`
    (que si se habia rebuildeado desde el principio): 25 passed, 6 failed -- **los 6 fallos son
    100% por LM Studio apagado en este host ahora mismo** (`curl localhost:1234/v1/models` ->
    connection refused), confirmado no relacionado con este cambio (son los tests E2E reales
    contra el LLM local, ya existian antes).

- **Hallazgo colateral (no corregido, fuera de alcance de esta tarea):** `ai_engine/tools/http_bridge.py::_map_response()`
  no tiene rama especifica para 5xx de Meta -- el `detail` util que Django ya arma (ej. "META_AD_ACCOUNT_ID
  no configurado") se pierde y el LLM solo ve "Error consultando los datos.". No es un riesgo de
  seguridad, es una perdida de contexto util para FASE 20 (Observabilidad) o un ajuste menor de
  `_map_response()` si se decide priorizarlo.

- **Honestamente NO hecho (no inventar que si):**
  - FASE 12 (routing dedicado): NO se agregaron intents nuevos (`marketing.meta_campaign_status`,
    etc.) ni reglas de router. Estas 4 Tools solo son alcanzables cuando `MarketingAgent` ya se
    selecciona por los intents existentes (`marketing_admin` -- su regex real en `routing.py` SI
    matchea "campan\|campaña\|metricas\|conversion", asi que en la practica alcanza estas Tools
    tambien -- verificado leyendo el regex real, no asumido -- pero no es una ruta dedicada).
  - Path MCP (datos publicitarios en tiempo real via `MetaAdsMCPClient`) sigue completamente sin
    conectar al Tool Registry -- bloqueado en el OAuth real (FASE 10 go-live, seccion 9).
  - `meta_ads_performance_diagnosis` (analisis compuesto) no existe.
  - Ninguna de las 4 Tools devuelve datos reales todavia -- depende de que `META_APP_ID`/
    `META_ACCESS_TOKEN`/`META_AD_ACCOUNT_ID` reales se carguen (bloqueado en FASE 0, ver seccion 3).

- **Tests formales: SI cubiertas, sin escribir nada nuevo.** `ai_engine/tests/test_tool_policy_matrix.py`
  esta parametrizado sobre `CapabilityRegistry.list_active()` (disenado explicitamente para no
  requerir un caso a mano por Tool nueva, ver su docstring) -- las 4 capabilities Meta quedaron
  cubiertas automaticamente: `consultar_campanas_meta`/`consultar_detalle_campana_meta`/
  `consultar_insights_meta`/`consultar_resumen_cuenta_meta`, 8/8 passed (deny a usuario normal,
  allow/confirm a staff) contra la imagen `sintel_ai` (OLD) recien reconstruida. La afirmacion
  anterior de esta seccion ("no se escribio un test dedicado, pendiente") estaba **incorrecta**
  -- corregida tras verificar contra el contenedor real, no asumida.

### FASE 12 - MarketingAgent + Meta
- **Archivos:** `ai_engine/agents/profiles/marketing_agent.yaml` (+intents `marketing.meta_campaign_status`, `marketing.ad_performance`, `marketing.budget_analysis`, `marketing.optimization`; +las 6 capabilities), router en `ai_engine/agents/__init__.py`.
- **Reglas:** NO crear `MetaAgent`. El router decide: interno -> Django, publicitario -> MCP, comparacion -> ambos.
- **Tests:** `ai_engine/tests/` - "cuanto gastamos ayer" enruta a MarketingAgent + capability READ.
- **PASS:** intents nuevos alcanzan MarketingAgent; los intents viejos no se rompen.

### FASE 13 - Comparacion Meta <-> ventas SINTEL
- **Goal:** "que campana produjo mas ventas *reales*" = insights MCP (spend, ROAS reportado) cruzado con `internal_ai` (pedidos, pagos confirmados, cancelaciones, devoluciones, margen).
- **Archivos:** `ai_engine/tools/marketing_tools.py` (tool de reconciliacion), selector nuevo en `marketing/services/meta_selectors.py` que junta ambos lados a nivel de `internal_ai`.
- **Reglas:** "Purchase real" = pago confirmado (no orden creada). Reusar la distincion orden/pago que ya hace `payment`.
- **PASS:** respuesta distingue "ROAS Meta" de "rentabilidad SINTEL".

### FASE 14 - Policy Layer Meta (WRITE gating)
- **Archivos:** `ai_engine/mcp/policy.py`, `ai_engine/action_graph.py` (metadata de las Tools de escritura), `ai_engine/tools/metadata.py`.
- **Reglas:** READ -> ALLOW. WRITE -> CONFIRM (interrupt humano). Cambios de cuenta/pago -> DENY.
- **Tests:** `ai_engine/tests/test_policy_layer.py`, `test_security_adversarial.py`.
- **PASS:** "pausa la campana X" -> `confirm`; "cambia el metodo de pago" -> `deny`.

### FASE 15 - Human Approval para writes
- **Archivos:** reusar `node_await_confirmation` / `interrupt()` de `ai_engine/action_graph.py`; UI de aprobacion en `/panel/soporte` o `/panel/marketing`.
- **PASS:** un write publicitario no se ejecuta hasta que un admin acepta en el panel; el `approval_id` queda en el audit trail (FASE 23).

### FASE 16 - Writes pequenos: pause / resume
- **Archivos:** `ai_engine/capabilities/registry.py` (+`meta_ads_pause_campaign`, `meta_ads_resume_campaign` - WRITE/CONFIRM), `marketing/services/meta_commands.py` (`MetaCampaignCommands.pause_campaign()/resume_campaign()` via `MetaMarketingClient`), `marketing/api/internal_ai.py` (POST correspondientes).
- **Reglas:** Command para escritura. El POST interno tiene permission class real + `SecurityEvent`.
- **PASS:** pause/resume funciona contra una **cuenta de test de Meta** tras aprobacion; sin aprobacion no hace nada.

### FASE 17 - Cambios de presupuesto
- **Archivos:** `MetaCampaignCommands.update_budget()`, capability `meta_ads_update_budget` (WRITE/CONFIRM), limites en `ai_engine/mcp/policy.py`.
- **Reglas (obligatorias):**
  ```
  cambio <= 10%        -> confirmacion simple
  10% < cambio <= 30%  -> confirmacion reforzada
  cambio > 30%         -> admin manual (fuera del agente)
  creacion de campana  -> siempre confirm
  borrado de campana   -> DENY
  cambios de cuenta/pago -> DENY
  ```
- **Tests:** matriz de porcentajes en `test_policy_layer.py`.
- **PASS:** subir $100 -> $110 pide confirmacion simple; $100 -> $5000 se escala a admin manual.

### FASE 18 - Creacion de campana
- **Archivos:** `MetaCampaignCommands.create_campaign()/create_adset()/create_ad()`, capabilities WRITE/CONFIRM.
- **PASS:** crea campana en cuenta de test tras confirm; queda auditada.

### FASE 19 - Conversions API (CAPI)
- **Archivos:** `marketing/integrations/meta/conversions.py` (`MetaConversionsClient`), hook en `payment` post-confirmacion (`transaction.on_commit` -> Celery -> `MetaConversionsClient`).
- **Reglas:** SSoT unica: `Purchase` = pago realmente confirmado, no `Order created`. Eventos: ViewContent/AddToCart/InitiateCheckout/Purchase/Lead/Contact/Schedule.
- **Tests:** `manage.py test payment` - `on_commit` dispara la tarea con el payload correcto; no dispara si el pago no se confirma.
- **PASS:** un pago APPROVED genera exactamente un evento `Purchase` en CAPI (sandbox/test event code).

### FASE 20 - Sincronizacion de catalogo
- **Archivos:** `marketing/integrations/meta/catalog.py`, `marketing/services/commands.py` (`MetaCatalogSyncService`), Celery task.
- **Reglas:** `shop.Product`/`shop.ProductVariant`/`inventory.StockRecord` -> Meta Catalog. Pull-based (no importar modelos de shop directo desde marketing -> usar los `*SummaryProvider` existentes). SINTEL = SSoT, Catalog = proyeccion.
- **PASS:** alta/baja/cambio de precio en un producto se refleja en el catalogo; nunca al reves.

### FASE 21 - APIs de Instagram / Facebook
- **Archivos:** `marketing/integrations/meta/{pages.py,instagram.py}` completos (posts, comments, DMs, mentions, insights, media).
- **Reglas:** dominio y policy distintos de WhatsApp. No mezclar.
- **PASS:** publicar/leer en Page e IG desde el panel; WhatsApp intacto.

### FASE 22 - Observabilidad
- **Archivos:** `ai_engine/observability.py`, metricas Django (latencia/errores/quota de Graph API; llamadas/latencia/errores de MCP; webhooks recibidos/rechazados/duplicados; mensajes enviados/fallidos; writes de campana; aprobaciones humanas; cambios de presupuesto).
- **Reglas:** correlacionar por `request_id`, `conversation_id`, `user_id`, `meta_object_id`, `tool_name`, `approval_id`.
- **PASS:** un dashboard muestra esas series; una llamada agentic se puede seguir end-to-end por `conversation_id`.

### FASE 23 - Audit trail de escrituras Meta
- **Archivos:** `marketing/models.py` (`MetaActionAudit`: actor, agent, conversation_id, action, object_type, object_id, before, proposed, after, source `API`|`MCP`, approval_required, approved_by, approved_at, meta_request_id, status, error, created_at), escritura desde cada Command de escritura Meta.
- **PASS:** se puede responder quien/por que/que agente propuso/quien aprobo/que habia antes/que respondio Meta para cualquier cambio.

### FASE 24 - Tests E2E sandbox / cuenta de test
- **Archivos:** `ai_engine/e2e_http/`, `ai_engine/e2e_ui/`, cuenta publicitaria de test de Meta.
- **PASS:** flujo completo "pregunta -> analisis -> propuesta -> aprobacion -> ejecucion -> auditoria" verde contra sandbox.

### FASE 25 - Canary produccion
- **PASS:** writes habilitados solo para 1 campana de bajo presupuesto durante N dias, con alertas; sin incidentes -> FASE 26.

### FASE 26 - Activacion completa
- **PASS:** todas las capabilities activas; runbook de rollback documentado; MEMORY.md + `.AGENT` docs actualizados.

---

## 7. Seguridad de tokens (aplica a todas las fases)

Nunca entregar el token Meta a: frontend, prompt del LLM, RAG, `ChatRoom`, audit
log, respuesta del MCP. API directa: `Django -> secret manager -> Graph API`.
MCP: `ai_engine -> OAuth MCP -> Meta` (credenciales independientes). `META_APP_SECRET`
solo para verificar la firma de webhooks entrantes.

## 8. Lo que NO se cambia

`ai_engine` separado de Django; `ai_engine` nunca toca el ORM; Web + WhatsApp ->
misma `ChatRoom`; Human Handoff controlado por Django; Capabilities antes que Tools;
Policy Layer `deny`/`confirm`/`allow`; Redis para rate limit; Commands para escritura;
Selectors para lectura; Celery para procesamiento externo.

## 9. Autorizar el MCP de Meta Ads (FASE 10 -- accion del usuario)

### 9.1 Crear el App de Meta (una vez)
1. https://developers.facebook.com/apps -> **Create App** -> tipo **Business**
   (asociado al Business Manager `3054417098283269`).
2. Agregar el producto **Facebook Login for Business**.
3. En "Facebook Login for Business" -> Settings -> **Valid OAuth Redirect URIs**:
   `http://localhost:8766/callback`
4. Copiar el **App ID** (Settings -> Basic).
5. Permisos: el flujo pide `ads_read, business_management, pages_show_list,
   ads_mcp_management`. Como administrador/developer del App funcionan en modo
   desarrollo sin App Review; para uso continuo, enviar a revision.

### 9.2 Autorizar (dev)
```
cd ecommerce_sintel
# en .env  ->  META_APP_ID=<el App ID del paso 9.1.4>
docker compose -f docker-compose.yml build sintel_ai          # instala mcp>=1.24
docker compose -f docker-compose.yml run --rm -p 8766:8766 \
    sintel_ai python -m mcp_client.authorize
```
Imprime una URL de `facebook.com/dialog/oauth`. Abrela, inicia sesion con la
cuenta que administra el Business Manager, acepta. El callback
(`http://localhost:8766/callback`) confirma solo; el script lista las tools y
termina. Luego:
```
# en .env  ->  MCP_META_ADS_ENABLED=true
docker compose -f docker-compose.yml up -d sintel_ai
```
Verificar: `GET http://localhost:8100/api/v1/ai/mcp/status` (JWT admin +
`AI_TOOLS_DEBUG=true`) -> `"authorized": true`.

**Prod:** igual con `docker-compose.prod.yml run --rm -p 8766:8766 sintel_ai
python -m mcp_client.authorize` en el host. El token queda en `sintel_prod_mcp_tokens`.
Reautorizar solo si Meta revoca.

El refresh token vive SOLO en `/data/mcp/` del contenedor `sintel_ai`. Django no
lo conoce; el LLM no lo ve; no aparece en logs.
