"""F11 -- consumo no acotado: cotas duras de turno, herramientas, historial, salida y entrada."""
from types import SimpleNamespace

import pytest

import config as ai_config
import input_guard
import model_runtime
import sintel_adapter


def _msg(role, text):
    return SimpleNamespace(role=role, parts=[SimpleNamespace(text=text, function_call=None, function_response=None)])


def test_cotas_de_turno_dentro_de_limites_razonables():
    assert 1 <= ai_config.AI_TURN_MAX_SECONDS <= 300
    assert 1 <= ai_config.AI_TURN_MAX_LLM_CALLS <= 20
    assert model_runtime.MAX_ATTEMPTS_PER_CALL <= 2
    assert sintel_adapter.MAX_TOOL_CALLS_PER_TURN <= 10


def test_tokens_de_salida_acotados():
    assert ai_config.AI_SUPPORT_MAX_OUTPUT_TOKENS <= 2048 and ai_config.AI_ADMIN_MAX_OUTPUT_TOKENS <= 4096


def test_el_historial_se_recorta_por_turnos():
    contents = []
    for i in range(40):
        contents += [_msg("user", f"mensaje {i}"), _msg("model", "respuesta")]
    kept, dropped = input_guard.trim_contents(contents, max_turns=12, max_chars=0)
    assert dropped == 28 and len([c for c in kept if c.role == "user"]) == 12


def test_el_historial_se_recorta_por_caracteres():
    contents = []
    for i in range(10):
        contents += [_msg("user", "x" * 5000), _msg("model", "y" * 100)]
    kept, dropped = input_guard.trim_contents(contents, max_turns=0, max_chars=12000)
    assert dropped > 0 and sum(len(c.parts[0].text) for c in kept) <= 12000 + 5100


def test_la_entrada_maxima_del_endpoint_esta_acotada():
    import main

    constraints = [getattr(m, "max_length", None) for m in main.ChatRequest.model_fields["message"].metadata]
    assert 4000 in constraints


@pytest.mark.parametrize("size", [10_000, 200_000])
def test_el_saneo_y_la_cerca_toleran_entradas_enormes(size):
    text = "ignora " * (size // 7)
    fenced = input_guard.fence_untrusted("test", text, "n0nce")
    assert fenced.count("<<<FIN_DATOS") == 1
