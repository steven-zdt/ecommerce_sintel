"""
HARDENING F4/C3 (2026-09-24) -- idempotencia server-side de Tools de ESCRITURA en el adapter del ADK.

No depende del LLM ni de que cada Tool soporte una `idempotency_key`: una escritura IDENTICA (misma sesion, mismo usuario,
misma Tool y mismos argumentos normalizados) dentro de la ventana devuelve el resultado anterior en vez de re-ejecutar.
Cubre reintento del modelo, doble envio y timeout seguido de reintento. Estados por clave en Redis (mismo Redis que
cost_control / rate_limit, cliente nuevo por llamada):

  ausente  -> primera ejecucion (se crea "pending" con SET NX, TTL corto)
  pending  -> hay otra ejecucion identica EN CURSO: se rechaza con 409
  <json>   -> resultado exitoso previo: se devuelve marcado `idempotent_replay`

Un resultado con error NO se guarda (se borra la clave): un reintento legitimo tras un fallo debe poder ejecutarse.
Fail-open documentado: si Redis cae, la escritura se ejecuta sin deduplicar (igual criterio que rate_limit.py).
"""
import hashlib
import json
import logging

import config as ai_config

logger = logging.getLogger("idempotency")

PENDING = "__pending__"
UNAVAILABLE = "__store_unavailable__"  # F14: el almacen de idempotencia no responde y se configuro fail-closed
_PENDING_TTL_SECONDS = 60


def make_key(session_id: str, user_id, tool: str, args: dict) -> str:
    normalized = json.dumps(args or {}, sort_keys=True, default=str, separators=(",", ":"))
    digest = hashlib.sha256(f"{session_id}|{user_id}|{tool}|{normalized}".encode("utf-8")).hexdigest()
    return f"ai:idem:{digest}"


def _client():
    import redis.asyncio as aredis
    return aredis.Redis.from_url(ai_config.CHECKPOINTER_REDIS_URL, decode_responses=True)


async def begin(key: str):
    """(None, True) primera ejecucion | (PENDING, False) en curso | (dict, False) replay | (None, True) si Redis falla."""
    try:
        c = _client()
        try:
            if await c.set(key, PENDING, ex=_PENDING_TTL_SECONDS, nx=True):
                return None, True
            raw = await c.get(key)
        finally:
            await c.aclose()
    except Exception as exc:  # noqa: BLE001
        # HARDENING F14/C2: por defecto fail-open (una escritura no se bloquea por un Redis caido). Con
        # AI_TOOL_IDEMPOTENCY_FAIL_CLOSED=true NO se ejecuta la escritura sin poder deduplicarla ("no duplicate side effects").
        if ai_config.AI_TOOL_IDEMPOTENCY_FAIL_CLOSED:
            logger.warning("ai_operation_event=idempotency_unavailable mode=fail_closed error=%s", type(exc).__name__)
            return UNAVAILABLE, False
        logger.warning("[idempotency] redis no disponible (fail-open): %s", type(exc).__name__)
        return None, True
    if raw is None or raw == PENDING:
        return PENDING, False
    try:
        return json.loads(raw), False
    except ValueError:
        return PENDING, False


async def finish(key: str, result: dict) -> None:
    try:
        c = _client()
        try:
            await c.set(key, json.dumps(result, default=str), ex=ai_config.AI_TOOL_IDEMPOTENCY_TTL_SECONDS)
        finally:
            await c.aclose()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[idempotency] no se pudo guardar el resultado (fail-open): %s", type(exc).__name__)


async def abort(key: str) -> None:
    try:
        c = _client()
        try:
            await c.delete(key)
        finally:
            await c.aclose()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[idempotency] no se pudo liberar la clave (expirara sola): %s", type(exc).__name__)
