"""
Tests para ai_editor/generation/performance.py -- FASE 56 "Performance"
(plan "AI Change Proposal Engine", 2026-08-11).

Corre el pipeline REAL (contra el repo real, mismo patron que
`test_ai_editor_generation_code_quality.py::_real_plan_and_context()`)
para verificar que las duraciones medidas son numeros reales (no
mockeados, no negativos) y que la etapa GENERATING_LLM queda
explicitamente NOT_MEASURED en vez de un numero fabricado.
"""
from ai_editor.generation.models import GenerationConfidence, PatchOperation, PatchProposal
from ai_editor.generation.performance import (
    STAGE_CODE_QUALITY,
    STAGE_GENERATING_LLM,
    STAGE_SANDBOX_VALIDATION_LOOP,
    measure_pipeline_stage_timings,
)
from ai_editor.intent.schema import ChangeIntent
from ai_editor.planner import build_change_plan
from ai_editor.resolver import resolve_change_context
from ai_editor.workspace import resolve_repo_file


def _real_proposal_plan_and_context():
    intent = ChangeIntent(
        id="perf-test", request="r", domain="core", intent="x",
        entities=["HomeCardGroupSelector.get_by_name"], scope=["backend"],
        confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)
    plan = build_change_plan(context)
    step1 = plan.to_dict()["steps"][0]
    real_path = resolve_repo_file(step1["file"])
    lines = real_path.read_text(encoding="utf-8").splitlines(keepends=True)
    exact_old = "".join(lines[step1["line_start"] - 1:step1["line_end"]])
    new_content = exact_old.replace("HomeCardGroup", "HomeCardGroupOK")
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=new_content, old_hash=None, expected_hash=None, reason="r",
    )
    proposal = PatchProposal(
        proposal_id="p", change_id="c", operations=[op], reasoning_summary="r",
        confidence=GenerationConfidence.from_score(0.9),
    )
    return proposal, plan, context


def test_generating_llm_stage_is_always_not_measured_never_fabricated():
    proposal, plan, context = _real_proposal_plan_and_context()

    report = measure_pipeline_stage_timings(proposal, plan, context)

    llm_stage = next(s for s in report.stages if s.stage == STAGE_GENERATING_LLM)
    assert llm_stage.duration_seconds is None
    assert "nunca se fabrica" in llm_stage.detail


def test_measured_stages_have_real_non_negative_durations():
    proposal, plan, context = _real_proposal_plan_and_context()

    report = measure_pipeline_stage_timings(proposal, plan, context)

    measured = [s for s in report.stages if s.duration_seconds is not None]
    assert len(measured) >= 5
    for s in measured:
        assert s.duration_seconds >= 0.0
    assert report.total_measured_seconds == sum(s.duration_seconds for s in measured)


def test_code_quality_and_sandbox_loop_stages_are_present():
    proposal, plan, context = _real_proposal_plan_and_context()

    report = measure_pipeline_stage_timings(proposal, plan, context)

    stage_names = {s.stage for s in report.stages}
    assert STAGE_SANDBOX_VALIDATION_LOOP in stage_names
    assert STAGE_CODE_QUALITY in stage_names


def test_report_to_dict_has_proposal_id_and_total():
    proposal, plan, context = _real_proposal_plan_and_context()

    report = measure_pipeline_stage_timings(proposal, plan, context)
    d = report.to_dict()

    assert d["proposal_id"] == "p"
    assert d["total_measured_seconds"] >= 0.0
    assert len(d["stages"]) == len(report.stages)
