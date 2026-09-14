# Autonomous Change Loop -- Fase 17 (Site Knowledge Graph / AI Editor Runtime, 2026-08-10)

## Que pide esta fase del plan

Un loop que encadene automaticamente `detect changes -> resolve target ->
plan -> patch -> validate -> (si falla) rollback/retry`, corriendo sin
intervencion humana entre pasos.

## Por que esta fase es SOLO documentacion, otra vez (mismo criterio que Fase 14)

`ai_editor/__init__.py` (Fase 14) ya dejo `patch/` deliberadamente sin
implementar: generar y APLICAR modificaciones automaticas a archivos de
codigo es una accion dificil de revertir con blast radius sobre todo el
repositorio, y requiere una decision humana explicita y separada -- no es
consecuencia implicita de "evolucionar el grafo de conocimiento". Esa
misma regla aplica aca con mas fuerza todavia: un LOOP que repite ese paso
automaticamente (potencialmente varias veces, sobre varios archivos, sin
pausa) es una escalada del mismo riesgo, no una capacidad nueva y separada
que se pueda evaluar de forma aislada.

**Construir el loop de orquestacion sin que `patch/` exista todavia no
tiene sentido funcional** (no hay nada real que orquestar en ese paso
salvo un stub), y construir el loop CON un `patch/` real seria la decision
de alto impacto que Fase 14 ya identifico como fuera de alcance de este
cambio. Por lo tanto Fase 17 documenta el DISENO del loop y el punto
exacto donde se detiene hoy, sin agregar codigo ejecutable de
orquestacion.

## Diseno intencionado del loop (documentado, no implementado)

```
  1. DETECT      -- incremental/diff.py::detect_changed_symbols() [REAL, Fase 15]
         |
         v
  2. RESOLVE     -- graph_sdk.resolve_change(target) [REAL, Fase 11/13]
         |
         v
  3. IMPACT      -- graph_sdk.calculate_impact(target) [REAL, Fase 10/13]
         |
         v
  4. PLAN        -- graph_sdk.build_change_plan(target) [REAL, Fase 13 --
                     orden RECOMENDADO, plantilla estatica, no calculado
                     dinamicamente]
         |
         v
  5. [HUMAN GATE]  -- punto de parada obligatorio: un humano revisa el plan
                     y decide si autoriza aplicar un patch. NO es un paso
                     tecnico pendiente de "implementar despues" -- es una
                     decision de producto/seguridad, igual que la
                     "Explicit permission required" que ya rige cualquier
                     accion dificil de revertir en este entorno.
         |
         v
  6. PATCH       -- ai_editor/patch/ [PLANIFICADO, NO IMPLEMENTADO -- Fase 14]
         |
         v
  7. VALIDATE    -- project_knowledge_graph/audit/change_validation.py::
                     build_change_validation_report() [REAL, Fase 16] --
                     corrido DESPUES del patch para confirmar que el grafo/
                     contratos siguen consistentes y listar los tests que
                     hay que correr
         |
         v
  8. ROLLBACK    -- [PLANIFICADO, NO IMPLEMENTADO] si (7) reporta
                     inconsistencia real, revertir el patch aplicado en (6)
```

## Lo que SI es real hoy (pasos 1-4 y 7, todos ya construidos en fases previas)

Los pasos 1, 2, 3, 4 y 7 del diagrama de arriba **ya existen y estan
probados contra el repo real** -- no son parte de esta fase, son el
trabajo de Fases 10/11/13/15/16. Lo unico que Fase 17 podria haber
agregado es la orquestacion automatica ENTRE esos pasos y los pasos 6/8
(que no existen). Encadenar 1->2->3->4->7 sin pasar por 5/6/8 no es un
"loop de cambio autonomo" -- es simplemente llamar 4 funciones de
solo-lectura en secuencia, que ya se puede hacer manualmente (o desde un
script trivial) sin necesitar un modulo nuevo.

## Estado real de `ai_editor/` tras esta fase

Sin cambios de codigo respecto a Fase 14 (ver `ai_editor/__init__.py`,
seccion "ESTADO REAL"). `patch/__init__.py` y `repository/__init__.py`
siguen siendo docstrings puros sin logica ejecutable (verificado por AST
en `project_knowledge_graph/tests/test_ai_editor_scaffold.py`).

## Que se necesitaria para des-bloquear esto en el futuro

1. Decision humana explicita de construir `patch/` (generar diffs +
   aplicarlos a archivos reales) -- fuera de alcance de este chat/sesion.
2. Un mecanismo real de aprobacion humana ANTES de cada aplicacion de
   patch (paso 5), no una bandera de configuracion que se pueda
   desactivar silenciosamente.
3. `repository/` con acceso de escritura controlado (probablemente sobre
   una rama/worktree aislada, nunca directo sobre el checkout principal).
4. `validation/` orquestando (7) automaticamente post-patch y decidiendo
   rollback (8) segun el resultado -- la logica de (7) ya existe
   (Fase 16), falta la orquestacion condicional.

**CHECKPOINT: PASS** (alcance: documentacion del diseno + razon explicita
de por que no se implementa orquestacion ejecutable; 0 archivos de codigo
nuevos, 0 tests nuevos -- no hay comportamiento nuevo que probar).

---

## ACTUALIZACION POST-GRAPH 14 (2026-08-11) -- el diagrama de arriba quedo desactualizado

Todo lo de arriba se escribio cuando `ai_editor/` era casi enteramente
scaffold. Desde entonces (rediseno "AI Editor Runtime", POST-GRAPH 0-13,
2026-08-11) **los 10 submodulos de `ai_editor/` tienen logica real** --
ver `ai_editor/.AGENT/AI_EDITOR_BASELINE.md` para el detalle fase por
fase. La conclusion de esta seccion (POST-GRAPH 14) NO cambia respecto a
Fase 17: **sigue sin construirse ningun codigo de orquestacion
automatica**, por el mismo motivo de seguridad, ahora con mas fuerza
porque hay mas piezas reales que orquestar (mas superficie de riesgo, no
menos). Se actualiza el diagrama para que sea util como mapa real del
sistema, no como excusa para orquestar.

### Diagrama actualizado (estado real, 2026-08-11)

```
  1. DETECT      -- incremental/diff.py::detect_changed_symbols() [REAL, Fase 15]
         |
         v
  2. INTENT      -- ai_editor.intent.interpret_request() [REAL, POST-GRAPH 2] --
         |          LLM interpreta + graph_client.find_node() confirma el dominio
         v
  3. RESOLVE     -- ai_editor.resolver.resolve_change_context() [REAL, POST-GRAPH 3] --
         |          cada entidad exige coincidencia EXACTA contra el grafo
         v
  4. PLAN        -- ai_editor.planner.build_change_plan() [REAL, POST-GRAPH 4]
         |
         v
  5. VALIDATE PLAN -- ai_editor.planner.validate_plan() [REAL, POST-GRAPH 5] --
         |            confirma archivos/lineas contra el disco real
         v
  6. SANDBOX     -- ai_editor.repository.create_sandbox() [REAL, POST-GRAPH 7]
         |
         v
  7. PATCH       -- ai_editor.patch.apply_operation() [REAL PERO ACOTADO,
         |          POST-GRAPH 6] -- aplica un `new_content` YA DECIDIDO
         |          (por un humano o un test) con verificacion de
         |          fingerprint; NO genera codigo el mismo
         v
  8. VALIDATE (Nivel 1) -- ai_editor.validation.run_validation() [REAL PARCIAL,
         |                  POST-GRAPH 8] -- solo sintaxis; Niveles 2-5 y
         |                  Graph Reconciliation [NOT_IMPLEMENTED, POST-GRAPH 8/9]
         v
  9. TEST IMPACT -- ai_editor.validation.build_test_validation_report() [REAL
         |          PARCIAL, POST-GRAPH 10] -- identifica tests, no los corre
         v
  10. [HUMAN GATE] -- ai_editor.approval.build_change_summary() +
         |            record_decision() [REAL, POST-GRAPH 11] -- sigue siendo
         |            el punto de parada OBLIGATORIO, ahora con datos reales
         |            de cada paso anterior en vez de un concepto abstracto
         v
  11. COMMIT     -- ai_editor.repository.promote_to_workspace()/commit_changes()
         |          [REAL PERO GATEADO, POST-GRAPH 12] -- exige
         |          ApprovalRecord(APPROVE) + confirm=True + sin drift de
         |          fingerprint; NUNCA invocado contra el checkout real en
         |          ninguna sesion hasta ahora
         v
  12. AUDIT      -- ai_editor.audit.audit_pipeline_run() [REAL, POST-GRAPH 13] --
                    registra la corrida completa, nunca secretos
```

### Por que sigue sin haber un `run_autonomous_loop()`

Cada flecha del diagrama de arriba se puede ENCADENAR manualmente hoy
(un script que llama las 12 funciones en orden ya funcionaria end-to-end
sobre codigo real, como demuestran los tests de integracion de cada
POST-GRAPH). Lo que NO existe -- a proposito, sin cambios respecto a la
decision original de Fase 17 -- es una funcion que haga ese encadenado
SOLA, sin que un humano dispare cada paso 10/11 deliberadamente. La razon
sigue siendo la misma: automatizar el ciclo completo (en particular saltar
del paso 9 al 11 sin que un humano mire el CHANGE SUMMARY del paso 10)
es la decision de alto impacto que este proyecto reserva para una
autorizacion separada y explicita, nunca una consecuencia implicita de
haber terminado de construir las piezas individuales.

**CHECKPOINT POST-GRAPH 14: PASS** (alcance: actualizacion de
documentacion para reflejar el estado real de 10 submodulos con logica
real; 0 codigo de orquestacion nuevo, 0 tests nuevos -- la decision de
Fase 17 de no construir el loop automatico sigue vigente sin cambios).
