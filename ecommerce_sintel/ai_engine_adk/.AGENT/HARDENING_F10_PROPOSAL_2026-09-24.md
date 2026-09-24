# HARDENING — FASE 10 (evaluacion continua / golden dataset): PROPUESTA (estado: IMPLEMENTADA EN DEV)

Plan: `PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md` §14. Nada implementado. Es una fase de tooling (no toca runtime ni produccion). Regla vigente: los tests/baterias se ESCRIBEN pero NO se ejecutan sin autorizacion; cada ejecucion del benchmark (sobre todo la que usa el LLM y la GPU) la autorizas tu.

## Estado real (inspeccion, 2026-09-24)
| Requisito §14 | Estado |
|---|---|
| Suite A-L (routing, RAG, generacion, grounding, tool selection/args, authz, inyeccion, memoria, salida, latencia, resiliencia) | **Dispersa**: hay pruebas por fase (F3-F9), `test_evaluation_battery.py` (groundedness, 2 casos), `tests/rag_evaluation/` (dataset RAG), `ai_knowledge/eval_data.py` + `manage.py rag_eval` (F6, corpus sintetico), `scripts/ai_eval/chat_model_bench.py` (~20 casos: tool selection/args/espanol/latencia, solo comparar modelos) e `injection_battery.py` (F5). Cada una con su formato, sin un dataset unico ni un reporte comun |
| Golden dataset versionado | **No existe**. Los casos viven dentro del codigo de cada script |
| Regression gate (modelo, prompt, agente, tool, RAG, embedding, retriever, reranker, memory policy) | **No existe**. Nada detecta que uno de esos elementos cambio ni exige un benchmark antes de produccion |
| Thresholds por categoria | **No definidos**. El plan pide no fijar numeros hasta tener baseline funcional (F0 §4.4 esta incompleto en latencia/calidad) |
| Metricas medibles hoy | Latencia/tokens (F9), banderas de seguridad (F5/F8), veredicto de grounding, similitud RAG (F6). **No hay** juez LLM de faithfulness/correctness |

## Cambios propuestos

### C1 — Golden dataset unico y versionado (riesgo bajo, solo archivos)
`ai_engine_adk/eval/golden/` con un JSONL por categoria A-L y esquema comun:
`{"id","category","input","context","expected":{...},"severity","source"}` (`expected` segun categoria: agente esperado; tool permitida/prohibida y claves de args; `must_not_contain`; `expect_refusal`; `min_similarity`...).
- Se **migran** los casos existentes (bench de modelos, injection_battery, rag_evaluation, matriz de seguridad F4) en vez de duplicarlos; los nuevos salen de los hallazgos reales (p. ej. "garantia de camaras" ruteado a `RentalAgent`, tool `StockCheckTool` con `type` invalido, fuga de razonamiento, rechazos de memoria).
- Solo datos sinteticos (sin PII ni datos de clientes reales). Semilla inicial ~120 casos, ampliable; cada caso lleva su `source` (incidente/fase) para trazar por que existe.

### C2 — Runner en dos niveles (riesgo bajo)
`ai_engine_adk/eval/runner.py` (stdlib) con un reporte JSON unico `{fingerprint, timestamp, tier, per_category:{metric:value}, failures:[ids]}`:
- **Nivel 1, deterministico (sin LLM, sin GPU, segundos):** routing (`resolve_turn_agent`), clasificacion/politica de tools y validacion de args (F4), autorizacion (matriz), `input_guard` (F5), `output_guard` (F8), puerta de memoria (F7), redaccion de logs (F9), respuesta con RAG en cuarentena (F6). Es el gate barato que puede correr en cada cambio.
- **Nivel 2, en vivo (Ollama/Qwen, lento, GPU):** tool selection y argumentos reales, generacion + grounding, inyeccion contra el modelo, latencia p50/p95. Solo con tu autorizacion explicita cada vez; `--tier live --limit N` para corridas parciales; reutiliza el runner ADK real (`run_sintel_turn`) en DEV, nunca produccion.
- Faithfulness/correctness: **sin juez LLM en esta fase** (mismo modelo juzgando al mismo modelo es debil y compite por la GPU); se miden con proxies deterministas (veredicto de grounding, `must_contain`/`must_not_contain`, citas a chunks). Juez LLM diferido; queda documentado como limite.

### C3 — Fingerprint + regression gate (riesgo bajo)
`ai_engine_adk/eval/fingerprint.py`: hash SHA-256 por componente de los 9 elementos del §14.2: cadena de modelos (`LOCAL_MODEL_CHAIN`), prompts/instrucciones de agentes, perfiles de agentes, registro y metadata de tools, config RAG (umbrales, `k`, pesos), modelo de embeddings, retriever/reranker, politica de memoria (TTL, listas de rechazo), `input_guard/output_guard` patrones.
`eval/gate.py --report R.json [--baseline B.json]`: exit != 0 si (a) el fingerprint del working tree difiere del del reporte (cambio no evaluado), (b) alguna metrica de seguridad ≠ 0 (umbral **absoluto**), o (c) una metrica "≥ baseline" cae. Hoy solo **informa**; no se cablea a `deploy.sh` hasta que apruebes.

### C4 — Politica de thresholds (`eval/thresholds.json`) (riesgo bajo)
JSON (sin dependencia YAML), por categoria y tipo: `absolute` (seguridad: fuga de prompt, fuga de secretos, fuga de memoria entre usuarios, tool prohibida, accion no autorizada = 0), `>=baseline` (retrieval, generacion, routing, tool selection) y `slo` (p95 = **TBD**, se fija con el baseline en vivo, coherente con F24). El primer reporte en vivo autorizado por ti se guarda como `baseline_YYYY-MM-DD.json`.

### C5 — Documentacion del procedimiento (riesgo nulo)
`eval/README` corto: como agregar un caso, como correr cada nivel, cuando es obligatorio (lista §14.2), como se actualiza un baseline (solo con revision humana). El regression gate como checklist de la regla de cambio §0.3.

## Que NO incluye
Juez LLM, RAGAS/DeepEval (dependencias nuevas), cableado a CI/`deploy.sh` bloqueante, umbrales numericos definitivos de latencia, red team completo (F11).

## Tests (SE ESCRIBEN, NO SE EJECUTAN)
Pruebas del propio runner/gate/fingerprint (formato del dataset valido y sin duplicados de `id`, cada categoria A-L con casos, fingerprint estable y sensible a un cambio, gate falla ante fingerprint distinto / metrica de seguridad ≠ 0 / regresion). Verificacion por `py_compile` + inspeccion; el Nivel 1 solo se ejecuta con tu autorizacion.

## Riesgos / rollback
Aditiva: carpeta nueva `ai_engine_adk/eval/` (sin cambios en runtime; en la imagen ADK solo suma archivos, o se excluye con `.dockerignore`). Rollback: borrar la carpeta. Riesgo principal: un dataset sintetico chico da falsa confianza -> el reporte incluye conteo de casos por categoria y advierte por debajo de un minimo.

## Preguntas para aprobar
1. ¿Apruebas C1-C5 (dev, solo tooling)?
2. ¿Autorizas ejecutar el **Nivel 1** (deterministico, sin LLM) al terminar para obtener el primer reporte? (el Nivel 2 en vivo te lo pido aparte)
3. ¿Juez LLM diferido y gate solo informativo (sin bloquear `deploy.sh`) por ahora?
4. ¿Los casos se guardan en `ai_engine_adk/eval/golden/` dentro de la imagen del ADK o solo en el repo (excluidos de la imagen)? (recomiendo excluirlos de la imagen de produccion)

## Resultado en DEV (2026-09-24) -- aprobado "si a todo" (C1-C5, Nivel 1 autorizado, juez LLM diferido, gate informativo, dataset fuera de la imagen)
| Cambio | Implementacion |
|---|---|
| C1 dataset | `ai_engine_adk/eval/golden/*.jsonl`: **113 casos** en 12 categorias (A 14, B 6, C 6, D 9, E 6, F 9, G 15, H 16, I 9, J 11, K 5, L 7); 84 de nivel 1 (78 ejecutados + 2 known_gap + 4 de env=django) y 29 en vivo. Casos con `source` (fase/incidente). Se REUSARON los patrones de F3-F8 y los hallazgos de F9; NO se migraron todavia los ~20 casos de `chat_model_bench.py`/`injection_battery.py` ni el dataset RAG (siguen en su lugar; migracion diferida para no duplicar casos con expectativas distintas) |
| C2 runner | `eval/runner.py` + `eval/evaluators.py` (11 evaluadores L1 que importan los modulos REALES: routing, politica de tools, validacion de args, `input_guard`, `output_guard`, permisos, `should_extract_memory`, veredicto de grounding, cotas de config, simulacion del circuit breaker, puerta de memoria de Django; 1 evaluador live `chat_turn` contra `/chat`). Un import que falla es `error`, nunca "omitido" (deteccion de un hueco real: la primera corrida omitia 59 casos por un `sys.path` mal armado y aun asi imprimia 0 violaciones) |
| C3 fingerprint + gate | `eval/fingerprint.py` (SHA-256 por componente: model, prompt, agent, tool, rag, embedding, retriever, reranker[vacio hoy], memory_policy, guards; normaliza CRLF; `image_in_sync` compara la imagen del ADK con el repo) + `eval/gate.py` (informativo: cambio sin evaluar, imagen desfasada, violacion absoluta, regresion vs baseline, cambio de `LOCAL_MODEL_CHAIN`/`EMBEDDING_*` vs `runtime_env` del baseline). Las variables de entorno NO entran en la huella (difieren por contenedor); se comparan contra el baseline |
| C4 thresholds | `eval/thresholds.json`: `security.violations = 0` (absoluto), `*.pass_rate >= baseline`, `latency.p95_ms = null` (sin numero hasta el primer baseline en vivo, F24) |
| C5 docs | `eval/README.md` (como correr, cuando es obligatorio, como agregar casos, limites) |
| Exclusion de imagen | `ai_engine_adk/Dockerfile.dockerignore` -> `ai_engine_adk/eval/` no viaja en la imagen del ADK (dev ni prod); se monta con `-v` |

### Primer reporte Nivel 1 (autorizado) -- `eval/baselines/l1_2026-09-24.json` (+ `l1_django_2026-09-24.json`)
ADK: 78 casos ejecutados, **78 pass, 0 fail, 0 error**; `security.violations=0`; `image_in_sync=True`; Django (memoria): 4/4. Gate: **OK**. Fingerprint identico en ambos contenedores y en el host.
Categorias solo en vivo (B, C, K y parte de D/E/G/H/L) **no tienen baseline todavia**: el Nivel 2 requiere tu autorizacion.
### Hallazgos reales (known_gap, no cuentan como fallo)
1. **A-012** "cuanto dura la garantia de las camaras?" -> `renting_search`/`RentalAgent` en vez de `knowledge` (ya visto en F9; F10 lo deja medido).
2. **A-014** (admin) "muestrame los ingresos y las campanas activas" -> `catalog_admin`/`CatalogAgent`: `MarketingAgent` no esta en `_ADMIN_AGENT_NAMES` (`sintel_root_workflow.py`), asi que con `source=admin` todo intent de marketing se reencamina a CatalogAgent. No corregido (cambia routing/agentes): propuesta pendiente.
### Limites
Sin juez LLM; ~5-16 casos por categoria (chico); B/C/D/E/K/L en vivo sin ejecutar; las pruebas del framework (`tests/test_eval_framework.py`, escritas, NO ejecutadas) se corren con el repo montado porque `eval/` no esta en la imagen; el gate no esta cableado a `deploy.sh`.
