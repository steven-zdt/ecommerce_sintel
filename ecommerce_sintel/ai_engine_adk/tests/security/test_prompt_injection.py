"""F11 -- inyeccion directa: la POLITICA (cerca, saneo, precedencia) sobrevive a toda variante; la DETECCION se exige solo en las robustas."""
import pytest

import input_guard
from eval import redteam as rt

from ._cases import attack_params, xfail_if_known


@pytest.mark.parametrize("category,kind,text", attack_params())
def test_la_cerca_contiene_cualquier_variante(category, kind, text):
    assert rt.fence_violations(text) == []


@pytest.mark.parametrize("category,kind,text", attack_params(kinds=rt.ROBUST_DETECTION))
def test_deteccion_en_mutaciones_robustas(category, kind, text):
    xfail_if_known(text=text)
    assert category in rt.detected_categories(text), f"no detectada ({category}/{kind})"


@pytest.mark.parametrize("category,kind,text", attack_params())
def test_el_saneo_elimina_invisibles_y_control(category, kind, text):
    clean = input_guard.sanitize_text(text)
    assert not any(ch in clean for ch in ("\u200b", "\u202e", "\x00", "\x1b"))


def test_la_politica_de_precedencia_prohibe_obedecer_datos():
    p = input_guard.PRECEDENCE_POLICY
    assert "DATOS_NO_CONFIABLES" in p and "nunca instrucciones" in p and "la autorizacion la decide la aplicacion" in p
