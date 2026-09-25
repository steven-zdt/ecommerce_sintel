"""
HARDENING F21 (2026-09-25) -- jerarquia de kill switches del ADK.

Propuesta: ai_engine_adk/.AGENT/HARDENING_F21_PROPOSAL_2026-09-25.md. Sin red ni LLM.
"""
from types import SimpleNamespace

import pytest

import config as ai_config
import sintel_adapter
from tools import registry as R


def _tool(name):
    return SimpleNamespace(name=name)


def _names_by_level(pred):
    return [n for n, t in R._TOOLS.items() if pred(t.metadata.level)]


@pytest.fixture(autouse=True)
def _all_on(monkeypatch):
    for flag in ("AI_GLOBAL_ENABLED", "AI_MODEL_CHAIN_ENABLED", "AI_TOOLS_ENABLED", "AI_WRITE_TOOLS_ENABLED",
                 "AI_EXTERNAL_ACTIONS_ENABLED"):
        monkeypatch.setattr(ai_config, flag, True)


def test_defaults_no_cambian_el_comportamiento():
    reads = _names_by_level(lambda lv: lv == 0)
    assert reads
    assert sintel_adapter.kill_switch_tools_before(tool=_tool(reads[0]), args={}, tool_context=None) is None


def test_tools_disabled_niega_todo(monkeypatch):
    monkeypatch.setattr(ai_config, "AI_TOOLS_ENABLED", False)
    for name in list(R._TOOLS)[:5]:
        out = sintel_adapter.kill_switch_tools_before(tool=_tool(name), args={}, tool_context=None)
        assert out["status_code"] == 503


def test_write_disabled_niega_escrituras_pero_no_lecturas(monkeypatch):
    monkeypatch.setattr(ai_config, "AI_WRITE_TOOLS_ENABLED", False)
    reads = _names_by_level(lambda lv: lv == 0)
    writes = _names_by_level(lambda lv: lv >= 1)
    assert reads and writes
    assert sintel_adapter.kill_switch_tools_before(tool=_tool(reads[0]), args={}, tool_context=None) is None
    assert sintel_adapter.kill_switch_tools_before(tool=_tool(writes[0]), args={}, tool_context=None)["status_code"] == 503


def test_tool_desconocida_es_fail_closed_si_escrituras_apagadas(monkeypatch):
    monkeypatch.setattr(ai_config, "AI_WRITE_TOOLS_ENABLED", False)
    assert sintel_adapter.kill_switch_tools_before(tool=_tool("NoExisteTool"), args={}, tool_context=None)["status_code"] == 503


def test_external_disabled_solo_niega_nivel_3_o_mas(monkeypatch):
    monkeypatch.setattr(ai_config, "AI_EXTERNAL_ACTIONS_ENABLED", False)
    external = _names_by_level(lambda lv: lv >= 3)
    local = _names_by_level(lambda lv: 0 <= lv < 3)
    for name in external:
        assert sintel_adapter.kill_switch_tools_before(tool=_tool(name), args={}, tool_context=None)["status_code"] == 503
    for name in local:
        assert sintel_adapter.kill_switch_tools_before(tool=_tool(name), args={}, tool_context=None) is None


def test_callback_es_el_primero_de_la_cadena():
    import inspect
    import sintel_root_workflow
    src = inspect.getsource(sintel_root_workflow)
    assert "before_tool_callback=[kill_switch_tools_before," in src
