"""
Unit tests para audit/change_validation.py -- Fase 16 "Change Validation",
Site Knowledge Graph, 2026-08-10. Aislados con mocks; la prueba contra el
repo real (agregacion sobre un simbolo real conocido, forma estable del
reporte sea cual sea el git diff del momento) vive en
test_pipeline_equivalence.py.
"""
from unittest.mock import MagicMock, patch

from project_knowledge_graph.audit.change_validation import (
    _RISK_ORDER,
    build_change_validation_report,
)


def _fake_impact(risk="LOW", contract=None, frontend=None, backend=None,
                  direct_tests=None, indirect_tests=None):
    empty = []
    return {
        "found": True,
        "direct_impact": {"contract": contract or [], "frontend": frontend or [], "backend": []},
        "indirect_impact": {"contract": [], "frontend": [], "backend": backend or []},
        "risk": risk,
        "tests": {"direct_tests": direct_tests or [], "indirect_tests": indirect_tests or []},
        "documentation": {"architecture_docs": [], "implementation_docs": [], "audit_docs": []},
    }


def test_risk_order_is_monotonic():
    assert _RISK_ORDER["LOW"] < _RISK_ORDER["MEDIUM"] < _RISK_ORDER["HIGH"]


@patch("project_knowledge_graph.audit.change_validation.get_knowledge_graph")
@patch("project_knowledge_graph.audit.change_validation.run_all_validations")
@patch("project_knowledge_graph.audit.change_validation.calculate_change_impact")
@patch("project_knowledge_graph.audit.change_validation.detect_changed_symbols")
def test_reports_no_changes_when_git_diff_is_empty(
    mock_detect, mock_impact, mock_validate, mock_get_kg
):
    mock_detect.return_value = []
    mock_validate.return_value = {"summary": {"orphaned_app_docs": 0}}
    mock_get_kg.return_value = MagicMock(nodes_of_type=lambda t: [])

    report = build_change_validation_report()

    assert report["files_changed"] == []
    assert report["symbols_changed"] == []
    assert report["risk"] == "LOW"
    assert report["tests_run"] is False
    mock_impact.assert_not_called()


@patch("project_knowledge_graph.audit.change_validation.get_knowledge_graph")
@patch("project_knowledge_graph.audit.change_validation.run_all_validations")
@patch("project_knowledge_graph.audit.change_validation.calculate_change_impact")
@patch("project_knowledge_graph.audit.change_validation.detect_changed_symbols")
def test_takes_the_highest_risk_across_multiple_changed_symbols(
    mock_detect, mock_impact, mock_validate, mock_get_kg
):
    mock_detect.return_value = [
        {"name": "Low.method", "file": "app/a.py"},
        {"name": "High.method", "file": "app/b.py"},
    ]
    mock_impact.side_effect = [_fake_impact(risk="LOW"), _fake_impact(risk="HIGH")]
    mock_validate.return_value = {"summary": {}}
    mock_get_kg.return_value = MagicMock(nodes_of_type=lambda t: [])

    report = build_change_validation_report()

    assert report["risk"] == "HIGH"
    assert report["files_changed"] == ["app/a.py", "app/b.py"]


@patch("project_knowledge_graph.audit.change_validation.get_knowledge_graph")
@patch("project_knowledge_graph.audit.change_validation.run_all_validations")
@patch("project_knowledge_graph.audit.change_validation.calculate_change_impact")
@patch("project_knowledge_graph.audit.change_validation.detect_changed_symbols")
def test_flags_endpoint_missing_serializer_edge_as_inconsistent(
    mock_detect, mock_impact, mock_validate, mock_get_kg
):
    mock_detect.return_value = [{"name": "Some.method", "file": "app/a.py"}]
    mock_impact.return_value = _fake_impact(
        contract=[{"name": "api/v1/orphan"}],
    )
    mock_validate.return_value = {"summary": {}}

    endpoint_node = MagicMock(id="endpoint:api/v1/orphan")
    endpoint_node.name = "api/v1/orphan"  # "name" is a reserved MagicMock kwarg, must set after construction
    kg = MagicMock()
    kg.nodes_of_type.return_value = [endpoint_node]
    kg.successors.return_value = [{"edge": "BELONGS_TO", "node": {}}]  # sin IMPLEMENTED_BY/SERIALIZES
    mock_get_kg.return_value = kg

    report = build_change_validation_report()

    assert report["contract_consistency"]["consistent"] is False
    issues = {i["issue"] for i in report["contract_consistency"]["issues"]}
    assert "sin Symbol que lo implemente" in issues
    assert "sin Serializer asociado" in issues
