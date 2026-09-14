"""
Unit tests para ai_editor/generation/test_awareness.py -- FASE 42
"Test-Aware Generation" (plan "AI Change Proposal Engine", 2026-08-11).
"""
from ai_editor.generation.models import GenerationConfidence, PatchOperation, PatchProposal
from ai_editor.generation.test_awareness import STATUS_FAIL, STATUS_PASS, check_test_awareness


def _proposal(operations, tests_to_remove=None):
    return PatchProposal(
        proposal_id="p42", change_id="c", operations=operations,
        reasoning_summary="r", confidence=GenerationConfidence.from_score(0.9),
        tests_to_remove=tests_to_remove or [],
    )


def _op(file, operation="MODIFY", old_content="x", new_content="y"):
    return PatchOperation(
        file=file, symbol=None, operation=operation, old_content=old_content,
        new_content=new_content, old_hash=None, expected_hash=None, reason="r",
    )


def test_deleting_a_test_file_without_declaring_it_fails():
    proposal = _proposal([_op("core/tests.py", operation="DELETE", new_content=None)])
    report = check_test_awareness(proposal)
    assert report.status == STATUS_FAIL
    assert report.issues[0].severity == "ERROR"


def test_deleting_a_declared_test_file_is_a_warning_not_a_failure():
    proposal = _proposal(
        [_op("core/tests.py", operation="DELETE", new_content=None)],
        tests_to_remove=["core/tests.py"],
    )
    report = check_test_awareness(proposal)
    assert report.status == STATUS_PASS
    assert report.issues[0].severity == "WARNING"


def test_modifying_a_test_file_is_not_flagged():
    proposal = _proposal([_op("core/tests.py", operation="MODIFY")])
    report = check_test_awareness(proposal)
    assert report.status == STATUS_PASS
    assert report.issues == []


def test_deleting_a_non_test_file_is_not_flagged():
    proposal = _proposal([_op("core/models.py", operation="DELETE", new_content=None)])
    report = check_test_awareness(proposal)
    assert report.status == STATUS_PASS
    assert report.issues == []


def test_recognizes_common_test_file_naming_conventions():
    for filename in ("app/tests.py", "app/test_foo.py", "app/foo_test.py", "app/tests_bar.py"):
        proposal = _proposal([_op(filename, operation="DELETE", new_content=None)])
        report = check_test_awareness(proposal)
        assert report.status == STATUS_FAIL, f"deberia detectar {filename} como archivo de test"
