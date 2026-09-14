# AI MODEL QUALIFICATION -- FASE 61.0 BASELINE

**Fecha:** 2026-08-12
**Plan:** "PROMPT MAESTRO -- FASE 61 -- AI MODEL QUALIFICATION" (nuevo, posterior al cierre del
plan "AI Change Proposal Engine", FASE 24-60, ver `AI_CHANGE_PROPOSAL_ENGINE.md`).
**Alcance de esta fase:** SOLO observacion/captura -- 0 archivos del proyecto modificados,
0 escritura sobre `WORKSPACE_ROOT`, 0 escritura sobre sandbox. Todos los comandos usados abajo
fueron detectados de configuracion REAL existente (`pytest.ini`, `package.json`, `docker ps`),
ninguno inventado.

---

## 1. Commit y estado de git

```
BASELINE_COMMIT: 5a9f642819759206c70e7321c5ce1fae7b6f2adf
BRANCH: fix/audit-p0-remediation (3 commits adelante de origin/fix/audit-p0-remediation)
ULTIMO COMMIT: fix(ai_engine): degradar con gracia en /chat cuando el motor primario falla
               sin fallback configurado (steven-zdt, 2026-08-07 15:44:45 -0500)
```

**BASELINE_GIT_STATUS: SUCIO (no limpio) -- pre-existente, sin relacion con ai_editor.**

```
645 rutas con cambios pendientes sin commitear:
  208 untracked (??)
  223 deleted (D)
  214 modified (M)
437 archivos trackeados modificados: +12130/-161843 lineas (git diff --stat)
```

Es trabajo real del usuario en curso en esta misma rama (no generado por ninguna sesion de
`ai_editor`) -- incluye, entre otros:
- Refactor de `core/services/commands.py` (nuevas clases `FeatureBannerSection`/
  `FeatureBannerBlock`, refactor de `HomeCardCommands`) -- **posible causa directa** de 3 tests
  fallidos en `shared/tests/test_content_blocks.py` (esperan 15 content blocks, encuentran 16 --
  consistente con un tipo de bloque nuevo agregado por ese trabajo en curso).
- Eliminacion masiva de `ai_engine/.AGENT/*`, `ai_engine/AI_MANIFESTS/*`, `ai_engine/APP_MEMORY/*`
  (223 deletes) -- migracion/limpieza documental de `ai_engine`, tampoco relacionada con
  `ai_editor`.
- Un path untracked anomalo: `"ecommerce_sintel/C\357\200\272/"` (bytes UTF-8 de un caracter de
  uso privado Unicode en el nombre) -- probable artefacto de un bug de Windows/Docker bind-mount,
  NO tocado, NO investigado en esta fase (fuera de alcance de FASE 61.0).

**Interpretacion para FASE 61 (seccion 6 del prompt maestro, "no escritura inicial"):** el arbol
sucio no bloquea FASE 61 porque (a) ninguna fase hasta Sandbox escribe sobre el repo real, y
(b) `ai_editor`/`agent/` no tienen capacidad estructural de promover sin `confirm=True` explicito
de un humano (garantizado por test AST, ver `AI_CHANGE_PROPOSAL_ENGINE.md` FASE 51-53). El
"ROLLBACK" de FASE 61.30 se refiere al SANDBOX de la prueba, no a este estado preexistente --
verificado que las lineas que cualquier caso de FASE 61 toque no deberian solaparse con este
trabajo en curso (mismo criterio aplicado en FASE 54-55).

---

## 2. Tests -- estado real (comandos detectados, no inventados)

Deteccion de infraestructura: `pyproject.toml` (sin `[tool.pytest]`), 3x `pytest.ini` (raiz,
`project_knowledge_graph/`, `ai_engine/`), `frontend/package.json` (`"test": "vitest run"`),
`frontend/playwright.config.js`, `frontend/e2e/*.spec.js`. **Gotcha real confirmado**:
`pytest-django` NO esta instalado en el host (`ModuleNotFoundError`) -- el `pytest.ini` de la
raiz asume Django via pytest, pero no es ejecutable asi en este entorno; los tests Django reales
corren via `manage.py test` DENTRO del contenedor `ecommerce_sintel_django` (Docker, confirmado
con `docker ps`).

### BASELINE_TESTS -- `project_knowledge_graph` + `ai_editor`

```
Comando: python -m pytest project_knowledge_graph/tests/ -q   (host, sin Docker, sin Django)
Resultado: 449 passed in 92.68s
```

100% PASS. Incluye toda la suite de `ai_editor` (`generation/`, `agent/`, resolver/planner/
patch/repository/validation/approval/audit/llm), no solo `project_knowledge_graph`.

### BASELINE_TESTS -- backend (Django, 21 apps)

```
Comando: docker exec ecommerce_sintel_django python manage.py test --verbosity=1 --noinput
Resultado: Ran 561 tests in 1363.285s (~22.7 min)
FAILED (failures=6, errors=14) -- 541/561 PASS (96.4%)
```

**Nota operativa real**: el primer intento fallo (`EOFError`) porque quedaba una base de test
`test_sintel_ecommerce` de una corrida interrumpida anterior -- resuelto con `--noinput` (recrea
solo la DB de test descartable vía Postgres, nunca toca `sintel_ecommerce` real). Documentado
como hallazgo de infraestructura, no de codigo.

**Los 20 fallos/errores son TODOS pre-existentes, en 2 apps, sin relacion con `ai_editor`:**

`renting/tests_presenters.py` (17 de 20) -- `EquipmentDetailEndpointTestCase`/
`EquipmentPublicDetailPresenterTestCase`:
- 5x `ValueError: Content-Type header is "text/html..."` -- el endpoint de detalle no esta
  devolviendo JSON donde el test lo espera.
- 2x `TypeError: ... got unexpected keyword arguments` (`RentalOptionalService.price_per_hour`,
  `EquipmentReview.is_active`) -- el modelo real ya no tiene esos campos, el test quedo
  desactualizado.
- 3x `AssertionError` en presenter (404 esperado no llega, `availability.status`/`hero_image`
  no coinciden).

`shared/tests/test_content_blocks.py` (3 de 20):
- 3x `AssertionError: 16 != 15` -- consistente con el trabajo en curso sin commitear en
  `core/services/commands.py` (nuevo tipo de content block).

**BASELINE_BACKEND_KNOWN_FAILURES = 20 (pre-existentes, documentados, NO corregidos en esta
fase -- regla 45 del prompt maestro: no corregir deuda tecnica fuera del ChangePlan).**

### BASELINE_TESTS -- frontend (Vitest)

```
Comando: npm run test  (== vitest run, frontend/package.json)
Resultado: Test Files 1 failed | 5 passed (6) -- Tests 25 passed (25)
Duracion: 29.19s
```

`src/modules/shop/ProductForm.test.js` falla al CARGAR (no al ejecutar) -- mock de `pinia`
incompleto (`No "defineStore" export is defined on the "pinia" mock"`), pre-existente, 0 tests de
ese archivo corrieron. Los otros 5 archivos (`usePaymentPolling`/`useTheme`/`useToast`/
`ProductForm` parcial no/`money`/`paymentStatus`) -- 25 tests, 100% PASS.

Playwright (`e2e/*.spec.js`, 3 specs: `home-landing`/`visual-regression`/`wompi-checkout`) --
**NO ejecutado en este baseline** (requiere servidor levantado + browsers instalados, no forma
parte del comando `npm test` estandar; se detectara/ejecutara si un caso de FASE 61 lo requiere).

---

## 3. Estado del Knowledge Graph (`BASELINE_GRAPH_STATUS`)

```
graph_client.get_graph_status():
  timestamp ultima auditoria: 2026-08-11T03:21:59 UTC
  kind: full
  apps_audited: 21
  endpoints: 150
  frontend_files: 521
  kg_nodes: 9575
  kg_edges: 20335
```

**Nodos por tipo (extracto relevante para FASE 61):** Model 167, Serializer 432, ViewSet 168,
Command 94, Selector 61, Endpoint 150, FrontendView 84, FrontendComponent 321, PiniaStore 29,
Composable 26, Route 89, Symbol 6396, File 1161.

**`validation_summary` (6 chequeos reales, POST-GRAPH 5) -- pre-existentes, no corregidos:**

```
orphaned_app_docs: 0
stale_documentation: 12
service_layer_violations: 2
import_cycles: 1
dead_frontend_components: 25
contradictory_counts: 43
```

**GRAPH GAP potencial identificado (a verificar en FASE 61.1/61.6):** la ultima auditoria del
grafo es de **2026-08-11**, y el arbol de trabajo tiene cambios reales sin commitear del
**2026-08-12** en adelante (seccion 1) -- cualquier simbolo/endpoint/componente introducido por
ese trabajo en curso (ej. `FeatureBannerSection`/`FeatureBannerBlock`) **NO existe todavia en el
grafo**. Si FASE 61.2 selecciona un caso que toque esas entidades nuevas, el Change Resolver
las reportara como `UNKNOWN`/`UNRESOLVED` correctamente (comportamiento esperado, no un bug) --
se preferira un caso sobre entidades YA conocidas por el grafo para evitar confundir "el modelo
fallo" con "el grafo esta desactualizado" (regla 36.D del prompt maestro).

---

## 4. Estado de `ai_editor` (`BASELINE_AI_EDITOR_STATUS`)

```
12 submodulos, TODOS con logica real: graph_client, llm, intent, resolver, planner,
repository, patch, validation, approval, audit, generation (24 submodulos), agent (3 submodulos).
```

Plan "AI Change Proposal Engine" (FASE 24-60): **60/60 fases cubiertas, 449/449 tests, 1
verificacion manual real contra `WORKSPACE_ROOT` (FASE 54-55, promote+rollback verificado con
SHA-256 exacto)**. `ai_editor/agent/run_autonomous_change_loop()` corrido una vez contra un LLM
real (FASE 51-53) -- resultado `REJECTED` (el modelo local de 8B no produjo JSON valido en 2
intentos), documentado como limitacion del modelo, no del pipeline.

**Frontera arquitectonica verificada, sigue intacta:** `ai_editor -> graph_client -> graph_sdk ->
project_knowledge_graph`, nunca imports internos arbitrarios (test AST). `ai_editor` nunca
importa `ai_engine`. `agent/` nunca importa `generation.promotion`/`repository.promote` (test
AST) -- no tiene capacidad estructural de promover.

Detalle completo: `ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md`,
`ai_editor/.AGENT/AI_EDITOR_BASELINE.md`.

---

## 5. Modelo LLM y configuracion (`MODEL`/`PROVIDER`/config)

```
Config activa (ai_editor.llm.config.load_llm_config(), sin override):
  provider: ollama
  base_url: http://localhost:11434
  model: llama3.1:8b
  api_key configurada: No (no requerida para ollama)
  timeout_seconds: 60.0
```

**Modelos disponibles en el servidor Ollama real (contenedor `ecommerce_sintel_ollama`):**

| Modelo | Tamano |
|---|---|
| `llama3.1:8b` (activo, default) | 8.0B |
| `qwen2.5-coder:1.5b` | 1.5B (especializado en codigo, mas chico -- candidato alternativo si `llama3.1:8b` no califica en FASE 61.9+) |
| `bge-m3:latest` | 566.70M (solo embeddings, no sirve para generacion) |

Variables `AI_EDITOR_LLM_PROVIDER`/`AI_EDITOR_OLLAMA_*`/`AI_EDITOR_OPENAI_*`/
`AI_EDITOR_ANTHROPIC_*` -- ninguna configurada en este entorno (ni en `.env`, ni en el shell
actual), corriendo 100% con los defaults de `ai_editor/llm/config.py`.

---

## 6. Stack (backend/frontend)

```
Backend (contenedor ecommerce_sintel_django):
  Django 5.2.13
  Python 3.13.14
  DB: PostgreSQL (Docker), test DB: Postgres descartable via manage.py test

Frontend (host):
  Vue 3.5.32
  Node 24.18.0
  npm 11.11.1
  Vite 8.0.9 (build/dev), Vitest 4.1.10 (unit), @playwright/test 1.61.1 (e2e, no corrido aca)
```

---

## 7. Contenedores reales activos (`docker ps`, verificado antes de correr nada)

```
ecommerce_sintel_django    Up 2h (healthy)   <- backend dev, donde corrio manage.py test
ecommerce_sintel_frontend  Up 2h             <- Vite dev server (node:24)
ecommerce_sintel_ollama    Up 2h             <- LLM real usado por ai_editor.llm
ecommerce_sintel_db        Up 2h (healthy)   <- Postgres dev
ecommerce_sintel_redis     Up 2h (healthy)
ecommerce_sintel_ai        Up 2h             <- ai_engine (chatbot, NO relacionado a ai_editor)
ecommerce_sintel_chromadb  Up 2h (healthy)
+ stack sintel_prod_* (produccion, NO tocado, NO relevante para FASE 61)
```

---

## Resumen ejecutivo del baseline

| Componente | Estado | Detalle |
|---|---|---|
| Git | SUCIO (pre-existente) | 645 rutas pendientes, sin relacion con `ai_editor`, sin bloquear FASE 61 |
| `project_knowledge_graph` + `ai_editor` tests | PASS | 449/449 |
| Backend Django tests | PASS_WITH_WARNING | 541/561 (96.4%), 20 fallos pre-existentes en `renting/`+`shared/`, ninguno en `ai_editor` |
| Frontend tests | PASS_WITH_WARNING | 25/25 tests OK, 1 suite no carga (mock roto, pre-existente) |
| Knowledge Graph | PASS_WITH_WARNING | 9575/20335, 6 tipos de gap ya conocidos, posible desactualizacion desde 2026-08-11 |
| `ai_editor` | PASS | 60/60 fases del plan anterior, frontera arquitectonica intacta |
| LLM | PASS | Ollama real alcanzable, `llama3.1:8b` activo |
