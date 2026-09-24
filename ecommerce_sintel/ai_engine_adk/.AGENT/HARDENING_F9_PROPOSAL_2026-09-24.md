# HARDENING — FASE 9 (observabilidad completa): PROPUESTA (estado: IMPLEMENTADA EN DEV, prod pendiente)

Plan: `PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md` §13. Nada implementado. Toca nginx de produccion, middleware de Django y el formato de logs
=> `SECURITY_REVIEW_REQUIRED` + aprobacion humana (§0.3). Regla vigente: los tests se ESCRIBEN pero NO se ejecutan sin autorizacion; verificacion por inspeccion y pruebas de humo.

## Estado real (inspeccion de codigo, 2026-09-24)
| Requisito del plan (§13) | Estado |
|---|---|
| Correlation ID `trace_id/request_id/session_id` a traves de nginx -> Django -> ai_bridge -> ADK -> agent -> RAG -> Tool -> modelo | **Roto en el origen**: nginx solo agrega `X-Real-IP/X-Forwarded-*` (no `X-Request-ID`); Django no tiene middleware de request id; `ai_bridge` no envia ninguna cabecera de traza; el ADK genera su propio `request_id` (`req-...`) DENTRO de `run_sintel_turn`. Un turno se puede seguir hoy solo por `conversation_id` / `room uuid` |
| Log separado por dominio (SECURITY / AI_OPERATION / PERFORMANCE / BUSINESS) | **Parcial**: ya hay eventos `key=value` con prefijos distintos (`security_event=`, `ai_operation_event=`, `ai_tool_audit`, `memory_event=`, `marketing_event=`) pero en texto plano mezclado en un solo stream de contenedor; sin campo `stream`, sin JSON |
| Metricas de rendimiento por turno | **Solo en BD**: `metrics` del ADK se persiste en `ChatMessage.ai_metrics` (web) y lo agrega `ChatAnalyticsSelector.get_summary(days)` (`support/services/selectors.py`). El ADK **no emite una linea de metricas por turno** (el sistema antiguo si: `ai_engine/observability.py`, JSON) |
| Tokens / costo | **No se miden** (comentario en `sintel_root_workflow.py`). Hallazgo: `LlmResponse.usage_metadata` existe en el ADK instalado -> se puede sumar en `FallbackLiteLlm` (F3), que ya envuelve cada llamada al modelo |
| TTFT | **No medible** hoy: `/chat` no hace streaming (un POST con respuesta completa). Solo latencia total y por etapa |
| Metricas de seguridad (rate-limit hits, injection detections, tool denials, memory rejections, output redactions, 401/403) | Existen como LINEAS de log (F2-F8) pero **no se cuentan ni se agregan en ningun sitio** |
| Prometheus / OpenTelemetry | No instalado (decision previa de costo del roadmap de Cloudflare, `observability.py`); solo aparecen como dependencias transitivas de google-adk |
| Privacidad de logs | Cada evento nuevo evita el contenido; **no hay una red de seguridad global** (un `httpx` o un error de terceros podria imprimir un JWT/URL con token) |

## Cambios propuestos (dev primero)

### C1 — Correlacion extremo a extremo (riesgo medio, toca nginx prod)
- nginx (`nginx-common.conf`/`nginx.prod.conf`): `map $http_x_request_id $req_id { default $http_x_request_id; '' $request_id; }` -> `proxy_set_header X-Request-ID $req_id;` y `add_header X-Request-ID $req_id always;`.
  (Solo se acepta el id entrante si tiene forma valida en Django; si no, se regenera.)
- Django: `RequestIDMiddleware` (valida `^[A-Za-z0-9-]{8,64}$`, si no genera uuid4), guarda en un `ContextVar`, cabecera de respuesta, y un `logging.Filter` que agrega `request_id` a TODOS los registros.
  WebSocket (`support/consumers.py`): un `request_id` por mensaje del cliente, incluido en cada linea `[CHAT]`.
- `ai_bridge` (`ask_ai`, `ask_ai_async`) y el Admin AI Assistant envian `X-Request-ID` y `X-Session-Id` (= `conversation_id`) al ADK.
- ADK: `main.py` lee la cabecera (validada), la guarda en un `ContextVar` y `run_sintel_turn` usa ese valor como `request_id` (en vez de generar otro); un `logging.Filter` lo agrega a cada linea (F3-F8 incluidas). Fallback: si no hay cabecera, se genera como hoy.
- Celery (WhatsApp/notificaciones): propagar `request_id` como argumento de la tarea al reintentar `ask_ai` (si aplica).

### C2 — Taxonomia de logs y formato JSON opt-in (riesgo bajo)
`LOG_FORMAT=json|text` (default `text`: nada cambia para quien hace `grep` hoy). En modo `json`: una linea por evento con `ts, level, logger, stream, request_id, session_id, message` y los pares `key=value` del mensaje parseados a campos.
`stream` se deriva del prefijo: `SECURITY` (`security_event=`), `AI_OPERATION` (`ai_operation_event=`, `ai_tool_audit`, `memory_event=`), `PERFORMANCE` (`ai_turn_metrics`), `BUSINESS` (`marketing_event=`), resto `APP`. Implementacion stdlib (sin dependencia nueva) en un modulo compartido usado por ADK y Django.

### C3 — Metricas por turno y tokens (riesgo bajo/medio)
- El ADK emite UNA linea `ai_turn_metrics {...json...}` por turno (stream PERFORMANCE): `request_id, session_id, agent, intent, source, channel, status (ok|degraded|timeout|rate_limited), duration_ms, retrieval_latency_ms, agent_latency_ms, grounding_latency_ms, llm_calls, tool_calls, provider, model, fallback_used, breaker_state, prompt_tokens, completion_tokens, tokens_per_s, injection_flags, output_flags, memory_used` (sin contenido).
- Tokens: `FallbackLiteLlm` suma `usage_metadata` de cada `LlmResponse` en la traza del turno (F3) -> `prompt_tokens/completion_tokens`; `tokens_per_s` = completion / tiempo del agente. TTFT queda **documentado como no disponible** hasta que exista streaming.
- Los mismos campos se guardan en `metrics` (ya viaja a `ChatMessage.ai_metrics`).

### C4 — Metricas de seguridad y de operacion agregadas (riesgo bajo)
Ampliar `ChatAnalyticsSelector.get_summary` (Django, sin infraestructura nueva) con: p50/p95/p99 de `duration_ms`, tasa de degradacion (`engine_unavailable`), tasa de fallback, tool calls por turno, tokens totales, conteo de `injection_flags`/`output_flags` por categoria y `rate_limited`. Comando `manage.py ai_observability_report --days 7` (texto/JSON). Es la fuente para las metricas de F0 §4.4 y los SLO de F24.
Los contadores de seguridad que hoy solo son lineas de log (rechazos de memoria, redacciones, bloqueos) se cuentan desde los propios `metrics` del turno; los de fuera del turno (401/403, rate limit por sala) quedan en logs con `stream=SECURITY`.

### C5 — Red de seguridad de privacidad en logs (riesgo bajo)
`logging.Filter` global (ADK y Django) que redacta en TODO mensaje: JWT (`eyJ...`), `Bearer ...`, y el valor exacto de secretos del entorno (misma lista que `output_guard`). Sin costo apreciable; un secreto en un log es incidente (§19).

### C6 — Decisiones que quedan fuera
Prometheus/Grafana/OpenTelemetry: **mantener diferido** (decision previa de costo); el formato JSON deja el camino listo (un exporter sobre el logger). Persistir eventos de seguridad de nivel alto en `security.SecurityEvent` (append-only): opcional, lo dejo a tu decision.

## Tests (SE ESCRIBEN, NO SE EJECUTAN sin autorizacion)
Middleware (id valido reutilizado / invalido regenerado / cabecera de respuesta), filtro agrega `request_id`, `ai_bridge` envia las cabeceras, ADK usa la cabecera como `request_id`, formateador JSON (stream y pares `key=value`), redaccion de JWT/Bearer/secreto en logs,
`ai_turn_metrics` sin contenido y con tokens sumados, `get_summary` percentiles, comando de reporte. Verificacion manual: una peticion del widget seguida por su `request_id` en los logs de Django y del ADK.

## Riesgos / rollback
nginx de produccion: un `map` mal escrito rompe el proxy -> validar con `nginx -t` en DEV antes (el nginx de dev existe) y recrear solo `nginx` en prod. El filtro de logs y el middleware son aditivos (rollback: quitar de `MIDDLEWARE`/`LOGGING`); `LOG_FORMAT=text` es el default.

## Preguntas para aprobar
1. ¿Apruebas C1-C5 (dev primero), incluido el cambio de nginx (validado con `nginx -t` en dev)?
2. `LOG_FORMAT`: ¿JSON solo opt-in (default texto, como propongo) o JSON por defecto?
3. ¿Aceptas que TTFT quede documentado como "no disponible" hasta tener streaming?
4. ¿Persistimos en `SecurityEvent` los eventos de nivel alto (bloqueo por fuga, autoridad en memoria)? (recomiendo no en esta fase)
5. Prometheus/OpenTelemetry: ¿seguimos diferidos?

## Resultado en DEV (2026-09-24) -- aprobado "si a todo" (C1-C5, JSON opt-in, TTFT no disponible, SecurityEvent si, Prometheus/OTel diferidos)
| Cambio | Implementacion | Verificacion |
|---|---|---|
| C1 correlacion | nginx: `map $http_x_request_id $sintel_request_id` (`nginx-upgrade-map.conf`) + `proxy_set_header X-Request-ID` (`nginx.conf`, `nginx-common.conf`). Django: `ecommerce/request_id.py` (`RequestIDMiddleware`, primero en `MIDDLEWARE`, valida forma, cabecera de respuesta), un id `ws-...` por mensaje WS (`support/consumers.py`). `ai_bridge.build_ai_headers(token, conversation_id)` envia `X-Request-ID` + `X-Session-Id` (ask_ai, ask_ai_async, Admin AI Assistant). ADK: `main.py` lee la cabecera y `run_sintel_turn` la usa como `request_id` | `nginx -t` OK en dev + reload; via nginx (`:8080`): id valido se respeta, sin cabecera se genera (32 hex); Django directo: id invalido -> `req-<uuid>`. Turno real Django->ADK: el mismo `rid=smokef9-corr-0001` aparece en las lineas de Django, `ai_tool_audit`, `security_event`, `public_response`, httpx y `ai_turn_metrics` del ADK |
| C2 taxonomia + JSON | `ai_engine_adk/observability_logging.py` (stdlib, compartido ADK+Django): `stream_for`, `JsonFormatter`, `ContextFilter`; `LOG_FORMAT=json` opt-in (default texto, agrega ` rid=...` al final) | inspeccion + test escrito |
| C3 metricas por turno | una linea `ai_turn_metrics {json}` por turno (`ok/degraded/timeout`), sin contenido. Tokens sumados de `usage_metadata` en `FallbackLiteLlm` (contexto aparte, la traza de F3 conserva su forma): `llm_calls`, `llm_tokens_in/out`, `tokens_per_s` (tambien en `metrics` -> `ChatMessage.ai_metrics`) | turno real: 6 llamadas LLM, 13360 tokens de entrada / 1337 de salida, 12.1 tok/s, provider ollama, `fallback_used=false`. **TTFT: no disponible** (sin streaming) |
| C4 agregados | `ChatAnalyticsSelector.summarize_observability` (p50/p95/p99, degraded_rate, provider_fallback_rate, provider_breakdown, tokens, tool calls/turno, rate_limited, conteo de `injection_flags`/`output_flags`) mezclado en `get_summary` (claves nuevas, aditivas); `manage.py ai_observability_report --days N [--json]` | el comando corre en dev contra datos reales (2 turnos historicos; tokens 0 porque son previos a F9) |
| C5 privacidad de logs | `RedactionFilter` (JWT, `Bearer`, valor exacto de secretos del entorno) en el handler de consola de Django y en el root logger del ADK | test escrito; sin secretos en las lineas revisadas |
| Persistencia | `SecurityEvent.AI_SECURITY_FLAG` (+ migracion `security.0010`, aplicada en dev) via `ai_bridge.record_ai_security_events` (sync en ask_ai, `database_sync_to_async` en ask_ai_async): solo turnos con `blocked_*`/`secret_*` en `output_flags` o `injection_flags`; metadata = flags + request_id + conversation_id + agente, nunca contenido | inspeccion + test escrito (no ejecutado) |

Limites conocidos: (a) los rechazos de memoria por autoridad (`memory_event=`) quedan solo como log `AI_OPERATION` (ocurren en background, fuera de las metricas del turno); (b) los 401/403 del servicio y el rate limit por sala quedan en logs; (c) `fallback_rate` historico de `get_summary` sigue midiendo el fallback de INTENCION del runtime viejo; el fallback de proveedor es la clave nueva `provider_fallback_rate`.
Tests escritos y NO ejecutados: `ai_engine_adk/tests/test_observability_logging.py`, `support/test_observability_f9.py`; se corrigio la expectativa de `support/test_ai_service_token.py` (ahora incluye `X-Request-ID`).
Pendiente para produccion (no aplicado): rebuild de `sintel_ai_adk` y `django`, `migrate security`, recrear `nginx` (la config se valido con `nginx -t` en dev; `nginx-common.conf` es el mismo bloque + el mismo `map` ya validado). Variable opcional `LOG_FORMAT=json` (default texto) -- si se activa, replicar en `.env` y `.env.production`.

Prueba de humo del widget web (2026-09-24, UI real con Playwright): un mensaje del cliente por WebSocket genero `rid=ws-<32 hex>` en las lineas `[CHAT]` y `[AI_BRIDGE]` de Django y el MISMO id en 7 lineas del ADK, incluida `ai_turn_metrics` (`channel=web`, 2601 tokens de entrada / 842 de salida, provider ollama, 68 s). La correlacion WS -> ai_bridge -> ADK queda verificada de extremo a extremo.
