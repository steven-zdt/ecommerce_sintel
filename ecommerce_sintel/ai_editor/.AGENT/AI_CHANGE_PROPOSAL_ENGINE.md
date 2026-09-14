# AI Change Proposal Engine -- `ai_editor/generation/`

Plan "AI CHANGE PROPOSAL ENGINE" (2026-08-11), primera ejecucion real
(FASE 24 + FASE 25 + FASE 26 + FASE 27 + FASE 28, tal como pide el propio
prompt maestro -- **no** las 60 fases), extendida fase por fase en la
misma sesion, cada una tras checkpoint y confirmacion explicita del
usuario: **FASE 29 "Patch Proposal Validator"**, **FASE 30 "Generation
Retry Engine"** y **FASE 31 "Patch Engine Integration"**. Construido
sobre el pipeline "AI Editor Runtime" ya cerrado (plan POST-GRAPH 0-23,
ver `AI_EDITOR_BASELINE.md`) -- cero fases del Site Knowledge Graph ni
del plan POST-GRAPH reabiertas, salvo un bug real encontrado en el
propio baseline de esta fase (ver "Baseline" abajo) y otro encontrado y
corregido dentro de la propia FASE 31 (ver seccion dedicada).

## Responsabilidad

Transformar `ChangeIntent` + `ChangeContext` + `ChangePlan` (ya
resueltos por el pipeline existente, POST-GRAPH 2/3/4) en una
`PatchProposal` estructurada, verificable y trazable, y (desde FASE 31)
poder aplicarla sobre un **Sandbox aislado** -- **nunca sobre
`WORKSPACE_ROOT`**. Promover al checkout real (`repository.
promote_to_workspace()`, POST-GRAPH 12) sigue siendo una decision
posterior y separada, fuera del alcance de `generation/`: esta capa se
detiene deliberadamente en "aplicado sobre sandbox", nunca decide por si
sola promover nada a produccion.

Regla central del prompt maestro, aplicada literal en todo el diseno:
"El LLM NO debe descubrir el proyecto por si mismo" -- el Knowledge
Graph descubre (ya resuelto antes de llegar aca), el Planner organiza
(ya resuelto antes de llegar aca), el AI Change Proposal Engine genera
(esto), el Patch Engine aplica (fase futura), el Validation Engine
verifica (fase futura, FASE 29+).

## Entradas

Un `ChangeGenerationRequest` (`models.py`), ensamblado por
`context.build_generation_context(intent, context, plan)`:

| Campo | Origen | Contenido |
|---|---|---|
| `change_intent` | `intent.to_dict()` (POST-GRAPH 2) | request/domain/entities/scope |
| `change_plan` | `plan.to_dict()` (POST-GRAPH 4) | steps concretos (file/symbol/lineas/operation) |
| `graph_context` | `context.context_packet` (Fase 12, ya compactado) | target/contracts/frontend_consumers/backend_dependencies/tests/documentation/stats |
| `source_context` | `context.build_source_context(plan)` (FASE 26, NUEVO) | codigo REAL solo del rango de lineas del target `MODIFY` + margen chico |
| `test_context` | `validation.build_test_validation_report(context)` (POST-GRAPH 10, reusado) | tests required/recommended |
| `architecture_context` | `context.build_architecture_context(context)` (FASE 26, NUEVO) | app/doc de arquitectura real (via `CLAUDE.md`) + 5 reglas globales reales (via `MEMORY.md`, leidas en vivo) |

Regla de contexto minimo (seccion 5 del prompt maestro), cumplida en
codigo, no solo en prosa: `graph_context` es SIEMPRE el packet
COMPACTADO (decenas de nodos, `id`/`type`/`name`/`file`/`lines`, nunca
`meta` completo), nunca el grafo completo (9.575/20.335 nodos/aristas al
cierre del plan anterior). `source_context` lee SOLO el rango de lineas
del target mas un margen chico (`MARGIN_BEFORE=10`/`MARGIN_AFTER=5`) --
nunca el archivo entero, verificado por test
(`test_read_symbol_source_reads_only_the_requested_range_plus_margin_not_the_whole_file`).

## Salidas

Un `GenerationResult` (`models.py`), uno de 3 estados:

- `PROPOSED`: el LLM devolvio JSON valido con el esquema esperado ->
  `PatchProposal` real, `proposal.operations` es una lista de
  `PatchOperation` estructuradas (nunca un string de patch libre).
- `REJECTED`: el LLM devolvio texto libre (no JSON) o JSON con forma
  invalida (campo faltante, tipo incorrecto, `operation` no reconocida,
  `confidence` fuera de `[0,1]`) -- **nunca se intenta reparar
  silenciosamente**, `result.issues` explica exactamente que fallo,
  `result.raw_llm_text` conserva la respuesta cruda para auditoria.
- `ERROR`: la llamada al LLM fallo (red/HTTP) -- distinto de
  `REJECTED` a proposito: un futuro Retry Engine (FASE 30) necesita
  poder distinguir "reintentar con mejor prompt" de "reintentar la
  llamada de red".

## Dependencias

```
ai_editor.generation
    -> ai_editor.llm            (POST-GRAPH 2, ya existente -- Ollama/OpenAI/Anthropic)
    -> ai_editor.intent.schema  (solo el tipo ChangeIntent, ya existente)
    -> ai_editor.resolver       (solo el tipo ChangeContext, ya existente)
    -> ai_editor.planner        (solo el tipo ChangePlan, ya existente)
    -> ai_editor.validation.tests  (build_test_validation_report, reusado)
    -> ai_editor.workspace      (resolve_repo_file, WORKSPACE_ROOT -- solo lectura)
    -> ai_editor.patch.schema   (solo las constantes OPERATION_*, para
                                  compartir vocabulario con el Patch Engine)
```

**Nunca** importa `ai_editor.patch.engine` (`apply_operation`) ni
`ai_editor.repository` (`promote_to_workspace`/`create_sandbox`) --
verificado por test AST
(`test_generate_patch_proposal_never_calls_patch_engine_or_writes_anything`),
no por convencion nada mas. Nunca importa `ai_engine` (regla
arquitectonica de Fase 0, verificada por el test transversal ya
existente `test_ai_editor_never_imports_ai_engine`, que camina TODOS los
`.py` de `ai_editor/` incluido este submodulo nuevo). Nunca importa
`project_knowledge_graph.*` directo -- todo dato del grafo llega ya
resuelto en `context`/`plan` (que a su vez lo obtuvieron via
`graph_client`, la frontera oficial de POST-GRAPH 1).

## Seguridad

- **Cero escritura**: ningun archivo de `generation/` tiene un `open(...,
  "w")` ni llama a nada que escriba -- es generacion de una PROPUESTA en
  memoria, punto. Verificado por test (ver "Dependencias" arriba).
- **Rechazo estricto de salida no estructurada**: `validators.
  extract_json()` nunca "rescata" un JSON parcial o texto libre con una
  regex laxa -- si `json.loads` falla (incluso tras quitar un code fence
  markdown), es `None`, y `generator.py` responde `REJECTED` de
  inmediato. Probado explicitamente
  (`test_generate_patch_proposal_rejects_free_text_never_fabricates_a_patch`).
- **Vocabulario de operaciones compartido**: `PatchOperation.operation`
  de `generation/` solo acepta los mismos 4 valores que
  `ai_editor.patch.schema` (`MODIFY`/`ADD`/`DELETE`/`REPLACE`) -- import
  directo de esas constantes, no una lista paralela que pueda divergir.
- **API keys**: `ai_editor.llm` (POST-GRAPH 2) ya garantiza que una key
  nunca se loguea ni aparece en un mensaje de error -- `generation/`
  hereda esa garantia sin logica adicional (no maneja keys directamente).
- **Limite de contexto real**: `_read_symbol_source()` fisicamente no
  puede devolver mas que rango + margen chico -- no hay un flag ni un
  parametro que permita "leer todo el archivo" desde este modulo.

## Flujo real (FASE 24-28, tal como se ejecuto)

```
ChangeIntent (ya resuelto, POST-GRAPH 2)
    |
ChangeContext (ya resuelto, POST-GRAPH 3)
    |
ChangePlan (ya resuelto, POST-GRAPH 4)
    |
    v
context.build_generation_context(intent, context, plan)   -- FASE 26
    |
    v
ChangeGenerationRequest
    |
    v
prompts.build_prompt(request)                              -- FASE 27
    |
    v
(system_prompt, user_prompt)
    |
    v
ai_editor.llm.complete(user_prompt, system=system_prompt)   -- POST-GRAPH 2, reusado
    |
    v
validators.extract_json(response.text)                      -- FASE 28
    |
    +-- None -> GenerationResult(REJECTED, INVALID_JSON)
    |
    v
validators.validate_raw_schema(raw)                          -- FASE 28
    |
    +-- issues de severidad ERROR -> GenerationResult(REJECTED, issues)
    |
    v
PatchProposal real                                            -- FASE 25
    |
    v
GenerationResult(PROPOSED, proposal)
    |
    v
proposal_validator.validate_proposal_against_repo(proposal, plan, context)  -- FASE 29
    |
    +-- issues de severidad ERROR -> REJECT (no aplicar, ver GenerationIssue)
    |
    v
Sandbox YA CREADO por el caller (repository.create_sandbox(plan), POST-GRAPH 7)
    |
    v
patch_integration.apply_proposal_to_sandbox(sandbox, proposal, plan, context)  -- FASE 31
    |
    +-- re-valida (FASE 29 de nuevo, defensa en profundidad)
    +-- convierte cada operacion -> patch.schema.PatchOperation real
    +-- patch.engine.apply_operation(sandbox.root, ...) por operacion   -- POST-GRAPH 6
    |
    v
PatchApplicationResult (aplicado sobre el SANDBOX, WORKSPACE_ROOT intacto)
    |
    X   <- SE DETIENE ACA. NO se promueve -- el flujo del prompt maestro
           llega explicitamente hasta "Sandbox", promover a un checkout
           real (repository.promote_to_workspace(), POST-GRAPH 12, con
           sus 5 capas de guardrail) sigue siendo una decision separada
           y posterior, fuera del alcance de generation/.
```

## FASE 29 -- Patch Proposal Validator

`proposal_validator.validate_proposal_against_repo(proposal, plan,
context=None)` -- la unica pieza de `generation/` que lee el filesystem
real (nunca escribe). Distinto de `validators.py` (FASE 28, valida FORMA
de la respuesta cruda del LLM): esto valida una `PatchProposal` YA
CONSTRUIDA contra el estado REAL del repo/plan.

Checks implementados (los 8 que pide el prompt maestro mas los 6 de
"VALIDAR TAMBIEN"), cada uno reusando logica YA construida en vez de
reimplementarla:

| Check | Como | Reusa |
|---|---|---|
| archivo existe | `resolve_repo_file(op.file)` | `ai_editor.workspace` (POST-GRAPH 5) |
| simbolo/step existe | empareja `op.file`(+`op.symbol`) contra `ChangePlan.steps` | -- |
| operacion permitida | solo el step `MODIFY` (target principal) acepta escritura real; un `REVIEW`/`RUN` rechaza | -- |
| old_content coincide | hash de `op.old_content` vs hash real del rango exacto del step | `patch.fingerprint` (POST-GRAPH 6) |
| hash coincide | `op.expected_hash` vs fingerprint real | `patch.fingerprint` (POST-GRAPH 6) |
| new_content no vacio | string no vacio salvo `DELETE` | -- |
| lineas validas | `read_lines_fingerprint()` devuelve `None` si el rango ya no es valido | `patch.fingerprint` |
| scope permitido | `op.file` debe aparecer en `ChangePlan.steps` | -- |
| fuera del ChangePlan | mismo check que "scope permitido" | -- |
| archivos sensibles | mismo patron que protege el sandbox | `repository.sandbox._SENSITIVE_PATTERNS` (POST-GRAPH 18) |
| supera limites | `MAX_OPERATIONS_PER_PROPOSAL=20` (default provisional) + `MAX_PATCH_CONTENT_BYTES` | `patch.schema` (POST-GRAPH 6/18) |
| contratos no declarados | si `op.file` es un Endpoint/Serializer del `resolution.contracts` y el step no es `MODIFY` -> ERROR | `context.resolution` (ya resuelto) |
| elimina codigo no relacionado | heuristica: `new_content` < 50% del tamano de `old_content` -> WARNING (no bloquea) | -- |
| dependencias inesperadas | **NO implementado en esta fase** -- ver "Limitaciones" | -- |

Verificado contra datos reales (`HomeCardGroupSelector.get_by_name`,
`core/services/commands.py`): una propuesta con `old_content` EXACTO
(leido del archivo real) produce 0 issues; una con `old_content`
inventado produce `OLD_CONTENT_MISMATCH`; una que declara un archivo
fuera del plan produce `FILE_OUTSIDE_PLAN`; una sobre `.env` produce
`SENSITIVE_FILE`; una que intenta escribir sobre un step `REVIEW`
(`services/renting/availabilityService.js`, un consumidor frontend real
de `EquipmentViewSet.check_availability`) produce
`OPERATION_NOT_ALLOWED_FOR_STEP`.

## FASE 30 -- Generation Retry Engine

`retry.generate_with_retry(request, plan, context=None,
max_retries=DEFAULT_MAX_RETRIES)` -- orquesta `generator.
generate_patch_proposal()` (FASE 28) + `proposal_validator.
validate_proposal_against_repo()` (FASE 29) en un ciclo de hasta
`DEFAULT_MAX_RETRIES=3` intentos (literal del prompt maestro: "Maximo: 3
intentos, configurable").

Un intento cuenta como FALLIDO si el generador devuelve `REJECTED` (JSON
invalido/forma invalida) o si devuelve `PROPOSED` pero
`validate_proposal_against_repo()` encuentra al menos un issue ERROR.
`ERROR` (fallo de red del LLM) es un caso aparte: se reintenta la MISMA
llamada sin agregar una nota de correccion (no hay contenido que
corregir, puede ser transitorio).

**"CADA RETRY DEBE EXPLICAR: error, causa, restriccion añadida,
correccion solicitada"** -- cumplido literal: `_build_correction_note()`
arma un texto con el codigo+mensaje+campo de CADA issue ERROR del intento
fallido, y `prompts.build_prompt()` (extendido con el parametro
`previous_attempts`) lo inyecta como seccion
`PREVIOUS_ATTEMPTS_FEEDBACK` en el prompt del SIGUIENTE intento --
verificado por test que la seccion aparece en el intento 2 pero no en el
1, y que el codigo de issue real (`OLD_CONTENT_MISMATCH`) aparece en el
texto que efectivamente recibe el LLM.

`RetryOutcome` conserva el HISTORIAL completo (`attempts: list[
RetryAttempt]`), no solo el resultado final -- cada `RetryAttempt` tiene
su propio `status`/`issues`/`correction_note`. Verificado end-to-end
contra `HomeCardGroupSelector.get_by_name` con 3 respuestas de LLM
mockeadas en secuencia (`side_effect`): intento 1 con `old_content`
inventado -> FAIL (`OLD_CONTENT_MISMATCH`); intento 2, mismo error
deliberado -> FAIL; intento 3 con `old_content` EXACTO (leido del
archivo real) -> PASS, `RetryOutcome.succeeded=True`. Exactamente el
ejemplo del prompt maestro ("Attempt 1 FAIL... Attempt 2 FAIL... Attempt
3 PASS").

`retry.py` sigue sin importar `ai_editor.patch.engine`/
`ai_editor.repository` -- mismo criterio que `generator.py`, verificado
por test AST.

## FASE 31 -- Patch Engine Integration

`patch_integration.apply_proposal_to_sandbox(sandbox, proposal, plan,
context=None)` -- primera pieza de `generation/` que TERMINA escribiendo
algo, pero solo dentro de un `Sandbox` YA CREADO por el caller
(`repository.create_sandbox(plan)`, POST-GRAPH 7). Nunca crea ni destruye
el sandbox, nunca llama a `promote_to_workspace()` (verificado por test
AST) -- el flujo se detiene explicitamente donde el prompt maestro dice
"Sandbox", no un paso mas alla.

Regla del prompt maestro cumplida en DOS capas independientes: (1)
`validate_proposal_against_repo()` (FASE 29) se vuelve a correr SIEMPRE
al principio, sin confiar en que el caller ya valido; (2) cada operacion
individual pasa por `patch.engine.apply_operation()` (POST-GRAPH 6), que
compara el `old_fingerprint` de la operacion contra el contenido REAL
del sandbox en el momento exacto de escribir.

**Bug real encontrado y corregido durante la verificacion de esta
fase**: la primera version de `_convert_to_engine_operation()` calculaba
`old_fingerprint` RELEYENDO el sandbox en el momento de convertir cada
operacion -- eso lo hace coincidir consigo mismo trivialmente (el
fingerprint "esperado" siempre iba a matchear lo que sea que hubiera ahi
en ese instante), anulando por completo la deteccion de drift entre
operaciones de una misma propuesta. Detectado con un test real de 2
operaciones sobre el mismo rango (la primera cambia el contenido, la
segunda deberia fallar por desactualizada): con el bug, las dos se
aplicaban igual. Corregido: `old_fingerprint = compute_fingerprint(
operation.old_content)` -- el `old_content` que FASE 29 YA verifico
identico al repo real, nunca una relectura del sandbox en ese instante.
Verificado con el mismo test: primera operacion `APPLIED`, segunda
`FINGERPRINT_MISMATCH`, fail-fast (no sigue aplicando el resto).

Verificado tambien: una operacion `ADD` inserta exactamente en
`step.line_end + 1` (leccion real de POST-GRAPH 21 sobre la semantica de
`apply_operation`); pasar un "sandbox" falso cuyo `.root` apunta a
`WORKSPACE_ROOT` sigue siendo rechazado por el guardrail propio de
`apply_operation()` (`REJECTED_OUTSIDE_SANDBOX`) aunque la pre-validacion
hubiera pasado -- defensa en profundidad real, no solo documentada; y el
archivo REAL del repo (`core/services/commands.py`) queda byte-a-byte
identico antes y despues de aplicar una propuesta sobre el sandbox.

## FASE 32 -- Sandbox Generation Loop

`sandbox_loop.run_sandbox_validation_loop(proposal, plan, context=None)`
-- flujo literal del prompt maestro: `PatchProposal -> Sandbox -> Apply
-> Syntax Validation -> Tests`. Cero logica nueva de validacion, solo
ENCADENA piezas ya reales:

```
create_sandbox(plan)                                    -- POST-GRAPH 7
    |
    v
apply_proposal_to_sandbox(sandbox, proposal, plan, context)   -- FASE 31
    |
    +-- no aplico -> validation_report=None, ready_for_approval=False
    |
    v
run_validation(sandbox, plan)                            -- POST-GRAPH 8 (Nivel 1 sintaxis)
    |
    v
build_test_validation_report(context)                    -- POST-GRAPH 10 (clasifica, no ejecuta)
    |
    v
SandboxLoopResult(ready_for_approval = applied AND level_1_passed)
```

A diferencia de `apply_proposal_to_sandbox()` (FASE 31, que espera un
sandbox creado por el caller porque su ciclo sigue mas alla), esta
funcion CREA su propio sandbox -- representa "probar esta propuesta de
punta a punta" en una sola llamada. No lo limpia automaticamente: si
`ready_for_approval=True` el caller lo necesita intacto para el
siguiente paso (`approval`/`promote_to_workspace()`, ya existentes); si
es `False`, el caller decide si inspeccionarlo antes de limpiar.

**`ready_for_approval` es honesto sobre lo que NO verifica**: significa
unicamente "se aplico sobre el sandbox Y paso sintaxis" -- nunca implica
aprobacion humana, nunca implica que los tests identificados pasen (no
se ejecutan, mismo motivo de siempre: el sandbox parcial no provee
Django/Postgres/Redis).

Verificado con 3 escenarios reales contra `HomeCardGroupSelector.
get_by_name`: (1) propuesta valida -> `applied=True`,
`level_1_passed=True`, `ready_for_approval=True`; (2) propuesta con
sintaxis Python rota -> el Patch Engine SI la aplica (`apply_operation`
solo escribe texto, no valida sintaxis) pero `run_validation()` la
atrapa despues -> `level_1_passed=False`, `ready_for_approval=False`
-- el mismo patron exacto que ocurrio de verdad en POST-GRAPH 21 (un
error real de indentacion se aplico y lo atrapo la validacion antes de
llegar a promote); (3) propuesta que ya falla la pre-validacion de FASE
29 -> nunca llega a `run_validation()`, `validation_report=None`. El
archivo REAL del repo queda intacto en los 3 casos.

## FASE 33-36 -- Validacion consolidada, Reconciliation, Impact Recheck, Code Quality

Construidas en un solo batch (pedido explicito del usuario: "continua
con fase 34 y demas, deja pruebas test para lo ultimo" -- tests
formales escritos y corridos al final del batch, no fase por fase).

**FASE 33 -- `validation_report.py`**: `build_generation_validation_
report(sandbox_loop_result, context=None)` consolida `syntax`/`tests`/
`contracts`/`errors`/`warnings` de un `SandboxLoopResult` (FASE 32) YA
calculado en un unico `GenerationValidationReport`. Cero deteccion
nueva -- agregacion honesta de `validation_report`/`test_report`/
`apply_result.pre_validation_issues` que ya existen. `tests_executed`
queda `False` siempre: ejecutar tests reales (`manage.py test`, el
runner real del proyecto -- no pytest, `pytest-django` no esta
instalado, ver MEMORY.md) sigue `NOT_IMPLEMENTED`, mismo motivo
estructural de siempre.

**FASE 34 -- `reconciliation.py`**: `reconcile_change_scope(proposal,
sandbox_loop_result, plan, context=None)` -- version SCOPE de Graph
Reconciliation, NO reconstruccion completa del grafo. Motivo #1 de
POST-GRAPH 9 (sandbox parcial, no se puede reconstruir el grafo
completo) sigue aplicando sin cambios. Motivo #2 de esa misma fase
("`ai_editor.patch` no genera contenido real") **ya NO aplica** desde
que `generation/` (FASE 25-33) SI produce `PatchProposal` reales -- eso
habilita comparar el SCOPE PREDICHO (`plan.steps`/`context.resolution`,
calculados ANTES del patch) contra el scope REAL declarado por la
propuesta, exactamente el formato del ejemplo del prompt maestro
("Plan: 3 files... Resultado: 3 files..." -> PASS/FAIL). Reusa
`SandboxLoopResult.apply_result.pre_validation_issues` (FASE 29, ya
calculado) para poblar `unexpected_impact` -- no es deteccion nueva, es
un reporte nuevo sobre datos ya reales.

**FASE 35 -- `impact_recheck.py`**: `capture_impact_baseline(context)` +
`recheck_impact(baseline)` -- re-consulta `graph_client.calculate_
impact()` sobre el mismo target y compara contra un baseline capturado
al planear, detectando **DRIFT DEL GRAFO** (alguien corrio `cli audit`
mientras tanto), no "impacto real de mi cambio recien aplicado" (eso
seguiria requiriendo reconstruir el grafo). **Bug real encontrado y
corregido durante esta misma fase**: el primer diseno aproximaba el
impacto "predicho" sumando 3 buckets de `ChangeContext.resolution`
(mismo truco que `approval.gate.build_change_summary()` usa para
`total_affected`) -- pero esa suma EXCLUYE tests/documentation/
configuration/otros, que SI cuentan en el `total_affected` real de
`calculate_change_impact()`. Verificado con datos reales: aproximacion=13
vs real=42 sobre `EquipmentViewSet.check_availability`, sin que nada
hubiera cambiado en el grafo -- habria producido `BLOCK` falso SIEMPRE.
Corregido con un diseno de 2 pasos: `capture_impact_baseline()` llama
`calculate_impact()` UNA vez y guarda el numero REAL (nunca aproximado);
`recheck_impact()` compara manzanas-con-manzanas contra ese baseline.
Verificado: sin drift real (recheck inmediato) -> `PASS` con numeros
identicos; baseline artificialmente bajo -> `BLOCK` real.

**FASE 36 -- `code_quality.py`**: `run_code_quality_checks(sandbox,
proposal)` -- auditoria real del repo ANTES de escribir el modulo:
`pyproject.toml` solo declara `[tool.bandit]` real (sin black/ruff/mypy/
flake8/eslint/prettier); de eso, `bandit` 1.9.4 SI esta instalado y
resoluble en PATH (verificado con `bandit --version`, no solo `grep`
sobre el config). Corre `bandit -c <pyproject.toml real> -ll` (misma
config que `.github/workflows/ci.yml`) contra los `.py` que la
propuesta toco DENTRO del sandbox -- probado con un hallazgo REAL
(`eval()`, B307) detectado por el bandit real instalado, no simulado.
Archivos `.vue`/`.js`/`.ts` reportan `NOT_CONFIGURED` explicito (sin
eslint/prettier instalados, verificado). **Bug real encontrado y
corregido durante esta fase**: la logica original de `overall_status`
caia a `PASS` cuando TODOS los checks eran `NOT_CONFIGURED` (ningun
linter corrio de verdad) -- implicaba falsamente "revisado y esta bien"
sobre un archivo `.vue` que nadie escaneo. Corregido: `PASS` exige al
menos un check que realmente se haya ejecutado.

## FASE 37 -- Architectural Compliance

`architecture_compliance.check_architectural_compliance(proposal)` --
valida `new_content` de una `PatchProposal` contra reglas YA
documentadas y reales del proyecto (nunca inventadas): Selectors sin
efectos secundarios (`.AGENT.md`), ViewSets sin ORM directo (`.AGENT.md`,
WARNING no bloqueante), import correcto de permisos (`CLAUDE.md`,
ERROR), frontend sin axios directo (`CLAUDE.md`/`MEMORY.md`, ERROR).
Cada `ComplianceIssue.source` cita el documento y la frase exacta.
"tenant boundaries"/"shared components" (pedidos por el prompt maestro)
quedan honestamente en `not_implemented` -- este proyecto no tiene
concepto de tenant real, y "shared components" requeriria parsear Vue
real, fuera de alcance de una regex. Heuristico (regex sobre
`new_content`), no un parser AST completo -- documentado como
limitacion, no oculto. Verificado con 4 casos reales: `.save()` en un
Selector -> `FAIL`; `.objects.` en un ViewSet -> `PASS` con warning (no
bloquea); import directo de `IsAdminUser` desde DRF -> `FAIL`; `axios.`
en un `.vue` -> `FAIL`; cambio backend limpio -> `PASS` sin issues.

## FASE 38 -- Cross-Stack Generation

**Toca un guardrail de seguridad ya cerrado y testeado (FASE 29) --
implementado SOLO tras confirmacion explicita del usuario en 2 pasos**
(primero confirmo que queria tocar el guardrail, despues eligio
explicitamente la opcion "Si, relajar el guardrail" entre 2 alternativas
concretas, no un "si" ambiguo).

**Antes de FASE 38**: `proposal_validator._check_scope_and_operation()`
solo permitia escritura sobre el step `MODIFY` (target principal) --
una `PatchProposal` jamas podia tocar mas de un archivo real, aunque
`PatchProposal.operations` ya fuera una lista desde FASE 25.

**Relajacion ACOTADA (no "cualquier archivo")**: ahora tambien se
permite escribir sobre steps `REVIEW` que el grafo YA vinculo como
contrato/consumidor-frontend/dependencia-backend REAL del target
(exactamente los 3 buckets de `resolve_change()`) y sobre steps `RUN`
(tests reales) -- coincide con el ejemplo de cross-stack del prompt
maestro: "Model -> Serializer -> Endpoint -> API Client -> Store ->
Component -> Tests". Los `REVIEW` de **documentacion** (`.md`) siguen
BLOQUEADOS a proposito -- FASE 43 "Documentation-Aware Generation" exige
que la documentacion quede como PROPUESTA, nunca aplicada
automaticamente. Un archivo que ni siquiera aparece en el plan sigue
bloqueado siempre (`FILE_OUTSIDE_PLAN`).

**3 cambios encadenados, todos necesarios para que la relajacion sea
util de verdad, no solo teorica**:
1. `proposal_validator._check_scope_and_operation()`: la relajacion en
   si (arriba). De paso corrige un bug latente real (no nuevo de esta
   fase): la version anterior tenia una condicion
   (`operation.operation != OPERATION_DELETE`) que en los hechos
   eximia CUALQUIER operacion `DELETE` de este chequeo por completo,
   sin importar el step -- nunca se exploto porque nada generaba DELETE
   sobre un REVIEW step todavia, pero era un agujero real. La reescritura
   lo elimina.
2. `proposal_validator._check_undeclared_contract()`: de `ERROR`
   bloqueante a `WARNING` -- un contrato REVIEW real ya no es "cambio
   silencioso" (el step existe en el plan, el grafo lo vinculo), cumple
   FASE 41 "Contract-Aware Generation" ("no permitir que el LLM cambie
   SILENCIOSAMENTE un contrato" -- un WARNING visible no es silencioso).
3. `generation/reconciliation.py`: `unexpected_impact` ahora filtra por
   severidad `ERROR` -- sin esto, el downgrade del punto 2 haria que
   CUALQUIER cambio cross-stack legitimo sobre un contrato reportara
   `RECONCILIATION=FAIL` igual, contradiciendo el proposito de esta fase.
4. `generation/context.py::build_source_context()`: extendido para leer
   fuente real (rango+margen, nunca el archivo completo) tambien de los
   steps `REVIEW`/`RUN` ahora escribibles -- sin esto, el LLM podria
   PROPONER un cambio cross-stack (permitido estructuralmente) pero
   nunca conocer el `old_content` real de esos archivos, y cualquier
   propuesta cross-stack fallaria `OLD_CONTENT_MISMATCH` por adivinar a
   ciegas.

**Verificado end-to-end contra el repo real**
(`EquipmentViewSet.check_availability`, `renting/api/views.py` +
`views/customer/renting/RentalDetailView.vue`, dos archivos de capas
distintas -- backend Django + frontend Vue): una unica `PatchProposal`
con 2 operaciones se aplica sobre el MISMO sandbox, sintaxis Nivel 1
pasa para ambos, `ready_for_approval=True`, y el checkout real queda
byte-a-byte identico en ambos archivos despues.

**Costo real medido, no estimado**: para el mismo target (alto riesgo,
16 nodos relacionados), `build_source_context()` extendido lee ~19.6K
caracteres de fuente real distribuidos en 17 targets -- documentado
como dato real, sin imponer un limite artificial (FASE 56 "Performance"
es donde corresponderia optimizar, solo despues de medir, tal como pide
el prompt maestro).

## FASE 40-41 -- Dependency-Aware y Contract-Aware Generation

**FASE 40 (`dependency_awareness.py`)**: `check_dependency_awareness(
proposal)` detecta imports NUEVOS que una propuesta introduce (diff
`old_content` vs `new_content`, regex, no AST completo) y bloquea ERROR
si alguno referencia `ai_engine` -- regla REAL ya establecida (servicio
FastAPI en su propio contenedor Docker, nunca un paquete Python
importable desde el resto del proyecto). Deteccion de dependencias
CIRCULARES explicitamente NO implementada: no existe una operacion en
`graph_sdk`/`graph_client` que la exponga hoy, y fabricar una heuristica
sin verificarla contra un caso real violaria la disciplina de toda esta
sesion. Verificado con 4 casos reales: import nuevo normal -> `PASS`
(reportado, no bloqueado); `from ai_engine.llm_factory import get_llm`
-> `FAIL`; `import ai_engine` -> `FAIL`; sin imports nuevos -> reporte
vacio; import PRE-EXISTENTE (ya en `old_content`) correctamente NO
marcado como "nuevo".

**FASE 41 (`contract_awareness.py`)**: `check_contract_coverage(
proposal, context)` profundiza el `UNDECLARED_CONTRACT_CHANGE` (WARNING
desde FASE 38) -- cuando el target afecta un contrato
(`resolution.contracts` no vacio, dato YA real de `calculate_change_
impact()`), compara los consumidores frontend/tests que el GRAFO ya
conoce contra lo que la `PatchProposal` realmente cubre
(`operations` tocadas + `tests_to_update` declarado). Nunca bloquea por
si solo -- "no permitir que cambie SILENCIOSAMENTE" se cumple
haciendolo VISIBLE en `recommendation`, no prohibiendo el cambio (un
contrato puede cambiar de forma retrocompatible sin tocar cada
consumidor). Verificado con datos reales: `EquipmentViewSet.
check_availability` (afecta un contrato real) con una propuesta minima
(solo el target) -> `PARTIAL_COVERAGE`, 6 consumidores frontend
conocidos, 0 cubiertos, reportados por nombre; declarando TODOS los
tests conocidos en `tests_to_update` -> `missing_tests` baja a `[]`;
`HomeCardGroupSelector.get_by_name` (sin contratos) -> `NOT_APPLICABLE`.

## FASE 42-44 -- Test-Aware, Documentation-Aware, Confidence Engine

`PatchProposal` (FASE 25) se extendio con 3 campos nuevos, todos con
default `[]` (retrocompatible): `tests_to_add`, `tests_to_remove`,
`documentation_to_update`. `prompts.py`/`generator.py`/`validators.py`
actualizados para pedirlos/leerlos/validarlos igual que `tests_to_update`.

**FASE 42 (`test_awareness.py`)**: `check_test_awareness(proposal)` --
`DELETE` sobre un archivo de test (`tests.py`/`test_*.py`/`*_test.py`/
`tests_*.py`) SIN declararlo en `tests_to_remove` -> `ERROR` ("no
eliminar tests porque dificultan el cambio", regla literal del prompt
maestro); declarado -> `WARNING` visible, no bloquea (eliminar un test
genuinamente obsoleto es legitimo si se declara por que).

**FASE 43 (`documentation_awareness.py`)**: `check_documentation_
awareness(proposal, context=None)` -- compara `documentation_to_update`
declarado contra la documentacion que el GRAFO ya sabe que referencia
el target (`context.resolution.documentation`); informativo, nunca
bloquea. Ademas re-verifica, por defensa en profundidad, que NINGUNA
operacion toca un `.md` directamente (garantia ya estructural desde
FASE 38, probada aca en aislamiento).

**FASE 44 (`confidence_engine.py`)**: `compute_composite_confidence(
proposal, context=None, validation_report=None, architecture_report=None,
contract_report=None)` -- combina `llm_confidence` (siempre presente,
`PatchProposal.confidence`) con `target_certainty`/`syntax_validation`/
`architecture_compliance`/`contract_coverage`, cada uno OPCIONAL (si el
caller no corrio esa fase, no participa -- nunca se fabrica un valor
neutro). Promedio SIMPLE de los factores disponibles, nunca una
ponderacion inventada sin datos historicos que la justifiquen.

Verificado con datos reales: target resuelto (`RESOLVED`) aporta
`target_certainty=1.0`; una propuesta minima sobre `EquipmentViewSet.
check_availability` (contrato real, cobertura parcial) aporta
`contract_coverage=0.0`, bajando el score compuesto de forma verificable
y trazable (cada factor queda listado con su fuente exacta).

## FASE 45-46 -- Human Review render y Promotion Gate consolidado

**FASE 45 (`human_review.py`)**: `render_full_review(proposal, ...)` --
texto humano que compone PATCH/RISKS/CONFIDENCE/GRAPH DIFF/IMPACT/
SYNTAX/ARCHITECTURE/CONTRATOS/DEPENDENCIAS/TESTS/DOCUMENTACION en un
unico bloque, extendiendo `approval.gate.ChangeSummary.render_text()`
(POST-GRAPH 11, que ya cubria REQUEST/FILES/SYMBOLS/RISK/TESTS). Cada
reporte es OPCIONAL -- verificado que ninguna seccion aparece si su
reporte no se paso (`test_render_never_fabricates_sections_for_missing_
reports`). Decisiones permitidas siguen siendo las 4 reales de
`approval.schema` (POST-GRAPH 11, cerrada) -- "REGENERAR" se documenta
como accion separada (`retry.generate_with_retry()`), no una decision
que se registre.

**FASE 46 (`promotion_gate.py`)**: `check_promotion_gate(sandbox_loop_
result, reconciliation_report=None, impact_report=None, architecture_
report=None, contract_report=None)` -- consolida Graph Reconciliation/
Impact Recheck/Architectural Compliance como BLOQUEANTES, Contract
Coverage como WARNING (mismo criterio de FASE 38/41: un contrato parcial
no bloquea solo). "Tests pass" queda marcado `NO VERIFICABLE` siempre --
honesto, no fabricado. **No reemplaza `promotion.review_and_promote()`**
-- `decision`/`confirm` explicitos siguen siendo obligatorios ahi, este
gate es un chequeo PREVIO mas amplio que un caller puede correr antes.

Verificado end-to-end con datos 100% reales
(`EquipmentViewSet.check_availability`): el render completo compone
correctamente 6+ reportes reales en un solo texto legible, y el
promotion gate calcula `READY` con warnings visibles (cobertura de
contrato parcial + tests no verificables) sin bloquear un cambio
legitimo.

## Cadena de promocion -- `promotion.py`

`review_and_promote(sandbox_loop_result, context, plan, workspace_root,
decision, reviewer_note=None, confirm=False)` -- pedido explicito del
usuario ("encadenar generation con approval/repository") tras el
checkpoint de FASE 32, no una fase numerada propia del plan de 60 fases;
mapea conceptualmente a FASE 45 "Human Review UI/CLI" (sin UI, solo el
mecanismo) + FASE 46 "Promotion Gate" (version minima, sin Graph
Reconciliation/Impact Recheck todavia).

```
SandboxLoopResult (FASE 32, ya calculado)
    |
    v
build_change_summary(context, plan, validation_report, test_report)  -- POST-GRAPH 11
    |
    +-- ready_for_approval=False -> PromotionOutcome(promoted=False, sin pedir decision)
    |
    v
record_decision(decision, reviewer_note)                              -- POST-GRAPH 11
    |
    +-- decision != APPROVE -> PromotionOutcome(promoted=False, promote_result=None)
    |
    v
promote_to_workspace(sandbox, approval, workspace_root, confirm, validation_report)  -- POST-GRAPH 12/20
    |
    v
PromotionOutcome(promoted = status=="PROMOTED")
```

**Regla final de seguridad del prompt maestro, cumplida literal**:
"Nunca permitir LLM -> WRITE -> PRODUCTION." `decision` y `confirm` son
parametros OBLIGATORIOS -- no hay ningun camino de codigo que promueva
sin que ambos vengan de un llamador que los paso explicitamente
(`confirm` default es `False`). Las 5 capas de guardrail de
`promote_to_workspace()` (incluida la de POST-GRAPH 20, que rechaza si
`validation_report.level_1_passed` es `False` sin importar la
aprobacion) se reusan tal cual, nunca se relajan.

Probado UNICAMENTE contra `fake_workspace` (`tmp_path`, mismo patron que
`test_ai_editor_commit_control.py`) -- **nunca invocado contra
`ai_editor.workspace.WORKSPACE_ROOT` real en esta sesion**. 4 escenarios
reales verificados: `ready_for_approval=False` bloquea sin siquiera
pedir una decision; `decision=REJECT` nunca llega a `promote_to_
workspace()`; `decision=APPROVE` sin `confirm=True` es rechazado por el
propio guardrail de `promote_to_workspace()` (`NOT_CONFIRMED`); `decision=
APPROVE` + `confirm=True` promueve de verdad sobre el `fake_workspace` y
deja el archivo con el contenido nuevo. Tambien verificado: un
`SandboxLoopResult` inconsistente a proposito (`ready_for_approval=True`
pero `validation_report.level_1_passed=False`) sigue siendo bloqueado
por el guardrail INDEPENDIENTE de `promote_to_workspace()` -- defensa en
profundidad real, no solo confiar en que `sandbox_loop.py` calculo bien
`ready_for_approval`.

## Limitaciones (honestas, no un gap oculto)

- **Nunca se corrio contra un LLM real** en esta fase -- Ollama/OpenAI/
  Anthropic no estan disponibles en este entorno de ejecucion. Los 45
  tests nuevos de `generation/` usan un LLM MOCKEADO
  (`unittest.mock.patch`, mismo patron que `test_ai_editor_llm.py`), pero
  con un `ChangeGenerationRequest` REAL (contra el grafo/repo reales) --
  solo la respuesta del LLM es sintetica. Correr contra un LLM real
  (Ollama local, por ejemplo) queda como verificacion pendiente antes de
  construir FASE 29+.
- **FASE 29 ya implementada** (ver seccion dedicada arriba) -- una
  `PatchProposal` puede validarse CONTRA el repo real. Lo que sigue
  faltando: "dependencias inesperadas" (¿el `new_content` introduce un
  import que crea una dependencia circular o viola un limite de modulo?)
  se documenta como NO implementado a proposito -- requeriria parsear
  imports del `new_content` propuesto y consultar el grafo de
  dependencias real (`graph_client`) para saber si es "inesperada", una
  pieza que FASE 40 "Dependency-Aware Generation" construira con mas
  profundidad; agregar una heuristica superficial ahora arriesgaba dar
  una falsa sensacion de cobertura. Aun con `validate_proposal_against_
  repo()` devolviendo 0 issues, la propuesta **sigue sin estar conectada
  al Patch Engine** -- ver limitacion siguiente.
- **`GenerationConfidence` es auto-reportada por el LLM**, no calculada
  con factores reales (graph certainty/contract certainty/test
  coverage/etc, que pide FASE 44 "Confidence Engine"). Se documenta la
  clasificacion HIGH/MEDIUM/LOW por umbral simple sobre ese numero, nunca
  se fabrica un factor adicional que no existe todavia.
- **`architecture_context` es minimo**, no la validacion de cumplimiento
  arquitectonico completa que pide FASE 37 "Architectural Compliance" --
  hoy solo agrega el doc de arquitectura real de la app (via `CLAUDE.md`)
  y las 5 reglas globales (via `MEMORY.md`), sin verificar
  automaticamente que la propuesta las respeta.
- **FASE 30 ya implementada** (ver seccion dedicada arriba) --
  `generate_with_retry()` reintenta hasta 3 veces con correccion
  explicita. `generate_patch_proposal()` en si (un solo intento) sigue
  sin retry propio -- es una decision deliberada del caller usar uno u
  otro, no todo el mundo necesita el ciclo completo.
- **FASE 31, FASE 32 y la cadena de promocion (`promotion.py`) ya
  implementadas** (ver secciones dedicadas arriba) -- una `PatchProposal`
  puede aplicarse sobre un `Sandbox` real, validarse (sintaxis, Nivel 1),
  someterse a una decision humana REAL (`decision`/`confirm` obligatorios,
  nunca defaulteados) y promoverse a un workspace real, todo encadenado.
  Lo que sigue faltando: Graph Reconciliation e Impact Recheck (POST-
  GRAPH 9, `NOT_IMPLEMENTED`) no se corren en ningun punto de esta
  cadena -- `promotion.py` es deliberadamente el mecanismo MINIMO de
  union, no la implementacion completa de FASE 45 "Human Review UI/CLI"
  (sin interfaz real, solo `change_summary.render_text()`) ni de FASE 46
  "Promotion Gate" (que exige ADEMAS Graph Reconciliation + Impact
  Recheck pasando antes de promover). Orquestar esto de forma totalmente
  autonoma (sin que un humano dispare cada paso) sigue siendo
  responsabilidad de una fase posterior (FASE 53 "Autonomous Controlled
  Loop" o el "AI Editor Agent" de FASE 51).
- **Los tests identificados nunca se ejecutan** (FASE 32, mismo motivo
  documentado desde POST-GRAPH 8/10: el sandbox parcial no provee
  Django/Postgres/Redis) -- `SandboxLoopResult.test_report` solo
  clasifica `required`/`recommended`, `ready_for_approval=True` NO
  significa "los tests pasan", solo "aplico y la sintaxis es valida".

## Baseline (FASE 24)

Al arrancar esta fase se corrio la suite completa
(`project_knowledge_graph/tests/`) para registrar el estado real ANTES
de tocar nada, tal como pide el prompt maestro ("ejecutar tests
actuales, registrar baseline"). Resultado real: **1 test fallo**, no
257/257 como decia la documentacion previa -- **bug real preexistente,
no causado por esta fase**: los nodos `Documentation` del grafo
(`project_knowledge_graph.knowledge_graph.enrichers.documentation`)
guardan su `file` relativo al repo GIT completo, no a `WORKSPACE_ROOT` --
`ai_editor.planner.validator.validate_plan()` nunca podia resolver esos
paths contra el disco real (probaba solo `WORKSPACE_ROOT`/
`FRONTEND_SRC_ROOT`), bloqueando CUALQUIER plan que incluyera una
referencia de documentacion fuera de `ecommerce_sintel/` (ej.
`Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md`, que vive
un nivel arriba). Corregido SIN TOCAR `project_knowledge_graph`
(consistente con la regla de no reabrir fases cerradas): se agrego
`ai_editor.workspace.REPO_ROOT`/`resolve_repo_doc_path()` (solo lectura,
nunca escribible) y `validate_plan()` ahora degrada este caso especifico
a WARNING en vez de BLOCKED cuando el `.md` referenciado SI existe bajo
`REPO_ROOT` (ver `AI_EDITOR_BASELINE.md` para el detalle completo). 6
tests nuevos de regresion. **Baseline real confirmado: 263/263.**

## Checkpoint (FASE 24-28, primera ejecucion)

```
========================================
AI EDITOR -- FASE 24-28 (primera ejecucion) [ver FASE 29 abajo]
========================================

Estado:
PASS

Objetivo:
Auditar el estado real de ai_editor/ (llm/planner/patch/resolver/
validation/graph_client) y construir el AI Change Proposal Engine
minimo: ChangeGenerationRequest -> LLM -> PatchProposal estructurada,
SIN aplicar el patch.

Implementado:
- FASE 24: auditoria completa (ver arriba) + bug real encontrado y
  corregido en el propio baseline + scaffold ai_editor/generation/
  + este documento.
- FASE 25: 6 dataclasses reales en generation/models.py
  (ChangeGenerationRequest/PatchProposal/PatchOperation/GenerationResult/
  GenerationIssue/GenerationConfidence) -- ninguna representa un patch
  como string libre.
- FASE 26: build_generation_context()/build_source_context()/
  build_architecture_context() en generation/context.py -- probado
  contra el repo real (EquipmentViewSet.check_availability, renting).
- FASE 27: build_prompt() en generation/prompts.py -- 8 estrategias
  segun tipo de cambio real (backend/frontend/api/tests/documentation/
  configuration/cross-stack/unknown), determinista.
- FASE 28: generate_patch_proposal() en generation/generator.py +
  validators.py -- JSON estructurado o REJECT, nunca reparado en
  silencio. Probado con LLM mockeado (4 escenarios: JSON valido, JSON
  con fence markdown, texto libre, fallo de red).

Archivos modificados:
- ai_editor/workspace.py (REPO_ROOT, resolve_repo_doc_path -- fix del
  baseline)
- ai_editor/planner/validator.py (degradar a warning el caso
  Documentation-fuera-de-WORKSPACE_ROOT)
- ai_editor/__init__.py (docstring actualizado, 11 submodulos)
- project_knowledge_graph/tests/test_ai_editor_workspace_and_validator.py
  (6 tests nuevos del fix)
- project_knowledge_graph/tests/test_ai_editor_scaffold.py (expected set
  incluye 'generation')

Archivos nuevos:
- ai_editor/generation/__init__.py
- ai_editor/generation/models.py
- ai_editor/generation/context.py
- ai_editor/generation/prompts.py
- ai_editor/generation/generator.py
- ai_editor/generation/validators.py
- ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md (este documento)
- project_knowledge_graph/tests/test_ai_editor_generation_models.py
- project_knowledge_graph/tests/test_ai_editor_generation_context.py
- project_knowledge_graph/tests/test_ai_editor_generation_prompts.py
- project_knowledge_graph/tests/test_ai_editor_generation_validators.py
- project_knowledge_graph/tests/test_ai_editor_generation_generator.py

Funciones nuevas (principales):
build_generation_context(), build_source_context(),
build_architecture_context(), build_prompt(), generate_patch_proposal(),
extract_json(), validate_raw_schema(), resolve_repo_doc_path()

Modelos nuevos:
ChangeGenerationRequest, PatchProposal, PatchOperation, GenerationResult,
GenerationIssue, GenerationConfidence

Tests:
308/308 (suite completa project_knowledge_graph/tests/)

Tests anteriores:
257 documentados -> 263 reales al arrancar (bug de baseline corregido +
6 tests de regresion, ver "Baseline" arriba)

Tests nuevos:
45 (generation/: 8 models + 12 context + 9 prompts + 13 validators + 6
generator + ajuste de 1 test de scaffold preexistente)

LLM utilizado:
Ninguno real -- mockeado en los 6 tests de generator.py (4 escenarios
reales de forma/comportamiento, no de calidad de generacion).

Contexto enviado:
Verificado real contra EquipmentViewSet.check_availability (renting):
graph_context compactado (13 claves, stats.relevant_nodes << stats.
total_graph_nodes), source_context con solo 33 lineas reales (rango
151-168 + margen, no el archivo completo de renting/api/views.py),
architecture_context con el doc real de renting
(ARQUITECTURA_COMPLETA_RENTIG.md) y las 5 reglas globales reales de
MEMORY.md.

Propuesta generada:
No aplicable en este checkpoint (sin LLM real corrido) -- el mecanismo
de generar/validar/rechazar SI se probo de punta a punta con datos
sinteticos de LLM sobre contexto real.

Problemas:
1 bug real preexistente encontrado y corregido en el baseline (ver
seccion "Baseline" arriba) -- unico problema real de esta fase.

Riesgos:
Una PatchProposal con status=PROPOSED de esta fase NO es segura para
aplicar todavia -- falta FASE 29 (validacion contra el repo real).
Nadie debe conectar generation/ con patch/repository sin construir esa
fase primero.

Regresiones:
Ninguna -- 308/308 (263 base + 45 nuevos).

Documentacion:
ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md (este documento),
ai_editor/__init__.py actualizado.

Siguiente fase:
FASE 29 "Patch Proposal Validator" -- validar una PatchProposal CONTRA
el repo real (archivo existe, old_content coincide, scope permitido,
no toca archivos fuera del ChangePlan) antes de considerar conectarla
con el Patch Engine (FASE 31).
```

## Checkpoint (FASE 29)

```
========================================
AI EDITOR -- FASE 29
========================================

Estado:
PASS

Objetivo:
Validar una PatchProposal (FASE 25/28) CONTRA el estado real del repo/
plan ANTES de que pueda llegar al Patch Engine -- archivo existe, simbolo/
step existe, operacion permitida, old_content coincide, hash coincide,
new_content no vacio, lineas validas, scope permitido, mas los 6 checks
de "VALIDAR TAMBIEN" (fuera del plan, dependencias inesperadas -- NO
implementado, eliminacion no relacionada, contratos no declarados,
archivos sensibles, limites).

Implementado:
ai_editor/generation/proposal_validator.py::validate_proposal_against_repo()
-- 13 de los 14 checks que pide el prompt maestro (uno, "dependencias
inesperadas", documentado como NO implementado a proposito, ver
"Limitaciones"). Reusa `patch.fingerprint` (mismo hash que el Patch
Engine real) y `repository.sandbox._SENSITIVE_PATTERNS` (misma lista que
protege el sandbox) en vez de reimplementar cualquiera de las dos.

Archivos nuevos:
- ai_editor/generation/proposal_validator.py
- project_knowledge_graph/tests/test_ai_editor_generation_proposal_validator.py

Archivos modificados:
- ai_editor/generation/__init__.py (exporta validate_proposal_against_repo)
- ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md (esta seccion)

Funciones nuevas:
validate_proposal_against_repo(), mas 6 helpers internos
(_find_matching_step/_check_scope_and_operation/_check_file_and_content/
_check_content_size_and_shrink/_check_sensitive_file/
_check_undeclared_contract)

Tests:
320/320 (suite completa project_knowledge_graph/tests/)

Tests anteriores:
308 (FASE 24-28)

Tests nuevos:
12 (proposal_validator: contenido exacto real, old_content roto, hash
roto, fuera del plan, archivo sensible, REVIEW-como-MODIFY, demasiadas
operaciones, new_content vacio, shrink sospechoso como warning no error,
ADD sin old_content, archivo inexistente, funciona sin context opcional)

LLM utilizado:
Ninguno -- este modulo no llama al LLM, valida una PatchProposal ya
construida.

Contexto enviado:
No aplica (este modulo no arma prompts).

Propuesta generada:
No aplica -- validado con propuestas SINTETICAS (construidas a mano en
los tests) pero contra CONTEXTO/PLAN/REPO reales
(HomeCardGroupSelector.get_by_name en core/services/commands.py, y
EquipmentViewSet.check_availability en renting para el caso REVIEW-como-
MODIFY).

Problemas:
Ninguno encontrado en esta fase (a diferencia de FASE 24, que si
encontro un bug real en el baseline).

Riesgos:
"Dependencias inesperadas" queda sin verificar -- una propuesta que
agrega un import problematico pasa esta validacion igual si el resto es
correcto. Documentado explicitamente, no un gap oculto (ver
"Limitaciones" arriba).

Regresiones:
Ninguna -- 320/320 (308 + 12 nuevos).

Documentacion:
Esta seccion + seccion "FASE 29 -- Patch Proposal Validator" arriba +
ai_editor/generation/__init__.py actualizado.

Siguiente fase:
FASE 30 "Generation Retry Engine" (regeneracion controlada, maximo 3
intentos, cada uno explicando el error anterior) o FASE 31 "Patch Engine
Integration" (conectar generation/ con patch/repository real) -- ninguna
construida todavia, requieren decision explicita de por cual seguir.
```

## Checkpoint (FASE 30)

```
========================================
AI EDITOR -- FASE 30
========================================

Estado:
PASS

Objetivo:
Regeneracion controlada cuando una propuesta falla FASE 28 (forma) o
FASE 29 (contra el repo real) -- maximo 3 intentos configurable, cada
uno explicando al LLM que fallo antes para que no repita el mismo error.

Implementado:
ai_editor/generation/retry.py::generate_with_retry() -- orquesta
generator+proposal_validator en un loop de hasta max_retries intentos.
prompts.build_prompt() extendido con previous_attempts (seccion nueva
PREVIOUS_ATTEMPTS_FEEDBACK). generator.generate_patch_proposal()
extendido para reenviar ese parametro. Nuevos modelos RetryAttempt/
RetryOutcome en generation/models.py.

Archivos nuevos:
- ai_editor/generation/retry.py
- project_knowledge_graph/tests/test_ai_editor_generation_retry.py

Archivos modificados:
- ai_editor/generation/models.py (RetryAttempt, RetryOutcome)
- ai_editor/generation/prompts.py (build_prompt acepta previous_attempts)
- ai_editor/generation/generator.py (generate_patch_proposal acepta
  previous_attempts, lo reenvia a build_prompt)
- ai_editor/generation/__init__.py (exporta generate_with_retry,
  DEFAULT_MAX_RETRIES, RetryAttempt, RetryOutcome)
- ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md (esta seccion + seccion
  "FASE 30" arriba + limitaciones actualizadas)

Funciones nuevas:
generate_with_retry(), _build_correction_note()

Modelos nuevos:
RetryAttempt, RetryOutcome

Tests:
327/327 (suite completa project_knowledge_graph/tests/)

Tests anteriores:
320 (FASE 24-29)

Tests nuevos:
7 (exito en primer intento sin retry, fail-fail-pass en 3 intentos
exacto al ejemplo del prompt maestro, agotar 3 intentos sin exito,
verificacion de que la correccion realmente llega al prompt del intento
2, fallo de red no consume nota de correccion, DEFAULT_MAX_RETRIES==3,
nunca importa patch.engine/repository)

LLM utilizado:
Ninguno real -- secuencia de respuestas mockeadas (side_effect) sobre
contexto/plan real (HomeCardGroupSelector.get_by_name).

Contexto enviado:
El mismo ChangeGenerationRequest real de FASE 26-28, mas
PREVIOUS_ATTEMPTS_FEEDBACK inyectado a partir del segundo intento en
adelante -- verificado que el codigo de issue real del intento anterior
(OLD_CONTENT_MISMATCH) efectivamente aparece en el texto que recibe el
LLM en el intento siguiente.

Propuesta generada:
No aplica -- propuestas sinteticas en los tests, comportamiento del loop
de retry es lo que se prueba, no la calidad de una generacion real.

Problemas:
Ninguno.

Riesgos:
Igual que FASE 29 -- una PatchProposal exitosa via retry sigue sin poder
aplicarse, no hay integracion con el Patch Engine todavia.

Regresiones:
Ninguna -- 327/327 (320 + 7 nuevos).

Documentacion:
Esta seccion + seccion "FASE 30 -- Generation Retry Engine" arriba +
limitaciones actualizadas + ai_editor/generation/__init__.py actualizado.

Siguiente fase:
FASE 31 "Patch Engine Integration" -- conectar generation/ con
patch/repository reales, el primer paso hacia que una PatchProposal
pueda terminar aplicandose sobre un sandbox (nunca directo, siempre
detras de validacion+aprobacion humana).
```

## Checkpoint (FASE 31)

```
========================================
AI EDITOR -- FASE 31
========================================

Estado:
PASS

Objetivo:
Conectar el AI Change Proposal Engine con el Patch Engine real -- una
PatchProposal (FASE 25/28) validada (FASE 29) debe poder aplicarse
sobre un Sandbox real (POST-GRAPH 7), sin confiar ciegamente en el LLM
(re-validar path/hash/scope/symbol/operation), y sin llegar nunca a
WORKSPACE_ROOT.

Implementado:
ai_editor/generation/patch_integration.py::apply_proposal_to_sandbox()
-- re-valida (FASE 29) + convierte generation.models.PatchOperation ->
patch.schema.PatchOperation real + aplica cada una via
patch.engine.apply_operation() sobre un sandbox YA CREADO por el
caller, fail-fast en el primer fallo. find_matching_step() de
proposal_validator.py se hizo publica (antes _privada) para reusarla
tal cual en vez de duplicar el emparejamiento operacion<->step.

Archivos nuevos:
- ai_editor/generation/patch_integration.py
- project_knowledge_graph/tests/test_ai_editor_generation_patch_integration.py

Archivos modificados:
- ai_editor/generation/models.py (PatchApplicationResult)
- ai_editor/generation/proposal_validator.py (find_matching_step publica)
- ai_editor/generation/__init__.py (exporta apply_proposal_to_sandbox,
  PatchApplicationResult; docstring actualizado)
- ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md (esta seccion + seccion
  "FASE 31" arriba + Responsabilidad/Flujo real/Limitaciones actualizados)

Funciones nuevas:
apply_proposal_to_sandbox(), _convert_to_engine_operation()

Modelos nuevos:
PatchApplicationResult

Tests:
333/333 (suite completa project_knowledge_graph/tests/)

Tests anteriores:
327 (FASE 24-30)

Tests nuevos:
6 (MODIFY valido aplica sobre sandbox y deja el repo real intacto,
propuesta invalida se rechaza ANTES de tocar el sandbox, guardrail de
apply_operation rechaza un 'sandbox' que apunta a WORKSPACE_ROOT, 2
operaciones sobre el mismo rango detienen en la primera que falla, ADD
inserta en line_end+1, nunca llama a promote_to_workspace)

LLM utilizado:
Ninguno -- este modulo no llama al LLM, aplica una PatchProposal ya
construida (por generator.py o retry.py, en pasos anteriores).

Contexto enviado:
No aplica (este modulo no arma prompts).

Propuesta generada:
No aplica al LLM -- propuestas construidas a mano en los tests, pero
aplicadas sobre un Sandbox REAL (create_sandbox(plan) real) contra
HomeCardGroupSelector.get_by_name (core/services/commands.py) --
verificado byte a byte que el archivo REAL del repo queda identico
antes y despues.

Problemas:
1 bug real encontrado y corregido DENTRO de esta misma fase (no
preexistente): old_fingerprint se calculaba releyendo el sandbox en el
momento de convertir cada operacion, anulando la deteccion de drift
entre operaciones de una misma propuesta -- ver seccion "FASE 31"
arriba para el detalle completo y el test que lo detecto.

Riesgos:
Ninguno nuevo mas alla de los ya documentados (FASE 29: "dependencias
inesperadas" sin verificar). El propio mecanismo de aplicacion es
estrictamente mas seguro que antes: 2 capas de re-validacion
independientes antes de escribir cualquier byte.

Regresiones:
Ninguna -- 333/333 (327 + 6 nuevos).

Documentacion:
Esta seccion + seccion "FASE 31 -- Patch Engine Integration" arriba +
Responsabilidad/Flujo real/Limitaciones actualizados +
ai_editor/generation/__init__.py actualizado.

Siguiente fase:
Sin decision tomada todavia -- candidatas naturales: FASE 32 "Sandbox
Generation Loop" (probar el codigo generado ANTES de aprobacion, ya
cubierto en gran parte por validation.engine existente), FASE 33
"Automated Test Impact Execution", o saltar directo a encadenar
generation/ con validation/approval/repository ya existentes en un
flujo unico (mencionado como limitacion arriba) -- requiere decision
explicita del usuario.
```

## Checkpoint (FASE 32)

```
========================================
AI EDITOR -- FASE 32
========================================

Estado:
PASS

Objetivo:
Permitir que el codigo generado se pruebe ANTES de aprobacion -- flujo
PatchProposal -> Sandbox -> Apply -> Syntax Validation -> Tests, con el
repositorio principal intacto en todo momento.

Implementado:
ai_editor/generation/sandbox_loop.py::run_sandbox_validation_loop() --
encadena create_sandbox() (POST-GRAPH 7) + apply_proposal_to_sandbox()
(FASE 31) + run_validation() (POST-GRAPH 8, sintaxis) +
build_test_validation_report() (POST-GRAPH 10) en un unico ciclo,
devolviendo SandboxLoopResult.ready_for_approval. Cero logica de
validacion nueva -- solo orquestacion de piezas ya reales.

Archivos nuevos:
- ai_editor/generation/sandbox_loop.py
- project_knowledge_graph/tests/test_ai_editor_generation_sandbox_loop.py

Archivos modificados:
- ai_editor/generation/__init__.py (exporta run_sandbox_validation_loop,
  SandboxLoopResult; docstring actualizado)
- ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md (esta seccion + seccion
  "FASE 32" arriba + limitaciones actualizadas)

Funciones nuevas:
run_sandbox_validation_loop()

Modelos nuevos:
SandboxLoopResult

Tests:
338/338 (suite completa project_knowledge_graph/tests/)

Tests anteriores:
333 (FASE 24-31)

Tests nuevos:
5 (propuesta valida -> applied+sintaxis OK+ready; sintaxis rota se
aplica pero falla validacion y no queda ready -- mismo patron que
ocurrio de verdad en POST-GRAPH 21; propuesta que falla pre-validacion
nunca llega a run_validation; funciona sin context (test_report=None);
to_dict() serializa objetos anidados)

LLM utilizado:
Ninguno -- este modulo no llama al LLM, prueba una PatchProposal ya
construida.

Contexto enviado:
No aplica (este modulo no arma prompts).

Propuesta generada:
No aplica al LLM -- 3 propuestas construidas a mano en los tests
(valida, sintaxis rota, pre-validacion fallida), todas aplicadas sobre
un Sandbox real, WORKSPACE_ROOT verificado intacto en los 3 casos.

Problemas:
Ninguno.

Riesgos:
`ready_for_approval=True` puede malinterpretarse como "listo para
promover" si un caller futuro no lee la documentacion -- documentado
explicitamente que solo significa "aplico + sintaxis valida", nunca
aprobacion humana ni tests reales pasando.

Regresiones:
Ninguna -- 338/338 (333 + 5 nuevos).

Documentacion:
Esta seccion + seccion "FASE 32 -- Sandbox Generation Loop" arriba +
limitaciones actualizadas + ai_editor/generation/__init__.py actualizado.

Siguiente fase:
Sin decision tomada -- candidatas: FASE 33 "Automated Test Impact
Execution" (clasificar tests sobre el resultado de FASE 32, ya cubierto
en gran parte por build_test_validation_report existente), o encadenar
generation/ con approval/repository.promote_to_workspace() en un flujo
unico (limitacion documentada arriba).
```

## Checkpoint (Cadena de promocion -- `promotion.py`)

```
========================================
AI EDITOR -- Cadena de promocion (generation -> approval -> promote)
========================================

Estado:
PASS

Objetivo:
Encadenar generation/ (FASE 24-32) con approval/ (POST-GRAPH 11) y
repository.promote_to_workspace() (POST-GRAPH 12) -- pedido explicito
del usuario tras el checkpoint de FASE 32 ("continua con encadenar
generation"). NUNCA permitir LLM -> WRITE -> PRODUCTION -- decision/
confirm deben venir de una revision humana real.

Implementado:
ai_editor/generation/promotion.py::review_and_promote() -- compone
ChangeSummary (POST-GRAPH 11) a partir de un SandboxLoopResult (FASE
32), exige una decision humana real, y solo si es APPROVE+confirm=True
llama a promote_to_workspace() (POST-GRAPH 12/20) con todos sus
guardrails intactos.

Archivos nuevos:
- ai_editor/generation/promotion.py
- project_knowledge_graph/tests/test_ai_editor_generation_promotion.py

Archivos modificados:
- ai_editor/generation/__init__.py (exporta review_and_promote,
  PromotionOutcome; docstring actualizado)
- ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md (esta seccion + seccion
  "Cadena de promocion" arriba + limitaciones actualizadas)

Funciones nuevas:
review_and_promote()

Modelos nuevos:
PromotionOutcome

Tests:
346/346 (suite completa project_knowledge_graph/tests/)

Tests anteriores:
338 (FASE 24-32)

Tests nuevos:
8 (bloquea si ready_for_approval=False sin pedir decision; REJECT nunca
llega a promote_to_workspace; APPROVE sin confirm=True queda
NOT_CONFIRMED; APPROVE+confirm=True promueve de verdad sobre
fake_workspace; decision invalida lanza ValueError; guardrail de
POST-GRAPH 20 sigue bloqueando aunque ready_for_approval fuera
incorrectamente True; ChangeSummary refleja el plan/context reales;
nunca importa ai_editor.llm)

LLM utilizado:
Ninguno -- esta funcion opera sobre resultados YA generados/validados.

Contexto enviado:
No aplica (esta funcion no arma prompts).

Propuesta generada:
No aplica al LLM -- 1 sandbox sintetico reusado en los 8 escenarios,
promovido de verdad SOLO sobre fake_workspace (tmp_path). Nunca
invocado contra ai_editor.workspace.WORKSPACE_ROOT real en esta sesion
-- mismo criterio que toda la suite de POST-GRAPH 12/20/21.

Problemas:
Ninguno.

Riesgos:
Ninguno nuevo -- esta funcion no relaja ningun guardrail existente,
solo los encadena. El riesgo real (que alguien la invoque contra
WORKSPACE_ROOT sin una decision humana genuina) es exactamente el mismo
riesgo que promote_to_workspace() ya mitiga por su cuenta desde
POST-GRAPH 12.

Regresiones:
Ninguna -- 346/346 (338 + 8 nuevos).

Documentacion:
Esta seccion + seccion "Cadena de promocion -- promotion.py" arriba +
limitaciones actualizadas + ai_editor/generation/__init__.py actualizado.

Siguiente fase:
Sin decision tomada -- el pipeline generation -> approval -> promote
esta completo a nivel de MECANISMO (nunca invocado contra el repo real
en esta sesion). Candidatas: probar el flujo completo contra el repo
real (requeriria la misma confirmacion explicita fresca que
POST-GRAPH 21), FASE 33 "Automated Test Impact Execution", o continuar
con fases posteriores del plan de 60 (34+).
```

## Checkpoint (FASE 33-36, batch)

```
========================================
AI EDITOR -- FASE 33, 34, 35, 36 (batch)
========================================

Estado:
PASS

Objetivo:
FASE 33 "Automated Test Impact Execution" (reporte consolidado), FASE 34
"Graph Reconciliation" (version scope), FASE 35 "Impact Recheck" (drift
del grafo), FASE 36 "Code Quality Validation" (bandit real) -- pedido
explicito del usuario de continuar en batch, tests formales al final.

Implementado:
- generation/validation_report.py::build_generation_validation_report()
- generation/reconciliation.py::reconcile_change_scope()
- generation/impact_recheck.py::capture_impact_baseline()/recheck_impact()
- generation/code_quality.py::run_code_quality_checks()

Archivos nuevos:
- ai_editor/generation/validation_report.py
- ai_editor/generation/reconciliation.py
- ai_editor/generation/impact_recheck.py
- ai_editor/generation/code_quality.py
- project_knowledge_graph/tests/test_ai_editor_generation_validation_report.py
- project_knowledge_graph/tests/test_ai_editor_generation_reconciliation.py
- project_knowledge_graph/tests/test_ai_editor_generation_impact_recheck.py
- project_knowledge_graph/tests/test_ai_editor_generation_code_quality.py

Archivos modificados:
- ai_editor/generation/__init__.py (exporta las 4 fases nuevas, docstring
  actualizado)
- ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md (esta seccion + seccion
  "FASE 33-36" arriba)

Funciones nuevas:
build_generation_validation_report(), reconcile_change_scope(),
capture_impact_baseline(), recheck_impact(), run_code_quality_checks()

Modelos nuevos:
GenerationValidationReport, GraphReconciliationReport, ImpactBaseline,
ImpactRecheckReport, CodeQualityReport, ToolCheckResult

Tests:
367/367 (suite completa project_knowledge_graph/tests/)

Tests anteriores:
346 (hasta la cadena de promocion)

Tests nuevos:
21 (5 FASE 33 + 5 FASE 34 + 7 FASE 35 + 4 FASE 36)

LLM utilizado:
Ninguno en FASE 33-35 (agregacion/comparacion de datos ya reales). FASE
36 SI ejecuta una herramienta externa real (`bandit`, no un LLM).

Contexto enviado:
No aplica (ninguna de las 4 fases arma prompts).

Propuesta generada:
No aplica al LLM -- todas probadas con propuestas construidas a mano
pero contra CONTEXTO/PLAN/GRAFO/SANDBOX/BANDIT reales (`HomeCardGroupSelector.
get_by_name`, `EquipmentViewSet.check_availability`).

Problemas:
2 bugs reales encontrados y corregidos DENTRO de este mismo batch (no
preexistentes): (1) FASE 35 aproximaba el impacto predicho de forma que
subestimaba sistematicamente el real, produciendo falsos BLOCK siempre
-- corregido con un baseline capturado via una llamada real a
`calculate_impact()`. (2) FASE 36 reportaba `PASS` cuando ningun linter
real habia corrido (`NOT_CONFIGURED` en todos los checks) -- corregido
para exigir al menos un check real ejecutado.

Riesgos:
Ninguno nuevo -- las 4 fases son de solo lectura/reporte (excepto FASE
36, que ejecuta `bandit` real pero nunca escribe). Ningun cambio a los
guardrails de escritura existentes.

Regresiones:
Ninguna -- 367/367 (346 + 21 nuevos).

Documentacion:
Esta seccion + seccion "FASE 33-36" arriba + ai_editor/generation/__init__.py
actualizado.

Siguiente fase:
Sin decision tomada -- 33 de las 60 fases del plan cubiertas (24-36 mas
la cadena de promocion). Candidatas naturales: FASE 37 "Architectural
Compliance", FASE 38 "Cross-Stack Generation", o pausar y consolidar.
```

## Checkpoint (FASE 37)

```
========================================
AI EDITOR -- FASE 37
========================================

Estado:
PASS

Objetivo:
Validar que el codigo generado sea compatible con la arquitectura
SINTEL, sin inventar reglas -- usar documentacion arquitectonica
existente como fuente.

Implementado:
generation/architecture_compliance.py::check_architectural_compliance()
-- 4 checks heuristicos (regex), cada uno citando la regla real y su
fuente documental exacta. 2 items del prompt maestro ("tenant
boundaries", "shared components") documentados honestamente como no
aplicables/fuera de alcance, no fabricados.

Archivos nuevos:
- ai_editor/generation/architecture_compliance.py
- project_knowledge_graph/tests/test_ai_editor_generation_architecture_compliance.py

Archivos modificados:
- ai_editor/generation/__init__.py (exporta check_architectural_compliance,
  ArchitecturalComplianceReport; docstring actualizado)
- ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md (esta seccion + seccion
  "FASE 37" arriba)

Funciones nuevas:
check_architectural_compliance()

Modelos nuevos:
ArchitecturalComplianceReport, ComplianceIssue

Tests:
376/376 (suite completa project_knowledge_graph/tests/)

Tests anteriores:
367 (hasta FASE 36)

Tests nuevos:
9 (Selector con .save() -> FAIL; Selector limpio -> PASS; ViewSet con
ORM directo -> WARNING no bloqueante; import DRF de IsAdminUser -> FAIL;
axios directo en .vue -> FAIL; cambio backend limpio -> PASS; tenant/
shared components documentados honestamente; archivo no relacionado no
dispara ningun check; to_dict serializa issues+not_implemented)

LLM utilizado:
Ninguno -- valida contenido ya generado, no genera ni llama al LLM.

Contexto enviado:
No aplica.

Propuesta generada:
No aplica al LLM -- 6 propuestas sinteticas en los tests, cada una
dirigida a activar (o confirmar que NO se activa) un check especifico.

Problemas:
Ninguno encontrado en esta fase.

Riesgos:
Checks heuristicos (regex) pueden tener falsos negativos reales (un
patron que la regex no reconozca) -- documentado explicitamente, no
oculto. El check de ViewSet+ORM es deliberadamente WARNING (no ERROR)
por el mismo riesgo de falso positivo (un comentario que mencione
'.objects.' sin ser una llamada real).

Regresiones:
Ninguna -- 376/376 (367 + 9 nuevos).

Documentacion:
Esta seccion + seccion "FASE 37 -- Architectural Compliance" arriba +
ai_editor/generation/__init__.py actualizado.

Siguiente fase:
FASE 38 "Cross-Stack Generation" es la candidata natural, pero requiere
una decision arquitectonica real: HOY `proposal_validator.
_check_scope_and_operation()` (FASE 29) rechaza CUALQUIER operacion de
escritura sobre un step que no sea el `MODIFY` principal (step 1) --
es decir, una propuesta JAMAS puede tocar mas de un archivo real hoy,
sin importar que `PatchProposal.operations` ya soporte una lista.
Habilitar cross-stack de verdad significa relajar ESE guardrail
especifico (FASE 29, ya cerrada y testeada) -- no se hace sin
confirmacion explicita del usuario, dado el criterio de seguridad de
toda esta sesion.
```

## Checkpoint (FASE 38)

```
========================================
AI EDITOR -- FASE 38
========================================

Estado:
PASS

Objetivo:
Permitir que una unica solicitud produzca modificaciones coordinadas
(Frontend + API + Backend + Tests) -- requiere relajar el guardrail de
FASE 29 que hoy limita cada propuesta a 1 solo archivo real.

Implementado:
Relajacion ACOTADA de proposal_validator._check_scope_and_operation()
(MODIFY + REVIEW no-documentacion + RUN, documentacion sigue bloqueada)
+ downgrade de UNDECLARED_CONTRACT_CHANGE a WARNING +
reconciliation.py filtra por severidad ERROR + context.py extiende
build_source_context() a los mismos steps ahora escribibles. Los 4
cambios son necesarios en conjunto -- ninguno por separado habilita
cross-stack de forma util.

Archivos modificados:
- ai_editor/generation/proposal_validator.py (relajacion + fix de un
  bug latente real en el bypass de DELETE, no nuevo de esta fase)
- ai_editor/generation/reconciliation.py (filtro por severidad ERROR)
- ai_editor/generation/context.py (build_source_context extendido)
- project_knowledge_graph/tests/test_ai_editor_generation_proposal_validator.py
  (1 test reemplazado por 3: escritura permitida en REVIEW no-doc,
  bloqueada en REVIEW-doc, permitida en RUN)
- project_knowledge_graph/tests/test_ai_editor_generation_context.py
  (1 test actualizado a la nueva cobertura de steps)
- project_knowledge_graph/tests/test_ai_editor_generation_patch_integration.py
  (1 test nuevo: cross-stack real de 2 archivos end-to-end)
- ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md (esta seccion + seccion
  "FASE 38" arriba)

Funciones nuevas:
Ninguna -- esta fase modifica funciones YA existentes de fases cerradas
(FASE 26, FASE 29, FASE 34), con confirmacion explicita.

Modelos nuevos:
Ninguno.

Tests:
379/379 (suite completa project_knowledge_graph/tests/)

Tests anteriores:
376 (hasta FASE 37)

Tests nuevos/modificados:
3 nuevos + 1 reemplazado en proposal_validator (neto +2), 1 actualizado
en context, 1 nuevo end-to-end en patch_integration (neto +1) = 379
total.

LLM utilizado:
Ninguno -- toda la verificacion fue con propuestas construidas a mano
contra datos reales.

Contexto enviado:
Medido real (no estimado): para EquipmentViewSet.check_availability
(alto riesgo, 16 nodos relacionados), build_source_context() extendido
lee ~19.6K caracteres distribuidos en 17 targets -- documentado, no
limitado artificialmente (FASE 56 "Performance" es donde correspondera
optimizar, solo despues de medir).

Propuesta generada:
No aplica al LLM -- verificado end-to-end con una propuesta real de 2
operaciones (renting/api/views.py + RentalDetailView.vue) aplicada
sobre el MISMO sandbox, ambas APPLIED, sintaxis Nivel 1 OK,
ready_for_approval=True, checkout real byte-a-byte identico despues en
ambos archivos.

Problemas:
1 bug latente real encontrado (no nuevo de esta fase, preexistente
desde FASE 29): la condicion original de `_check_scope_and_operation()`
eximia CUALQUIER operacion DELETE del chequeo de scope, sin importar el
step -- nunca se exploto (nada generaba DELETE sobre un REVIEW step
todavia) pero era un agujero real. Corregido como parte de la
reescritura de esta fase.

Riesgos:
La relajacion es deliberadamente ACOTADA (solo steps que el grafo YA
vinculo como reales, nunca "cualquier archivo") -- pero SI amplia la
superficie de escritura real de todo el sistema, confirmado
explicitamente por el usuario en 2 pasos antes de tocar codigo. El
downgrade de UNDECLARED_CONTRACT_CHANGE a WARNING significa que un
cambio de contrato ya no bloquea solo -- queda visible en el reporte
(FASE 33/41), la decision de bloquear pasa a ser humana (Human Approval
Gate, POST-GRAPH 11), consistente con el resto del sistema.

Regresiones:
Ninguna funcional -- 379/379. 1 test de comportamiento ANTERIOR
reemplazado deliberadamente (el comportamiento que probaba ya no es el
esperado, documentado arriba).

Documentacion:
Esta seccion + seccion "FASE 38 -- Cross-Stack Generation" arriba.

Siguiente fase:
Sin decision tomada -- FASE 39 "Multi-file Patch Proposal" ya esta
sustancialmente cubierta (una PatchProposal siempre soporto multiples
operaciones desde FASE 25, y FASE 38 acaba de probarlo end-to-end).
Candidatas reales: FASE 40 "Dependency-Aware Generation", FASE 41
"Contract-Aware Generation" (profundizar mas alla del WARNING actual),
o pausar y consolidar -- 34 de las 60 fases del plan cubiertas.
```

## Checkpoint (FASE 40-41)

```
========================================
AI EDITOR -- FASE 40, 41
========================================

Estado:
PASS

Objetivo:
FASE 40: el LLM/la propuesta no debe introducir dependencias hacia
`ai_engine` (module boundary real). FASE 41: si un cambio afecta un
contrato, verificar consumidores/tests conocidos, sin permitir que
cambie silenciosamente.

Implementado:
- generation/dependency_awareness.py::check_dependency_awareness()
- generation/contract_awareness.py::check_contract_coverage()

Archivos nuevos:
- ai_editor/generation/dependency_awareness.py
- ai_editor/generation/contract_awareness.py
- project_knowledge_graph/tests/test_ai_editor_generation_dependency_awareness.py
- project_knowledge_graph/tests/test_ai_editor_generation_contract_awareness.py

Archivos modificados:
- ai_editor/generation/__init__.py (exporta ambas funciones + reports;
  docstring actualizado)
- ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md (esta seccion + seccion
  "FASE 40-41" arriba)

Funciones nuevas:
check_dependency_awareness(), check_contract_coverage()

Modelos nuevos:
DependencyIssue, DependencyAwarenessReport, ContractCoverageReport

Tests:
390/390 (suite completa project_knowledge_graph/tests/)

Tests anteriores:
379 (hasta FASE 38)

Tests nuevos:
11 (7 FASE 40 + 4 FASE 41)

LLM utilizado:
Ninguno -- ambas fases validan/comparan datos ya reales (propuesta +
grafo), no llaman al LLM.

Contexto enviado:
No aplica.

Propuesta generada:
No aplica al LLM -- verificado con propuestas construidas a mano contra
PLAN/CONTEXTO/GRAFO reales (EquipmentViewSet.check_availability para
FASE 41, casos sinteticos de imports para FASE 40 dado que esta fase no
depende del grafo).

Problemas:
Ninguno encontrado en este batch.

Riesgos:
Ninguno nuevo -- ambas fases son de solo lectura/reporte, nunca
escriben ni relajan ningun guardrail de escritura existente.

Regresiones:
Ninguna -- 390/390 (379 + 11 nuevos).

Documentacion:
Esta seccion + seccion "FASE 40-41" arriba + ai_editor/generation/
__init__.py actualizado.

Siguiente fase:
Sin decision tomada -- 36 de las 60 fases del plan cubiertas (24-38,
40-41, mas la cadena de promocion). FASE 39 ya cubierta implicitamente
por FASE 38. Candidatas: FASE 42 "Test-Aware Generation" (ya cubierta
en gran parte por tests_to_update + FASE 41), FASE 44 "Confidence
Engine" (profundizar GenerationConfidence mas alla del auto-reporte del
LLM), o pausar y consolidar.
```

## Checkpoint (FASE 42-44)

```
========================================
AI EDITOR -- FASE 42, 43, 44
========================================

Estado: PASS

Implementado:
- models.py: PatchProposal += tests_to_add/tests_to_remove/documentation_to_update
  (default [], retrocompatible) + prompts.py/generator.py/validators.py actualizados
- test_awareness.py::check_test_awareness()
- documentation_awareness.py::check_documentation_awareness()
- confidence_engine.py::compute_composite_confidence()

Archivos nuevos:
- ai_editor/generation/test_awareness.py
- ai_editor/generation/documentation_awareness.py
- ai_editor/generation/confidence_engine.py
- project_knowledge_graph/tests/test_ai_editor_generation_test_awareness.py
- project_knowledge_graph/tests/test_ai_editor_generation_documentation_awareness.py
- project_knowledge_graph/tests/test_ai_editor_generation_confidence_engine.py

Archivos modificados:
- ai_editor/generation/models.py, generator.py, prompts.py, validators.py, __init__.py

Tests: 404/404 (390 + 14 nuevos). Regresiones: 0.

Documentacion: esta seccion + seccion "FASE 42-44" arriba.

Siguiente: FASE 45 "Human Review UI/CLI" (render de texto, sin UI real) +
FASE 46 "Promotion Gate" (consolidar TODOS los reportes nuevos como
gate antes de review_and_promote) -- candidatas naturales para
encadenar todo lo construido en un unico punto de decision humana.
```

## Checkpoint (FASE 45-46)

```
========================================
AI EDITOR -- FASE 45, 46
========================================

Estado: PASS

Implementado:
- human_review.py::render_full_review() -- compone 11 secciones opcionales
- promotion_gate.py::check_promotion_gate() -- consolida 4 reportes como gate PREVIO

Archivos nuevos:
- ai_editor/generation/human_review.py
- ai_editor/generation/promotion_gate.py
- project_knowledge_graph/tests/test_ai_editor_generation_human_review.py
- project_knowledge_graph/tests/test_ai_editor_generation_promotion_gate.py

Archivos modificados: ai_editor/generation/__init__.py, confidence_engine.py
(docstring aclarado tras confundir dos tipos de ValidationReport en mi propio
smoke test -- ver detalle en la seccion "FASE 45-46" arriba).

Tests: 414/414 (404 + 10 nuevos). Regresiones: 0.

Problemas: al hacer el smoke test end-to-end encontre que `confidence_engine.py`
y `human_review.py` esperan especificamente `generation.validation_report.
GenerationValidationReport` (`.syntax_passed`), NO el `ai_editor.validation.
engine.ValidationReport` crudo de `SandboxLoopResult.validation_report`
(`.level_1_passed`) -- mismo nombre generico, dos tipos distintos. No era un
bug de logica (la implementacion siempre espero el tipo correcto), pero SI
una fuente real de confusion para cualquier caller -- documentado
explicitamente en ambos docstrings para que no se repita.

Documentacion: esta seccion + seccion "FASE 45-46" arriba.

Siguiente: 41 de 60 fases cubiertas. Candidatas: FASE 47 (Rollback, ya
construido POST-GRAPH 16, solo confirmar que sigue aplicando) + FASE 48
(Generation Audit, integrar con audit_pipeline_run existente) + FASE 49
(Security Hardening, auditoria real de lo agregado en FASE 24-46) + FASE 50
(Failure Recovery, estados formales) -- o FASE 60 (Final Readiness) como
capstone. FASE 51-53 (AI Editor Agent) y FASE 54-55 (pruebas reales contra
el repo) requieren decision/confirmacion explicita aparte.
```

## FASE 47-50

Ejecutadas en batch, autorizado por instruccion explicita del usuario
("continua todas las fases de la tarea hasta darla por terminada"). Ninguna
de las 4 toco un guardrail de seguridad existente ni escribio contra
`WORKSPACE_ROOT` real -- por eso se ejecutaron sin pausar a confirmar
(a diferencia de FASE 38, que si relajo un guardrail, o de FASE 54-55, que
siguen requiriendo confirmacion explicita aparte por escribir contra el
repo real).

**FASE 47 "Rollback"**: `promotion.py::rollback_outcome(workspace_root,
outcome: PromotionOutcome) -> RollbackResult` -- wrapper delgado sobre
`repository.rollback.rollback_promotion()` (POST-GRAPH 16, ya construido y
probado, sin cambios), unica conveniencia: acepta el `PromotionOutcome` de
`review_and_promote()` directo en vez de que el caller extraiga
`.promote_result` a mano. Si `outcome.promote_result` es `None` (la
propuesta nunca se promovio), `rollback_promotion()` ya devuelve
`NOTHING_TO_ROLLBACK` para ese caso sin lanzar excepcion -- no se duplica
esa logica aca. Probado UNICAMENTE contra `fake_workspace` (`tmp_path`),
mismo criterio que `review_and_promote()`.

**FASE 48 "Generation Audit"**: dos extensiones, ambas backward-compatible
(campos nuevos con default `None`, sin romper ningun caller existente):
- `generation/models.py::GenerationResult` gana `provider: str | None` y
  `model: str | None` -- gap real encontrado en la propia verificacion de
  esta fase: el prompt maestro pide registrar "model, model version" pero
  `GenerationResult` nunca guardaba de donde vino la respuesta del LLM.
  `generator.py::generate_patch_proposal()` los popula desde
  `LLMResponse.provider`/`.model` (POST-GRAPH 2) en los 3 puntos donde
  hay una respuesta real (el path de `LLMRequestError` no tiene
  `LLMResponse`, queda sin poblar, correctamente).
- `audit/pipeline_audit.py::audit_pipeline_run()` gana `proposal=None,
  generation_result=None` (opcionales) -- registra `generation_status`/
  `generation_provider`/`generation_model`/`generation_attempt` y
  `proposal_id`/`proposal_confidence`/`proposal_files`/
  `proposal_operations_count`. Verificado explicitamente (test dedicado)
  que NUNCA se registra `old_content`/`new_content`/`raw_llm_text` --
  solo metadatos, mismo criterio que el resto de `audit/log.py`
  (sanitizacion de claves sensibles ya existente, reusada tal cual).

**FASE 49 "Security Hardening"**: auditoria real (no fabricada) de todo lo
agregado en FASE 24-46. Metodo: grep de `subprocess`/`os.system`/`eval`/
`exec`/`open`/`Path`/`shell=True`/`pickle`/`yaml.load` en TODO
`ai_editor/generation/*.py`, mas verificacion manual de cada resultado.
Hallazgos:
- **Gap real encontrado y corregido**: `code_quality.py::
  run_code_quality_checks()` (FASE 36) construia
  `real_path = Path(sandbox.root) / rel` sin el chequeo anti-traversal
  que `patch.engine.apply_operation()` (POST-GRAPH 6, pre-existente) ya
  aplica antes de tocar cualquier archivo del sandbox
  (`real_path.relative_to(sandbox_root)`, capturando `ValueError`).
  Riesgo real en la practica: BAJO -- `op.file` ya esta constreñido
  aguas arriba por `proposal_validator.find_matching_step()` (FASE 29):
  debe matchear un `PlanStep.file` real, derivado del grafo, nunca
  aceptado directo del LLM: un `file="../../etc/passwd"` jamas
  matchearia un step real y ya se rechaza antes con
  `FILE_OUTSIDE_PLAN`. Aun asi, corregido por el mismo criterio de
  defensa en profundidad que el resto de `ai_editor` (nunca depender de
  una sola capa de validacion): se agrego el mismo patron
  `resolve().relative_to()` de `patch/engine.py`, con test dedicado
  (`test_path_traversal_operation_file_is_rejected_never_scanned_outside_sandbox`)
  que prueba el modulo en aislamiento (Sandbox fake directo, sin pasar
  por `proposal_validator`), igual criterio que el test ya existente de
  `.vue`.
  El unico `subprocess.run(...)` de todo `generation/` (bandit, mismo
  archivo) ya usaba arg-list (nunca `shell=True`), `capture_output=True`,
  y `timeout=30` -- confirmado seguro, sin cambios.
- Ningun otro modulo de `generation/` toca el filesystem directo: todos
  operan sobre dataclasses/dicts YA cargados por capas anteriores
  (`patch_integration.py`/`sandbox_loop.py` delegan 100% en
  `patch.engine`/`repository.sandbox`, ya auditados en POST-GRAPH 18).
  `context.py` (unico lector de codigo fuente real) usa
  `workspace.resolve_repo_file()` (el resolver seguro con boundary
  check), nunca un join manual.
- Limites documentados verificados REALES y activos, sin fabricar
  ninguno nuevo: `MAX_OPERATIONS_PER_PROPOSAL=20`
  (`proposal_validator.py`), `MAX_PATCH_CONTENT_BYTES=5MB`
  (`patch/schema.py`, reusado en `proposal_validator.py`, doble capa),
  `MAX_SANDBOX_FILES=500` (`repository/sandbox.py`),
  `DEFAULT_MAX_RETRIES=3` (`retry.py`). Deteccion de simlinks: fuera de
  alcance de esta fase (pertenece a `repository/sandbox.py`, code
  POST-GRAPH 7/18 ya cerrado, no algo agregado en FASE 24-46).

**FASE 50 "Failure Recovery"**: `generation/pipeline_states.py` (nuevo) --
los 15 estados nombrados literalmente por el prompt maestro (`RECEIVED`,
`RESOLVED`, `PLANNED`, `GENERATING`, `PROPOSED`, `VALIDATING`, `SANDBOXED`,
`TESTING`, `RECONCILING`, `APPROVAL_REQUIRED`, `APPROVED`, `PROMOTED`,
`REJECTED`, `FAILED`, `ROLLED_BACK`) mas
`classify_pipeline_state(intent=, context=, plan=, generation_result=,
sandbox_loop_result=, promotion_outcome=, rollback_result=)`, que
CLASIFICA (nunca orquesta) el estado actual de un cambio a partir de los
objetos reales que cada etapa ya produce -- se evalua en orden inverso
(del mas avanzado al mas temprano) para que el estado devuelto sea siempre
el mas reciente alcanzado. No existe un objeto `Pipeline` nuevo que
mantenga este estado de punta a punta -- eso pertenece a FASE 53
"Autonomous Controlled Loop", fuera de alcance de este batch. `VALIDATING`/
`SANDBOXED`/`APPROVED` (3 de los 15) no tienen un dato real hoy que los
distinga de sus vecinos en el flujo actual (`sandbox_loop_result`
consolida validar+sandboxear en una sola llamada, y "aprobado pero aun sin
promover" no es un estado observable por separado hoy) -- quedan definidos
como constantes validas (`ALL_STATES` los incluye) pero
`classify_pipeline_state()` nunca los devuelve todavia; documentado
explicitamente en el docstring, no fabricado.

## Checkpoint (FASE 47-50)

```
========================================
AI EDITOR -- FASE 47, 48, 49, 50
========================================

Estado: PASS

Implementado:
- promotion.py::rollback_outcome() -- FASE 47
- models.py::GenerationResult.provider/.model + pipeline_audit.py::
  audit_pipeline_run(proposal=, generation_result=) -- FASE 48
- code_quality.py: gap real de path traversal encontrado y corregido -- FASE 49
- pipeline_states.py::classify_pipeline_state() + 15 estados -- FASE 50

Archivos nuevos:
- ai_editor/generation/pipeline_states.py
- project_knowledge_graph/tests/test_ai_editor_generation_pipeline_states.py

Archivos modificados:
- ai_editor/generation/promotion.py (rollback_outcome)
- ai_editor/generation/models.py (GenerationResult.provider/.model)
- ai_editor/generation/generator.py (poblar provider/model)
- ai_editor/audit/pipeline_audit.py (proposal=/generation_result=)
- ai_editor/generation/code_quality.py (fix path traversal)
- ai_editor/generation/__init__.py (exports)
- project_knowledge_graph/tests/test_ai_editor_generation_promotion.py (+2 tests)
- project_knowledge_graph/tests/test_ai_editor_audit.py (+1 test)
- project_knowledge_graph/tests/test_ai_editor_generation_code_quality.py (+1 test)

Tests: 437/437 (414 + 23 nuevos). Regresiones: 0.

Problemas: 1 gap de seguridad real encontrado en codigo de FASE 36
(code_quality.py sin boundary check anti-traversal) -- riesgo practico BAJO
(ya mitigado aguas arriba por FASE 29), corregido igual por defensa en
profundidad, con test dedicado. Ningun otro hallazgo en la auditoria FASE 49.

Documentacion: esta seccion + seccion "FASE 47-50" arriba.

Siguiente: 45 de 60 fases cubiertas. FASE 51-53 (AI Editor Agent -- loop
autonomo con tool-calling real) representa una escalada de alcance
arquitectonica genuina (el propio prompt maestro pide "Solo despues de que
el Proposal Engine sea estable") -- requiere check-in explicito con el
usuario antes de construir, no una continuacion automatica de "continua
todas las fases". FASE 54-55 (pruebas contra el repo REAL) siguen
requiriendo confirmacion explicita aparte, mismo criterio que
POST-GRAPH 21/22. FASE 56 (Performance) y FASE 57-59
(Documentacion/Test Suite/Regression, ya mayormente satisfechas por lo
existente) son seguras de continuar sin pausar. FASE 60 (Final Readiness)
como capstone despues de esas.
```

## FASE 56

`generation/performance.py::measure_pipeline_stage_timings(proposal, plan,
context) -> PipelineTimingReport` -- cronometra con `time.perf_counter()`
REAL cada etapa del pipeline que no depende de un LLM externo (sandbox
validation loop, code quality/bandit, reconciliation, impact recheck x2,
confidence, human review), corrido contra el repo real
(`HomeCardGroupSelector.get_by_name`). La etapa `GENERATING_LLM` queda
siempre `duration_seconds=None`/`NOT_MEASURED` -- ningun LLM real
(Ollama/OpenAI/Anthropic) se invoco en ningun punto de todo el desarrollo
de este plan de 60 fases, asi que no hay un tiempo real que medir; nunca
se fabrica un numero. Medicion real de referencia (una corrida, un
proposal de 1 operacion): `SANDBOX_VALIDATION_LOOP` ~0.048s,
`CODE_QUALITY` (bandit real) ~1.03s (con diferencia la etapa mas cara,
esperable -- es un subprocess externo), `RECONCILIATION` ~0.00003s,
`IMPACT_RECHECK` (captura) ~0.071s + (recheck) ~0.109s (2 llamadas reales
a `calculate_impact()` contra el grafo), `CONFIDENCE`/`HUMAN_REVIEW`
~0.00002s (puro Python, sin I/O). Total medido ~1.26s de las 6 etapas no-LLM.

## FASE 57-59

Verificacion de consolidacion (sin construccion nueva -- el prompt maestro
pide "Documentation"/"Test Suite"/"Regression" como fases propias, pero la
disciplina de esta ejecucion ya las viene satisfaciendo continuamente
desde FASE 24): confirmado con un script real que TODOS los modulos de
`ai_editor/generation/*.py` (23 submodulos, sin contar `__init__.py`)
tienen su archivo de test correspondiente en
`project_knowledge_graph/tests/` -- 0 gaps encontrados. `AI_CHANGE_
PROPOSAL_ENGINE.md` (este archivo) documenta cada fase con su propia
seccion tecnica + checkpoint. Regression: full suite corrida despues de
CADA fase/batch de este plan (no solo al final), 441/441 al cierre de
FASE 56.

## FASE 60 -- Final AI Editor Readiness (parcial)

Capstone de lo efectivamente construido y verificado (FASE 24-50 + 56-59
del plan de 60 fases) -- **NO cubre FASE 51-53 (AI Editor Agent) ni FASE
54-55 (prueba contra repo real)**, ambas pendientes de decision/
confirmacion explicita del usuario, documentado como tal, nunca marcado
falsamente "listo".

| Componente | Estado | Evidencia |
|---|---|---|
| Generacion estructurada (LLM -> PatchProposal) | REAL, sin probar contra LLM real | FASE 28, `generator.py` |
| Validacion contra repo real (scope/hash/limites) | REAL | FASE 29, `proposal_validator.py` |
| Retry con correccion explicita | REAL | FASE 30, `retry.py` |
| Aplicacion sobre sandbox aislado | REAL | FASE 31, `patch_integration.py` |
| Ciclo sandbox + validacion sintaxis | REAL | FASE 32, `sandbox_loop.py` |
| Encadenar con aprobacion humana + promocion | REAL, solo `fake_workspace` | promotion.py, POST-GRAPH 11/12 |
| Reporte de validacion consolidado | REAL | FASE 33, `validation_report.py` |
| Graph Reconciliation (scope, no rebuild completo) | REAL (parcial), rebuild completo NOT_IMPLEMENTED | FASE 34 |
| Impact Recheck (drift del grafo) | REAL | FASE 35 |
| Code Quality (bandit real, JS/Vue NOT_CONFIGURED) | REAL | FASE 36 |
| Architectural Compliance (heuristico, regex) | REAL (parcial) | FASE 37 |
| Cross-Stack Generation (guardrail acotado) | REAL, relajado con confirmacion explicita | FASE 38 |
| Dependency-Aware Generation | REAL (parcial, sin deteccion circular) | FASE 40 |
| Contract-Aware Generation | REAL | FASE 41 |
| Test-Aware Generation | REAL | FASE 42 |
| Documentation-Aware Generation | REAL, nunca escribe .md | FASE 43 |
| Confidence Engine (score compuesto) | REAL | FASE 44 |
| Human Review (render de texto) | REAL, sin UI | FASE 45 |
| Promotion Gate (gates bloqueantes) | REAL, "tests pass" NO VERIFICABLE honesto | FASE 46 |
| Rollback | REAL, reusa POST-GRAPH 16 | FASE 47 |
| Generation Audit (provider/model/metadata) | REAL, nunca contenido crudo | FASE 48 |
| Security Hardening | REAL, 1 gap encontrado y corregido | FASE 49 |
| Failure Recovery (15 estados formales) | REAL (parcial, 3/15 sin caso observable hoy) | FASE 50 |
| Performance (timings reales, LLM NOT_MEASURED) | REAL | FASE 56 |
| Documentation/Test Suite/Regression | REAL, 0 gaps, 441/441 | FASE 57-59 |
| AI Editor Agent (loop autonomo tool-calling) | NO CONSTRUIDO -- requiere check-in explicito | FASE 51-53 |
| Cross-Stack REAL TEST / REAL CHANGE TEST | NO EJECUTADO -- requiere confirmacion explicita (escribe contra WORKSPACE_ROOT real) | FASE 54-55 |

**Regla de seguridad final verificada, sin excepcion en todo el plan**:
ningun test, smoke test manual, ni codigo de `generation/` escribio jamas
contra `WORKSPACE_ROOT` real -- todo (incluida esta auditoria) opero sobre
`fake_workspace`/`tmp_path` o sandboxes aislados. `promote_to_workspace()`
siempre exige `confirm=True` explicito, nunca defaulteado.

## FASE 51-53 -- AI Editor Agent (2026-08-12)

Autorizado explicitamente por el usuario tras un check-in dedicado (el
plan se habia pausado a proposito despues de FASE 60 parcial, dado que
esto representa una escalada de alcance real, no una fase de validacion
mas). Paquete nuevo `ai_editor/agent/` (`policy.py` FASE 52, `schema.py`,
`loop.py` FASE 51+53):

- **`AgentPolicy`** (FASE 52 "Agent Policy"): `max_retries`/`provider`
  unicamente. Deliberadamente SIN un campo `allow_auto_promote` -- no
  hace falta un flag para apagar una capacidad que este paquete nunca
  tiene.
- **`run_autonomous_change_loop(request, policy=None, intent=None)`**
  (FASE 51+53): orquesta, en una sola llamada, EXACTAMENTE lo que
  `generation/` (FASE 24-50) ya construyo fase por fase -- intent ->
  context -> plan -> validate_plan -> impact baseline -> generate_with_
  retry -> sandbox_loop -> {code_quality, architecture_compliance,
  dependency_awareness, contract_awareness, test_awareness,
  documentation_awareness} -> reconciliation -> impact_recheck ->
  confidence -> promotion_gate -> human_review -> `classify_pipeline_
  state()` para el status final. Pura composicion -- cero logica de
  decision nueva, se detiene (return anticipado) en el primer punto
  donde una etapa no produce un resultado usable.
- **REGLA FINAL DE SEGURIDAD, garantizada ESTRUCTURALMENTE**: `agent/`
  nunca importa `generation.promotion` ni `repository.promote` (test AST
  dedicado, `test_never_imports_promotion_or_repository_promote`) -- el
  status mas avanzado que este paquete puede producir es
  `APPROVAL_REQUIRED`. Promover sigue siendo, sin excepcion, una llamada
  SEPARADA a `generation.promotion.review_and_promote()` con
  `decision`/`confirm` de un humano real, fuera de este paquete.

**Primera vez en las 60 fases del plan que se corrio contra un LLM REAL**
(no mockeado): se verifico que Ollama esta alcanzable en este entorno
(`localhost:11434`, modelo `llama3.1:8b`, el default de `ai_editor.llm`
cuando no se configura ningun provider) -- una correccion real a la
documentacion previa, que afirmaba (incorrectamente, nunca verificado
hasta ahora) que ningun LLM estaba disponible. Corrida real end-to-end
(intent inyectado para hacer determinista esa unica etapa, `generate_
with_retry()` SI llamo al LLM real): con `max_retries=2`, el modelo local
de 8B no logro producir un JSON estructurado valido en ninguno de los 2
intentos -- `REJECTED` correcto y honesto (nunca se fabrico un patch),
30.8s reales. Hallazgo real sobre CALIDAD DEL MODELO, no un bug del
pipeline. El camino feliz completo (`APPROVAL_REQUIRED` con los 10
reportes de FASE 33-46 adjuntos) se verifico con una `PatchProposal`
REAL (mismo patron de `old_content` exacto que el resto de la suite) en
vez de depender de que el LLM local produzca una propuesta valida de
forma confiable -- se evita un test lento/flaky sin sacrificar
cobertura real de la orquestacion POSTERIOR a la generacion (que es
justamente la parte nueva que aporta este paquete).

## Checkpoint (FASE 51-53)

```
========================================
AI EDITOR -- FASE 51, 52, 53
========================================

Estado: PASS

Implementado:
- ai_editor/agent/policy.py::AgentPolicy
- ai_editor/agent/schema.py::AgentRunResult
- ai_editor/agent/loop.py::run_autonomous_change_loop()

Archivos nuevos:
- ai_editor/agent/__init__.py
- ai_editor/agent/policy.py
- ai_editor/agent/schema.py
- ai_editor/agent/loop.py
- project_knowledge_graph/tests/test_ai_editor_agent.py

Archivos modificados:
- ai_editor/__init__.py (docstring: 12 submodulos, agent/ documentado,
  correccion de la afirmacion falsa sobre disponibilidad de Ollama)
- project_knowledge_graph/tests/test_ai_editor_scaffold.py (expected
  set + docstring, agrega "agent")

Tests: 449/449 (441 + 8 nuevos). Regresiones: 0. Incluye 1 test contra
Ollama real (se salta si no esta alcanzable, nunca finge el resultado).

Problemas: ninguno de codigo -- el unico "problema" es un hallazgo real
sobre el modelo local (llama3.1:8b no siempre produce JSON valido en
pocos intentos), documentado como tal, no tratado como bug.

Documentacion: esta seccion + seccion "FASE 51-53" arriba +
`ai_editor/__init__.py` corregido.

Siguiente: 52 de 60 fases cubiertas (24-53 + 56-59; 60 completo requiere
54-55 primero). FASE 54-55 (Cross-Stack REAL TEST / REAL CHANGE TEST)
siguen siendo las unicas fases que faltan, y siguen requiriendo
confirmacion explicita del usuario en el momento -- escriben contra
`WORKSPACE_ROOT` real, mismo criterio inalterado desde POST-GRAPH 21/22
en toda la sesion.
```

## FASE 54-55 -- Cross-Stack REAL TEST / REAL CHANGE TEST (2026-08-12)

Ejecutada con confirmacion explicita del usuario en 3 pasos (que generar
el contenido, que hacer despues de promover, y el diff EXACTO antes de
escribir). Primera y UNICA vez en toda la sesion que se escribio de
verdad sobre `WORKSPACE_ROOT` real.

**Hallazgo pre-ejecucion (transparencia, no bloqueante)**: el archivo
objetivo (`core/services/commands.py`) tenia trabajo real del usuario
sin commitear (clases `FeatureBannerSection`/`FeatureBannerBlock`
nuevas, refactor de `HomeCardCommands`, ajustes en
`BrandSliderSelector`/`AboutUsSelector`) -- verificado con `git diff`
ANTES de tocar nada que ese trabajo pendiente no se solapaba con las
lineas objetivo (129-130, `HomeCardGroupSelector.get_by_name`).
Comunicado al usuario, quien confirmo proceder de todos modos.

**Cambio de prueba**: un comentario aclaratorio de una linea arriba del
`return` de `HomeCardGroupSelector.get_by_name` -- cero cambio de
logica, contenido construido a mano (no generado por LLM, decision
explicita del usuario para que la prueba fuera predecible).

**Secuencia real ejecutada** (`resolve_change_context` ->
`build_change_plan` -> `PatchProposal` manual -> `run_sandbox_validation_
loop` -> `review_and_promote(..., confirm=True)` -> verificacion ->
`audit_pipeline_run` -> `rollback_outcome` -> verificacion ->
`audit_pipeline_run` -> `sandbox.cleanup()`):

1. `plan.status == PLANNED` (real, contra el grafo).
2. `run_sandbox_validation_loop()`: `ready_for_approval=True`.
3. `review_and_promote(..., decision="APPROVE", confirm=True)`:
   `outcome.promoted=True`, `promote_result.status="PROMOTED"`.
4. Verificado leyendo el archivo real: el comentario SI aparece.
5. `rollback_outcome(WORKSPACE_ROOT, outcome)`:
   `status="ROLLED_BACK"`, `files_restored=["core/services/commands.py"]`.
6. Verificado con SHA-256 del archivo completo: hash ANTES == hash
   DESPUES DEL ROLLBACK, byte a byte -- restauracion exacta, incluido el
   trabajo pendiente del usuario en el resto del archivo.
7. Verificado con `git diff`: 0 ocurrencias del comentario de prueba en
   el diff final -- ningun rastro quedo.
8. `audit_pipeline_run()` registro ambas etapas (promote y rollback) en
   el log real, `ai_editor/data/CHANGE_AUDIT_LOG.jsonl`.

**Conclusion**: el mecanismo completo (`generation.sandbox_loop` ->
`generation.promotion.review_and_promote` -> `repository.promote.
promote_to_workspace` -> `repository.rollback.rollback_promotion` via
`generation.promotion.rollback_outcome`) funciona de punta a punta
contra el `WORKSPACE_ROOT` real de este proyecto, de forma segura y
reversible, tal como todas las fases anteriores lo diseñaron sin poder
probarlo hasta ahora.

**60 de 60 fases del plan cubiertas.** El unico punto que sigue siendo un
hallazgo abierto (no un defecto de este mecanismo): promover con
contenido generado por el LLM en vez de manual depende de que el modelo
local (`llama3.1:8b`) produzca una propuesta valida -- documentado en
FASE 51-53, verificado que no lo hace de forma confiable con pocos
reintentos.

