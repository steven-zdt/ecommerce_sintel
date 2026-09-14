"""
Unit tests para ai_editor/generation/architecture_compliance.py -- FASE
37 "Architectural Compliance" (plan "AI Change Proposal Engine",
2026-08-11).

Cada test verifica un check contra una regla REAL, ya documentada del
proyecto (ver docstring del modulo para la cita exacta de CLAUDE.md/
.AGENT.md de cada una) -- no reglas inventadas para esta fase.
"""
from ai_editor.generation.architecture_compliance import (
    STATUS_FAIL,
    STATUS_PASS,
    check_architectural_compliance,
)
from ai_editor.generation.models import GenerationConfidence, PatchOperation, PatchProposal


def _proposal(file, new_content, old_content="x"):
    op = PatchOperation(
        file=file, symbol=None, operation="MODIFY", old_content=old_content,
        new_content=new_content, old_hash=None, expected_hash=None, reason="r",
    )
    return PatchProposal(
        proposal_id="p37", change_id="c", operations=[op],
        reasoning_summary="r", confidence=GenerationConfidence.from_score(0.9),
    )


def test_selector_with_save_call_fails_with_error():
    proposal = _proposal("core/services/selectors.py", "def f():\n    obj.save()\n    return obj\n")
    report = check_architectural_compliance(proposal)
    assert report.status == STATUS_FAIL
    assert report.issues[0].rule == "selectors_no_side_effects"
    assert report.issues[0].severity == "ERROR"
    assert ".AGENT.md" in report.issues[0].source


def test_selector_read_only_passes():
    proposal = _proposal("core/services/selectors.py", "def f():\n    return Model.objects.filter(x=1)\n")
    report = check_architectural_compliance(proposal)
    assert report.status == STATUS_PASS
    assert report.issues == []


def test_viewset_direct_orm_access_is_a_warning_not_a_blocking_error():
    proposal = _proposal("renting/api/views.py", "def f():\n    return Model.objects.all()\n")
    report = check_architectural_compliance(proposal)
    assert report.status == STATUS_PASS  # WARNING no bloquea
    assert report.issues[0].rule == "viewsets_no_direct_orm"
    assert report.issues[0].severity == "WARNING"


def test_viewset_importing_drf_permissions_directly_fails_with_error():
    proposal = _proposal(
        "renting/api/views.py",
        "from rest_framework.permissions import IsAdminUser\n",
    )
    report = check_architectural_compliance(proposal)
    assert report.status == STATUS_FAIL
    assert report.issues[0].rule == "permissions_correct_import"
    assert "CLAUDE.md" in report.issues[0].source


def test_frontend_axios_direct_call_fails_with_error():
    proposal = _proposal(
        "frontend/src/views/Foo.vue",
        'import axios from "axios"\naxios.get("/x")\n',
    )
    report = check_architectural_compliance(proposal)
    assert report.status == STATUS_FAIL
    assert report.issues[0].rule == "frontend_no_direct_axios"


def test_clean_backend_change_produces_no_issues():
    proposal = _proposal("core/services/commands.py", "def f():\n    return 1\n")
    report = check_architectural_compliance(proposal)
    assert report.status == STATUS_PASS
    assert report.issues == []


def test_tenant_and_shared_components_are_honestly_documented_as_not_checked():
    """Regla del prompt maestro: 'no inventar reglas' -- este proyecto no
    tiene concepto de tenant real, y 'shared components' esta fuera de
    alcance de un chequeo por regex. Ambos deben aparecer documentados
    como no implementados, nunca fabricados como PASS silencioso."""
    proposal = _proposal("core/services/commands.py", "def f():\n    return 1\n")
    report = check_architectural_compliance(proposal)
    joined = " ".join(report.not_implemented)
    assert "tenant" in joined
    assert "shared components" in joined


def test_only_files_matching_the_relevant_pattern_are_checked():
    """Un archivo que no es selectors.py/views.py/frontend no dispara
    ningun check -- evita falsos positivos sobre codigo no relacionado."""
    proposal = _proposal("core/models.py", "obj.save()\n")
    report = check_architectural_compliance(proposal)
    assert report.status == STATUS_PASS
    assert report.issues == []


def test_to_dict_serializes_issues_and_not_implemented():
    proposal = _proposal("core/services/selectors.py", "obj.delete()\n")
    report = check_architectural_compliance(proposal)
    d = report.to_dict()
    assert d["status"] == STATUS_FAIL
    assert d["issues"][0]["rule"] == "selectors_no_side_effects"
    assert len(d["not_implemented"]) == 2
