"""F11 -- fuga de razonamiento interno (<think>) en distintas formas."""
import pytest

import output_guard

CASES = [
    "<think>debo decidir que decir</think>Hola, en que puedo ayudarte?",
    "<THINK>razonamiento</THINK>Respuesta",
    "Hola.<think>el usuario pide algo y yo debo decidir que hac",
    "Respuesta</think> final",
    "<think>\nlinea 1\nlinea 2\n</think>\nListo.",
    "<think>a</think><think>b</think>Visible",
]


@pytest.mark.parametrize("text", CASES)
def test_el_razonamiento_no_llega_al_cliente(text):
    out, _ = output_guard.guard_public_response(text)
    assert "think" not in out.lower()
    for fragment in ("debo decidir", "razonamiento", "linea 1", "el usuario pide"):
        assert fragment not in out


def test_la_respuesta_visible_se_conserva():
    out, _ = output_guard.guard_public_response("<think>x</think>Hola, en que puedo ayudarte?")
    assert out == "Hola, en que puedo ayudarte?"
