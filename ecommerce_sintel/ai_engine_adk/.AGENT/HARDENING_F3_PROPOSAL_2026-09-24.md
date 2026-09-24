# HARDENING — FASE 3 (rate limit + control de costo + circuit breaker / fallback)

**Estado: C1 y C2 APROBADOS (2026-09-24), IMPLEMENTADOS Y VERIFICADOS EN DEV; PRODUCCION SIN DESPLEGAR.** C3/C4 sin iniciar. Ver "Resultado en DEV" al final.

Plan: `PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md` §7. Nada implementado. Toca el proveedor de modelo
(fallback) y limites de servicio => aprobacion humana (§0.3, LOOP-08).

## Evidencia real (corrige el baseline F0)
- **Ya existe** un limite diario por usuario: `ai_engine/cost_control.py::check_and_increment_daily_turns`, 200 turnos/usuario/dia, Redis DB 2,
  fail-open, invocado en `sintel_root_workflow.py:372` (responde `rate_limited`). El baseline F0 decia "sin limite por usuario": incompleto.
- Django: 20 turnos IA por sala cada 10 min (`AI_CHAT_RATE_LIMIT`). Por Tool: `rate_limit.py` (Redis, fail-open).
- Presupuesto de turno hoy: `MAX_TOOL_CALLS_PER_TURN = 6` (`sintel_adapter.py`), timeout 90 s **por llamada** LLM
  (`_LLM_TIMEOUT_SECONDS`), corte total de 300 s solo en Django (`AI_CHAT_TIMEOUT_SECONDS`), mensaje <= 4000 chars.
- **Sin usar**: `google.adk.agents.run_config.RunConfig.max_llm_calls` existe en el ADK instalado pero `sintel_root_workflow.py` no lo configura.
- **Sin limite**: tokens de salida por agente (`max_output_tokens`), tiempo total del turno en el ADK, contexto maximo, y limites por IP/sesion/canal.
- **Fallback**: `_resolve_primary_llm_params()` solo usa `entries[0]` de `LOCAL_MODEL_CHAIN`; la 2da entrada (LM Studio) no se usa nunca.
  Con LM Studio caido, el fallback real seria "nada" => hoy un fallo de Ollama termina en la respuesta degradada de `main.py`
  ("asistente no disponible") + `engine_unavailable`, sin reintentos ni estado compartido entre turnos.
- `LiteLlm` (ADK) expone `generate_content_async`, por lo que se puede envolver/subclasificar sin tocar ADK.

## Cambios propuestos

### C1 — Presupuesto de turno (riesgo bajo, solo `ai_engine_adk`)
Variables (`ai_engine/config.py`, con defaults conservadores y calibrables tras F13):
`AI_TURN_MAX_SECONDS=120`, `AI_TURN_MAX_LLM_CALLS=6`, `AI_SUPPORT_MAX_OUTPUT_TOKENS=512`, `AI_ADMIN_MAX_OUTPUT_TOKENS=1024`.
- `RunConfig(max_llm_calls=AI_TURN_MAX_LLM_CALLS)` al ejecutar el Runner.
- `asyncio.wait_for(run_sintel_turn(...), AI_TURN_MAX_SECONDS)` en `main.py::chat`; al vencer => respuesta segura de handoff
  (mismo `engine_unavailable`), sin dejar herramientas a medias (las de escritura ya son idempotentes por confirmacion).
- Limite de salida por agente via `max_tokens`/`num_predict` en la llamada litellm (Ollama: `num_predict`).
Nota: con Qwen3.5 y razonamiento activo el turno tarda 9-22 s; 120 s deja margen 5x y evita turnos colgados de 300 s.

### C2 — Fallback multi-entry + circuit breaker por proveedor (riesgo medio, requiere rebuild de `sintel_ai_adk`)
Nuevo modulo `ai_engine_adk/model_runtime.py`:
- `ProviderBreaker` con estados CLOSED/OPEN/HALF_OPEN por entrada de `LOCAL_MODEL_CHAIN`, estado en Redis (compartido entre replicas y
  sobrevive reinicios), clave `ai:breaker:<nombre>`. Abre tras `AI_BREAKER_FAILURES=3` fallos en `AI_BREAKER_WINDOW_SECONDS=60`; permanece
  OPEN `AI_BREAKER_OPEN_SECONDS=60`; luego HALF_OPEN deja pasar 1 peticion de prueba.
- `FallbackLiteLlm(LiteLlm)` que sobreescribe `generate_content_async`: intenta la primera entrada con breaker no OPEN; ante timeout/5xx/conexion
  rechazada/salida malformada marca fallo y pasa a la siguiente UNA sola vez por turno (presupuesto de reintentos = 1, nunca reintenta ambas).
  Si no queda ninguna disponible => excepcion controlada => respuesta segura + handoff.
- Trazabilidad por turno (`metrics`): `provider`, `model`, `fallback_used`, `fallback_reason`, `breaker_state`; log `ai_operation_event=...`
  sin prompts ni respuestas completas.
- NO vuelve silenciosamente a LM Studio como primario: el orden Ollama -> LM Studio es fijo; el retorno al primario es solo por el HALF_OPEN.
Caveat honesto: LM Studio esta caido hoy => el fallback efectivo falla y cae en handoff; el breaker evita ademas martillar un Ollama caido.

### C3 — Limites por IP/sesion/canal (riesgo medio, decidir donde)
- Edge: `limit_req` en nginx para `/api/v1/support/*` y el WebSocket (no verificado si ya existe en `nginx.prod.conf`; lo reviso antes).
- Django: contador por usuario/IP ademas del de sala (Redis/cache), con burst + sostenido.
Se propone como PR aparte; C1/C2 no dependen de C3.

### C4 — Degradacion controlada (F3 §7.4)
Cliente: ya existe respuesta estatica + marcador; añadir handoff/ticket automatico cuando el breaker esta OPEN >N minutos.
Admin: error operacional explicito, sin ejecutar Tools parciales (verificar en test).

## Tests
Breaker (transiciones y ventanas, con Redis simulado), orden de fallback, presupuesto de reintentos (nunca doble), timeout de turno,
`max_llm_calls`, respuesta segura si todo cae, trazabilidad sin PII, admin no ejecuta Tool tras fallo. Suite de regresion = mismos 31 fallos
preexistentes (dependen del LLM de dev) + verificacion E2E en DEV contra el Ollama real y contra un Ollama detenido a proposito.

## Riesgos / rollback
- Un `AI_TURN_MAX_SECONDS` demasiado bajo cortaria respuestas legitimas de Qwen: calibrar con F13 (default 120 s).
- Breaker mal calibrado podria abrir por picos de latencia: contar solo errores, no latencia.
- Rollback: variables a valores altos/`AI_BREAKER_ENABLED=false` y volver a la imagen anterior de `sintel_ai_adk`.

## Preguntas para aprobar
1. ¿Apruebas C1 y C2 (dev primero, luego prod)? C3/C4 los separo.
2. ¿Valores iniciales: 120 s por turno, 6 llamadas LLM, 512/1024 tokens, breaker 3 fallos/60 s y 60 s abierto?
3. Como LM Studio esta caido: ¿lo dejamos como segunda entrada (fallback nominal) o pones otro fallback real (p. ej. `llama3.1:8b` en el mismo Ollama)?

## Resultado en DEV (2026-09-24)
Implementado: `ai_engine_adk/model_runtime.py` (ProviderBreaker CLOSED/OPEN/HALF_OPEN sobre Redis o memoria, `FallbackLiteLlm`, traza por turno),
variables en `ai_engine/config.py` (`AI_TURN_MAX_SECONDS=120`, `AI_TURN_MAX_LLM_CALLS=6`, `AI_SUPPORT_MAX_OUTPUT_TOKENS=1024`,
`AI_ADMIN_MAX_OUTPUT_TOKENS=2048`, `AI_BREAKER_*`), integracion en `sintel_root_workflow.py` (`RunConfig.max_llm_calls`,
`generate_content_config.max_output_tokens`, `metrics.model_trace`) y timeout total en `main.py` (respuesta segura con handoff).
Desviacion respecto a la propuesta: topes de salida 1024/2048 (no 512/1024) porque los tokens de razonamiento de Qwen3.5 cuentan en `num_predict`.
Tests: `ai_engine_adk/tests/test_model_runtime.py` (19) + F2 (9) en verde. Regresion: suite del ADK 31 fallos identicos a la linea base (preexistentes,
dependen del LLM de dev), 55 -> 83 aprobados (+28 nuevos).
E2E real en DEV (ADK de prueba con cadena Ollama(qwen3.5:9b)->LM Studio, breaker 3 fallos/60 s, abierto 20 s, turnos reales con JWT de un cliente de dev):
- A) Ollama arriba: respuesta real; `model_trace = {provider: ollama, model: qwen3.5:9b, fallback_used: false, breaker_state: CLOSED}`.
- B) Ollama de dev detenido: turnos 1-3 fallan en ambos proveedores (APIConnectionError; 42 s / 6.6 s / 6.6 s) y responden el mensaje seguro
  `engine_unavailable`; el breaker abre para ollama y lmstudio (`breaker_opened`); turnos 4-5 en 0.1 s (`provider_skipped state=OPEN`).
- C) Ollama de vuelta + 22 s: HALF_OPEN deja pasar la prueba, `breaker_closed provider=ollama`, respuestas normales otra vez.
Observaciones: (1) los turnos reales en dev tardaron 56-108 s (carga en frio + RAG con bge-m3 + 2+ llamadas al modelo en una GPU de 8 GB compartida):
`AI_TURN_MAX_SECONDS=120` queda muy justo => calibrar con la prueba de carga (F13) antes de produccion, o subirlo; (2) en el camino degradado
`metrics` no incluye `model_trace` (la excepcion sale antes); (3) el fallback a LM Studio no pudo probarse con exito porque LM Studio esta caido.
No verificado: comportamiento en produccion, `sintel_ai_adk` de dev en ejecucion sigue con la imagen anterior (la imagen `:latest` ya esta reconstruida).

## Pasos pendientes para PRODUCCION (no ejecutados)
1. Decidir `AI_TURN_MAX_SECONDS` con datos (F13). 2. Rebuild `--no-cache` de `sintel_ai_adk` y `up -d --no-deps` (las variables tienen defaults; no requieren `.env.production`).
3. Verificar en logs `ai_operation_event=` y `model_trace` en `metrics`. Rollback: `AI_BREAKER_ENABLED=false` (vuelve al LiteLlm primario) y/o imagen anterior.
