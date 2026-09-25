"""
PLAN_LLMDINAMICO (2026-09-25), FASE 4 -- resolver de proveedores LLM desde el Registry de Django (`ai_provider`).

Hasta ahora el ADK solo leia `LOCAL_MODEL_CHAIN` (env): lo que el admin editaba en /panel/soporte/ia-config no llegaba al
runtime real. Este modulo consulta `GET /api/v1/internal/ai/provider-config/?channel=support_chat` (endpoint interno, aislado
por red igual que el resto de /internal/*), lo cachea unos segundos y devuelve la cadena en el MISMO formato que
`model_chain.parse_local_model_chain` (name/kind/base_url/model/api_key_env) mas `api_key_value`.

Reglas:
- Apagado por defecto (`AI_PROVIDER_REGISTRY_ENABLED=false`): el comportamiento actual (LOCAL_MODEL_CHAIN) no cambia.
- `None` = "usa LOCAL_MODEL_CHAIN": Django respondio sin primario / canal apagado, o el Registry no responde y no hay una
  ultima cadena buena reciente. Nunca se inventa un proveedor.
- Si Django falla, se conserva la ultima cadena buena hasta `AI_PROVIDER_REGISTRY_STALE_SECONDS` (un Django reiniciando no
  debe cambiar de modelo a mitad de trafico).
- Las API keys (`api_key_value`) viven solo en memoria de este proceso: nunca se loguean ni entran a las metricas.
- El LLM no participa: la cadena la decide el admin (BD) y la ejecuta codigo determinista.
"""
import asyncio
import logging
import time

import httpx

import config as ai_config
from model_chain import VALID_KINDS
from url_guard import UnsafeProviderURL, validate_provider_url

logger = logging.getLogger("provider_registry")

_PATH = "/internal/ai/provider-config/"
_CHANNEL = "support_chat"

_state = {"entries": None, "fetched_at": 0.0, "good_at": 0.0, "good": None}
_lock = None


def _get_lock() -> asyncio.Lock:
    global _lock
    if _lock is None:
        _lock = asyncio.Lock()
    return _lock


def current_config_version():
    """config_version del canal en la ultima carga del Registry (None si nunca se cargo o no se usa)."""
    return _state.get("version")


def reset_cache() -> None:
    """Solo para tests y para forzar recarga."""
    _state.update(entries=None, fetched_at=0.0, good_at=0.0, good=None)


def _is_loopback(url: str) -> bool:
    from urllib.parse import urlparse
    return (urlparse(url or "").hostname or "").lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0")


def _to_entry(item) -> dict | None:
    if not isinstance(item, dict):
        return None
    name, kind, model = item.get("name"), item.get("kind"), item.get("model")
    if not (name and model) or kind not in VALID_KINDS:
        logger.warning("ai_operation_event=registry_entry_invalid name=%s kind=%s", name, kind)
        return None
    base_url = item.get("base_url") or ""
    if base_url and _is_loopback(base_url):
        # Dentro del contenedor del ADK, localhost/127.0.0.1 es el propio contenedor: nunca alcanza a LM Studio/Ollama del host.
        # En el panel se debe usar host.docker.internal (o el nombre del servicio). Se descarta en vez de fallar en cada turno.
        logger.warning("ai_operation_event=registry_entry_loopback name=%s (usar host.docker.internal)", name)
        return None
    if base_url:
        # PLAN_LLMDINAMICO F3: el ADK no confia en la URL que viene de la BD; se re-valida antes de llamarla (defensa en profundidad).
        try:
            validate_provider_url(base_url)
        except UnsafeProviderURL as exc:
            logger.warning("security_event=registry_entry_unsafe_url name=%s reason=%s", name, exc)
            return None
    entry = {
        "name": str(name), "kind": kind, "base_url": item.get("base_url") or "", "model": str(model),
        "api_key_env": item.get("api_key_env") or None, "api_key_value": item.get("api_key_value") or None,
    }
    # PLAN_LLMDINAMICO sec. 3: campos opcionales del Registry (los entrega ai_provider.services.providers.base.build_runtime_config).
    for key in ("provider_uuid", "auth_type", "api_key_header", "verify_tls", "generation", "timeout"):
        if item.get(key) is not None:
            entry[key] = item[key]
    return entry


def parse_registry_payload(payload: dict) -> list[dict] | None:
    """Payload del endpoint -> lista de entradas. None si el canal esta apagado o no hay primario (usar LOCAL_MODEL_CHAIN)."""
    if not isinstance(payload, dict) or not payload.get("enabled", True):
        return None
    primary = payload.get("primary")
    if not primary:
        return None
    primary_entry = _to_entry(primary)
    if primary_entry is None:
        # Un primario invalido/inseguro/loopback NO se sustituye en silencio por un fallback: se ignora todo el registro y el ADK usa
        # LOCAL_MODEL_CHAIN (el operador ve el warning y corrige el panel).
        logger.warning("ai_operation_event=registry_primary_unusable using=LOCAL_MODEL_CHAIN")
        return None
    return [primary_entry] + [e for e in (_to_entry(i) for i in (payload.get("fallbacks") or [])) if e]


async def _fetch() -> tuple[str, list[dict] | None]:
    """('ok'|'empty'|'error', entradas). 'empty' = Django respondio pero no hay config utilizable."""
    from config import DJANGO_INTERNAL_API_URL, internal_django_headers

    try:
        async with httpx.AsyncClient(timeout=ai_config.AI_PROVIDER_REGISTRY_TIMEOUT_SECONDS) as client:
            resp = await client.get(f"{DJANGO_INTERNAL_API_URL}{_PATH}", params={"channel": _CHANNEL},
                                    headers=internal_django_headers(
                                        {"X-AI-Service-Token": ai_config.AI_SERVICE_TOKEN} if ai_config.AI_SERVICE_TOKEN else None))
        if resp.status_code != 200:
            logger.warning("ai_operation_event=registry_fetch_failed status=%s", resp.status_code)
            return "error", None
        payload = resp.json()
        _state["version"] = payload.get("config_version") if isinstance(payload, dict) else None
        entries = parse_registry_payload(payload)
    except Exception as exc:  # noqa: BLE001 - el Registry nunca debe tumbar el chat
        logger.warning("ai_operation_event=registry_fetch_failed error=%s", type(exc).__name__)
        return "error", None
    return ("ok", entries) if entries else ("empty", None)


async def get_registry_entries() -> list[dict] | None:
    """Cadena vigente del Registry (cache con TTL) o None para usar LOCAL_MODEL_CHAIN."""
    if not ai_config.AI_PROVIDER_REGISTRY_ENABLED:
        return None
    ttl = ai_config.AI_PROVIDER_REGISTRY_TTL_SECONDS
    now = time.monotonic()
    if _state["fetched_at"] and now - _state["fetched_at"] < ttl:
        return _state["entries"]
    async with _get_lock():
        now = time.monotonic()
        if _state["fetched_at"] and now - _state["fetched_at"] < ttl:
            return _state["entries"]
        status, entries = await _fetch()
        if status == "ok":
            changed = entries != _state["good"]
            _state.update(entries=entries, good=entries, good_at=now, fetched_at=now)
            if changed:
                logger.info("ai_operation_event=registry_chain_loaded config_version=%s providers=%s", _state.get("version"),
                            ",".join(f"{e['name']}:{e['model']}" for e in entries))
        elif status == "empty":
            _state.update(entries=None, good=None, fetched_at=now)
        else:
            stale_ok = _state["good"] and now - _state["good_at"] < ai_config.AI_PROVIDER_REGISTRY_STALE_SECONDS
            _state.update(entries=_state["good"] if stale_ok else None, fetched_at=now)
            if not stale_ok:
                _state["good"] = None
        return _state["entries"]
