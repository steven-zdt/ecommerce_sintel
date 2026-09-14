"""
Unit tests para ai_editor/generation/models.py -- FASE 25 "Generation
Domain Model" (plan "AI Change Proposal Engine", 2026-08-11).
"""
import pytest

from ai_editor.generation.models import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    ChangeGenerationRequest,
    GenerationConfidence,
    GenerationIssue,
    GenerationResult,
    PatchOperation,
    PatchProposal,
    SEVERITY_ERROR,
    STATUS_PROPOSED,
)


def test_generation_confidence_classifies_high_medium_low_by_real_thresholds():
    assert GenerationConfidence.from_score(0.95).level == CONFIDENCE_HIGH
    assert GenerationConfidence.from_score(0.8).level == CONFIDENCE_HIGH
    assert GenerationConfidence.from_score(0.6).level == CONFIDENCE_MEDIUM
    assert GenerationConfidence.from_score(0.5).level == CONFIDENCE_MEDIUM
    assert GenerationConfidence.from_score(0.2).level == CONFIDENCE_LOW


def test_generation_confidence_rejects_out_of_range_score():
    with pytest.raises(ValueError):
        GenerationConfidence(score=1.5, level=CONFIDENCE_HIGH)


def test_generation_confidence_rejects_invalid_level():
    with pytest.raises(ValueError):
        GenerationConfidence(score=0.5, level="SUPER_HIGH")


def test_patch_operation_rejects_invalid_operation():
    with pytest.raises(ValueError):
        PatchOperation(
            file="x.py", symbol=None, operation="RENAME", old_content=None,
            new_content="y", old_hash=None, expected_hash=None, reason="r",
        )


def test_patch_operation_accepts_valid_operation_and_round_trips_to_dict():
    op = PatchOperation(
        file="core/services/commands.py", symbol="HomeCardGroupSelector.get_by_name",
        operation="MODIFY", old_content="old", new_content="new",
        old_hash="abc", expected_hash="abc", reason="test real",
    )
    d = op.to_dict()
    assert d["file"] == "core/services/commands.py"
    assert d["operation"] == "MODIFY"


def test_patch_proposal_round_trips_to_dict_with_nested_operations_and_confidence():
    proposal = PatchProposal(
        proposal_id="gen-1", change_id="change-1",
        operations=[PatchOperation(
            file="a.py", symbol=None, operation="ADD", old_content=None,
            new_content="x = 1\n", old_hash=None, expected_hash=None, reason="r",
        )],
        reasoning_summary="resumen", confidence=GenerationConfidence.from_score(0.9),
        risks=["riesgo 1"], assumptions=["supuesto 1"], tests_to_update=["tests.py::test_x"],
    )
    d = proposal.to_dict()
    assert d["proposal_id"] == "gen-1"
    assert d["confidence"] == {"score": 0.9, "level": CONFIDENCE_HIGH}
    assert len(d["operations"]) == 1
    assert d["tests_to_update"] == ["tests.py::test_x"]


def test_change_generation_request_round_trips_to_dict():
    request = ChangeGenerationRequest(
        change_intent={"id": "i"}, change_plan={"status": "PLANNED"},
        graph_context={}, source_context={}, test_context={}, architecture_context={},
    )
    assert request.to_dict()["change_intent"] == {"id": "i"}


def test_generation_result_with_no_proposal_serializes_proposal_as_none():
    result = GenerationResult(
        status="REJECTED", proposal=None,
        issues=[GenerationIssue(code="X", message="m", severity=SEVERITY_ERROR)],
    )
    d = result.to_dict()
    assert d["proposal"] is None
    assert d["issues"][0]["code"] == "X"


def test_generation_result_with_proposal_serializes_nested_proposal():
    proposal = PatchProposal(
        proposal_id="gen-2", change_id="change-2", operations=[],
        reasoning_summary="r", confidence=GenerationConfidence.from_score(0.5),
    )
    result = GenerationResult(status=STATUS_PROPOSED, proposal=proposal)
    assert result.to_dict()["proposal"]["proposal_id"] == "gen-2"
