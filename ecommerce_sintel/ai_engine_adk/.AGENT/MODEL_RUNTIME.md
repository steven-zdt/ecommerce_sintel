# MODEL_RUNTIME — runtime del modelo (Ollama + Qwen3.5-9B primario, LM Studio respaldo)

> Documento vivo (HARDENING F19, 2026-09-24). Fuente de verdad de código: `ai_engine_adk/model_runtime.py`, `sintel_root_workflow.py`, `ai_engine/config.py`.

## 1. Cadena de modelos
`LOCAL_MODEL_CHAIN` = entradas `nombre|tipo|base_url|modelo` separadas por `;`. Decisión fija: **PRIMARIO = Ollama `qwen3.5:9b`** (`ollama-nativo`, `http://sintel_ollama:11434`), **RESPALDO = LM Studio `qwen/qwen3.5-9b`** (`openai-compatible`, `host.docker.internal:1234/v1`). Embeddings RAG: `bge-m3` vía Ollama.

## 2. Fallback y circuit breaker (F3)
`FallbackLiteLlm` recorre la cadena; **máximo 2 intentos por llamada** (primario + 1 respaldo); nunca cambia de proveedor a mitad de una respuesta ya emitida. `ProviderBreaker` (Redis, fail-open): CLOSED -> OPEN tras `AI_BREAKER_FAILURES=3` fallos en `AI_BREAKER_WINDOW_SECONDS=60`; OPEN `AI_BREAKER_OPEN_SECONDS=60`; luego HALF_OPEN deja pasar UNA prueba. Los errores del *request* (4xx) no cuentan. Todo falla -> `ModelUnavailableError` -> respuesta degradada con handoff. Traza por turno (`model_trace`): proveedor, modelo, `fallback_used`, motivo, estado del breaker, intentos.

## 3. Presupuestos
| Límite | Valor por defecto | Variable |
|---|---|---|
| Tiempo total del turno | 120 s | `AI_TURN_MAX_SECONDS` |
| Llamadas al modelo por turno | 6 | `AI_TURN_MAX_LLM_CALLS` |
| Tool calls por turno | 6 | `MAX_TOOL_CALLS_PER_TURN` (`sintel_adapter.py`) |
| Tokens de salida (incluye razonamiento) | 1024 cliente / 2048 admin; por agente opcional | `AI_SUPPORT_MAX_OUTPUT_TOKENS`, `AI_ADMIN_MAX_OUTPUT_TOKENS`, `AI_AGENT_MAX_OUTPUT_TOKENS` (`RentalAgent=1536,...`) |
| Historial | 12 turnos / 48 000 caracteres | `AI_MAX_HISTORY_TURNS`, `AI_MAX_CONTEXT_CHARS` |
| Resultado de tool al modelo | 8 000 caracteres (monitor) | `AI_TOOL_MAX_RESULT_CHARS`, `AI_TOOL_RESULT_ENFORCE` |
| Concurrencia de turnos | sin límite (apagado) | `AI_MAX_CONCURRENT_TURNS`, `AI_QUEUE_MAX_DEPTH=20`, `AI_QUEUE_MAX_WAIT_SECONDS=30` |

## 4. Hechos medidos del hardware/modelo (DEV, 2026-09-24)
- GPU única RTX 4060 8 GB compartida (Ollama dev, Ollama prod, LM Studio). `qwen3.5:9b` reparte **20 % CPU / 80 % GPU**, **contexto 4096** (default de Ollama; no se fija `num_ctx`), `keep_alive` 5 min.
- Turno real (RentalAgent, 6 llamadas): 13 360 tokens de entrada, 1 337 de salida, 12.1 tok/s, 111 s. Turnos típicos 56–110 s.
- Coste fijo de las tools por agente (~tokens): CatalogAgent ≈ 3 040 (75 % del contexto), AdminAgent ≈ 1 030, RentalAgent ≈ 750, MarketingAgent ≈ 610, SupportAgent ≈ 400.
- **Riesgo abierto (F12/C2)**: F5 permite ~12 000 tokens de historial contra 4096 de contexto; falta medir el margen real (`scripts/ai_eval/efficiency_baseline.py`, lo corre el usuario) antes de fijar `num_ctx` / `AI_MAX_CONTEXT_CHARS` / `OLLAMA_KEEP_ALIVE` (propuesto 30m, nunca -1).
- TTFT no existe: `/chat` no hace streaming (solo latencia total).

## 5. Razonamiento de Qwen
Los tokens `<think>` cuentan en `max_output_tokens`; `public_response.py` separa el razonamiento y `output_guard` lo elimina (incluido `<think>` sin cerrar). Desactivar el razonamiento por intención es un experimento pendiente (requiere el dataset de F10).

## 6. Métricas por turno (F9)
Una línea `ai_turn_metrics {json}` por turno (sin contenido): agente, intent, `status` (ok/degraded/timeout), `duration_ms`, `llm_calls`, `llm_tokens_in/out`, `tokens_per_s`, proveedor/modelo/fallback/breaker, `queue_wait_ms`, banderas. Agregado en Django: `manage.py ai_observability_report --days N`.

## 7. Versiones y supply chain (F16)
Ollama prod `0.30.10` (dev fijado igual); `google-adk==2.9.0`, `litellm==1.100.1`; `requirements.lock.txt` regenerado el 2026-09-24 desde la imagen de dev (**no conectado al Dockerfile**: decisión pendiente). Modelo por tag (`qwen3.5:9b`): registrar el **digest** de prod con `scripts/supply_chain/collect_versions.py` y verificar tras cada `ollama pull`. Un cambio de modelo, `num_ctx` o versión exige re-correr el benchmark F10 (`EVALUATION_BASELINE.md`).

## 8. Rollback del modelo
Antes de un `pull` que cambie el tag: `ollama cp qwen3.5:9b qwen3.5:9b-prev`; volver = `ollama cp qwen3.5:9b-prev qwen3.5:9b` (o cambiar el tag en `LOCAL_MODEL_CHAIN`). El resto (imagen, prompts, perfiles, tools) se revierte con `deploy/release_ai.sh rollback`.
