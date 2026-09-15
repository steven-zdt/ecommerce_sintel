"""
Auditoria de hardening (2026-09-14, "PROMPT MAESTRO" seccion 34, "Seguridad del
Agente"): ADK no expone un limite nativo de tool calls/iteraciones por turno
(confirmado via introspeccion real de `LlmAgent`/`Runner`) -- gap real que no
tenia equivalente en el runtime nuevo. `deny_after_max_tool_calls_per_turn()`
(sintel_adapter.py) lo cierra via el hook real `before_tool_callback` de ADK.

Mismo criterio que el resto de la Policy Layer portada esta sesion (rate_limit.py/
permissions.py): probado directamente contra la funcion real que ADK invoca, no
contra un mock de "como creo que funciona ADK" -- confirmado por lectura directa
de `google.adk.flows.llm_flows._tool_caller` que un `before_tool_callback` que
devuelve un dict (no None) salta la ejecucion real de la Tool.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sintel_adapter import (
    MAX_TOOL_CALLS_PER_TURN,
    _TOOL_CALL_COUNTS,
    clear_tool_call_count,
    deny_after_max_tool_calls_per_turn,
)


def _fake_tool(name: str = "SomeTool"):
    return SimpleNamespace(name=name)


def _fake_tool_context(invocation_id: str):
    return SimpleNamespace(invocation_id=invocation_id)


@pytest.mark.asyncio
async def test_al1_permite_hasta_el_limite_y_bloquea_a_partir_de_ahi():
    invocation_id = "al1-invocation"
    clear_tool_call_count(invocation_id)
    tool, ctx = _fake_tool(), _fake_tool_context(invocation_id)

    for _ in range(MAX_TOOL_CALLS_PER_TURN):
        result = deny_after_max_tool_calls_per_turn(tool=tool, args={}, tool_context=ctx)
        assert result is None   # None = deja pasar la llamada real

    blocked = deny_after_max_tool_calls_per_turn(tool=tool, args={}, tool_context=ctx)
    assert blocked is not None
    assert blocked["status_code"] == 429

    clear_tool_call_count(invocation_id)


@pytest.mark.asyncio
async def test_al2_turnos_distintos_no_comparten_contador():
    """invocation_id es por-turno, no acumulativo entre turnos -- un usuario
    legitimo con muchos turnos normales nunca deberia verse afectado."""
    for _ in range(MAX_TOOL_CALLS_PER_TURN + 2):
        deny_after_max_tool_calls_per_turn(
            tool=_fake_tool(), args={}, tool_context=_fake_tool_context("al2-turn-A"),
        )
    result_turn_b = deny_after_max_tool_calls_per_turn(
        tool=_fake_tool(), args={}, tool_context=_fake_tool_context("al2-turn-B"),
    )
    assert result_turn_b is None   # turno B empieza en 0, no hereda el conteo de A

    clear_tool_call_count("al2-turn-A")
    clear_tool_call_count("al2-turn-B")


@pytest.mark.asyncio
async def test_al3_clear_tool_call_count_limpia_el_estado_de_proceso():
    invocation_id = "al3-invocation"
    deny_after_max_tool_calls_per_turn(tool=_fake_tool(), args={}, tool_context=_fake_tool_context(invocation_id))
    assert invocation_id in _TOOL_CALL_COUNTS

    clear_tool_call_count(invocation_id)
    assert invocation_id not in _TOOL_CALL_COUNTS
