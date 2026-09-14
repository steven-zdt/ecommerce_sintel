"""
Cost Control agregado (Fase 23, PLAN_MAESTRO_SINTEL_AI_SUPPORT, 2026-08-08).

Hallazgo real que motivo este archivo: el unico rate limit que existia
(`_RATE_HITS` en action_graph.py) es (a) en memoria del proceso -- se resetea en
cada restart del contenedor y no serviria si sintel_ai algun dia corre en mas de
una replica -- y (b) solo cubre 5 de ~30 Tools, todas de escritura. No existia
ningun limite agregado de `requests/user`/`requests/day` como pide la Fase 23,
asi que un usuario autenticado podia, en teoria, generar trafico de lectura
ilimitado hacia el LLM sin disparar nada.

Este modulo agrega ESO especificamente: un limite diario de turnos de /chat por
usuario, respaldado en el mismo Redis que ya usa redis_checkpointer.py (DB 2,
CHECKPOINTER_REDIS_URL) -- distribuido de verdad, sobrevive restarts. No
reemplaza el rate limit por-Tool de la Policy Layer (ese sigue aplicando a las
escrituras); esto es una capa adicional, mas gruesa, contra abuso/loops.
"""
import datetime
import logging

import redis.asyncio as aredis

from config import CHECKPOINTER_REDIS_URL

logger = logging.getLogger("cost_control")

DAILY_TURN_LIMIT_PER_USER = 200  # generoso a proposito -- frena abuso/loops, no uso normal
_KEY_TTL_SECONDS = 26 * 60 * 60  # >24h de margen, se limpia solo sin necesidad de un cron


def _daily_key(user_id) -> str:
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    return f"ai:cost:daily_turns:{user_id}:{today}"


def _client() -> aredis.Redis:
    """
    Cliente nuevo por llamada, a proposito -- no un singleton a nivel de
    modulo. redis.asyncio ata su pool de conexiones al event loop activo en
    el primer comando; un singleton compartido rompe (RuntimeError: Event
    loop is closed / Future attached to a different loop) apenas el loop
    cambia (confirmado en vivo: exactamente eso paso entre tests de
    pytest-asyncio, cada uno con su propio loop function-scoped). En
    produccion hay un solo loop de por vida (uvicorn), asi que esto no
    afecta rendimiento real -- es una llamada por turno de chat, no un
    hot path.
    """
    return aredis.Redis.from_url(CHECKPOINTER_REDIS_URL, decode_responses=True)


async def check_and_increment_daily_turns(user_id, limit: int = DAILY_TURN_LIMIT_PER_USER) -> bool:
    """
    True si el usuario todavia tiene cupo hoy (y el turno actual ya quedo
    contado); False si ya alcanzo el limite diario (no incrementa mas alla).
    Fail-open ante un Redis caido: un contador de costos no debe tumbar el chat.
    """
    key = _daily_key(user_id)
    client = _client()
    try:
        current = await client.get(key)
        if current is not None and int(current) >= limit:
            logger.warning("[cost_control] limite diario alcanzado user=%s (%s/%s)", user_id, current, limit)
            return False
        pipe = client.pipeline()
        pipe.incr(key)
        pipe.expire(key, _KEY_TTL_SECONDS)
        await pipe.execute()
        return True
    except Exception:
        logger.exception("[cost_control] Redis no disponible, fail-open (no se bloquea el turno)")
        return True
    finally:
        await client.aclose()
