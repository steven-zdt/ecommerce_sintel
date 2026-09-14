"""
`measure_pipeline_stage_timings()` -- FASE 56 "Performance" (plan "AI
Change Proposal Engine", 2026-08-11).

Mide DURACION REAL (no estimada) de cada etapa del pipeline que no
requiere una llamada real a un LLM -- esta ejecucion nunca invoco un
provider real (Ollama/OpenAI/Anthropic) durante todo el desarrollo del
plan de 60 fases (ver `generator.py`, docstring: "sin probar todavia
contra un LLM real"), asi que la etapa GENERATING (LLM) queda
explicitamente `NOT_MEASURED` -- nunca se fabrica un numero para ella.
Las etapas SI medidas usan las funciones REALES de `generation/`,
llamadas con un `proposal` ya construido a mano (mismo patron que
`test_ai_editor_generation_code_quality.py`/`_reconciliation.py`), nunca
mockeadas.
"""
import time
from dataclasses import dataclass, field

from ai_editor.generation.code_quality import run_code_quality_checks
from ai_editor.generation.confidence_engine import compute_composite_confidence
from ai_editor.generation.human_review import render_full_review
from ai_editor.generation.impact_recheck import capture_impact_baseline, recheck_impact
from ai_editor.generation.reconciliation import reconcile_change_scope
from ai_editor.generation.sandbox_loop import run_sandbox_validation_loop

STAGE_SANDBOX_VALIDATION_LOOP = "SANDBOX_VALIDATION_LOOP"
STAGE_CODE_QUALITY = "CODE_QUALITY"
STAGE_RECONCILIATION = "RECONCILIATION"
STAGE_IMPACT_RECHECK = "IMPACT_RECHECK"
STAGE_CONFIDENCE = "CONFIDENCE"
STAGE_HUMAN_REVIEW = "HUMAN_REVIEW"
STAGE_GENERATING_LLM = "GENERATING_LLM"

NOT_MEASURED = "NOT_MEASURED"


@dataclass
class StageTiming:
    stage: str
    duration_seconds: float | None
    detail: str = ""

    def to_dict(self) -> dict:
        return {"stage": self.stage, "duration_seconds": self.duration_seconds, "detail": self.detail}


@dataclass
class PipelineTimingReport:
    proposal_id: str
    stages: list[StageTiming] = field(default_factory=list)
    total_measured_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "stages": [s.to_dict() for s in self.stages],
            "total_measured_seconds": self.total_measured_seconds,
        }


def _timed(stage: str, fn, *args, **kwargs):
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    duration = time.perf_counter() - start
    return result, StageTiming(stage=stage, duration_seconds=duration)


def measure_pipeline_stage_timings(proposal, plan, context) -> PipelineTimingReport:
    """`proposal`/`plan`/`context` YA construidos y validos (mismo
    precondicion que el resto de `generation/`) -- esta funcion no
    genera nada nuevo, solo cronometra las etapas reales que SI pueden
    correr sin depender de un LLM externo. La etapa GENERATING (LLM) se
    reporta aparte, siempre `NOT_MEASURED` (ver docstring del modulo)."""
    stages: list[StageTiming] = [
        StageTiming(stage=STAGE_GENERATING_LLM, duration_seconds=None,
                    detail="Ningun LLM real se invoco durante el desarrollo de este plan -- "
                            "nunca se fabrica un tiempo para esta etapa."),
    ]

    loop_result, timing = _timed(STAGE_SANDBOX_VALIDATION_LOOP, run_sandbox_validation_loop,
                                  proposal, plan, context)
    stages.append(timing)

    try:
        _, timing = _timed(STAGE_CODE_QUALITY, run_code_quality_checks, loop_result.sandbox, proposal)
        stages.append(timing)

        _, timing = _timed(STAGE_RECONCILIATION, reconcile_change_scope, proposal, loop_result, plan, context)
        stages.append(timing)

        baseline, timing = _timed(STAGE_IMPACT_RECHECK, capture_impact_baseline, context)
        stages.append(timing)
        if baseline is not None:
            _, timing = _timed(STAGE_IMPACT_RECHECK + "_RECHECK", recheck_impact, baseline)
            stages.append(timing)

        confidence_report, timing = _timed(
            STAGE_CONFIDENCE, compute_composite_confidence, proposal, context=context,
        )
        stages.append(timing)

        _, timing = _timed(STAGE_HUMAN_REVIEW, render_full_review, proposal,
                            confidence_report=confidence_report)
        stages.append(timing)
    finally:
        loop_result.sandbox.cleanup()

    total = sum(s.duration_seconds for s in stages if s.duration_seconds is not None)
    return PipelineTimingReport(proposal_id=proposal.proposal_id, stages=stages, total_measured_seconds=total)


__all__ = [
    "measure_pipeline_stage_timings", "PipelineTimingReport", "StageTiming",
    "STAGE_SANDBOX_VALIDATION_LOOP", "STAGE_CODE_QUALITY", "STAGE_RECONCILIATION",
    "STAGE_IMPACT_RECHECK", "STAGE_CONFIDENCE", "STAGE_HUMAN_REVIEW", "STAGE_GENERATING_LLM",
    "NOT_MEASURED",
]
