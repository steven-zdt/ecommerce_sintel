# LLM Provider Registry dinamico - FASE 0 (discovery) y FASE 4 (resolver + runtime) - 2026-09-25

Plan: `PLAN_LLMDINAMICO.md`. Estado global: **IN_PROGRESS**. Esta entrega cubre el discovery y la FASE 4; el resto queda como hoja de ruta.
Los tests se escribieron pero NO se ejecutaron (instruccion del usuario). Nada se toco en produccion (regla 0-DEV-FIRST).

## 1. Hallazgo principal
La app `ai_provider` ya existe (2026-08-13): modelos `AIProvider`/`AIModel`/`AIChannelConfig`/`AIChannelFallback`, API admin
(`/api/v1/dashboard/ai-providers/`, `ai-channel-config/`), UI `/panel/soporte/ia-config`, adapters Ollama/OpenAI-compatible/Anthropic,
key cifrada (Fernet) y endpoint interno `/api/v1/internal/ai/provider-config/`. Pero lo consumia el motor **viejo** (`ai_engine`).
El runtime real del chat, `ai_engine_adk`, solo leia `LOCAL_MODEL_CHAIN` (env): **cambiar el modelo desde el panel no tenia efecto**.
No se creo una segunda entidad: se reutiliza el modelo existente (el plan pide buscar antes de crear).

## 2. Estado por seccion del plan
| Plan | Estado | Nota |
|---|---|---|
| 1 Capacidad admin (crear/editar/probar/detectar modelos/primary/fallback/orden) | Existe | `ai_provider` + `ia-config` |
| 1 Historial, rollback, `config_version` | **Hecho (backend)** | `AIConfigRevision` + `services/revisions.py`, migracion `0007` (con baseline v1 de lo existente). Endpoints: `GET/POST ai-channel-config/history|rollback/` y `GET/POST ai-providers/<uuid>/history|rollback/`. Falta la UI (pestana Historial, comparar) |
| 3 Modelo de datos | Existe parcial | `config_version` hecho (canal y proveedor). Faltan `verify_tls`, `top_p`, `auth_type`/`api_key_header`, `connect_timeout`, `endpoint_path`, capabilities |
| 4 Proveedores | Parcial | OLLAMA, OPENAI_COMPATIBLE, ANTHROPIC. Faltan GEMINI, GENERIC_REST, MCP, CUSTOM |
| 5 MCP como integracion independiente | Falta | existe `ai_engine/mcp_client` (Meta Ads) sin relacion con el Registry |
| 6 PRIMARY/FALLBACK ordenados | Existe | `AIChannelConfig` + `AIChannelFallback`; ADK ya recorre la cadena con breaker (F3) |
| 7 Cambio en caliente + snapshot por turno | **Hecho en esta fase (ADK)** | ver sec. 3. Falta `provider_changed` y validar antes de activar |
| 8 Secretos | Existe | cifrado en reposo, la API admin solo devuelve `has_api_key` |
| 9 SSRF | **Hecho en Django (parcial)** | `ai_provider/services/url_guard.py` llamado desde `AIProvider.clean()` (create y update pasan por `full_clean`): bloquea esquemas no http(s), metadatos de nube, link-local, puerto de la API de Docker y credenciales en la URL; los adapters ya no siguen redirects. El ADK re-valida la URL con su copia `ai_engine_adk/url_guard.py` y descarta entradas inseguras. Falta cubrir DNS rebinding |
| 10 Capabilities | Falta | solo `TOOL_CALLING_UNSUPPORTED` como codigo de error |
| 11 ADK + LiteLLM | **Hecho en esta fase** | `FallbackLiteLlm` resuelve la cadena por turno |
| 12 Commands | Parcial | `AIProviderCommands`, rollback en `services/revisions.py`; **SetPrimary ya valida antes de persistir** (`services/activation.py`). Faltan comandos separados Activate/SetFallback con validacion |
| 13 API admin | Parcial | faltan `/activate`, `/primary`, `/fallback`, `/health`, `/history`, `/rollback` con esos nombres |
| 14 UI | Parcial (mejorada) | `AIProviderConfigView.vue` ahora muestra proveedor/modelo activos, estado, latencia de la ultima prueba y `config_version`; aviso 409 con "Activar de todas formas"; `AIConfigHistory.vue` (historial + restaurar). Faltan: comparar versiones, historial por proveedor, formulario por secciones |
| 15-16 Test de conexion / health / circuit | Parcial | breaker por proveedor en el ADK (F3); falta estado HEALTHY/DEGRADED/... persistido |
| 17 Observabilidad | Parcial | ADK ya registra provider/model/fallback_used/reason; `config_version` viaja en el endpoint interno y se loguea al cargar la cadena (`registry_chain_loaded`); falta en las metricas por turno |
| 19 Compatibilidad `LOCAL_MODEL_CHAIN` | **Hecho** | queda como bootstrap/emergencia si el Registry esta apagado, vacio o inalcanzable sin cadena previa |
| 20 Seguridad admin | Existe | `IsAdminUser` en todo `dashboard/ai-*` |
| 21-23 Tests / E2E / fallback real | Parcial | tests de F4 escritos; E2E y fallback real los corre el usuario |

## 3. Que cambio en FASE 4
- `ai_engine_adk/provider_registry.py` (nuevo): consulta el endpoint interno, cache con TTL (15 s), conserva la ultima cadena buena hasta
  5 min si Django falla, y devuelve `None` (= usar `LOCAL_MODEL_CHAIN`) si el canal esta apagado, sin primario o sin respuesta previa.
- `ai_engine_adk/model_runtime.py`: `FallbackLiteLlm(use_registry=...)` resuelve la cadena por turno (snapshot en un ContextVar aparte,
  que nunca entra a las metricas), reutiliza el `LiteLlm` por entrada mientras no cambien URL/modelo/key, y `llm_params_for_entry` usa la
  `api_key_value` del Registry. Sin flag el comportamiento es identico al anterior.
- `ai_engine/config.py`: `AI_PROVIDER_REGISTRY_ENABLED` (**false por defecto**), `_TTL_SECONDS`, `_TIMEOUT_SECONDS`, `_STALE_SECONDS`.
- Tests: `ai_engine_adk/tests/test_provider_registry.py`.

## 4. Limitaciones conocidas de esta entrega
1. `grounding.py` sigue usando `_resolve_primary_llm_params()` (primera entrada de `LOCAL_MODEL_CHAIN`) para su llamada directa de
   verificacion: con el Registry activo esa llamada no sigue el cambio. Se corrige en la siguiente entrega.
2. Los agentes estan cacheados por proceso, por eso el modelo resuelve la cadena en cada llamada y no al construir el agente.
3. El endpoint interno devuelve `api_key_value`. Defensa en profundidad agregada: exige `X-AI-Service-Token` (mismo `AI_SERVICE_TOKEN` de F2,
   con rotacion por `AI_SERVICE_TOKEN_PREVIOUS`). `AI_PROVIDER_CONFIG_TOKEN_REQUIRED=false` (default) = solo monitor (log
   `ai_provider_config_token_invalid`); `true` = 403 uniforme. El ADK ya envia el token. Antes de poner `true`, verificar que
   `AI_SERVICE_TOKEN` sea igual en el `.env` de Django y en el del ADK, y que el motor viejo `ai_engine` (que llama a este endpoint sin token)
   no se use; si se usa, queda en monitor.
4. SSRF: Django y ADK validan la URL, pero ninguno detecta DNS rebinding ni un host que resuelve distinto despues. Con el Registry en
   produccion, cualquier admin (`IsAdminUser`) decide a que URL llama el ADK: revisar quien tiene ese permiso antes de activarlo.

## 5. Activacion (cuando corresponda; la hace el usuario, dev primero)
1. En dev: `AI_PROVIDER_REGISTRY_ENABLED=true` en `.env` **y** en `.env.production` en el mismo cambio (ver memoria de sincronia de flags);
   recrear el contenedor: `docker compose up -d --force-recreate sintel_ai_adk` (un `restart` no relee `env_file`).
2. En `/panel/soporte/ia-config` verificar que `support_chat` tenga primario (p. ej. Ollama / `qwen3.5:9b`) y fallback.
3. Cambiar el primario en el panel; en <= 15 s el siguiente turno debe usarlo (log `ai_operation_event=registry_chain_loaded`, y
   `provider`/`model` en las metricas del turno). Sin reinicios.
4. Rollback: `AI_PROVIDER_REGISTRY_ENABLED=false` (o vaciar el primario en el panel) y volver a `LOCAL_MODEL_CHAIN`.

## 6. Siguiente orden recomendado
1. ~~FASE 3 Seguridad~~ hecha (guard Django + ADK, token ADK -> Django en monitor). Tests: `ai_provider/tests_url_guard.py`, `test_provider_registry.py`.
2. ~~Historial + `config_version` + rollback~~ hecho (backend + UI del canal). ~~Validacion previa al activar un primario~~ hecha (`POST ai-channel-config/set-primary/` valida y devuelve 409 con el motivo; `force=true` la omite; `POST .../validate-model/` es el dry-run).
3. Capabilities y detectar capacidades; bloquear operaciones que requieren tool calling si el proveedor no lo soporta.
4. Adapters Gemini y GenericREST (mapping declarativo, sin eval); MCP como integracion aparte.
5. `grounding.py` sobre el Registry; UI: estado/latencia/version/historial.
6. Canary (F17) y produccion, con aprobacion humana.

## 7. Historial y rollback (entrega 3)
- Cada cambio que afecta al canal `support_chat` (primario, fallbacks, enabled, edicion/activacion/borrado de proveedor o modelo) sube
  `AIChannelConfig.config_version` y guarda un snapshot inmutable; cada cambio de un proveedor sube su propia `config_version`.
- Los snapshots **no contienen secretos** (`has_api_key` booleano). Rollback de proveedor conserva la key actual; la URL restaurada vuelve a
  pasar por el guard SSRF. Rollback de canal es todo-o-nada: si un modelo referenciado fue borrado se rechaza sin cambios.
- El rollback es un cambio nuevo (`rollback_to_vN`), el historial nunca se reescribe.
- Migracion `0007` (crea `AIConfigRevision`, agrega `config_version` y crea baseline v1). **La aplica el usuario en dev primero:**
  `docker exec ecommerce_sintel_django python manage.py migrate ai_provider`; y para comprobar que no hay deriva entre modelo y migracion:
  `... manage.py makemigrations --check --dry-run ai_provider` (la migracion se escribio a mano).
- Tests escritos, no ejecutados: `ai_provider/tests_revisions.py`.

## 8. Validacion previa y UI (entrega 4)
- `set-primary` valida (modelo y proveedor activos, conectividad, el proveedor reporta el modelo) ANTES de persistir; ante un fallo responde
  409 `{error: 'validation_failed', report}` y NO cambia nada. Proveedores que no listan modelos pasan con advertencia. `force=true`
  (confirmacion explicita en la UI) omite la validacion. Quitar el primario no se valida. Solo pruebas inocuas (ping + listado de modelos).
- UI: la pantalla de `ia-config` muestra la configuracion activa y el historial con restaurar. Verificacion de sintaxis de los `.vue` con
  `@vue/compiler-sfc` (sin errores de plantilla/script); la prueba visual es manual.
- Tests escritos, no ejecutados: `ai_provider/tests_activation.py`. Se ajusto `ai_provider/tests.py::test_add_model_and_set_as_primary`
  (usa `force` porque su proveedor `http://x:11434` no existe).

## 9. Bug "Conexion fallo: No se pudo establecer conexion" en /panel/soporte/ia-config (2026-09-25)
- **Causa raiz (reproducida en dev con una red temporal):** el servicio `django` de `docker-compose.prod.yml` fija `dns: 1.1.1.1 / 8.8.8.8` y no tenia
  `extra_hosts`; con DNS publicos, `host.docker.internal` no resuelve dentro del contenedor (`Name or service not known`). "Probar conexion" y
  "Detectar modelos" corren en Django, asi que nunca llegaban a LM Studio. Con `extra_hosts: host.docker.internal:host-gateway` responde 200.
  (`sintel_ai` y `sintel_ai_adk` ya lo tenian por el mismo hallazgo de 2026-09-14.)
- **Arreglo de conectividad:** `extra_hosts` agregado al servicio `django` (compose prod). Requiere recrear `django`; no requiere reconstruir imagen.
- **Arreglo de diagnostico (codigo, requiere rebuild de django):** el mensaje generico ocultaba la causa. Ahora `ai_provider/services/providers/base.py::
  connection_failure` devuelve mensajes especificos (DNS, conexion rechazada, sin ruta, timeout) y detecta `localhost/127.0.0.1` (que dentro de Docker es
  el contenedor) con la instruccion de usar `host.docker.internal`. Verificado en dev con 5 escenarios reales; tests escritos en
  `ai_provider/tests_providers.py::TestConnectionFailureMessages` (no ejecutados).
- **Nota:** el chat NO usa lo que se configura en el panel hasta activar `AI_PROVIDER_REGISTRY_ENABLED`; hoy manda `LOCAL_MODEL_CHAIN`.
