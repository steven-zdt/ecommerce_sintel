# HARDENING — FASE 17 (canary y promocion a produccion, P0): DISENO + HERRAMIENTAS (estado: LISTO; despliegue = TU)

Plan: `PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md` §21. Regla firme del usuario: **el asistente no ejecuta tests ni benchmarks, y nunca despliega/recrea contenedores de produccion** (regla del proyecto + clasificador). Se entrega codigo con defaults inocuos, un overlay de compose y scripts para que TU los ejecutes. Nada se ejecuto (solo `py_compile`, `bash -n` y ASCII).

## 1. Estado real (inspeccion)
| Requisito §21 | Hoy | Veredicto |
|---|---|---|
| Nunca `build -> production` | `deploy.sh` reconstruye (`--no-cache`) django/celery y sobrescribe el tag `:prod` **directamente sobre lo que sirve trafico**; `sintel_ai_adk` se reconstruye a mano. Sin etapa canary; STAGING = el stack de dev (no hay entorno aparte) | **Gap** |
| Canary: internos y luego una fraccion | No existe: `AI_ENGINE_URL` es UNA sola URL para todos | **Gap** -> C1 |
| Medir error, latencia, calidad, denegaciones de tools, eventos de seguridad, fallback | Existen las piezas (F9: `ai_turn_metrics`, `summarize_observability`, `SecurityEvent`), pero nada las compara entre dos versiones | **Gap** -> C2 |
| Rollback: imagen | El tag `:prod` se pisa en cada build: **no queda la imagen anterior**; volver = reconstruir desde git | **Gap** -> C3 |
| Rollback: modelo / prompt / perfil de agente / registro de tools / indice RAG / config | Prompt, perfiles (`agents/profiles/*.yaml`) y tools viajan **dentro de la imagen** (el rollback de imagen los cubre); modelo = tag de Ollama sin copia previa; RAG = versionado por documento (F6 `rollback_to_version`); config = `.env.production` sin historial | Parcial -> C3 |

## 2. Pipeline propuesto
`DEV` (desarrollo + humo manual) -> `STAGING` (stack de dev reconstruido con el MISMO arbol y las MISMAS banderas que prod) -> `CANARY` (ADK canary en prod, internos y luego 5 -> 25 -> 50 %) -> `PRODUCCION` (100 %, el canary pasa a ser el estable).
Gates: `promote_check.sh` (F10 gate, secretos, manifest de versiones, banderas sincronizadas) antes de entrar a CANARY; `ai_canary_report` para pasar de cada porcentaje; `release_ai.sh snapshot` antes de cada despliegue.

## 3. Entregado (dev; defaults inocuos, nada aplicado en produccion)
### C1 — Enrutamiento canary en Django (`support/services/engine_routing.py`, `ai_bridge.py`, `settings/base.py`)
`AI_CANARY_ENGINE_URL` (**vacia = apagado = comportamiento actual; es el KILL SWITCH**), `AI_CANARY_USER_EMAILS` (internos, siempre canary) y `AI_CANARY_PERCENT` (0-100, asignacion **determinista por usuario** con hash del id: nadie salta de version a mitad de conversacion y subir el porcentaje nunca saca a nadie del canary). `ask_ai`/`ask_ai_async` eligen el ADK, registran `track=stable|canary` en los logs y escriben `metrics.engine_track` (llega a `ChatMessage.ai_metrics` y a `SecurityEvent.metadata`). **Si el canary no acepta la conexion** (no se ejecuto nada) se atiende con el stable; un **timeout NO se reintenta** (el turno pudo ejecutarse: evita duplicar efectos). El Admin AI Assistant sigue siempre en stable.
### C2 — Comparacion canary vs stable (`manage.py ai_canary_report --hours 24`)
Por version: intentos, degradacion, p50/p95, fallback de proveedor, handoff, banderas de seguridad, tokens. **Veredicto sugerido** (no automatico): `HOLD` (< 30 turnos), `ROLLBACK` (degradacion +2 pp, p95 x1.3, banderas de seguridad +1 pp o mas fallback) o `PROCEED`; umbrales ajustables por parametro (los definitivos salen de F24 con el baseline en vivo).
### C3 — Rollback (`deploy/release_ai.sh`)
`snapshot` (antes de construir): etiqueta lo que corre como `:prev` y `:rel-<ts>`, guarda manifiesto (commit, ids de imagen) y las **banderas NO secretas** de `.env.production` (lista blanca, excluye TOKEN/SECRET/PASSWORD/KEY). `rollback adk|django|all`: muestra el plan, exige escribir `ROLLBACK`, re-etiqueta `:prev` -> `:prod` y recrea con `--no-build`. `list`. Cubre imagen + prompt + perfiles + tools + config de codigo; **no** migraciones aplicadas, modelo, indice RAG ni `.env.production` (cabecera del script explica como revertir cada uno: `ollama cp qwen3.5:9b qwen3.5:9b-prev` antes de un pull, `rollback_to_version` para RAG, `flags_<ts>.env` para banderas).
### C4 — Puerta previa (`deploy/promote_check.sh --reports ...`)
Automatica: arbol git/push, gate F10 sobre los reportes que pases (falla sin reportes), escaner de secretos, verificacion del manifest de F16 y **banderas AI_*/LOG_FORMAT sincronizadas entre `.env` y `.env.production`** (solo nombres; falla si hay una en dev que falte en prod). Manual: checklist impresa (snapshot, humo de staging, canary, medir, rollback probado).
### C5 — ADK canary (`docker-compose.canary.yml`, perfil `canary`)
Copia explicita del bloque `sintel_ai_adk` con imagen `ecommerce_sintel_ai_adk:canary` y contenedor `sintel_prod_ai_adk_canary`; **no arranca con un `up` normal** y no toca el estable. Comparte Redis/Postgres/Ollama; `CANARY_LOCAL_MODEL_CHAIN` permite probar otra cadena de modelos (cuidado: dos modelos distintos cargados no caben en 8 GB de VRAM). Nota: no modifica `docker-compose.prod.yml` (tiene tus cambios `ai_private` sin aplicar).
Tests escritos, NO ejecutados: `support/test_canary_routing.py` (apagado, internos, determinismo y monotonia del porcentaje, `engine_track`, fallback solo ante fallo de conexion y no ante timeout, veredictos).

## 4. Procedimiento de promocion (lo ejecutas tu)
1. `python ai_engine_adk/eval/runner.py ...` (F10) y `./deploy/promote_check.sh --reports ...`.
2. `./deploy/release_ai.sh snapshot`.
3. Construir el canary: `docker compose -f docker-compose.prod.yml -f docker-compose.canary.yml --profile canary --env-file .env.production build sintel_ai_adk_canary` y `up -d --no-deps sintel_ai_adk_canary`.
4. En `.env.production`: `AI_CANARY_ENGINE_URL=http://sintel_ai_adk_canary:8101`, `AI_CANARY_USER_EMAILS=<internos>`, `AI_CANARY_PERCENT=0`; recrear `django` (y `celery_worker` si WhatsApp entra al canary). Replicar las 3 variables en `.env` de dev (incidente del 503).
5. Turnos reales con los usuarios internos; `python manage.py ai_canary_report --hours 24` -> si `PROCEED`, `AI_CANARY_PERCENT=5`; repetir a 25 -> 50 -> 100 con cada decision.
6. En 100 % estable: reconstruir `sintel_ai_adk` con el mismo arbol, `AI_CANARY_ENGINE_URL=` (vacia) y bajar el canary. Si algo falla en cualquier paso: vaciar `AI_CANARY_ENGINE_URL` (todo vuelve al estable) y/o `./deploy/release_ai.sh rollback adk`.

## 5. Recomendaciones (no aplicadas)
- Anadir `./deploy/release_ai.sh snapshot` como primer paso de `deploy.sh` (hoy no lo llama; toca el script de produccion: cambio tuyo o con tu OK).
- Cuando exista el baseline en vivo de F10, fijar los umbrales de `ai_canary_report` y del SLO (F24).
- WhatsApp (Celery) usa `ask_ai` sincrono y tambien pasa por el canary: aplicar `CANARY_PERCENT` solo cuando F13 (cola dedicada) este resuelto o limitar a internos.
