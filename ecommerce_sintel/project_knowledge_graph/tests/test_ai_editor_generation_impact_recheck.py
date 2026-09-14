"""
Integration tests para ai_editor/generation/impact_recheck.py -- FASE 35
"Impact Recheck" (plan "AI Change Proposal Engine", 2026-08-11).

El test `test_predicted_vs_actual_via_bucket_sum_would_have_produced_a_
false_block` documenta explicitamente el bug real encontrado y
corregido durante esta fase (ver docstring de impact_recheck.py).
"""
from ai_editor.generation.impact_recheck import (
    STATUS_BLOCK,
    STATUS_PASS,
    ImpactBaseline,
    capture_impact_baseline,
    recheck_impact,
)
from ai_editor.intent.schema import ChangeIntent
from ai_editor.resolver import resolve_change_context


def _real_context(entities=("HomeCardGroupSelector.get_by_name",), scope=("backend",), domain="core"):
    intent = ChangeIntent(
        id="test-impact-recheck", request="r", domain=domain, intent="x",
        entities=list(entities), scope=list(scope), confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    return resolve_change_context(intent)


def test_capture_impact_baseline_returns_real_data_from_the_graph():
    context = _real_context()
    baseline = capture_impact_baseline(context)
    assert baseline is not None
    assert baseline.target == "HomeCardGroupSelector.get_by_name"
    assert baseline.risk in ("LOW", "MEDIUM", "HIGH")
    assert isinstance(baseline.total_affected, int)
    assert baseline.captured_at


def test_recheck_immediately_after_baseline_passes_no_drift():
    """Sin drift real del grafo entre capturar el baseline y el recheck
    (corren en el mismo instante) -- debe dar PASS, no un falso BLOCK."""
    context = _real_context()
    baseline = capture_impact_baseline(context)
    report = recheck_impact(baseline)

    assert report.status == STATUS_PASS
    assert report.predicted_risk == report.actual_risk
    assert report.predicted_total_affected == report.actual_total_affected


def test_predicted_vs_actual_via_bucket_sum_would_have_produced_a_false_block():
    """Documenta el bug real: aproximar 'predicted_total_affected' sumando
    contracts+frontend_consumers+backend_dependencies de ChangeContext.
    resolution (lo que hace approval.gate.build_change_summary() para
    OTRO proposito) da un numero MENOR que el total_affected real de
    calculate_impact() (que tambien cuenta tests/docs/config/otros) --
    compararlos habria producido BLOCK siempre, sin drift real."""
    context = _real_context(entities=["EquipmentViewSet.check_availability"], domain="renting")
    context_dict = context.to_dict()
    resolution = context_dict["resolution"]
    bucket_sum_approximation = (
        len(resolution.get("contracts") or [])
        + len(resolution.get("frontend_consumers") or [])
        + len(resolution.get("backend_dependencies") or [])
    )

    baseline = capture_impact_baseline(context)

    assert bucket_sum_approximation < baseline.total_affected, (
        "si esto deja de ser cierto, la aproximacion por buckets ya no seria un bug real -- "
        "pero al momento de escribir este test, confirmado que subestima."
    )


def test_recheck_blocks_when_baseline_is_none():
    report = recheck_impact(None)
    assert report.status == STATUS_BLOCK


def test_recheck_blocks_when_target_no_longer_found_in_the_graph():
    fake_baseline = ImpactBaseline(target="EstoNoExisteEnElGrafoNunca123", risk="LOW", total_affected=0)
    report = recheck_impact(fake_baseline)
    assert report.status == STATUS_BLOCK
    assert "ya no se encuentra" in report.detail


def test_recheck_blocks_when_actual_risk_is_higher_than_baseline():
    """Simula drift real: un baseline artificialmente bajo comparado
    contra el estado real actual del grafo."""
    real_baseline = capture_impact_baseline(_real_context(
        entities=["EquipmentViewSet.check_availability"], domain="renting",
    ))
    artificially_low_baseline = ImpactBaseline(
        target=real_baseline.target, risk="LOW", total_affected=0,
    )
    report = recheck_impact(artificially_low_baseline)
    assert report.status == STATUS_BLOCK
    assert "subio" in report.detail


def test_capture_impact_baseline_returns_none_for_context_without_primary_target():
    empty_context = {"primary_target": None, "resolution": None}
    assert capture_impact_baseline(empty_context) is None
