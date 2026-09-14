"""
ADK-13 -- gate `IsAdminUser` portado desde la Policy Layer de action_graph.py
(OLD) hacia ai_engine_adk (NEW). Mismo hallazgo/patron que el rate limiter
de ADK-12 (ver test_rate_limit.py): la auditoria de consumidores reales
encontro que `ToolMetadata.permissions = ["IsAdminUser"]` nunca se aplicaba
en este runtime.

P1: user_lacks_admin_permission -- unitario puro, sin dependencias.
P2: adapt_sintel_tool aplica el gate ANTES de invocar la funcion real de la
Tool -- objeto RegisteredTool REAL, no un mock del adapter. Cubre el caso
bloqueado (no-staff) y el caso permitido (staff).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from permissions import user_lacks_admin_permission
from sintel_adapter import adapt_sintel_tool
from tools.metadata import ToolMetadata
from tools.registry import RegisteredTool


def test_p1_bloquea_sin_permiso_admin_para_usuario_no_staff():
    assert user_lacks_admin_permission(["IsAdminUser"], {"is_staff": False}) is True
    assert user_lacks_admin_permission(["IsAdminUser"], {}) is True


def test_p1_permite_a_usuario_staff():
    assert user_lacks_admin_permission(["IsAdminUser"], {"is_staff": True}) is False


def test_p1_permite_si_la_tool_no_exige_admin():
    assert user_lacks_admin_permission([], {"is_staff": False}) is False
    assert user_lacks_admin_permission(["IsBuyerOrAdmin"], {"is_staff": False}) is False


class _FakeAdkToolContext:
    """Mismo doble minimo que test_rate_limit.py::_FakeAdkToolContext -- el
    wrapper de adapt_sintel_tool solo lee `.state` y `.session.id`."""
    def __init__(self, state: dict):
        self.state = state
        self.session = None


def _admin_only_tool():
    calls = []

    async def _fake_tool(ctx, **kwargs):
        calls.append(kwargs)
        return {"ok": True}

    metadata = ToolMetadata(
        name="AdminOnlyTestTool",
        description="Tool sintetica solo para probar el gate IsAdminUser del adapter.",
        owner="ai_engine_adk.tests",
        capabilities=["admin_test_capability"],
        permissions=["IsAdminUser"],
        args_schema={"properties": {}, "required": []},
    )
    registered = RegisteredTool(metadata=metadata, func=_fake_tool)
    return adapt_sintel_tool(registered), calls


@pytest.mark.asyncio
async def test_p2_adapt_sintel_tool_bloquea_a_usuario_no_staff_antes_de_ejecutar():
    function_tool, calls = _admin_only_tool()
    tool_context = _FakeAdkToolContext({
        "sintel_user": {"user_id": "p2-non-staff-user", "is_staff": False},
        "sintel_token": "",
    })
    result = await function_tool.func(tool_context=tool_context)
    assert result == {"error": "Esta accion es solo para administradores.", "status_code": 403}
    assert calls == []   # la funcion real NUNCA se llamo


@pytest.mark.asyncio
async def test_p2_adapt_sintel_tool_permite_a_usuario_staff():
    function_tool, calls = _admin_only_tool()
    tool_context = _FakeAdkToolContext({
        "sintel_user": {"user_id": "p2-staff-user", "is_staff": True},
        "sintel_token": "",
    })
    result = await function_tool.func(tool_context=tool_context)
    assert result == {"ok": True}
    assert len(calls) == 1
