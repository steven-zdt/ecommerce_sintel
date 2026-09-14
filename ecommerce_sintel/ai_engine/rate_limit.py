"""
Rate limiter por (user_id, tool), respaldado en Redis -- extraido de
`action_graph.py::_rate_limit_exceeded` (mision "ADK-SINTEL", ADK-12,
2026-09-14) por el mismo motivo real que `routing.py`/`model_chain.py`:
la logica en si es pura (solo `redis.asyncio` + `logging`, sin
LangChain/LangGraph), pero vivia dentro de `action_graph.py`, que SI
importa `langchain_core`/`langgraph` a nivel de modulo -- y por eso nunca
se pudo reusar directo desde `ai_engine_adk` (conflicto de dependencias
`langchain-openai` vs `litellm`, ver `routing.py`).

Hallazgo real de la auditoria ADK-12 (ver AUDITORIA/ADK_CUTOVER_PLAN.md):
`ai_engine_adk`, ya en produccion real sirviendo clientes (AI_SUPPORT_CHAT_
ENABLED=True desde 2026-09-14), NUNCA porto este rate limiter -- las Tools
de escritura con `ToolMetadata.rate_limit` (cancelar_alquiler, crear_
alquiler, KYC, cotizaciones, tickets de soporte) no tenian ningun limite
por hora/dia en el runtime nuevo, y Django no las throttlea por su cuenta
(la Policy Layer vieja era el UNICO rate limiter real). Este modulo cierra
ese hueco para AMBOS runtimes: `action_graph.py` (OLD) sigue importando
`_rate_limit_exceeded` desde aqui sin cambio de comportamiento (mismos
tests, `tests/test_policy_layer.py`), y `sintel_adapter.py` (ADK/NEW) lo
usa directo desde su wrapper de Tools.

Extraccion mecanica -- CERO cambio de comportamiento: misma clave Redis,
misma ventana, mismo criterio fail-open si Redis no esta disponible.
"""
import logging

from config import CHECKPOINTER_REDIS_URL

logger = logging.getLogger(__name__)

_RATE_WINDOWS = {"hour": 3600, "day": 86400}


def _tool_rate_key(user_id, tool_name: str, window_name: str) -> str:
    return f"ai:tool_rate:{user_id}:{tool_name}:{window_name}"


async def rate_limit_exceeded(user_id, tool_name: str, rate_limit: str) -> bool:
    """rate_limit: formato `ToolMetadata.rate_limit`, ej. "10/hour/user". Un
    valor vacio o mal formado nunca bloquea (mismo criterio que antes)."""
    if not rate_limit:
        return False
    try:
        count_raw, window_name, _scope = rate_limit.split("/")
        limit, window = int(count_raw), _RATE_WINDOWS[window_name]
    except (ValueError, KeyError):
        return False

    import redis.asyncio as aredis
    key = _tool_rate_key(user_id, tool_name, window_name)
    # Cliente nuevo por llamada, a proposito -- mismo motivo que cost_control.py:
    # redis.asyncio ata su pool al event loop activo en el primer comando, un
    # singleton de modulo rompe entre loops distintos (tests, o cualquier reload).
    client = aredis.Redis.from_url(CHECKPOINTER_REDIS_URL, decode_responses=True)
    try:
        current = await client.incr(key)
        if current == 1:
            await client.expire(key, window)
        return current > limit
    except Exception:
        logger.exception("[policy] Redis no disponible para rate limit de %s, fail-open", tool_name)
        return False
    finally:
        await client.aclose()
