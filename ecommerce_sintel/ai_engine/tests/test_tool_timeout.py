"""
tools/registry.py::invoke() -- enforcement real de ToolMetadata.timeout_ms
(Gap 2, Fase 28-29, agregado 2026-08-08). Antes el campo era puramente
declarativo: una Tool que colgara bloqueaba el turno sin limite.
"""
import asyncio

from tools.metadata import ToolContext, ToolMetadata
from tools.registry import invoke, register_tool


_SLOW_TOOL_METADATA = ToolMetadata(
    name="_TestSlowTool",
    description="Tool de prueba que tarda mas que su timeout declarado.",
    owner="test",
    capabilities=[],
    timeout_ms=50,
)


@register_tool(_SLOW_TOOL_METADATA)
async def _slow_tool(ctx: ToolContext) -> dict:
    await asyncio.sleep(1)
    return {"ok": True}


_FAST_TOOL_METADATA = ToolMetadata(
    name="_TestFastTool",
    description="Tool de prueba que responde antes de su timeout declarado.",
    owner="test",
    capabilities=[],
    timeout_ms=2000,
)


@register_tool(_FAST_TOOL_METADATA)
async def _fast_tool(ctx: ToolContext) -> dict:
    await asyncio.sleep(0.01)
    return {"ok": True}


async def test_tool_que_excede_su_timeout_devuelve_error_504():
    ctx = ToolContext(user={"user_id": 1}, token="fake")
    result = await invoke("_TestSlowTool", ctx)
    assert result.get("status_code") == 504
    assert "error" in result


async def test_tool_dentro_de_su_timeout_responde_normal():
    ctx = ToolContext(user={"user_id": 1}, token="fake")
    result = await invoke("_TestFastTool", ctx)
    assert result == {"ok": True}
