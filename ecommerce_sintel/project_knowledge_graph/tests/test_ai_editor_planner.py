"""
Unit tests para ai_editor/planner/ -- POST-GRAPH 4 "Change Plan" (rediseno
"AI Editor Runtime", 2026-08-11). Aislados: construyen un `ChangeContext`
sintetico a mano (sin tocar el grafo real ni ai_editor.resolver) para
verificar la LOGICA de transformacion pura; la prueba de que el plan
resultante tiene sentido sobre datos reales (lineas reales,
dependencias reales) vive en test_pipeline_equivalence.py.
"""
from ai_editor.planner import STATUS_BLOCKED, STATUS_PLANNED, build_change_plan
from ai_editor.resolver.schema import STATUS_RESOLVED, ChangeContext


def _symbol_node(name, file, start, end):
    return {
        "id": f"symbol:{file}:{name}", "type": "Symbol", "name": name,
        "app": "x", "file": file, "meta": {"start_line": start, "end_line": end},
    }


def _resolution(target_node, contracts=None, frontend=None, backend=None,
                 direct_tests=None, indirect_tests=None, docs=None, risk="MEDIUM"):
    return {
        "found": True,
        "target": target_node,
        "risk": risk,
        "contracts": contracts or [],
        "frontend_consumers": frontend or [],
        "backend_dependencies": backend or [],
        "tests": {"direct_tests": direct_tests or [], "indirect_tests": indirect_tests or []},
        "documentation": {"architecture_docs": docs or [], "implementation_docs": [], "audit_docs": []},
    }


def test_blocked_when_context_has_no_resolution():
    context = ChangeContext(intent={"request": "x"}, status="UNRESOLVED", resolution=None)

    plan = build_change_plan(context)

    assert plan.status == STATUS_BLOCKED
    assert plan.steps == []
    assert "no confirmo" in plan.blocked_reason


def test_primary_target_is_always_step_1_with_modify_operation():
    target = _symbol_node("Foo.bar", "app/x.py", 10, 20)
    context = ChangeContext(
        intent={"intent": "add_field", "request": "agregar campo X"},
        status=STATUS_RESOLVED, primary_target=target,
        resolution=_resolution(target, risk="HIGH"),
    )

    plan = build_change_plan(context)

    assert plan.status == STATUS_PLANNED
    assert plan.steps[0].step == 1
    assert plan.steps[0].operation == "MODIFY"
    assert plan.steps[0].file == "app/x.py"
    assert plan.steps[0].symbol == "Foo.bar"
    assert plan.steps[0].line_start == 10
    assert plan.steps[0].line_end == 20
    assert plan.steps[0].risk == "HIGH"
    assert plan.steps[0].dependencies == []


def test_dependent_steps_reference_the_primary_step_as_dependency():
    target = _symbol_node("Foo.bar", "app/x.py", 10, 20)
    consumer = _symbol_node("Consumer.call", "app/consumer.py", 1, 5)
    context = ChangeContext(
        intent={"intent": "add_field", "request": "r"}, status=STATUS_RESOLVED,
        primary_target=target, resolution=_resolution(target, backend=[consumer]),
    )

    plan = build_change_plan(context)

    dependent_steps = [s for s in plan.steps if s.step != 1]
    assert len(dependent_steps) == 1
    assert dependent_steps[0].dependencies == [1]
    assert dependent_steps[0].operation == "REVIEW"


def test_tests_get_run_operation_not_modify_or_review():
    target = _symbol_node("Foo.bar", "app/x.py", 10, 20)
    test_node = _symbol_node("FooTestCase.test_bar", "app/tests.py", 1, 10)
    context = ChangeContext(
        intent={"intent": "add_field", "request": "r"}, status=STATUS_RESOLVED,
        primary_target=target, resolution=_resolution(target, indirect_tests=[test_node]),
    )

    plan = build_change_plan(context)

    test_steps = [s for s in plan.steps if s.symbol == "FooTestCase.test_bar"]
    assert len(test_steps) == 1
    assert test_steps[0].operation == "RUN"


def test_node_without_symbol_type_gets_none_symbol_and_line_fields():
    """Un Endpoint/Model/FrontendView no es un `Symbol` -- no tiene rango
    de lineas util, el plan no debe inventar uno."""
    target = _symbol_node("Foo.bar", "app/x.py", 10, 20)
    endpoint_node = {"id": "endpoint:api/v1/x", "type": "Endpoint", "name": "api/v1/x",
                      "app": "x", "file": "", "meta": {}}
    context = ChangeContext(
        intent={"intent": "add_field", "request": "r"}, status=STATUS_RESOLVED,
        primary_target=target, resolution=_resolution(target, contracts=[endpoint_node]),
    )

    plan = build_change_plan(context)

    contract_step = next(s for s in plan.steps if s.step == 2)
    assert contract_step.symbol is None
    assert contract_step.file is None  # "" se normaliza a None, no se inventa un path
    assert contract_step.line_start is None
    assert contract_step.line_end is None


def test_step_numbers_are_sequential_across_all_buckets():
    target = _symbol_node("Foo.bar", "app/x.py", 10, 20)
    nodes = [_symbol_node(f"N{i}.m", f"app/n{i}.py", 1, 2) for i in range(4)]
    context = ChangeContext(
        intent={"intent": "x", "request": "r"}, status=STATUS_RESOLVED,
        primary_target=target,
        resolution=_resolution(target, contracts=[nodes[0]], frontend=[nodes[1]],
                                backend=[nodes[2]], indirect_tests=[nodes[3]]),
    )

    plan = build_change_plan(context)

    assert [s.step for s in plan.steps] == list(range(1, len(plan.steps) + 1))
