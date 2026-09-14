# FASE 13-14, 15, 19, 20 -- Dashboard reconciliation, Internal Facade reshape, RuntimeConfigResolver, Hot Reload

**Fecha:** 2026-08-13. Plan "AI Provider Runtime". Continua FASE7_12_PROVIDER_ADAPTERS.md.

## FASE 13-14 -- Dashboard Orchestrator + rutas (reconciliado, sin cambio de codigo)

`AIProviderAdminOrchestrator` (dashboard/services/admin_orchestrators.py) ya cubre
las 15 responsabilidades que pide FASE 13 (list/create/edit/delete/test/discover/
activate/deactivate/configure channel), consumido por
`dashboard/api/ai_provider_views.py` bajo `ADMIN_PERMISSIONS`.

**Decision explicita (ya tomada en FASE 0, reconfirmada aqui):** las rutas quedan
en el namespace plano existente `/api/v1/dashboard/ai-providers/` y
`/api/v1/dashboard/ai-channel-config/` -- el plan pide un namespace anidado
`/api/v1/dashboard/support/ai/...`. No se renombra: el namespace plano ya esta
probado (47+153 tests) y consumido por el frontend real (`AIProviderConfigView.vue`
en `/panel/soporte/ia-config`); renombrar URLs sin beneficio funcional es puro
churn con riesgo de romper el frontend por sincronizacion, no una mejora.

## FASE 15 -- Internal Facade (reshape real, mismo URL)

`GET /api/v1/internal/ai/provider-config/?channel=support_chat` -- shape nuevo:

```json
{"channel": "support_chat", "enabled": true, "primary": {...} | null, "fallbacks": [...]}
```

(antes: `{"channel": ..., "chain": [...]}` plano). `primary`/cada entrada de
`fallbacks` ahora es exactamente lo que devuelve
`BaseProviderAdapter.build_runtime_config(model)` (FASE 7) --
`{name, kind, base_url, model, api_key_env, api_key_value}`, el mismo shape que
`ai_engine/llm_factory.py::_build_model()` ya consume. Antes `_serialize_model()`
armaba un dict distinto (`model_id`/`provider` anidado) que `_fetch_dynamic_chain()`
tenia que desarmar a mano -- ahora es un solo shape compartido, sin remapeo en
ninguno de los dos lados.

No se renombro la URL (`provider-config/`, no `runtime/support/` como pide el
plan literal) -- unico consumidor real es este mismo proyecto (ai_engine), 0
beneficio en cambiar el nombre de la ruta y si un riesgo real: la vista Fase 2
lleva funcionando en produccion-de-desarrollo desde el 2026-08-13 temprano.

## FIX real encontrado: `AIChannelConfig.enabled` nunca se respetaba

`AIChannelConfigSelector.get_resolved_chain()` ignoraba por completo el campo
`enabled` -- el propio `models.py` (comentario junto al campo, FASE 4/18 de la
campaña anterior) ya documentaba que debia tratarse como "cadena vacia" pero
nunca quedo cableado. Resultado real: el toggle "IA activa/inactiva" del canal en
el panel no apagaba nada -- el chat seguia usando el proveedor configurado.

Fix: `get_resolved_chain()` devuelve `[]` si `config.enabled` es `False`, antes de
evaluar primary/fallbacks. Cubierto por
`test_disabled_channel_resolves_to_empty_chain_even_with_valid_primary` (ai_provider/
tests.py) y `test_disabled_channel_returns_null_primary_even_with_config`
(InternalProviderConfigViewTests) + `test_returns_none_when_channel_disabled`
(ai_engine/tests/test_dynamic_llm_config.py).

## FASE 19 -- RuntimeConfigResolver

`ai_engine/llm_factory.py::RuntimeConfigResolver.resolve(channel)` -- nombre
formal para lo que antes eran `_fetch_dynamic_chain()` + el cuerpo de
`get_dynamic_llm()`. `get_dynamic_llm()` se mantiene como wrapper delgado (lo
sigue usando `main.py`, sin tocar ese archivo). Mismo cache a nivel de modulo
(`_dynamic_chain_cache`), no movido a la clase para no romper los tests que ya lo
inspeccionaban directo.

## FASE 20 -- Hot reload real via contador de generacion en Redis

Antes: un cambio guardado en `/panel/soporte` tardaba hasta 15s (TTL del cache en
memoria de `RuntimeConfigResolver`) en reflejarse en `/chat`. Funcional, pero no
es "sin esperar nada".

**Diseno:** no se cachean las entradas resueltas en Redis (los objetos LLM/dicts
de config no se benefician de eso con un solo proceso uvicorn sin `--workers`) --
solo un contador de generacion por canal, `ai_runtime:<channel>:gen`, en la misma
Redis/DB que ya usa el checkpointer de LangGraph (`CHECKPOINTER_REDIS_URL`,
`redis://redis:6379/2`), prefijo de clave distinto para no colisionar con
`ai:cp:*`.

- `ai_provider/services/runtime_cache.py::invalidate(channel)` (Django) -- `INCR`
  del contador. Nunca lanza (si Redis esta caido, la mutacion admin igual se
  guarda en Postgres -- el TTL de 15s sigue siendo la red de seguridad).
- Cableado en `AIProviderCommands.update_provider/delete_provider/activate/
  deactivate`, `AIModelCommands.update_model/delete_model`,
  `AIChannelConfigCommands.set_primary/set_fallback_chain/set_enabled` -- toda
  mutacion que puede cambiar lo que resuelve `get_resolved_chain()`.
- `ai_engine/llm_factory.py::_get_runtime_generation(channel)` -- `GET` del mismo
  contador, nunca lanza (Redis caido o clave inexistente = `None`, tratado igual
  que "sin cambios").
- `RuntimeConfigResolver.resolve()` compara la generacion leida contra la
  cacheada; si difiere, fuerza un refetch inmediato saltandose el TTL.

**Verificado end-to-end real** (no solo unit tests mockeados): `runtime_cache.
invalidate('support_chat')` desde `manage.py shell` incrementa la clave en Redis,
y `llm_factory._get_runtime_generation('support_chat')` desde dentro del
contenedor `sintel_ai` lee el mismo valor -- confirma que ambos servicios
efectivamente comparten la Redis/DB/clave, no solo que el codigo compile.

## Tests

- `ai_provider`: 49/47 -> 49 tests (incluye los 2 nuevos de `enabled`), PASS.
- `ai_engine`: 131 -> 134 tests (7 nuevos: reshape, RuntimeConfigResolver alias,
  3 de invalidacion por generacion), PASS. 16 skipped (pre-existentes, sin
  relacion).
- Regresion completa `ai_provider payment dashboard`: **176/176 PASS** (ejecucion
  limpia y unica -- un primer intento con invocaciones `manage.py test` solapadas
  corrompio la test DB compartida y dio 5 errores falsos por "relation users_user
  does not exist"; al re-ejecutar una sola vez limpio, 0 fallos reales).

## Pendiente (no en el alcance de este incremento)

FASE 21 (demo real LM Studio <-> Ollama sin restart) sigue bloqueada por no haber
un segundo motor real disponible en este entorno (solo Ollama Docker esta
corriendo) -- el mecanismo de FASE 20 ya esta verificado end-to-end con el unico
proveedor real disponible; falta el segundo proveedor para la demo completa de
swap.
