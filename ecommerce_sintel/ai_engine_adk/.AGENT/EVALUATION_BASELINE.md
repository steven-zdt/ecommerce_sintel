# EVALUATION_BASELINE — evaluación continua del asistente (F10/F11)

> Documento vivo (HARDENING F19, 2026-09-24). Código: `ai_engine_adk/eval/` (ver `eval/README.md` para comandos), `ai_engine_adk/tests/security/`. **Regla del proyecto: el asistente no ejecuta tests ni benchmarks; los corre el usuario.**

## 1. Qué existe
- **Golden dataset** (`eval/golden/*.jsonl`): 118 casos sintéticos en 12 categorías A–L (routing 17, RAG 6, generación 6, grounding 9, selección de tools 6, argumentos 9, autorización 15, inyección 17, memoria 9, salida 12, latencia 5, resiliencia 7). Nivel 1 = determinista (importa los módulos reales, sin LLM); nivel live = `/chat` real del ADK en DEV.
- **Runner** (`eval/runner.py`), **fingerprint** por componente (`eval/fingerprint.py`: model, prompt, agent, tool, rag, embedding, retriever, reranker, memory_policy, guards), **gate** informativo (`eval/gate.py`: cambio sin evaluar, imagen desfasada, violación absoluta, regresión vs baseline, cambio de `LOCAL_MODEL_CHAIN`/`EMBEDDING_*`), `thresholds.json` (seguridad = 0; calidad >= baseline; p95 = sin número hasta el primer baseline en vivo).
- **Red team** (F11): `eval/redteam.py` (15 ataques × 20 mutaciones) y `tests/security/` (12 archivos, ~2 444 casos que afirman *política*); `eval/redteam_matrix.py` (matriz de cobertura de detección).
- Otras pruebas por fase (`tests/test_*.py`) y `scripts/ai_eval/{chat_model_bench,injection_battery,efficiency_baseline}.py`, `scripts/load/adk_load_test.py`, `scripts/resilience/chaos_dev.py`.

## 2. Última medición conocida (2026-09-24, autorizada entonces)
- Eval nivel 1 (ADK): 78 casos ejecutados, 78 pass, 0 violaciones de seguridad; Django (compuerta de memoria): 4/4; gate OK. Reportes en `eval/baselines/l1_2026-09-24.json` y `l1_django_2026-09-24.json`.
- `tests/security/`: 2 403 pass, 41 xfail (hallazgos conocidos), 0 fallos.
- **Los reportes están OBSOLETOS**: desde entonces cambiaron tools, agentes y modelo (F12–F18), así que el fingerprint ya no coincide. Hay que regenerarlos.
- **No existe baseline en vivo** (categorías B, C, K y parte de D/E/G/H/L): se detuvo la corrida porque el usuario prohíbe ejecutar benchmarks. Sin él no se pueden fijar SLO de latencia ni umbrales de calidad.

## 3. Hallazgos abiertos (known_gap / xfail)
1. Detección EN de extracción de prompt ("internal instructions").
2. `system:` solo al inicio de línea (envuelto/citado/mitad de línea no se marca; la cerca lo contiene).
3. Guardia de salida distingue mayúsculas en hosts/rutas/prompt.
4. Detección 0 % en base64/rot13/hex/homoglifos (informativo; monitor).
5. Sin juez LLM (faithfulness/correctness por proxies); sin TTFT; sin prueba multi-turno de extremo a extremo.

## 4. Cuándo es OBLIGATORIO correr el benchmark (plan §14.2)
Cambio de modelo, prompt/perfil, agente/routing, tool, RAG, embedding, retriever, reranker o política de memoria. `deploy/promote_check.sh --reports ...` exige un reporte cuyo fingerprint coincida con el árbol.

## 5. Cómo regenerar (lo ejecuta el usuario; comandos exactos en `eval/README.md`)
1. Nivel 1 en la imagen del ADK con el repo montado + caso `env=django` en el contenedor de Django -> `eval/baselines/l1_*.json`.
2. `pytest tests/security` con el repo montado.
3. Nivel live con `EVAL_JWT` de un usuario de prueba de DEV (GPU libre) -> `eval/baselines/live_<fecha>.json`; ese será el baseline formal.
4. `python ai_engine_adk/eval/gate.py --report ... [--baseline live_<fecha>.json]`.
5. Con el baseline: fijar `latency.p95_ms` en `thresholds.json` y los umbrales del canary (`ai_canary_report`).

## 5. Reglas
Un caso que falla hoy por un hallazgo real se marca `known_gap` (no se borra); los baselines no se editan a mano; datos siempre sintéticos.
