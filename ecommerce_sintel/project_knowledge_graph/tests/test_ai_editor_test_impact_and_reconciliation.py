"""
Unit tests para ai_editor/validation/tests.py (POST-GRAPH 10) y
ai_editor/validation/reconciliation.py (POST-GRAPH 9) -- rediseno "AI
Editor Runtime", 2026-08-11. Aislados: `ChangeContext` sintetico. La
prueba de clasificacion sobre tests reales del grafo vive en
test_pipeline_equivalence.py.
"""
from ai_editor.resolver.schema import STATUS_RESOLVED, ChangeContext
from ai_editor.validation import (
    RECONCILIATION_NOT_IMPLEMENTED_REASON,
    build_test_validation_report,
    classify_tests,
    reconcile_graph,
)


def _context(direct_tests=None, indirect_tests=None):
    return ChangeContext(
        intent={"request": "r"}, status=STATUS_RESOLVED,
        primary_target={"id": "x", "type": "Model", "name": "X"},
        resolution={
            "found": True,
            "tests": {"direct_tests": direct_tests or [], "indirect_tests": indirect_tests or []},
        },
    )


def _test_node(name):
    return {"id": f"symbol:x:{name}", "type": "Symbol", "name": name, "app": "x", "file": "x.py", "meta": {}}


def test_direct_tests_are_required_indirect_are_recommended():
    context = _context(
        direct_tests=[_test_node("FooTestCase.test_direct")],
        indirect_tests=[_test_node("BarTestCase.test_indirect")],
    )

    classified = classify_tests(context)

    assert [t["name"] for t in classified["required"]] == ["FooTestCase.test_direct"]
    assert [t["name"] for t in classified["recommended"]] == ["BarTestCase.test_indirect"]
    assert classified["optional"] == []


def test_report_never_claims_tests_were_run():
    context = _context(direct_tests=[_test_node("FooTestCase.test_direct")])

    report = build_test_validation_report(context)

    assert report["tests_run"] is False
    assert report["passed"] is None
    assert report["failed"] is None
    assert "Django/Postgres/Redis/Docker" in report["tests_run_note"]


def test_report_counts_match_the_lists():
    context = _context(
        direct_tests=[_test_node("A.test_a"), _test_node("B.test_b")],
        indirect_tests=[_test_node("C.test_c")],
    )

    report = build_test_validation_report(context)

    assert report["required_count"] == 2
    assert report["recommended_count"] == 1
    assert report["required"] == ["A.test_a", "B.test_b"]


def test_empty_context_produces_empty_report():
    context = _context()
    report = build_test_validation_report(context)
    assert report["required"] == []
    assert report["recommended"] == []
    assert report["required_count"] == 0


def test_reconcile_graph_always_reports_not_implemented_regardless_of_input():
    result = reconcile_graph(plan="cualquier cosa, no importa")
    assert result.status == "NOT_IMPLEMENTED"
    assert result.reason == RECONCILIATION_NOT_IMPLEMENTED_REASON
    assert result.to_dict() == {"status": "NOT_IMPLEMENTED", "reason": RECONCILIATION_NOT_IMPLEMENTED_REASON}
