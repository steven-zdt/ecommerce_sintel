# HARDENING — FASE 14 (failover y resiliencia): DISENO + HERRAMIENTAS (estado: LISTO PARA QUE EL USUARIO SIMULE FALLOS)

Plan: `PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md` §18. Regla firme del usuario: **el asistente NO ejecuta tests ni simulaciones** (esta fase detiene contenedores: mucho menos aun). Se entrega analisis de codigo, un script de chaos SOLO para DEV y un cambio de codigo con default inocuo; **las simulaciones las corres tu**. Nada se ejecuto (solo `py_compile` + ASCII + inspeccion).

## Estado real por escenario del plan (inspeccion de codigo, 2026-09-24)
| Escenario §18 | Comportamiento hoy (leido en el codigo) | Veredicto |
|---|---|---|
| **Ollama down** | Breaker + fallback a LM Studio (F3, max 2 intentos); si ambos fallan -> `ModelUnavailableError` -> respuesta degradada con handoff (nunca 500 crudo, F3). Riesgo de cascada por sobrecarga: ver F13 | Cubierto; falta prueba real |
| **LM Studio down** | Solo se usa si el primario falla; con Ollama sano no se nota. Con ambos caidos: degradado + handoff | Cubierto |
| **Model unavailable** | Mismo camino (`ModelUnavailableError`); el turno vence a `AI_TURN_MAX_SECONDS` (120 s) como maximo | Cubierto |
| **Redis degradado** | Rate limit por tool, limite diario por usuario, breaker e idempotencia son **fail-open** (el chat sigue). Consecuencia: **sin Redis no hay limites ni deduplicacion** -> una escritura se puede duplicar si el usuario/reintento repite | **Gap** (idempotencia: cerrado con flag, ver C2; rate limits: recomendacion) |
| **Postgres degradado** | Sesiones del ADK (`DatabaseSessionService`) y Django (JWT/perfil) dependen de el: el turno falla -> `except` general de `/chat` -> degradado + handoff, sin fuga del error (respuesta fija) | Cubierto; falta prueba real |
| **RAG no disponible** | `retrieve_knowledge_for_chat` captura `httpx.HTTPError` y devuelve `[]` -> "sin evidencia" -> respuesta honesta ("no encontre informacion"), nunca inventa. **Pero es indistinguible de "no hay documento"** en metricas | Seguro; observabilidad pobre (recomendacion) |
| **Tool timeout** | `http_bridge` usa 8-10 s por llamada y devuelve un `dict` de error (no lanza al modelo), sin reintentos; el tope de 6 tool calls por turno y el turno de 120 s acotan todo | Cubierto (acotado, sin bucle infinito) |
| **WebSocket reconnect** | Depende del cliente (frontend) y de Channels; el historial se reenvia al conectar (`history`). El `request_id` es por mensaje (F9) | Solo verificable a mano (checklist abajo) |
| **ADK restart** | Sesiones persistentes en Postgres (`ADK_SESSION_BACKEND=database`); claves de idempotencia PENDING expiran a los 60 s (no bloquean reintentos). **Las confirmaciones pendientes viven en un dict EN MEMORIA (`_PENDING_CONFIRMATIONS` en `sintel_root_workflow.py`)**: un reinicio las pierde -> el "si, confirmo" posterior no encuentra nada (seguro: no se ejecuta, pero el usuario tiene que repetir la peticion); ademas no escala a varios workers | **Hallazgo** (no corregido: moverlo a Redis/BD es un cambio de diseno aparte) |
| Esperado: sin corrupcion / sin efectos duplicados / sin fuga / sin reintento infinito / handoff disponible | Sin corrupcion: escrituras via Django atomicas (la IA no toca la BD). Duplicados: idempotencia (fail-open sin Redis -> C2). Fuga: respuestas degradadas son texto fijo + guardia de salida F8 + redaccion de logs F9. Reintento infinito: no existe (2 intentos de modelo, 6 tools, 120 s; Celery `max_retries=3`). Handoff: mensaje fijo hacia agente humano | Cubierto salvo lo indicado |
| Recuperacion (§18.1) | Compose con `restart: unless-stopped` y healthchecks en la mayoria de servicios de prod. **ADK de dev sin healthcheck** (ya visto en F0) | Ver script |

## Cambios entregados (dev; defaults inocuos)
### C1 — Script de chaos SOLO dev (`scripts/resilience/chaos_dev.py`, NO ejecutado)
Escenarios `ollama_down`, `redis_down`, `postgres_down`, `django_down`, `adk_restart` (y `lmstudio_manual`, solo sonda). Para cada uno: detiene el/los contenedor(es) `ecommerce_sintel_*`, envia un turno real y comprueba **respuesta acotada en tiempo**, **degradacion segura (respuesta real o handoff)**, **sin fuga** (hosts internos, trazas, `.env`, JWT, URLs de BD/Redis en el cuerpo), **fail-closed de identidad** cuando Django cae y, tras reiniciar, **recuperacion** (y en `adk_restart`, que **la misma conversacion sigue respondiendo**). Reinicia siempre lo que detuvo (`finally`), se niega a tocar `sintel_prod_*` o URLs de produccion.
### C2 — Idempotencia fail-closed opcional (`AI_TOOL_IDEMPOTENCY_FAIL_CLOSED`, default `false`)
Con `true`, si Redis no responde una ESCRITURA no se ejecuta sin poder deduplicarla: el adapter devuelve `{"error": ..., "status_code": 503}` (audit `idempotency_unavailable`, log `ai_operation_event=idempotency_unavailable`) y el modelo deriva a un humano. Cierra el "no duplicate side effects" cuando Redis cae, a costa de que las escrituras (abrir ticket, crear solicitud...) fallen mientras Redis este caido. Default = comportamiento anterior; si lo activas, replicar en `.env` **y** `.env.production` en el mismo cambio. Archivos: `ai_engine/config.py`, `idempotency.py` (`UNAVAILABLE`), `sintel_adapter.py`.
Tests escritos, NO ejecutados: `ai_engine_adk/tests/test_idempotency_fail_closed.py` (fail-open por defecto, fail-closed, 503 en el adapter, finish/abort nunca lanzan, TTL de PENDING acotado, `/chat` degrada sin fuga, identidad falla cerrada 401).

## Como simularlo tu (DEV; avisa: para servicios compartidos unos minutos)
```
EVAL_JWT=<jwt de un usuario de PRUEBA> python scripts/resilience/chaos_dev.py --base-url http://localhost:8101 --out scripts/resilience/_out/chaos.json
# uno solo:  --only redis_down      |  LM Studio: cierralo a mano y --only lmstudio_manual
```
Manual (no automatizable aqui): (a) WebSocket: con el widget abierto, reiniciar `ecommerce_sintel_django` y comprobar que el cliente reconecta y recibe el `history`; (b) con `AI_TOOL_IDEMPOTENCY_FAIL_CLOSED=true` y Redis parado, pedir "abre un ticket": debe responder con handoff y NO crear ticket; (c) confirmaciones pendientes: pedir una accion que exige confirmacion, reiniciar el ADK y confirmar -> hoy pide repetir la peticion.

## Hallazgos / recomendaciones (no implementados)
1. **`_PENDING_CONFIRMATIONS` en memoria** (perdida en reinicio, no apta para varios workers): mover a Redis/BD con TTL — propuesta aparte (cambia el flujo human-in-the-loop).
2. **Rate limits fail-open sin Redis**: un limitador local de respaldo (en memoria, por proceso) evitaria quedar sin limites; hoy solo la admision (F13) y los topes por turno acotan.
3. **RAG caido vs sin evidencia**: registrar `ai_operation_event=rag_unavailable` distinto de "sin documentos" y exponerlo en `ai_turn_metrics` (una linea en `retrievers.py`).
4. **ADK de dev sin healthcheck**: agregarlo (como el de prod) para que "esperar a healthy" sea posible en la recuperacion.
5. **Celery/WhatsApp**: si el ADK esta caido, `ask_ai` devuelve `None`; confirmar en `notifications/tasks.py` que el mensaje de WhatsApp recibe respuesta de degradacion y no se reintenta sin fin (`max_retries=3` acota los reintentos de Celery, pero el camino del `None` no se reviso en esta fase).
