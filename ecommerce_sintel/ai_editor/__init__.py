"""
ai_editor -- Fase 14 "AI Editor Runtime" del rediseno "Site Knowledge Graph
/ AI Editor Runtime" (2026-08-10), evolucionado via el plan "POST-GRAPH"
("PROMPT MAESTRO - EVOLUCION DE AI_EDITOR", 2026-08-11, las 24 fases
POST-GRAPH 0-23 completas y verificadas -- ver
`ai_editor/.AGENT/AI_EDITOR_BASELINE.md`) y ahora evolucionando via el
plan "AI CHANGE PROPOSAL ENGINE" ("PROMPT MAESTRO - AI CHANGE PROPOSAL
ENGINE", 2026-08-11, FASE 24 en adelante, 49 de 60 fases cubiertas al
2026-08-12 -- FASE 24-50 + 51-53 + 56-59 (60 parcial); FASE 54-55
pendientes de confirmacion explicita del usuario, ver
`ai_editor/.AGENT/AI_CHANGE_PROPOSAL_ENGINE.md`). 12
submodulos con logica real -- los 7 originales de Fase 14 mas `llm/`
(POST-GRAPH 2), `approval/` (POST-GRAPH 11) y `audit/` (POST-GRAPH 13)
mas `generation/` (FASE 25-50/56-59 del nuevo plan) mas `agent/` (FASE
51-53, el loop autonomo controlado que orquesta todo `generation/` en
una sola llamada, SIN capacidad estructural de promover) -- pero varios
con ALCANCE
DELIBERADAMENTE ACOTADO: `patch/` no genera codigo real por si solo (esa
generacion ahora vive, PROPUESTA pero SIN aplicar, en `generation/`),
`validation/` solo cubre Nivel 1 de 5 (sintaxis), `validation.
reconcile_graph()` es NOT_IMPLEMENTED, `generation/` produce una
`PatchProposal` estructurada pero NUNCA la conecta con `patch.engine.
apply_operation()` todavia (eso es FASE 31, no construida). Ver la
seccion "ESTADO REAL" abajo antes de asumir que algo de aca hace mas de
lo que realmente hace.

REGLA ARQUITECTONICA ABSOLUTA (repetida de la Fase 0 del rediseno, sigue
aplicando aca): este paquete es INDEPENDIENTE de `ai_engine/` (el chatbot
de soporte) -- ninguno de los dos importa al otro. `ai_engine` sigue siendo
EXCLUSIVAMENTE el chatbot de soporte; este paquete es donde viviria, en el
futuro, la logica de "recibir una solicitud de cambio de codigo y
planificar/aplicar el cambio", si esa capacidad se construye alguna vez.

Flujo INTENCIONADO (parcialmente implementado -- ver "ESTADO REAL" para el
detalle exacto de que corre hoy):

    USER REQUEST
         |
         v
    intent/        -- IMPLEMENTADO (POST-GRAPH 2): interpreta la solicitud
         |             humana via llm/, confirma el dominio contra el grafo real
         v
    resolver/       -- IMPLEMENTADO (POST-GRAPH 3): resuelve cada entidad del
         |             intent contra graph_client.find_node(), exige coincidencia
         |             EXACTA (nunca acepta un fuzzy match como confirmado), y
         |             compone resolve_change()/build_context_packet() para el
         |             target principal
         v
    planner/        -- IMPLEMENTADO (POST-GRAPH 4): convierte el ChangeContext en
         |             PlanStep concretos (file/symbol/lineas/operation/reason/
         |             dependencies/risk/validation), 0 llamadas nuevas al grafo --
         |             solo reordena datos que resolver/ ya trajo
         v
    repository/     -- IMPLEMENTADO (POST-GRAPH 7/12): create_sandbox(plan) copia
         |             SOLO los archivos reales que el plan toca a un directorio
         |             temporal aislado -- el checkout real nunca se modifica en
         |             esta etapa. promote_to_workspace()/commit_changes()
         |             (POST-GRAPH 12) SI escriben sobre un workspace real, pero
         |             requieren ApprovalRecord(APPROVE) + confirm=True explicito
         |             + fingerprint sin drift -- nunca invocado contra el
         |             checkout real de este proyecto en esta sesion
         v
    patch/          -- IMPLEMENTADO PARCIALMENTE (POST-GRAPH 6): el MECANISMO de
         |             aplicar un cambio de forma segura SOBRE EL SANDBOX de
         |             repository/ (fingerprint antes de escribir, rechazo si el
         |             destino no es un sandbox explicito) -- generar el
         |             new_content real de un cambio sigue sin existir (requeriria
         |             una capa de generacion de codigo, LLM escribiendo diffs
         |             reales, no construida todavia)
         v
    validation/     -- IMPLEMENTADO PARCIALMENTE (POST-GRAPH 8/9/10): Nivel 1
                        (sintaxis) real; Niveles 2-5 y Graph Reconciliation
                        (POST-GRAPH 9) NOT_IMPLEMENTED explicito -- el sandbox
                        parcial no alcanza para Django/rebuild del grafo, y
                        ademas no hay generacion de codigo real que pueda
                        producir impacto inesperado que reconciliar todavia.
                        Test Impact Execution (POST-GRAPH 10) SI es real:
                        clasifica tests required/recommended con datos ya
                        existentes, pero no los ejecuta (mismo motivo)
         v
    approval/       -- IMPLEMENTADO (POST-GRAPH 11): build_change_summary()
                        arma el resumen legible (files/symbols/contracts/
                        impacto/riesgo/tests/validacion) para revision humana;
                        record_decision() valida y registra APPROVE/REJECT/
                        MODIFY_PLAN/REQUEST_EXPLANATION -- punto de parada
                        estructural antes de cualquier escritura al repo real

audit/              -- IMPLEMENTADO (POST-GRAPH 13, transversal a todo el
                        flujo, no un paso secuencial mas): audit_pipeline_run()
                        registra cada corrida (request/intent/files/symbols/
                        tests/validation/approval/commit) en un JSONL propio,
                        sanitizado (nunca secrets/tokens/passwords, ni de
                        primer nivel ni anidados -- bug real encontrado y
                        corregido en la propia verificacion de esta fase)

ESTADO REAL (2026-08-11, honesto -- no aspiracional. Actualizado en
POST-GRAPH 0/1 del rediseno "AI Editor Runtime" -- ver
`ai_editor/.AGENT/AI_EDITOR_BASELINE.md` para el detalle completo de la
auditoria):
  - `graph_client/`  : IMPLEMENTADO. Wrapper de SOLO LECTURA sobre
                        `project_knowledge_graph.graph_sdk` -- cero riesgo,
                        no modifica nada, es literalmente una capa de
                        import mas fina. Es LA FRONTERA OFICIAL entre
                        `ai_editor` y `project_knowledge_graph` (POST-GRAPH
                        1): 16 operaciones (`resolve_change`/`find_node`/
                        `find_symbol`/`find_file`/`find_endpoint`/
                        `find_consumers`/`trace_data_flow`/`trace_execution`/
                        `find_tests`/`find_docs`/`calculate_impact`/
                        `build_change_plan`/`build_context_packet`/
                        `find_configuration`/`get_app_summary`/
                        `get_graph_status`). Ningun otro submodulo de aca
                        debe importar `project_knowledge_graph.knowledge_
                        graph.*`/`.internal.*` directo -- siempre a traves
                        de `graph_client`.
  - `llm/`            : IMPLEMENTADO (POST-GRAPH 2, 2026-08-11). Acceso a
                        un LLM TOTALMENTE INDEPENDIENTE -- no importa
                        `ai_engine.llm_factory` ni ningun otro modulo del
                        proyecto, implementacion propia sobre
                        `urllib.request` (stdlib, cero dependencias
                        nuevas). 3 proveedores intercambiables (`ollama`
                        local, `openai`, `anthropic`), seleccionables por
                        `AI_EDITOR_LLM_PROVIDER` o por argumento explicito
                        en cada llamada. Decision directa del usuario
                        (2026-08-11): "ai_editor accede al llm de forma
                        totalmente independiente... poder cambiar de llm
                        segun sea conveniente".
  - `intent/`         : IMPLEMENTADO (POST-GRAPH 2, 2026-08-11). Convierte
                        una solicitud humana en un `ChangeIntent`
                        estructurado usando `llm/` para interpretar y
                        `graph_client.find_node()` para CONFIRMAR que el
                        dominio propuesto es una app real -- si el LLM
                        alucina un nombre de app inexistente, o la
                        solicitud es ambigua, el `ChangeIntent` queda
                        `status="NEEDS_CLARIFICATION"` en vez de avanzar
                        con una suposicion no verificada.
  - `resolver/`       : IMPLEMENTADO (POST-GRAPH 3, 2026-08-11).
                        `resolve_change_context(intent)` convierte un
                        `ChangeIntent` en un `ChangeContext`: resuelve
                        cada entidad contra `graph_client.find_node()`
                        exigiendo coincidencia EXACTA (un match fuzzy NO
                        se acepta como confirmado -- bug real encontrado y
                        corregido en esta misma fase, ver
                        `AI_EDITOR_BASELINE.md` seccion 10), prioriza
                        Symbol > Model > ... para elegir el target
                        principal, y compone `resolve_change()`/
                        `build_context_packet()` (Fase 11/12, sin
                        reimplementar nada) para el resultado final.
  - `planner/`        : IMPLEMENTADO (POST-GRAPH 4/5, 2026-08-11).
                        `build_change_plan(context)` convierte un
                        `ChangeContext` en `PlanStep` concretos -- target
                        principal SIEMPRE step 1 (`operation=MODIFY`),
                        despues contratos/frontend/backend dependientes
                        (`REVIEW`) y tests (`RUN`), en ese orden, derivado
                        de las categorias REALES de impacto (Fase 10), no
                        de una plantilla inventada. `validate_plan(plan)`
                        (POST-GRAPH 5) es la primera pieza de todo
                        `ai_editor` que LEE el filesystem real (via
                        `ai_editor.workspace`, nunca escribe) -- confirma
                        que archivos/lineas siguen existiendo en disco tal
                        como el grafo los describio, bloquea si hay drift
                        o entidades no confirmadas. Sigue sin AUTOMATIZAR
                        la ejecucion de ese plan -- eso es responsabilidad
                        de `patch/` (deliberadamente no implementado) mas
                        el "HUMAN GATE" de la Fase 17 del rediseno
                        anterior, que sigue aplicando.
  - `repository/`      : IMPLEMENTADO (POST-GRAPH 7/12, 2026-08-11).
                        `create_sandbox(plan)` copia SOLO los archivos
                        reales que un `ChangePlan` toca (resueltos backend
                        o frontend via `ai_editor.workspace`) a un
                        directorio temporal aislado -- es el UNICO
                        `sandbox_root` legitimo para
                        `patch.apply_operation()`. Rechaza copiar paths
                        que matcheen patrones sensibles (`.env`/secrets/
                        claves) incluso si aparecieran en un plan. El
                        checkout real (`WORKSPACE_ROOT`) nunca se
                        modifica en esta etapa -- verificado end-to-end:
                        aplicar un patch sobre el sandbox no altera el
                        archivo real correspondiente.
                        `promote_to_workspace(sandbox, approval,
                        workspace_root, confirm, validation_report)`
                        (POST-GRAPH 12/20) SI escribe sobre un workspace
                        real -- exige `ApprovalRecord.decision ==
                        APPROVE` MAS `confirm=True` explicito MAS
                        re-verificacion de fingerprint contra el estado
                        actual del destino (todo-o-nada) MAS, si se pasa
                        `validation_report`, rechaza estructuralmente si
                        la sintaxis fallo -- **gap real encontrado en
                        POST-GRAPH 20**: antes de esto, nada impedia en
                        codigo promover un cambio con sintaxis rota si un
                        humano lo aprobaba por error. `commit_changes()`
                        hace como maximo `git add`+`git commit` LOCAL, nunca
                        push. **Esta sesion probo el mecanismo solo
                        contra directorios/repos git temporales -- nunca
                        se invoco contra el `WORKSPACE_ROOT` real de este
                        proyecto.**
                        `rollback_promotion(workspace_root,
                        promote_result)` (POST-GRAPH 16) revierte un
                        `PromoteResult` exitoso usando `files_before`
                        (contenido COMPLETO de cada archivo, capturado
                        por `promote_to_workspace()` mismo justo antes de
                        sobrescribir) -- no depende de git. Reconstruir
                        el grafo despues de un rollback es simplemente
                        `cli audit` de nuevo, no se duplica esa logica
                        aca. Multi-step change (DAG multi-modulo,
                        POST-GRAPH 15) queda DOCUMENTADO COMO DIFERIDO --
                        requeriria extender `planner/` de una topologia
                        de estrella (1 target + dependientes) a un grafo
                        de dependencias real entre multiples targets, sin
                        un caso real que lo motive todavia.
  - `patch/`           : IMPLEMENTADO PARCIALMENTE (POST-GRAPH 6,
                        2026-08-11). `apply_operation(sandbox_root,
                        operation)` -- MECANISMO de escritura segura:
                        verifica fingerprint (sha256) del contenido real
                        ANTES de escribir (aborta si no coincide, el
                        archivo cambio desde que se genero el plan), y
                        RECHAZA estructuralmente escribir sobre
                        `WORKSPACE_ROOT` (el checkout real) salvo
                        `allow_live_workspace=True` explicito -- ni
                        siquiera necesita el sandbox de POST-GRAPH 7 para
                        fallar cerrado. **NO genera `new_content`
                        automaticamente**: eso requeriria una capa de
                        generacion de codigo real (LLM escribiendo diffs
                        sobre un codebase Django/Vue real) que ninguna
                        fase de este rediseno construye todavia -- probado
                        solo con contenido SINTETICO (fixtures de test),
                        nunca contra codigo real de la aplicacion.
  - `validation/`      : IMPLEMENTADO PARCIALMENTE (POST-GRAPH 8/9/10,
                        2026-08-11). `run_validation()`: SOLO Nivel 1
                        (sintaxis) real -- `ast.parse()` para Python,
                        `node --check` para JS/Vue (shell-out seguro, solo
                        parsea). Niveles 2-5 y `reconcile_graph()`
                        (POST-GRAPH 9) quedan `NOT_IMPLEMENTED` explicito
                        -- el sandbox parcial no alcanza para Django/
                        rebuild del grafo. `build_test_validation_report()`
                        (POST-GRAPH 10) SI clasifica tests reales
                        (`required`/`recommended`), pero nunca los ejecuta.
  - `approval/`        : IMPLEMENTADO (POST-GRAPH 11, 2026-08-11).
                        `build_change_summary()` compone el CHANGE SUMMARY
                        a partir de datos YA reales de fases anteriores --
                        cero consultas nuevas al grafo. `record_decision()`
                        valida y registra `APPROVE`/`REJECT`/
                        `MODIFY_PLAN`/`REQUEST_EXPLANATION`, rechaza
                        cualquier otra cosa. `unexpected_changes_note`
                        siempre aclara que Graph Reconciliation no esta
                        implementado -- no finge haber verificado algo que
                        no verifico.
  - `audit/`           : IMPLEMENTADO (POST-GRAPH 13, 2026-08-11).
                        `audit_pipeline_run()` registra cada corrida
                        (request/intent/domain/files/symbols/tests/
                        validation/approval/commit/timestamp) en
                        `ai_editor/data/CHANGE_AUDIT_LOG.jsonl`
                        (append-only, propio -- no reusa
                        `project_knowledge_graph.audit.query_log`, que es
                        "internal" de ese paquete). `log_change_operation()`
                        sanitiza CUALQUIER clave que matchee un patron
                        sensible (secret/password/token/api_key/
                        credential), tanto de primer nivel como anidada --
                        **bug real encontrado y corregido en la propia
                        verificacion**: la primera version solo sanitizaba
                        valores via un dict-comprehension manual, nunca
                        las claves de primer nivel, dejando pasar
                        `log_change_operation(api_key="...")` integro.
                        `compute_metrics()` (POST-GRAPH 17) agrega
                        metricas reales (changes_requested/planned/
                        approved/rejected/promoted, patch_failures,
                        validation_failures, rollback_count) sobre esos
                        mismos registros -- `graph_mismatches`/
                        `unexpected_impacts`/tiempos por etapa quedan
                        explicitamente `None` (no `0`, para no fingir
                        "0 problemas" cuando en realidad es "nunca se
                        midio"), documentado por que en `metrics.py`.

  - `generation/`      : IMPLEMENTADO PARCIALMENTE (FASE 24-28 del plan
                        "AI Change Proposal Engine", 2026-08-11 -- primera
                        ejecucion del plan, NO las 60 fases). LLM +
                        contexto MINIMO real (nunca el grafo completo) ->
                        `PatchProposal` estructurada, o `REJECTED`/`ERROR`
                        explicito -- nunca escribe nada, nunca llama a
                        `patch/`/`repository/` (verificado por test AST,
                        `test_ai_editor_generation_generator.py`).
                        `models.py`: dataclasses (`ChangeGenerationRequest`/
                        `PatchProposal`/`PatchOperation`/`GenerationResult`/
                        `GenerationIssue`/`GenerationConfidence`) -- el
                        `PatchOperation` de aca NO es el de `patch.schema`
                        (ver docstring del modulo para la distincion
                        deliberada). `context.py`:
                        `build_generation_context()` ensambla los 6 campos
                        del request reusando `ChangeContext.context_packet`
                        (ya compactado, Fase 12) + lee SOLO el rango de
                        lineas real del target `MODIFY` (mas un margen
                        chico, nunca el archivo completo) + resuelve el
                        doc de arquitectura real de la app via la tabla de
                        `CLAUDE.md` (nunca una convencion de nombre
                        adivinada -- los nombres de doc NO son uniformes
                        entre apps) + lee las 5 reglas globales reales
                        desde `MEMORY.md` en vivo (no una copia
                        hardcodeada). `prompts.py`: `build_prompt()` con 8
                        estrategias segun tipo de cambio real (backend/
                        frontend/api/tests/documentation/configuration/
                        cross-stack/unknown), determinista. `generator.py`
                        + `validators.py`: `generate_patch_proposal()`
                        llama `ai_editor.llm.complete()`, exige JSON
                        estructurado -- **regla critica verificada por
                        test**: si el LLM devuelve texto libre, se
                        RECHAZA sin intentar convertirlo en un patch
                        (nunca se repara silenciosamente). La suite de
                        tests de `generation/` sigue usando un LLM
                        MOCKEADO (determinismo) -- pero **CORRECCION
                        2026-08-12 (FASE 51-53)**: la afirmacion previa de
                        que "Ollama/OpenAI/Anthropic no estan disponibles
                        en este entorno" era FALSA -- Ollama local SI esta
                        alcanzable (`localhost:11434`, `llama3.1:8b`) y
                        `ai_editor.agent.run_autonomous_change_loop()` lo
                        uso contra un LLM real por primera vez en todo el
                        plan (ver `ai_editor/agent/loop.py` y
                        `test_ai_editor_agent.py`) -- verificado en la
                        practica que el modelo local de 8B no siempre
                        devuelve JSON estructurado valido en pocos
                        intentos, un hallazgo real sobre calidad del
                        modelo, no un bug del pipeline (que rechazo
                        correctamente en vez de fingir exito). FASE 29
                        (Patch Proposal Validator) y FASE 31 (Patch
                        Engine Integration) ya estan construidas -- ver
                        `AI_CHANGE_PROPOSAL_ENGINE.md` para el detalle
                        completo de FASE 24-60.

  - `agent/`           : IMPLEMENTADO (FASE 51-53 del plan "AI Change
                        Proposal Engine", 2026-08-12). `run_autonomous_
                        change_loop(request, policy=None, intent=None)`
                        orquesta, en una sola llamada, TODO lo que
                        `generation/` (FASE 24-50) ya construyo fase por
                        fase -- pura composicion, cero logica de decision
                        nueva. Se detiene en el primer punto donde una
                        etapa no produce un resultado usable
                        (`ChangeIntent`/`ChangeContext`/`ChangePlan` sin
                        resolver, generacion agotando reintentos, sandbox
                        sin quedar listo) -- nunca sigue adelante con
                        datos parciales. El resultado mas avanzado
                        posible es `APPROVAL_REQUIRED` (via
                        `generation.pipeline_states.classify_pipeline_
                        state()`) -- **REGLA FINAL DE SEGURIDAD
                        garantizada de forma ESTRUCTURAL**: este
                        submodulo nunca importa `generation.promotion` ni
                        `repository.promote` (verificado por test AST),
                        asi que no existe ninguna linea de codigo en todo
                        `agent/` que pueda escribir sobre `WORKSPACE_ROOT`
                        real. `AgentPolicy` (FASE 52) expone solo
                        `max_retries`/`provider` -- deliberadamente SIN
                        un flag de "auto-promover", porque esa capacidad
                        no existe aca, no hace falta un interruptor para
                        apagarla.

**Escritura real, resumen exacto de quien escribe que**: `patch/` escribe
DENTRO de un sandbox (nunca el checkout real, salvo
`allow_live_workspace=True` explicito que nadie invoca hoy).
`repository.promote_to_workspace()` SI puede escribir sobre un checkout
real, pero solo con `ApprovalRecord(APPROVE)` + `confirm=True` + sin
drift de fingerprint -- **confirmado real contra `WORKSPACE_ROOT` en
POST-GRAPH 21** (2026-08-11, ejecucion delegada al usuario, PROMOTE +
ROLLBACK verificados, ver `AI_EDITOR_BASELINE.md` seccion 26), la unica
vez que ocurrio, sobre un cambio minimo y revertido de inmediato -- no es
un flujo automatizado ni recurrente. `generation/` NUNCA escribe nada,
solo PROPONE (ver arriba). Todo lo demas (`graph_client`/`intent`/
`resolver`/`planner`/`validation`/`approval`/`audit`) es de solo lectura
sobre el filesystem (cuando lee algo) y nunca modifica nada. `llm/`/
`intent/`/`generation/` SI hacen network calls (al proveedor de LLM
configurado) -- la unica excepcion deliberada a "sin red" de este
paquete, acotada a INTERPRETAR/GENERAR texto, nunca a escribir codigo en
disco ni ejecutar nada por si solas.
"""
