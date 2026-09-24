"""
HARDENING F12 (2026-09-24) -- tope de resultado de Tools (C4) y limites de salida por agente (C3).
ESCRITO PERO NO EJECUTADO (regla vigente: el usuario ejecuta los tests a mano). Deterministas, sin LLM ni red.
"""
import json
import logging

import pytest

import config as ai_config
import result_limits as rl


def _size(v):
    return len(json.dumps(v, ensure_ascii=False))


def test_un_resultado_pequeno_queda_intacto():
    data = {"items": [{"id": 1}], "total": 1}
    assert rl.limit_result(data, 8000) == (data, None)


def test_no_muta_el_original_ni_toca_escalares():
    big = {"items": [{"n": "x" * 100} for _ in range(100)]}
    before = json.dumps(big)
    out, info = rl.limit_result(big, 2000)
    assert json.dumps(big) == before and info is not None
    assert rl.limit_result("texto", 5) == ("texto", None) and rl.limit_result(None, 5) == (None, None)


def test_recorta_la_lista_mas_larga_conservando_el_orden_y_deja_marcador():
    big = {"total": 100, "items": [{"id": i, "d": "x" * 80} for i in range(100)]}
    out, info = rl.limit_result(big, 2000)
    assert _size(out) <= 2000 and out["total"] == 100
    assert [i["id"] for i in out["items"]] == list(range(info["shown"]))
    assert out["_truncated"] == {"shown": info["shown"], "total": 100} and info["total"] == 100


def test_lista_de_nivel_superior_termina_con_un_elemento_marcador():
    out, info = rl.limit_result([{"id": i, "d": "y" * 60} for i in range(200)], 1500)
    assert out[-1] == {"_truncated": {"shown": info["shown"], "total": 200}} and _size(out) <= 1500 + 60


def test_una_cadena_gigante_se_acorta_con_marcador():
    out, info = rl.limit_result({"descripcion": "z" * 50000}, 4000)
    assert info["strings_capped"] and len(out["descripcion"]) <= 2000 and out["descripcion"].endswith(rl.TRUNC_SUFFIX)


def test_limite_cero_o_negativo_desactiva():
    assert rl.limit_result({"a": "x" * 100}, 0)[1] is None


def test_es_determinista():
    big = {"items": [{"id": i} for i in range(500)]}
    assert rl.limit_result(big, 1000) == rl.limit_result(big, 1000)


def test_parse_de_limites_por_agente():
    parse = ai_config._parse_agent_limits
    assert parse("RentalAgent=1536, SupportAgent=768") == {"RentalAgent": 1536, "SupportAgent": 768}
    assert parse("") == {} and parse("Malo=abc,=5,SinValor,Cero=0") == {}


def test_el_limite_por_agente_tiene_prioridad_y_sin_el_se_conserva_el_de_superficie(monkeypatch):
    import sintel_root_workflow as wf

    monkeypatch.setattr(ai_config, "AI_AGENT_MAX_OUTPUT_TOKENS", {"RentalAgent": 1536})
    monkeypatch.setattr(ai_config, "AI_SUPPORT_MAX_OUTPUT_TOKENS", 1024)
    monkeypatch.setattr(ai_config, "AI_ADMIN_MAX_OUTPUT_TOKENS", 2048)
    assert wf._max_output_tokens_for("RentalAgent") == 1536
    assert wf._max_output_tokens_for("SupportAgent") == 1024
    assert wf._max_output_tokens_for("CatalogAgent") == 2048


def test_el_adapter_monitorea_y_solo_recorta_con_enforce():
    import inspect

    import sintel_adapter

    src = inspect.getsource(sintel_adapter.adapt_sintel_tool)
    assert "result_limits.limit_result(" in src and "if ai_config.AI_TOOL_RESULT_ENFORCE:" in src
    assert "tool_result_truncated" in src


def test_los_defaults_conservan_el_comportamiento_anterior():
    assert ai_config.AI_TOOL_RESULT_ENFORCE is False and ai_config.AI_AGENT_MAX_OUTPUT_TOKENS == {}
