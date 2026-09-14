"""
ADK-12 -- rate limiting portado desde la Policy Layer de action_graph.py
(OLD) hacia ai_engine_adk (NEW). Hallazgo de la auditoria previa a ADK-12
(ver AUDITORIA/ADK_CUTOVER_PLAN.md): ai_engine_adk ya sirve clientes reales
(AI_SUPPORT_CHAT_ENABLED=True) sin ningun limite por hora/dia en Tools de
escritura -- Django no las throttlea por su cuenta, la Policy Layer vieja
era el UNICO rate limiter real.

RL1: rate_limit.rate_limit_exceeded contra Redis REAL (mismo DB 2,
CHECKPOINTER_REDIS_URL) -- mismo criterio que
ai_engine/tests/test_policy_layer.py::test_rate_limit_exceeded_bloquea_al_superar_el_limite,
corrido aqui para confirmar que el modulo extraido se comporta igual desde
este runtime.
RL2: formato invalido nunca bloquea (fail-open).
RL3: adapt_sintel_tool aplica el limite ANTES de invocar la funcion real de
la Tool -- objeto RegisteredTool REAL (tools.registry.RegisteredTool +
tools.metadata.ToolMetadata), no un mock del adapter.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rate_limit import rate_limit_exceeded
from sintel_adapter import adapt_sintel_tool
from tools.metadata import ToolMetadata
from tools.registry import RegisteredTool

from google.adk.tools.tool_context import ToolContext as AdkToolContext


@pytest.fixture(autouse=True)
async def _flush_tool_rate_limits():
    """Mismo motivo que ai_engine/tests/conftest.py::_flush_tool_rate_limits --
    Redis (DB 2) persiste entre corridas, y esta suite usa user_id/tool_name
    fijos por test."""
    import redis.asyncio as aredis
    from config import CHECKPOINTER_REDIS_URL
    client = aredis.Redis.from_url(CHECKPOINTER_REDIS_URL, decode_responses=True)
    try:
        keys = [k async for k in client.scan_iter(match="ai:tool_rate:*")]
        if keys:
            await client.delete(*keys)
    except Exception:
        pass
    finally:
        await client.aclose()
    yield


@pytest.mark.asyncio
async def test_rl1_rate_limit_exceeded_bloquea_al_superar_el_limite():
    user_id, tool_name, limit = "rl-adk-user", "SomeTool", "2/hour/user"
    assert await rate_limit_exceeded(user_id, tool_name, limit) is False   # hit 1
    assert await rate_limit_exceeded(user_id, tool_name, limit) is False   # hit 2
    assert await rate_limit_exceeded(user_id, tool_name, limit) is True    # hit 3, bloqueado


@pytest.mark.asyncio
async def test_rl2_formato_invalido_nunca_bloquea():
    assert await rate_limit_exceeded("u", "t", "no-es-un-rate-limit") is False
    assert await rate_limit_exceeded("u", "t", "") is False


class _FakeAdkState(dict):
    pass


class _FakeAdkToolContext:
    """Doble minimo de google.adk.tools.tool_context.ToolContext: el wrapper de
    adapt_sintel_tool solo lee `.state` y `.session.id` (ver
    sintel_adapter._sintel_ctx_from_adk_state). No se mockea la logica bajo
    prueba (rate_limit_exceeded / adapt_sintel_tool), solo el objeto de
    entrada que ADK normalmente construye a partir de una Session real."""
    def __init__(self, state: dict):
        self.state = state
        self.session = None


@pytest.mark.asyncio
async def test_rl3_adapt_sintel_tool_bloquea_antes_de_llamar_la_funcion_real():
    calls = []

    async def _fake_tool(ctx, **kwargs):
        calls.append(kwargs)
        return {"ok": True}

    metadata = ToolMetadata(
        name="RLTestTool",
        description="Tool sintetica solo para probar el rate limit del adapter.",
        owner="ai_engine_adk.tests",
        capabilities=["rl_test_capability"],
        rate_limit="2/hour/user",
        args_schema={"properties": {}, "required": []},
    )
    registered = RegisteredTool(metadata=metadata, func=_fake_tool)
    function_tool = adapt_sintel_tool(registered)

    tool_context = _FakeAdkToolContext({
        "sintel_user": {"user_id": "rl-adk-adapter-user"},
        "sintel_token": "",
    })

    run = function_tool.func
    assert await run(tool_context=tool_context) == {"ok": True}     # hit 1 -- ejecuta
    assert await run(tool_context=tool_context) == {"ok": True}     # hit 2 -- ejecuta
    blocked = await run(tool_context=tool_context)                  # hit 3 -- bloqueado
    assert blocked["status_code"] == 429
    assert "limite" in blocked["error"].lower()
    assert len(calls) == 2   # la funcion real NUNCA se llamo en el hit bloqueado
