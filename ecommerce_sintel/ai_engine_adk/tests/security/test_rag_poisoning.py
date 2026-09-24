"""F11 -- envenenamiento de RAG: los chunks hostiles se detectan para cuarentena y siempre se cercan."""
import pytest

import sintel_rag_adapter as rag
from eval import redteam as rt

from ._cases import attack_params, xfail_if_known


@pytest.mark.parametrize("category,kind,text", attack_params(categories=set(rag._QUARANTINE_CATEGORIES), kinds={"plain"}))
def test_las_variantes_llanas_caen_en_categorias_de_cuarentena(category, kind, text):
    xfail_if_known(text=text)
    assert set(rt.detected_categories("Garantia 12 meses. " + text)) & set(rag._QUARANTINE_CATEGORIES)


@pytest.mark.parametrize("category,kind,text", attack_params(kinds={"plain", "wrapper", "quoted", "long_context", "fake_system"}))
def test_el_chunk_hostil_siempre_queda_cercado(category, kind, text):
    assert rt.fence_violations("Documento: " + text) == []


def test_las_categorias_de_cuarentena_son_las_de_mayor_riesgo():
    assert {"override_instructions", "fake_system_message", "delimiter_forgery"} == set(rag._QUARANTINE_CATEGORIES)
