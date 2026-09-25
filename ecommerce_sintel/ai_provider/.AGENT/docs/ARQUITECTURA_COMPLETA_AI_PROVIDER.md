# ARQUITECTURA COMPLETA -- ai_provider

**Creada:** 2026-08-13, plan maestro "CONFIGURACION DINAMICA DE MODELOS LOCALES
PARA CHAT SUPPORT". Ver `ai_provider/.AGENT/FASE1_MODELOS.md` a `FASE5_FRONTEND.md`
para el detalle fase por fase (evidencia, tests, decisiones).

## Responsabilidad

Fuente oficial de configuracion operativa del/los motor(es) LLM usados por el
chatbot de soporte (`support`/`ai_engine`) -- que proveedor y modelo estan activos,
en que orden cae el fallback, credenciales cifradas en reposo. Editable en runtime
desde `/panel/soporte/ia-config` sin tocar `.env` ni reiniciar contenedores
(dentro de la ventana de cache de 15s de `ai_engine`).

**NO** reemplaza `LOCAL_MODEL_CHAIN` (`ai_engine/config.py`) -- ese mecanismo
queda como bootstrap/fallback/emergencia (regla explicita del plan maestro).
**NO** es el "cerebro" del chatbot -- `ai_engine` sigue siendo el unico que
ejecuta el Action Graph, RAG, Tools; esta app solo le dice QUE modelo usar.

## Modelos (`models.py`)

- `AIProvider`: `name`, `kind` (`ollama-nativo`/`openai-compatible`/`anthropic`
  -- mismo vocabulario que `ai_engine/llm_factory.py`), `base_url`, `api_key`
  (`shared.fields.EncryptedTextField`, Fernet), `is_active`, `display_order`,
  campos de ultimo test de conexion.
- `AIModel`: FK a `AIProvider`, `model_id` (literal, nunca traducido),
  `display_name`, `is_active`, `discovered_automatically`.
- `AIChannelConfig`: canal (hoy solo `support_chat`) -> `primary_model`.
- `AIChannelFallback`: cadena ordenada de fallback por canal.

## Servicios (`services/`)

- `selectors.py`: `AIProviderSelector`, `AIChannelConfigSelector` (incluye
  `get_resolved_chain()`, la forma que consume el internal API).
- `commands.py`: `AIProviderCommands` (create/update/delete-soft/
  record_test_result -- `api_key=''` en update NUNCA borra la key existente),
  `AIModelCommands`, `AIChannelConfigCommands`.
- `connection_probe.py`: `probe_provider()`/`discover_provider_models()` --
  llamadas HTTP reales (nunca una generacion completa) para "probar conexion"
  y descubrimiento de modelos.

## Integracion cross-app (frontera oficial)

```
Django admin (/panel/soporte/ia-config)
    |  dashboard/ai-providers/, dashboard/ai-channel-config/ (IsAdminUser)
    v
dashboard.services.admin_orchestrators.AIProviderAdminOrchestrator
    |
    v
ai_provider.services.{selectors,commands}  -->  Postgres

AI Engine (/chat)
    |  GET /api/v1/internal/ai/provider-config/ (AllowAny -- aislamiento de red,
    |  mismo patron que el resto de /internal/ai/*, ver ai_provider/api/internal_ai.py)
    v
ai_provider.api.internal_ai.AiProviderConfigView
    |
    v
ai_provider.services.selectors.AIChannelConfigSelector.get_resolved_chain()
```

`ai_engine` **nunca** importa `ai_provider` ni Django ORM -- solo HTTP.
`ai_engine/llm_factory.py::get_dynamic_llm()` cachea la respuesta 15s, cae a
`LOCAL_MODEL_CHAIN` si la config esta vacia o Django es inalcanzable.

## Endpoints

| Metodo/Ruta | Uso | Permiso |
|---|---|---|
| `GET /api/v1/internal/ai/provider-config/?channel=` | AI Engine resuelve el LLM real | `AllowAny` (aislamiento de red) |
| `GET/POST/PATCH/DELETE /api/v1/dashboard/ai-providers/` | CRUD admin | `IsAdminUser` |
| `POST /api/v1/dashboard/ai-providers/<uuid>/test-connection/` | Probar conexion real | `IsAdminUser` |
| `GET /api/v1/dashboard/ai-providers/<uuid>/discover-models/` | Descubrir modelos reales | `IsAdminUser` |
| `POST/DELETE /api/v1/dashboard/ai-providers/<uuid>/models/...` | Agregar/quitar modelo | `IsAdminUser` |
| `GET/POST /api/v1/dashboard/ai-channel-config/...` | Primario/fallback del canal | `IsAdminUser` |

## Frontend

`/panel/soporte/ia-config` (`AIProviderConfigView.vue`) -- child route bajo el
grupo "Soporte" existente, no reemplaza `/panel/soporte` (analitica de chat).
Store: `frontend/src/store/aiProviderAdmin.js`. Servicio:
`frontend/src/services/aiProvider/aiProviderService.js`.

## Seguridad

- `api_key` cifrada en reposo (Fernet, `shared/fields.py::EncryptedTextField`,
  clave de `AI_PROVIDER_ENCRYPTION_KEY` o derivada de `SECRET_KEY`).
- Nunca expuesta al frontend (`AIProviderSerializer` solo serializa
  `has_api_key`, nunca el valor).
- Si expuesta a `ai_engine` (consumidor interno sancionado, la necesita para el
  cliente LLM real) -- via el endpoint interno, aislado de red igual que el
  resto de `/api/v1/internal/*`.

## Limitaciones conocidas (2026-08-13)

- `docker-compose.prod.yml` no define `sintel_ai`/`sintel_ollama` -- el motor de
  IA no corre en produccion hoy (hallazgo de FASE 0, no introducido por este
  plan).
- `sintel_ai` no tiene bind-mount de codigo -- cualquier cambio en `ai_engine/`
  requiere `docker compose build sintel_ai` real, no un simple restart
  (hallazgo de FASE 4).

## Cambios Recientes

### 2026-09-25 - Registry dinamico consumido por el ADK (PLAN_LLMDINAMICO, fases 0-4 parcial)
- `ai_engine_adk` ahora puede tomar la cadena de modelos de este dominio (`ai_engine_adk/provider_registry.py`, flag
  `AI_PROVIDER_REGISTRY_ENABLED`, apagado por defecto; `LOCAL_MODEL_CHAIN` queda como bootstrap/emergencia).
- Seguridad: `services/url_guard.py` (SSRF) llamado desde `AIProvider.clean()`; el ADK re-valida con su copia; el endpoint interno
  `provider-config` exige `X-AI-Service-Token` (`AI_PROVIDER_CONFIG_TOKEN_REQUIRED`, monitor por defecto); adapters sin redirects.
- Historial: `AIConfigRevision`, `config_version` en `AIChannelConfig` y `AIProvider`, `services/revisions.py` (rollback), migracion `0007`.
  Los Commands ya no llaman a `runtime_cache.invalidate` directo: pasan por `revisions.touch_channel`, que invalida y versiona.
- Endpoints nuevos (IsAdminUser): `ai-channel-config/history|rollback/`, `ai-providers/<uuid>/history|rollback/`.
- Detalle y pendientes: `AUDITORIA/LLM_PROVIDER_REGISTRY_F0_F4_2026-09-25.md`.
- Validacion previa: `services/activation.py`; `set-primary` responde 409 si el modelo no pasa (proveedor activo, conectividad, modelo
  disponible) salvo `force=true`; `POST ai-channel-config/validate-model/` es el dry-run. UI: `AIConfigHistory.vue` y panel de configuracion activa.

### 2026-09-25 - Incidente "Conexion fallo" / localhost (ver `AUDITORIA/INCIDENTE_IA_CONFIG_LOCALHOST_2026-09-25.md`)
- **Trampa conocida:** la `base_url` de un proveedor se usa DESDE el contenedor (Django para probar/descubrir, ADK para inferir). `localhost` = el contenedor. Usar
  `http://host.docker.internal:PUERTO` (host) o el nombre del servicio (`http://sintel_ollama:11434`). `AIProvider.clean()` rechaza loopback salvo
  `AI_PROVIDER_ALLOW_LOOPBACK=true` (Django fuera de Docker).
- `services/providers/base.py::connection_failure()` centraliza los mensajes de fallo de conexion (codigos: DNS, CONNECTION_REFUSED, NETWORK_UNREACHABLE, TIMEOUT,
  LOOPBACK_URL, UNKNOWN). Todo adapter nuevo debe usarlo; nunca devolver un mensaje generico.
- `django` en prod necesita `extra_hosts: host.docker.internal:host-gateway` (tiene `dns:` publicos). Lo mismo para cualquier servicio que llame al host.
- Diagnostico: si la peticion no aparece en el log del servidor LLM, el problema es red/URL. `config_version 1` = nunca se guardo una edicion.

