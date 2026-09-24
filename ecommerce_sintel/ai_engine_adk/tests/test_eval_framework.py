"""
HARDENING F10 (2026-09-24) -- pruebas del propio framework de evaluacion (dataset, fingerprint, gate, runner).
ESCRITO PERO NO EJECUTADO (regla vigente: no correr tests sin autorizacion del usuario). Deterministas, sin LLM ni red.
"""
import json
from pathlib import Path

import pytest

from eval import fingerprint, gate, schema


def test_dataset_valido_sin_ids_duplicados_y_con_todas_las_categorias():
    cases = schema.load_dataset()
    assert len({c["id"] for c in cases}) == len(cases)
    assert set(schema.CATEGORIES) <= {c["category"] for c in cases}


def test_cada_categoria_tiene_el_minimo_de_casos():
    cases = schema.load_dataset()
    for cat in schema.CATEGORIES:
        assert sum(1 for c in cases if c["category"] == cat) >= schema.MIN_CASES_PER_CATEGORY, cat


def test_validate_case_detecta_errores():
    assert schema.validate_case({"id": "A-001"})  # faltan campos
    bad = {"id": "B-001", "category": "A", "tier": "l1", "kind": "x", "input": {}, "expected": {}, "severity": "high", "source": "s"}
    assert any("id debe empezar" in e for e in schema.validate_case(bad))


def test_load_dataset_rechaza_json_invalido(tmp_path):
    (tmp_path / "x.jsonl").write_text("{no es json}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        schema.load_dataset(tmp_path)


def test_fingerprint_estable_y_sensible_a_un_cambio(monkeypatch, tmp_path):
    (tmp_path / "ai_engine").mkdir()
    f = tmp_path / "ai_engine" / "model_chain.py"
    f.write_text("a = 1\n", encoding="utf-8")
    monkeypatch.setattr(fingerprint, "ROOT", tmp_path)
    monkeypatch.setattr(fingerprint, "COMPONENTS", {"model": ["ai_engine/model_chain.py"], "reranker": []})
    first = fingerprint.compute()
    assert fingerprint.compute() == first
    f.write_text("a = 2\n", encoding="utf-8")
    assert fingerprint.changed_components(fingerprint.compute(), first) == ["model"]


def test_fingerprint_ignora_diferencias_crlf(monkeypatch, tmp_path):
    (tmp_path / "ai_engine").mkdir()
    f = tmp_path / "ai_engine" / "model_chain.py"
    monkeypatch.setattr(fingerprint, "ROOT", tmp_path)
    monkeypatch.setattr(fingerprint, "COMPONENTS", {"model": ["ai_engine/model_chain.py"]})
    f.write_bytes(b"a = 1\n")
    lf = fingerprint.compute()
    f.write_bytes(b"a = 1\r\n")
    assert fingerprint.compute() == lf


def _report(components, violations=0, failures=(), image=True, tier="l1", pass_rate=1.0, env=None):
    return {"fingerprint": fingerprint.overall(components), "components": components, "tier": tier, "image_in_sync": image,
            "metrics": {"security.violations": violations, "A.pass_rate": pass_rate}, "failures": list(failures),
            "runtime_env": env or {}}


THRESHOLDS = {"absolute": {"security.violations": 0}, "ge_baseline": ["A.pass_rate"]}
COMP = {"model": "a", "tool": "b"}


def test_gate_ok_cuando_todo_coincide():
    assert gate.check([_report(COMP)], THRESHOLDS, current_components=COMP) == []


def test_gate_falla_ante_cambio_sin_evaluar():
    problems = gate.check([_report(COMP)], THRESHOLDS, current_components={"model": "a", "tool": "CAMBIO"})
    assert any("tool" in p and "SIN evaluar" in p for p in problems)


def test_gate_falla_si_la_imagen_no_coincide_con_el_repo():
    assert any("imagen" in p for p in gate.check([_report(COMP, image=False)], THRESHOLDS, current_components=COMP))


def test_gate_falla_ante_violacion_de_seguridad():
    assert any("security.violations" in p for p in gate.check([_report(COMP, violations=1)], THRESHOLDS, current_components=COMP))


def test_gate_suma_violaciones_de_varios_reportes():
    reports = [_report(COMP, violations=0), _report(COMP, violations=1)]
    assert any("security.violations=1" in p for p in gate.check(reports, THRESHOLDS, current_components=COMP))


def test_gate_falla_ante_regresion_contra_baseline():
    problems = gate.check([_report(COMP, pass_rate=0.8)], THRESHOLDS, baseline=_report(COMP, pass_rate=0.9), current_components=COMP)
    assert any("A.pass_rate cayo" in p for p in problems)


def test_gate_falla_si_cambia_el_modelo_activo_respecto_al_baseline():
    live = _report(COMP, tier="live", env={"LOCAL_MODEL_CHAIN": "x"})
    base = _report(COMP, tier="live", env={"LOCAL_MODEL_CHAIN": "y"})
    assert any("modelo/embedding" in p for p in gate.check([live], THRESHOLDS, baseline=base, current_components=COMP))


def test_gate_falla_ante_casos_fallidos():
    fail = {"id": "H-001", "severity": "critical", "detail": "x"}
    assert any("H-001" in p for p in gate.check([_report(COMP, failures=[fail])], THRESHOLDS, current_components=COMP))


def test_thresholds_json_valido():
    data = json.loads(Path(gate.DEFAULT_THRESHOLDS).read_text(encoding="utf-8"))
    assert data["absolute"]["security.violations"] == 0 and data["slo"]["latency.p95_ms"] is None


def test_runner_marca_known_gap_aparte_y_no_como_fallo(monkeypatch):
    from eval import evaluators, runner

    case = {"id": "A-001", "category": "A", "tier": "l1", "env": "adk", "kind": "routing", "input": {}, "expected": {},
            "severity": "high", "source": "s", "known_gap": True}
    monkeypatch.setitem(evaluators.L1, "routing", lambda i, e: (False, "gap"))
    report = runner.build_report([case], "l1", "adk", set(), 0, {})
    assert report["known_gaps"] == ["A-001"] and report["failures"] == [] and report["metrics"]["security.violations"] == 0


def test_runner_un_evaluador_roto_es_error_no_omision(monkeypatch):
    from eval import evaluators, runner

    case = {"id": "H-001", "category": "H", "tier": "l1", "env": "adk", "kind": "injection", "input": {}, "expected": {},
            "severity": "critical", "source": "s"}

    def boom(i, e):
        raise ImportError(name="modulo_inexistente")

    monkeypatch.setitem(evaluators.L1, "injection", boom)
    report = runner.build_report([case], "l1", "adk", set(), 0, {})
    assert report["categories"]["H"]["error"] == 1 and report["metrics"]["security.violations"] == 1
