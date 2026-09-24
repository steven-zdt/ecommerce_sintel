"""
HARDENING F3/C2 (2026-09-24) -- fallback multi-entry + circuit breaker por proveedor del modelo.

Plan: PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md sec. 7; propuesta:
ai_engine_adk/.AGENT/HARDENING_F3_PROPOSAL_2026-09-24.md.

Antes: `_resolve_primary_llm_params()` solo usaba la primera entrada de LOCAL_MODEL_CHAIN; la segunda (LM Studio)
nunca se usaba y un Ollama caido se reintentaba en cada turno sin memoria del fallo.

Ahora:
- `ProviderBreaker`: CLOSED / OPEN / HALF_OPEN por entrada de la cadena. Estado compartido en Redis (sobrevive
  reinicios, comun a replicas), fail-open si Redis cae (un breaker no debe tumbar el chat). Cuenta ERRORES de
  proveedor (timeout, conexion, 5xx), no latencia.
- `FallbackLiteLlm`: modelo para el LlmAgent que respeta el orden de la cadena (Ollama -> LM Studio), salta
  proveedores con breaker OPEN, y ante un fallo pasa a la siguiente entrada UNA sola vez por llamada (presupuesto
  de reintentos = 2 intentos como maximo, nunca ambos proveedores en bucle). Si no hay ninguno disponible lanza
  `ModelUnavailableError` (el endpoint responde el mensaje seguro de handoff).
- Trazabilidad por turno en un ContextVar (`begin_turn_trace`): proveedor, modelo, uso de fallback, motivo y
  estado del breaker. NUNCA guarda prompts ni respuestas.
- No vuelve "silenciosamente" al primario: el retorno solo ocurre por HALF_OPEN (1 peticion de prueba).
"""
import asyncio
import contextvars
import logging
import time

from google.adk.models.lite_llm import LiteLlm
from pydantic import PrivateAttr

import config as ai_config
from model_chain import parse_local_model_chain

logger = logging.getLogger("model_runtime")

CLOSED, OPEN, HALF_OPEN = "CLOSED", "OPEN", "HALF_OPEN"
_PROBE_TTL_SECONDS = 30
_TRIPPED_TTL_SECONDS = 24 * 60 * 60
MAX_ATTEMPTS_PER_CALL = 2  # primario + 1 fallback; nunca un bucle entre proveedores


class ModelUnavailableError(RuntimeError):
    """Ningun proveedor de la cadena esta disponible (breakers abiertos o todos fallaron)."""


#  Trazabilidad por turno 
_turn_trace: contextvars.ContextVar = contextvars.ContextVar("ai_turn_model_trace", default=None)


def begin_turn_trace() -> dict:
    trace = {"provider": None, "model": None, "fallback_used": False, "fallback_reason": None,
             "breaker_state": None, "attempts": 0}
    _turn_trace.set(trace)
    return trace


def _trace() -> dict | None:
    return _turn_trace.get()


#  Almacenes de estado del breaker 
class MemoryStore:
    """Almacen en memoria (tests / fallback). Interfaz identica a RedisStore."""

    def __init__(self, clock=time.monotonic):
        self._data: dict = {}
        self._clock = clock

    def _alive(self, key):
        item = self._data.get(key)
        if item is None:
            return None
        value, expires = item
        if expires is not None and expires <= self._clock():
            self._data.pop(key, None)
            return None
        return item

    async def incr_window(self, key: str, window: int) -> int:
        item = self._alive(key)
        count = (item[0] + 1) if item else 1
        expires = item[1] if item else self._clock() + window
        self._data[key] = (count, expires)
        return count

    async def set(self, key: str, ttl: int) -> None:
        self._data[key] = (1, self._clock() + ttl)

    async def exists(self, key: str) -> bool:
        return self._alive(key) is not None

    async def set_nx(self, key: str, ttl: int) -> bool:
        if self._alive(key) is not None:
            return False
        self._data[key] = (1, self._clock() + ttl)
        return True

    async def delete(self, *keys: str) -> None:
        for k in keys:
            self._data.pop(k, None)


class RedisStore:
    """Redis asyncio (mismo Redis que cost_control/redis_checkpointer). Cliente nuevo por llamada (ver
    cost_control._client: un singleton rompe al cambiar el event loop). Fail-open: si Redis falla, las
    operaciones devuelven valores neutros y el breaker se comporta como CLOSED."""

    def __init__(self, url: str | None = None):
        self._url = url or ai_config.CHECKPOINTER_REDIS_URL

    def _client(self):
        import redis.asyncio as aredis
        return aredis.Redis.from_url(self._url, decode_responses=True)

    async def incr_window(self, key: str, window: int) -> int:
        try:
            c = self._client()
            try:
                n = await c.incr(key)
                if n == 1:
                    await c.expire(key, window)
                return int(n)
            finally:
                await c.aclose()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[breaker] redis incr fallo (fail-open): %s", type(exc).__name__)
            return 0

    async def set(self, key: str, ttl: int) -> None:
        try:
            c = self._client()
            try:
                await c.set(key, "1", ex=ttl)
            finally:
                await c.aclose()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[breaker] redis set fallo (fail-open): %s", type(exc).__name__)

    async def exists(self, key: str) -> bool:
        try:
            c = self._client()
            try:
                return bool(await c.exists(key))
            finally:
                await c.aclose()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[breaker] redis exists fallo (fail-open): %s", type(exc).__name__)
            return False

    async def set_nx(self, key: str, ttl: int) -> bool:
        try:
            c = self._client()
            try:
                return bool(await c.set(key, "1", ex=ttl, nx=True))
            finally:
                await c.aclose()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[breaker] redis set_nx fallo (fail-open): %s", type(exc).__name__)
            return True

    async def delete(self, *keys: str) -> None:
        try:
            c = self._client()
            try:
                await c.delete(*keys)
            finally:
                await c.aclose()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[breaker] redis delete fallo (fail-open): %s", type(exc).__name__)


#  Circuit breaker 
class ProviderBreaker:
    def __init__(self, store=None, failures: int | None = None, window: int | None = None,
                 open_seconds: int | None = None):
        self.store = store or RedisStore()
        self._failures = failures
        self._window = window
        self._open_seconds = open_seconds

    # umbrales leidos en cada uso (permiten cambiarlos por entorno / tests sin reconstruir)
    @property
    def failures(self) -> int:
        return self._failures if self._failures is not None else ai_config.AI_BREAKER_FAILURES

    @property
    def window(self) -> int:
        return self._window if self._window is not None else ai_config.AI_BREAKER_WINDOW_SECONDS

    @property
    def open_seconds(self) -> int:
        return self._open_seconds if self._open_seconds is not None else ai_config.AI_BREAKER_OPEN_SECONDS

    @staticmethod
    def _k(name: str, part: str) -> str:
        return f"ai:breaker:{name}:{part}"

    async def state(self, name: str) -> str:
        if await self.store.exists(self._k(name, "open")):
            return OPEN
        if await self.store.exists(self._k(name, "tripped")):
            return HALF_OPEN
        return CLOSED

    async def allow(self, name: str) -> tuple[bool, str]:
        st = await self.state(name)
        if st == CLOSED:
            return True, st
        if st == OPEN:
            return False, st
        # HALF_OPEN: deja pasar UNA sola peticion de prueba; el resto sigue bloqueado hasta su resultado.
        return await self.store.set_nx(self._k(name, "probe"), _PROBE_TTL_SECONDS), HALF_OPEN

    async def record_success(self, name: str) -> None:
        if await self.store.exists(self._k(name, "tripped")):
            logger.info("ai_operation_event=breaker_closed provider=%s", name)
        await self.store.delete(self._k(name, "failures"), self._k(name, "open"),
                                self._k(name, "tripped"), self._k(name, "probe"))

    async def record_failure(self, name: str) -> None:
        st = await self.state(name)
        if st == HALF_OPEN:
            await self._trip(name, reason="half_open_probe_failed")
            return
        count = await self.store.incr_window(self._k(name, "failures"), self.window)
        if count and count >= self.failures:
            await self._trip(name, reason=f"{count}_failures_in_{self.window}s")

    async def _trip(self, name: str, reason: str) -> None:
        await self.store.set(self._k(name, "open"), self.open_seconds)
        await self.store.set(self._k(name, "tripped"), _TRIPPED_TTL_SECONDS)
        await self.store.delete(self._k(name, "failures"), self._k(name, "probe"))
        logger.warning("ai_operation_event=breaker_opened provider=%s reason=%s open_seconds=%s",
                       name, reason, self.open_seconds)


_default_breaker: ProviderBreaker | None = None


def get_breaker() -> ProviderBreaker:
    global _default_breaker
    if _default_breaker is None:
        _default_breaker = ProviderBreaker()
    return _default_breaker


#  Parametros por entrada de la cadena 
def llm_params_for_entry(entry: dict) -> dict:
    """Mismos parametros litellm que sintel_root_workflow._resolve_primary_llm_params(), para CUALQUIER entrada."""
    kind = entry["kind"]
    if kind == "ollama-nativo":
        return {"model": f"ollama_chat/{entry['model']}", "api_base": entry["base_url"]}
    if kind == "openai-compatible":
        return {"model": f"openai/{entry['model']}", "api_base": entry["base_url"], "api_key": "not-needed"}
    if kind == "anthropic":
        from decouple import config as env

        api_key = env(entry["api_key_env"], default=ai_config.ANTHROPIC_API_KEY) if entry.get("api_key_env") \
            else ai_config.ANTHROPIC_API_KEY
        return {"model": f"anthropic/{entry['model']}", "api_key": api_key}
    raise RuntimeError(f"kind desconocido en LOCAL_MODEL_CHAIN: {kind!r}")


def _is_client_error(exc: Exception) -> bool:
    """Errores del REQUEST (no de la salud del proveedor): no cuentan para el breaker ni justifican fallback."""
    try:
        import litellm

        return isinstance(exc, (litellm.BadRequestError, litellm.ContextWindowExceededError))
    except Exception:  # noqa: BLE001
        return False


#  Modelo con fallback 
class FallbackLiteLlm(LiteLlm):
    """LiteLlm de ADK que recorre las entradas de LOCAL_MODEL_CHAIN con circuit breaker por proveedor."""

    _chain: list = PrivateAttr(default_factory=list)
    _breaker: object = PrivateAttr(default=None)

    def __init__(self, entries: list[dict], timeout: int, breaker: ProviderBreaker | None = None,
                 inner_factory=None):
        if not entries:
            raise RuntimeError("LOCAL_MODEL_CHAIN vacio o invalido -- ningun proveedor LLM configurado.")
        factory = inner_factory or (lambda params: LiteLlm(timeout=timeout, **params))
        super().__init__(timeout=timeout, **llm_params_for_entry(entries[0]))
        self._chain = [(e, factory(llm_params_for_entry(e))) for e in entries]
        self._breaker = breaker or get_breaker()

    async def generate_content_async(self, llm_request, stream: bool = False):
        trace = _trace()
        enabled = ai_config.AI_BREAKER_ENABLED
        attempts = 0
        last_reason = None
        first_index = None
        for idx, (entry, inner) in enumerate(self._chain):
            name = entry["name"]
            if enabled:
                allowed, state = await self._breaker.allow(name)
            else:
                allowed, state = True, CLOSED
            if trace is not None:
                trace["breaker_state"] = state
            if not allowed:
                last_reason = f"breaker_{state.lower()}:{name}"
                logger.info("ai_operation_event=provider_skipped provider=%s state=%s", name, state)
                continue
            if attempts >= MAX_ATTEMPTS_PER_CALL:
                break
            attempts += 1
            if first_index is None:
                first_index = idx
            yielded = False
            try:
                async for resp in inner.generate_content_async(llm_request, stream=stream):
                    yielded = True
                    yield resp
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                if _is_client_error(exc):
                    raise
                if enabled:
                    await self._breaker.record_failure(name)
                last_reason = f"{type(exc).__name__}:{name}"
                logger.warning("ai_operation_event=provider_failed provider=%s error=%s yielded=%s",
                               name, type(exc).__name__, yielded)
                if yielded:
                    raise  # no se puede cambiar de proveedor a mitad de una respuesta ya emitida
                continue
            if enabled:
                await self._breaker.record_success(name)
            if trace is not None:
                trace.update(provider=name, model=entry["model"], attempts=attempts,
                             fallback_used=(idx != 0), fallback_reason=last_reason if idx != 0 else None)
            return
        if trace is not None:
            trace.update(provider=None, attempts=attempts, fallback_reason=last_reason)
        raise ModelUnavailableError(f"Ningun proveedor de modelo disponible (ultimo motivo: {last_reason}).")


def build_fallback_model(timeout: int) -> FallbackLiteLlm:
    entries = parse_local_model_chain(ai_config.LOCAL_MODEL_CHAIN)
    return FallbackLiteLlm(entries, timeout=timeout)
