"""
Unit tests para ai_editor/generation/dependency_awareness.py -- FASE 40
"Dependency-Aware Generation" (plan "AI Change Proposal Engine",
2026-08-11).
"""
from ai_editor.generation.dependency_awareness import (
    STATUS_FAIL,
    STATUS_PASS,
    check_dependency_awareness,
)
from ai_editor.generation.models import GenerationConfidence, PatchOperation, PatchProposal


def _proposal(file, old_content, new_content):
    op = PatchOperation(
        file=file, symbol=None, operation="MODIFY", old_content=old_content,
        new_content=new_content, old_hash=None, expected_hash=None, reason="r",
    )
    return PatchProposal(
        proposal_id="p40", change_id="c", operations=[op],
        reasoning_summary="r", confidence=GenerationConfidence.from_score(0.9),
    )


def test_new_python_import_is_detected():
    proposal = _proposal(
        "core/services/commands.py",
        "from django.db import transaction\n",
        "from django.db import transaction\nfrom core.models import HomeCardGroup\n",
    )
    report = check_dependency_awareness(proposal)
    assert report.status == STATUS_PASS
    assert report.new_imports["core/services/commands.py"] == ["core.models"]


def test_ai_engine_import_is_rejected():
    proposal = _proposal(
        "core/services/commands.py", "x = 1\n",
        "x = 1\nfrom ai_engine.llm_factory import get_llm\n",
    )
    report = check_dependency_awareness(proposal)
    assert report.status == STATUS_FAIL
    assert report.issues[0].module == "ai_engine.llm_factory"
    assert report.issues[0].severity == "ERROR"


def test_ai_engine_bare_import_is_rejected():
    proposal = _proposal("core/services/commands.py", "x = 1\n", "x = 1\nimport ai_engine\n")
    report = check_dependency_awareness(proposal)
    assert report.status == STATUS_FAIL


def test_no_new_imports_produces_empty_report():
    proposal = _proposal("core/services/commands.py", "x = 1\n", "x = 2\n")
    report = check_dependency_awareness(proposal)
    assert report.status == STATUS_PASS
    assert report.new_imports == {}
    assert report.issues == []


def test_pre_existing_import_is_not_flagged_as_new():
    """Un import que YA estaba en old_content no es 'nuevo', aunque siga
    presente en new_content."""
    proposal = _proposal(
        "core/services/commands.py",
        "from ai_engine.llm_factory import get_llm\nx = 1\n",
        "from ai_engine.llm_factory import get_llm\nx = 2\n",
    )
    report = check_dependency_awareness(proposal)
    assert report.new_imports == {}
    assert report.issues == []


def test_new_js_import_is_detected():
    proposal = _proposal(
        "frontend/src/views/Foo.vue",
        "<script setup>\n</script>\n",
        '<script setup>\nimport axios from "axios"\n</script>\n',
    )
    report = check_dependency_awareness(proposal)
    assert report.new_imports["frontend/src/views/Foo.vue"] == ["axios"]


def test_to_dict_serializes_issues_and_imports():
    proposal = _proposal(
        "core/services/commands.py", "x = 1\n", "x = 1\nfrom ai_engine.llm_factory import get_llm\n",
    )
    report = check_dependency_awareness(proposal)
    d = report.to_dict()
    assert d["status"] == STATUS_FAIL
    assert d["issues"][0]["module"] == "ai_engine.llm_factory"
    assert "core/services/commands.py" in d["new_imports"]
