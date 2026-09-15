"""
Mision RAG Enterprise (2026-09-16, FASE 7). Cubre `grounding.py`:
parseo de veredicto, degradacion cuando el validador falla, y que la
llamada litellm se construye con el modelo/proveedor pasado (nunca uno
distinto -- Regla 3 de la mision: no cambiar de modelo sin evidencia).

`litellm.acompletion` se mockea (rapido, determinista) -- el comportamiento
E2E real (¿el validador realmente detecta una respuesta no sustentada, o que
CONTRADICE la evidencia, contra LM Studio real?) se cubre aparte en
ai_engine_adk/tests/test_grounding_integration.py (referencia corregida
2026-09-16, Mision RAG-POST2 -- el nombre anterior, test_grounding_e2e.py,
nunca existio en este repo).
"""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from grounding import (  # noqa: E402
    PARTIALLY_SUPPORTED,
    SUPPORTED,
    UNSUPPORTED,
    _parse_verdict,
    check_grounding,
)


def _completion(text: str):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


class TestParseVerdict:
    def test_supported_exacto(self):
        assert _parse_verdict("SUPPORTED") == SUPPORTED

    def test_partially_supported_exacto(self):
        assert _parse_verdict("PARTIALLY_SUPPORTED") == PARTIALLY_SUPPORTED

    def test_unsupported_exacto(self):
        assert _parse_verdict("UNSUPPORTED") == UNSUPPORTED

    def test_con_texto_extra_alrededor(self):
        # El modelo a veces agrega puntuacion/explicacion pese a la instruccion.
        assert _parse_verdict("La respuesta es SUPPORTED.") == SUPPORTED

    def test_minusculas(self):
        assert _parse_verdict("unsupported") == UNSUPPORTED

    def test_partially_no_se_confunde_con_supported(self):
        # "SUPPORTED" es substring literal de "PARTIALLY_SUPPORTED" -- el
        # orden de chequeo en _parse_verdict debe evitar el falso positivo.
        assert _parse_verdict("PARTIALLY_SUPPORTED") == PARTIALLY_SUPPORTED

    def test_veredicto_no_reconocido_es_unsupported_fail_safe(self):
        assert _parse_verdict("no tengo idea que responder") == UNSUPPORTED

    def test_vacio_es_unsupported_fail_safe(self):
        assert _parse_verdict("") == UNSUPPORTED
        assert _parse_verdict(None) == UNSUPPORTED


@pytest.mark.asyncio
class TestCheckGrounding:
    async def test_llama_con_el_modelo_pasado_no_uno_distinto(self):
        with patch("litellm.acompletion", new=AsyncMock(return_value=_completion("SUPPORTED"))) as mock_call:
            await check_grounding(
                response="respuesta", evidence="evidencia",
                model="ollama_chat/qwen3.5", api_base="http://ollama:11434",
            )
        _, kwargs = mock_call.call_args
        assert kwargs["model"] == "ollama_chat/qwen3.5"
        assert kwargs["api_base"] == "http://ollama:11434"
        assert kwargs["max_tokens"] == 10  # pregunta minima, no una respuesta larga

    async def test_veredicto_supported_real(self):
        with patch("litellm.acompletion", new=AsyncMock(return_value=_completion("SUPPORTED"))):
            verdict = await check_grounding(response="r", evidence="e", model="m")
        assert verdict == SUPPORTED

    async def test_veredicto_unsupported_real(self):
        with patch("litellm.acompletion", new=AsyncMock(return_value=_completion("UNSUPPORTED"))):
            verdict = await check_grounding(response="r", evidence="e", model="m")
        assert verdict == UNSUPPORTED

    async def test_proveedor_caido_degrada_a_partially_supported_nunca_lanza(self):
        with patch("litellm.acompletion", new=AsyncMock(side_effect=TimeoutError("proveedor caido"))):
            verdict = await check_grounding(response="r", evidence="e", model="m")
        assert verdict == PARTIALLY_SUPPORTED

    async def test_api_key_opcional_no_se_envia_si_no_se_pasa(self):
        with patch("litellm.acompletion", new=AsyncMock(return_value=_completion("SUPPORTED"))) as mock_call:
            await check_grounding(response="r", evidence="e", model="m")
        _, kwargs = mock_call.call_args
        assert "api_key" not in kwargs
