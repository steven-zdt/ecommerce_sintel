# FASE 4 -- AI Engine: loader dinamico

**Fecha:** 2026-08-13. Ver `FASE1_MODELOS.md`/`FASE2_INTERNAL_API.md`/
`FASE3_DASHBOARD_API.md`.

## Cambios

- `ai_engine/llm_factory.py`:
  - `_resolve_api_key(entry, default)`: entradas dinamicas usan `api_key_value`
    (ya descifrada por Django), entradas de `LOCAL_MODEL_CHAIN` siguen usando
    `api_key_env` (nombre de variable) -- `_build_model()` no se bifurca, ambos
    caminos convergen aqui.
  - `_fetch_dynamic_chain(channel)` (async, `httpx.AsyncClient`): consulta
    `GET /api/v1/internal/ai/provider-config/` (FASE 2). None ante cualquier fallo
    (HTTP != 200, red inalcanzable, JSON invalido) -- nunca lanza.
  - `get_dynamic_llm(channel)` (async): cache de 15s en memoria del proceso: cadena
    dinamica si existe, si no `LOCAL_MODEL_CHAIN` (bootstrap/fallback/emergencia,
    **sin cambios** -- regla explicita del plan maestro).
  - `get_llm()` (la funcion original, sincrona, usada UNA sola vez en el
    `lifespan` de `main.py` para `_STATE['llm']`) **no se toco** -- sigue
    alimentando `/generate` (AI Editor), fuera de alcance de este plan.
- `ai_engine/main.py`: `/chat` ahora llama `await get_dynamic_llm()` en vez de usar
  `_STATE['llm']` directo. El guard `if not _STATE.get('llm')` se mantiene como
  señal de que el proceso arranco bien (sigue siendo valido: si el arranque fallo,
  nada funciona; si arranco bien pero la config dinamica falla, `get_dynamic_llm()`
  cae sola a `LOCAL_MODEL_CHAIN`).

## Hallazgo operativo real (bloqueante hasta resolverlo)

`sintel_ai` **no tiene bind-mount de codigo** (`docker-compose.yml`: solo
`.:/workspace:ro`, de solo lectura, para indexar la base de conocimiento -- no es
`/app`). El codigo real vive horneado en la imagen desde `build: context: ./ai_engine`
-- `uvicorn --reload` observa `/app` DENTRO del contenedor, que nunca cambia, asi que
edits en el host nunca se reflejan sin un rebuild real. Diferente de `django`/
`frontend`, que si tienen bind-mount + reload real. **Para cualquier cambio de codigo
futuro en `ai_engine`, el flujo real es:** `docker compose build sintel_ai &&
docker compose up -d sintel_ai` (no un simple restart). Confirmado con evidencia: el
primer intento de probar esta fase con solo `docker restart` no reflejo los cambios
(`grep get_dynamic_llm /app/main.py` vacio dentro del contenedor); tras el rebuild
real, el mismo grep encontro el codigo nuevo.

## Tests

`ai_engine/tests/test_dynamic_llm_config.py` (nuevo, `httpx.AsyncClient.get`
mockeado -- no hay `respx` instalado en este entorno): **12/12 PASS** -- parseo de la
forma real de respuesta, cadena vacia/HTTP≠200/error de red -> `None`, api_key
dinamica preservada, fallback a `LOCAL_MODEL_CHAIN` cuando no hay config real, cache
de 15s (no reconsulta dentro de la ventana, si reconsulta despues). Suite completa de
`ai_engine`: **127 passed, 16 skipped** (skips preexistentes, no relacionados) -- 0
regresiones.

## Validacion en vivo (end-to-end real, ambos caminos)

1. Con el provider "Ollama Docker (real)" activo (creado en FASE 2) como primario de
   `support_chat`: llamada real a `ask_ai()` -> logs de `sintel_ai` confirman
   `GET .../provider-config/... 200 OK` -> `[llm] motor 'Ollama Docker (real)'
   (ollama-nativo): llama3.1:8b @ http://sintel_ollama:11434` ->
   `[llm] /chat usando config dinamica (ai_provider) (1 motores)` -> respuesta real
   coherente.
2. Con el mismo provider `is_active=False` (esperando el TTL de 15s del cache):
   misma llamada -> `[llm] /chat usando config LOCAL_MODEL_CHAIN (bootstrap/fallback)
   (1 motores)` -> respuesta real igual de coherente, sin interrupcion. Provider
   reactivado despues.

## Siguiente fase

FASE 5 -- Frontend: panel de configuracion en `/panel/soporte`. Consumira
`/api/v1/dashboard/ai-providers/` y `/api/v1/dashboard/ai-channel-config/` (FASE 3).
Cambios guardados desde el panel llegan a `/chat` dentro de la ventana de cache de
15s de `get_dynamic_llm()` -- sin reiniciar `sintel_ai`, cumpliendo el requisito
explicito del plan maestro.
