# Evaluacion continua del asistente (HARDENING F10)

Golden dataset + runner + fingerprint + gate. Solo tooling: no toca el runtime ni produccion, y NO viaja en la imagen del ADK
(`ai_engine_adk/Dockerfile.dockerignore`); se monta con `-v` en DEV. Regla del proyecto: **los benchmarks se ejecutan solo con
autorizacion del usuario** (el nivel live usa la GPU y el modelo).

## Estructura
- `golden/*.jsonl` -- un archivo por categoria A-L (routing, RAG, generacion, grounding, tool selection, tool args, authz, inyeccion,
  memoria, salida, latencia, resiliencia). Esquema en `schema.py` (`id`, `category`, `tier`, `env`, `kind`, `input`, `expected`,
  `severity`, `source`, `known_gap`). Solo datos SINTETICOS, sin PII.
- `evaluators.py` -- un evaluador por `kind`. `tier=l1`: deterministico, importa los modulos reales (sin LLM). `tier=live`: `chat_turn`
  contra el `/chat` real del ADK en DEV.
- `runner.py` -- corre un nivel y escribe un reporte JSON (`fingerprint`, `components`, `runtime_env`, `metrics`, `failures`,
  `known_gaps`). `fingerprint.py` -- SHA-256 por componente. `gate.py` -- compara reporte vs arbol de trabajo/baseline/thresholds.
- `thresholds.json` -- `absolute` (seguridad = 0), `ge_baseline` (no puede caer), `slo` (null hasta el primer baseline en vivo, F24).
- `baselines/` -- reportes de referencia versionados (`l1_*.json`, luego `live_*.json`).

## Como correr (desde `ecommerce_sintel/`)
```bash
# Nivel 1 (sin LLM, segundos) -- dentro de la imagen del ADK con el repo montado
MSYS_NO_PATHCONV=1 docker compose run --rm --no-deps -T -v "$(pwd -W):/repo:ro" -v "$(pwd -W)/ai_engine_adk/eval/baselines:/out" \
  -e EVAL_REPO_ROOT=/repo -e ADK_SESSION_BACKEND=memory -w /app sintel_ai_adk \
  python /repo/ai_engine_adk/eval/runner.py --tier l1 --out /out/l1_FECHA.json
# Casos env=django (puerta de memoria del servidor) -- dentro del contenedor de Django (repo montado en /code)
docker exec -w /code ecommerce_sintel_django python ai_engine_adk/eval/runner.py --tier l1 --env django --out /tmp/l1_django.json
# Nivel 2 (en vivo, lento, SOLO con autorizacion): EVAL_JWT = JWT de un usuario de PRUEBA de DEV
EVAL_JWT=... python ai_engine_adk/eval/runner.py --tier live --base-url http://localhost:8101 --out live.json
# Gate (informativo)
python ai_engine_adk/eval/gate.py --report l1.json --report l1_django.json [--baseline baselines/live_FECHA.json]
```
La imagen del ADK debe estar reconstruida con el codigo a evaluar (`image_in_sync` lo verifica).

## Cuando es OBLIGATORIO correr el benchmark (plan sec. 14.2)
Cambio de: modelo (`LOCAL_MODEL_CHAIN`), prompt/perfil de agente, agente/routing, tool (registro, metadata, adapter), RAG, embedding,
retriever, reranker o politica de memoria. El gate lo detecta por fingerprint (`cambio SIN evaluar en: ...`); el cambio de modelo o de
embedding ACTIVO (variables de entorno, no archivos) se detecta comparando `runtime_env` contra el baseline.

## Agregar un caso
Una linea JSON en el archivo de su categoria, id correlativo `<cat>-NNN`, `source` explicando por que existe (incidente/fase). Un caso
que falla HOY por un hallazgo real va con `"known_gap": true` (se lista aparte y avisa cuando empiece a pasar). No editar un baseline a
mano: se regenera corriendo el runner y con revision humana.

## Red team (HARDENING F11)
- `redteam.py`: ataques semilla + 20 mutaciones deterministas + chequeos de POLITICA (cerca de datos no confiables, guardia de salida).
  Para agregar un ataque: una entrada en `ATTACKS` (`{"es": ..., "en": ...}`); si falla HOY por un hallazgo real, agregar `"gap": {"kinds":
  {...}, "reason": ...}` (xfail no estricto) en vez de borrarlo.
- Paquete `tests/security/` (12 archivos): se corre con el repo montado, p. ej.
  `docker compose run --rm --no-deps -T -v "$(pwd -W):/repo:ro" -e EVAL_REPO_ROOT=/repo -e ADK_SESSION_BACKEND=memory -w /app sintel_ai_adk python -m pytest /repo/ai_engine_adk/tests/security -q -p no:cacheprovider`
  (solo con autorizacion del usuario). "Politica sobrevive" = fallo real; "no detectada" en una mutacion no robusta = solo informe.
- `redteam_matrix.py`: tabla categoria x mutacion de cobertura de DETECCION (informe, no gate).

## Limites conocidos
Casos sinteticos y pocos por categoria (aviso `min_cases_warning` bajo 5); el nivel 1 no mide calidad del modelo; faithfulness/
correctness usan proxies deterministas (sin juez LLM); TTFT no existe (sin streaming); memoria entre usuarios y RAG real requieren BD
(casos `env=django` / nivel live).
