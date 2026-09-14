"""
`build_change_plan()` -- POST-GRAPH 4 "Change Plan" (rediseno "AI Editor
Runtime", 2026-08-11).

Convierte un `ChangeContext` (POST-GRAPH 3, ya resuelto contra el grafo
real) en una secuencia de `PlanStep` concretos. **Cero llamadas nuevas al
grafo** -- toda la informacion (`file`/`symbol`/lineas/impacto) ya vino
resuelta en `context.resolution` (el envelope de `graph_client.
resolve_change()`, Fase 11); este modulo solo la REORDENA y le da forma
de plan, no vuelve a consultar `project_knowledge_graph`.

Orden de los pasos: el target principal SIEMPRE va primero (step 1,
`operation="MODIFY"`) -- es la unica entidad que el usuario pidio cambiar
explicitamente. El resto de los pasos son las categorias de IMPACTO real
(`contracts`/`frontend_consumers`/`backend_dependencies`/`tests`/
`documentation`, en ese orden) tal como las devolvio `calculate_change_
impact()` (Fase 10) -- osea, derivadas de las ARISTAS reales del grafo
(`CONSUMES_ENDPOINT`/`USES_STORE`/`TESTS`/`REFERENCES`/etc.), no una
plantilla arbitraria inventada aca (aunque coincida en espiritu con
`change_order`, el orden REAL de los pasos sale de que bucket de impacto
categorizo cada nodo, no de copiar ese texto estatico).

`operation` por bucket -- ninguno de estos es una decision fabricada, cada
uno refleja lo que realisticamente se sabe sobre esa entidad sin haber
generado codigo todavia (que es tarea de una fase futura, `patch/`, no de
esta):
  - target principal      -> MODIFY (el usuario pidio cambiar esto)
  - contracts/frontend/
    backend dependientes   -> REVIEW (puede verse afectado, no se sabe
                               todavia SI necesita un cambio real)
  - tests                  -> RUN (deben correr para validar el cambio,
                               no se asume que necesiten reescribirse)
  - documentation          -> REVIEW (puede quedar desactualizada)
"""
from ai_editor.planner.schema import STATUS_BLOCKED, STATUS_PLANNED, ChangePlan, PlanStep


def _make_step(step_num: int, node: dict, operation: str, reason: str,
                dependencies: list[int], risk: str, validation: str) -> PlanStep:
    meta = node.get("meta") or {}
    return PlanStep(
        step=step_num,
        file=node.get("file") or None,
        symbol=node["name"] if node.get("type") == "Symbol" else None,
        line_start=meta.get("start_line"),
        line_end=meta.get("end_line"),
        operation=operation,
        reason=reason,
        dependencies=dependencies,
        risk=risk,
        validation=validation,
    )


def build_change_plan(context) -> ChangePlan:
    """`context` es un `ai_editor.resolver.ChangeContext`. Si no llego a
    resolverse (POST-GRAPH 3 no encontro un target real), no hay nada
    real que planificar -- `BLOCKED`, nunca se inventa un plan sobre una
    resolucion incompleta."""
    context_dict = context.to_dict() if hasattr(context, "to_dict") else dict(context)
    resolution = context_dict.get("resolution")

    if resolution is None:
        return ChangePlan(
            context=context_dict, status=STATUS_BLOCKED,
            blocked_reason="ChangeContext sin 'resolution' real -- POST-GRAPH 3 no confirmo "
                            "un target contra el grafo, no hay nada que planificar.",
        )

    steps: list[PlanStep] = []
    step_num = 1

    primary_node = context_dict["primary_target"]
    intent = context_dict.get("intent") or {}
    steps.append(_make_step(
        step_num, primary_node, operation="MODIFY",
        reason=f"{intent.get('intent') or 'cambio solicitado'}: {intent.get('request', '')}".strip(": "),
        dependencies=[], risk=resolution.get("risk", "MEDIUM"),
        validation="Ejecutar los tests del paso RUN de este plan; correr de nuevo "
                    "graph_client.calculate_impact() sobre este target y comparar contra "
                    "el impacto aca listado (Graph Reconciliation, POST-GRAPH 9).",
    ))
    primary_step = step_num
    step_num += 1

    review_buckets = [
        ("contracts", "Contrato (Endpoint/Serializer) que expone o serializa el target -- "
                       "confirmar que sigue consistente tras el cambio."),
        ("frontend_consumers", "Consumidor frontend del target -- confirmar que la UI sigue "
                                "funcionando con el nuevo comportamiento."),
        ("backend_dependencies", "Dependencia backend del target -- confirmar que sigue "
                                  "funcionando con el nuevo comportamiento."),
    ]
    for key, reason in review_buckets:
        for node in resolution.get(key) or []:
            steps.append(_make_step(
                step_num, node, operation="REVIEW", reason=reason,
                dependencies=[primary_step], risk="LOW",
                validation="Revision manual o tests asociados a esta entidad.",
            ))
            step_num += 1

    tests = resolution.get("tests") or {}
    for node in (tests.get("direct_tests") or []) + (tests.get("indirect_tests") or []):
        steps.append(_make_step(
            step_num, node, operation="RUN",
            reason="Test que cubre el target o sus dependientes -- correr para validar el cambio.",
            dependencies=[primary_step], risk="LOW",
            validation="Debe seguir pasando (o empezar a pasar, si el cambio lo requiere) "
                        "despues de aplicar el patch.",
        ))
        step_num += 1

    documentation = resolution.get("documentation") or {}
    for category in ("architecture_docs", "implementation_docs", "audit_docs"):
        for node in documentation.get(category) or []:
            steps.append(_make_step(
                step_num, node, operation="REVIEW",
                reason="Documentacion que referencia el target -- revisar si sigue vigente.",
                dependencies=[primary_step], risk="LOW",
                validation="Revision manual del contenido contra el comportamiento nuevo.",
            ))
            step_num += 1

    return ChangePlan(context=context_dict, steps=steps, status=STATUS_PLANNED)
