# HARDENING — FASE 13 (concurrencia y load test): DISENO + HERRAMIENTAS (estado: LISTO PARA QUE EL USUARIO MIDA)

Plan: `PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md` §17 (prioridad P0/P1: con Ollama como primario es un gate de produccion). Regla firme del usuario: **el asistente NO ejecuta tests ni benchmarks** (ni "solo nivel 1"): esta fase entrega el diseno, el script de carga y el control de admision; **las mediciones las corres tu**. Nada de lo de abajo se ejecuto (solo `py_compile` + ASCII + inspeccion).

## Estado real (inspeccion read-only, 2026-09-24)
| Componente | Hallazgo |
|---|---|
| ADK | `uvicorn main:app` **un solo worker** asyncio; acepta turnos **sin limite**. Cada turno = 1-6 llamadas al modelo (F9: ~6 llamadas, 111 s en un turno de RentalAgent con 5 tools) |
| Modelo | Una **RTX 4060 de 8 GB** compartida por Ollama dev, Ollama prod y LM Studio. `qwen3.5:9b` reparte 20 % CPU / 80 % GPU. Sin `OLLAMA_NUM_PARALLEL` explicito (Ollama decide) => en la practica **~1 turno cada 60-110 s por GPU** |
| Modelo de capacidad (ordenes de magnitud, a confirmar midiendo) | ~1 turno en curso a la vez => 60-100 turnos/hora. Con N usuarios simultaneos el ultimo espera ~N x 60-110 s. Ya con **N >= 2** el turno cercano al limite de `AI_TURN_MAX_SECONDS` (120 s) empieza a vencer |
| Cascada bajo carga (riesgo P0) | Los turnos que esperan en la cola de Ollama agotan el timeout de 90 s por llamada -> el circuit breaker (F3) cuenta **espera** como **fallo del proveedor** -> salta a LM Studio (la MISMA GPU) y abre el breaker de Ollama: sobrecarga confundida con caida |
| Django/WS | Daphne un proceso; `ask_ai_async` (httpx) no bloquea el pool (arreglado el 2026-08-17); limites: 20 turnos/10 min por sala, 200 turnos/dia por usuario (fail-open) |
| Celery | `--concurrency=4`; **`ask_ai` (WhatsApp) es `requests.post` SINCRONO de hasta 300 s dentro de una tarea**: 4 turnos de WhatsApp simultaneos ocupan los 4 workers minutos y bloquean tambien las colas `marketing` y `notifications` (hallazgo, no corregido: requiere cola/worker dedicado en el despliegue) |
| Redis / DB | Redis unico con `requirepass`; ADK con `ADK_SESSION_BACKEND=database` en prod (pool por defecto de SQLAlchemy). Sin datos de contencion |
| Metricas disponibles | F9: `ai_turn_metrics` (latencia, tokens, `tokens_per_s`, `turn_timeout`, `engine_unavailable`). **TTFT no existe** (sin streaming) |

## Cambios entregados (dev; defaults inocuos)
### C1 — Script de carga (`scripts/load/adk_load_test.py`, NO ejecutado)
Escenarios `--scenarios 1,5,10,20,50` (plan §17.1), mezcla 70/15/10/5 soporte/RAG/tools/borde (§17.2, con casos borde: entrada de 3 900 chars, inyeccion, emoji), N workers por escenario con varios JWT de usuarios de **prueba** de dev (el limite diario por usuario es 200), muestreo cada 5 s de GPU/VRAM (`--gpu`), reparto CPU/GPU de Ollama (`--ollama`), clientes de Redis (`--redis-container`) y conexiones de Postgres (`--db-container`). Reporta por escenario: turnos/min, tasa de exito, degradados, timeouts, rechazos de cola, latencia p50/p95/p99, tokens/s, espera en cola y picos de recursos. **Se niega a apuntar a produccion.** No cubre sesiones WebSocket (necesita un cliente WS; hoy la carga entra por `/chat` del ADK, que es donde esta el cuello).
### C2 — Control de admision (`ai_engine_adk/admission.py` + `main.py`)
`AI_MAX_CONCURRENT_TURNS` (**0 = desactivado = comportamiento actual**), `AI_QUEUE_MAX_DEPTH=20`, `AI_QUEUE_MAX_WAIT_SECONDS=30`. Con un valor > 0: solo N turnos a la vez; los demas esperan en una cola acotada y, si la cola esta llena o la espera vence, reciben **respuesta degradada inmediata con handoff** (`metrics.queue_rejected`, `queue_reason`, `ai_operation_event=turn_rejected`, `status=degraded` en `ai_turn_metrics`) SIN llegar al modelo ni tocar el breaker (rompe la cascada). La espera en cola se reporta en `metrics.queue_wait_ms` (fuera de `AI_TURN_MAX_SECONDS`). Un solo proceso: con varios workers de uvicorn el tope se multiplica. Valor sugerido tras medir: igual a la concurrencia con la que la latencia p95 sigue dentro del SLO (probablemente 1-2 en esta GPU).
Tests escritos, NO ejecutados: `ai_engine_adk/tests/test_admission.py`.

## Como medir (lo haces tu, en DEV)
1. Cierra LM Studio y cualquier otra carga de la GPU; deja el ADK de dev con `AI_MAX_CONCURRENT_TURNS=0` (baseline sin control).
2. Crea 5-10 usuarios de prueba de dev y guarda sus JWT (exp largo) en `jwts.txt`.
3. `python scripts/load/adk_load_test.py --base-url http://localhost:8101 --jwt-file jwts.txt --scenarios 1,5,10 --turns-per-worker 2 --gpu --ollama http://localhost:11434 --redis-container ecommerce_sintel_redis --db-container ecommerce_sintel_db --out scripts/load/_out/baseline.json`
4. Repite con `AI_MAX_CONCURRENT_TURNS=1` (y luego 2) para 10/20/50 y compara: exito, rechazos, p95, ausencia de saltos a LM Studio (`ai_operation_event=provider_failed` / `breaker_opened` en los logs del ADK).
5. Con esos numeros se fijan `AI_MAX_CONCURRENT_TURNS`, los SLO de F24 y (F12) `num_ctx`/`OLLAMA_NUM_PARALLEL`.
Para aplicar el control tras reconstruir la imagen (`docker compose up -d --build sintel_ai_adk`): variable en `.env` **y** `.env.production` en el mismo cambio (incidente del 503).

## Pendiente / recomendaciones (no implementado)
- **Celery**: mover `ask_ai` de WhatsApp a una cola/worker dedicado (`-Q ai --concurrency=1-2`) o a `httpx` async para que un turno lento no paralice `marketing`/`notifications` (cambio de despliegue; propuesta aparte).
- **OLLAMA_NUM_PARALLEL / OLLAMA_MAX_QUEUE**: decidir con la medicion (cada slot paralelo multiplica el KV cache en una GPU de 8 GB); F12 mide `num_ctx`.
- **Breaker vs cola**: con la admision activa, las llamadas al modelo dejan de esperar en cola, por lo que los timeouts vuelven a significar "proveedor lento/caido".
- **WebSocket**: prueba de sesiones WS concurrentes con cliente dedicado (fuera de este script).
- La GPU es UNA: cualquier objetivo de concurrencia > 2 turnos simultaneos probablemente exige mas hardware o un modelo/servicio distinto; la medicion lo confirmara con datos.
