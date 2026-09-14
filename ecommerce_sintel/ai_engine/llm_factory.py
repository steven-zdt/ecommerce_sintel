import logging
import time

import httpx
import redis.asyncio as aredis
from redis.exceptions import RedisError
from decouple import config as env
from langchain_core.language_models import BaseChatModel
from config import CHECKPOINTER_REDIS_URL, DJANGO_INTERNAL_API_URL, LOCAL_MODEL_CHAIN, OPENAI_API_KEY, ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

# G2 (AUDITORIA/16, 2026-08-01): ninguna llamada al LLM tenia timeout propio -- el unico corte
# end-to-end era el timeout de Django esperando /chat completo (AI_CHAT_TIMEOUT_SECONDS=300,
# support/services/ai_bridge.py). Con un solo proceso uvicorn (Dockerfile, sin --workers), una
# llamada colgada al proveedor degradaba la capacidad practica del proceso entero sin que el
# motor mismo pudiera cortar nada.
LLM_TIMEOUT_SECONDS = 90

_VALID_KINDS = {"ollama-nativo", "openai-compatible", "anthropic"}


def parse_local_model_chain(raw: str) -> list[dict]:
    """Parsea LOCAL_MODEL_CHAIN (ver config.py para el formato). Entradas invalidas se
    ignoran con un warning en vez de tumbar el arranque -- un typo en una entrada de
    fallback no deberia impedir que el motor arranque con las demas."""
    entries: list[dict] = []
    for chunk in (raw or "").split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = [p.strip() for p in chunk.split("|")]
        if len(parts) not in (4, 5):
            logger.warning("[llm_factory] entrada invalida en LOCAL_MODEL_CHAIN, se ignora: %r", chunk)
            continue
        name, kind, base_url, model = parts[:4]
        if kind not in _VALID_KINDS:
            logger.warning("[llm_factory] tipo desconocido '%s' en LOCAL_MODEL_CHAIN, se ignora: %r", kind, chunk)
            continue
        entries.append({
            "name": name, "kind": kind, "base_url": base_url, "model": model,
            "api_key_env": parts[4] if len(parts) == 5 else None,
        })
    return entries


def _resolve_api_key(entry: dict, default: str) -> str:
    """FASE 4 (plan "CONFIGURACION DINAMICA DE MODELOS LOCALES", 2026-08-13): las
    entradas dinamicas (Django/ai_provider, via get_dynamic_llm) traen la key ya
    resuelta en 'api_key_value' (descifrada por Django, ver ai_provider/api/
    internal_ai.py); las entradas de LOCAL_MODEL_CHAIN (estatico, bootstrap/
    emergencia) siguen resolviendo 'api_key_env' (nombre de variable de entorno) como
    siempre. Ambos caminos conviven en el mismo _build_model() sin bifurcar la logica
    de construccion del cliente LLM."""
    if entry.get("api_key_value"):
        return entry["api_key_value"]
    if entry.get("api_key_env"):
        return env(entry["api_key_env"], default=default)
    return default


def _build_model(entry: dict) -> BaseChatModel:
    kind = entry["kind"]

    if kind == "ollama-nativo":
        from langchain_ollama import ChatOllama
        logger.info("[llm] motor '%s' (ollama-nativo): %s @ %s", entry["name"], entry["model"], entry["base_url"])
        return ChatOllama(
            model=entry["model"], base_url=entry["base_url"], temperature=0.1,
            num_predict=1500, num_ctx=8192, client_kwargs={"timeout": LLM_TIMEOUT_SECONDS},
        )

    if kind == "anthropic":
        from langchain_anthropic import ChatAnthropic
        api_key = _resolve_api_key(entry, default=ANTHROPIC_API_KEY)
        logger.info("[llm] motor '%s' (anthropic): %s", entry["name"], entry["model"])
        return ChatAnthropic(
            model=entry["model"], api_key=api_key, temperature=0.1,
            default_request_timeout=LLM_TIMEOUT_SECONDS,
        )

    # openai-compatible: cubre CUALQUIER motor que hable /v1/chat/completions -- LM Studio,
    # vLLM, llama.cpp (modo servidor), text-generation-webui, LocalAI, DeepSeek, OpenAI real --
    # sin una clase de Python por motor. Motores locales no exigen una key real.
    from langchain_openai import ChatOpenAI
    api_key = _resolve_api_key(entry, default=OPENAI_API_KEY or "not-needed")
    logger.info("[llm] motor '%s' (openai-compatible): %s @ %s", entry["name"], entry["model"], entry["base_url"])
    return ChatOpenAI(
        model=entry["model"], base_url=entry["base_url"], api_key=api_key, temperature=0.1,
        request_timeout=LLM_TIMEOUT_SECONDS,
        # CERRADO 2026-08-17 (auditoria LM Studio) -- hallazgo real, no hipotetico:
        # sin este limite, el cliente `openai` reintenta automaticamente (default
        # 2 reintentos) cada vez que request_timeout se cumple -- con un motor
        # local lento (qwen3.5-9b "razonador" tardo >90s en generar en este
        # hardware), eso convierte UN timeout de 90s en un turno real de ~289s
        # antes de degradar (verificado en vivo, traceback real capturado:
        # openai.APITimeoutError tras varios "Retrying request to
        # /chat/completions"). El fallback de main.py sigue siendo seguro (nunca
        # un 500 crudo), pero tardar 5 minutos en llegar a "asistente no
        # disponible" es inaceptable para un chat en vivo. max_retries=0: falla
        # rapido a los ~90s, una sola vez, en vez de reintentar y acumular
        # minutos. El fallback nativo de LangChain (.with_fallbacks(), otro
        # motor en LOCAL_MODEL_CHAIN) sigue siendo el mecanismo correcto para
        # tolerancia a fallos -- reintentar el MISMO motor lento no ayuda.
        max_retries=0,
        # Mismo hallazgo: sin limite de tokens de salida, el modelo razonador
        # puede generar de forma practicamente ilimitada antes de que
        # request_timeout corte la conexion. 2048 da margen para razonamiento
        # largo sin abrir la puerta a generacion sin techo.
        max_tokens=2048,
    )


def get_llm() -> BaseChatModel:
    """
    Nivel A (auditoria 2026-08-07): ya no hay un unico proveedor fijo. LOCAL_MODEL_CHAIN
    describe una cadena ordenada de motores -- locales, en Docker, o cloud -- el primero
    es el primario y el resto son fallback automatico via .with_fallbacks() (nativo de
    langchain-core, sin dependencia nueva). Si el motor primario no responde, LangChain
    conmuta al siguiente por request, no solo al arrancar el proceso. Verificado que
    .bind_tools() (action_graph.py) sigue funcionando sobre la cadena completa sin
    modificarse -- aplica el binding a cada motor encadenado.

    Agregar, quitar o reordenar motores es editar LOCAL_MODEL_CHAIN, nunca este archivo.
    """
    entries = parse_local_model_chain(LOCAL_MODEL_CHAIN)
    if not entries:
        raise ValueError("LOCAL_MODEL_CHAIN no tiene ninguna entrada valida -- revisa el formato en config.py.")

    models = [_build_model(entry) for entry in entries]
    primary, *fallbacks = models
    if not fallbacks:
        return primary

    logger.info("[llm] cadena con fallback (%d motores): %s", len(entries), " -> ".join(e["name"] for e in entries))
    return primary.with_fallbacks(fallbacks)


# ---------------------------------------------------------------------------
# FASE 4 (plan "CONFIGURACION DINAMICA DE MODELOS LOCALES", 2026-08-13): version
# dinamica de get_llm(), usada SOLO por /chat (main.py). /generate (AI Editor) sigue
# usando get_llm()/_STATE['llm'] sin cambios -- fuera de alcance de este plan.
# ---------------------------------------------------------------------------
_DYNAMIC_CHAIN_CACHE_TTL_SECONDS = 15
_dynamic_chain_cache = {"entries": None, "fetched_at": 0.0, "generation": None}


async def _get_runtime_generation(channel: str) -> int | None:
    """FASE 20 (plan 'AI Provider Runtime', 2026-08-13): lee el contador de
    generacion que Django incrementa en cada mutacion relevante de ai_provider
    (ver ai_provider/services/runtime_cache.py::invalidate()) -- misma Redis/DB que
    el checkpointer de LangGraph (CHECKPOINTER_REDIS_URL), prefijo de clave distinto
    ('ai_runtime:') para no colisionar con las claves 'ai:cp:*' del checkpointer.

    None si la clave no existe todavia (nunca hubo una mutacion) o si Redis no
    responde -- en ambos casos RuntimeConfigResolver.resolve() lo trata igual que
    'sin cambios detectados' y sigue con el TTL normal como red de seguridad
    (nunca lanza, mismo criterio que _fetch_dynamic_chain())."""
    try:
        async with aredis.Redis.from_url(CHECKPOINTER_REDIS_URL, socket_timeout=2) as r:
            raw = await r.get(f"ai_runtime:{channel}:gen")
        return int(raw) if raw is not None else None
    except (RedisError, OSError, ValueError) as exc:
        logger.warning("[llm_factory] fallo leyendo generacion de cache (%s), se ignora", exc)
        return None


async def _fetch_dynamic_chain(channel: str = "support_chat") -> list[dict] | None:
    """Consulta el internal API de Django (ai_provider, FASE 2/15/19:
    GET /api/v1/internal/ai/provider-config/) por primary+fallbacks configurados
    desde /panel/soporte. None si no hay config real (canal deshabilitado o sin
    primary_model) o la llamada falla -- nunca lanza; el caller
    (RuntimeConfigResolver) cae a LOCAL_MODEL_CHAIN en cualquiera de esos casos,
    exactamente el comportamiento previo a esta fase.

    FASE 19: cada entrada de 'primary'/'fallbacks' ya viene en el shape exacto de
    _build_model() (name/kind/base_url/model/api_key_env/api_key_value) -- Django
    la construye con BaseProviderAdapter.build_runtime_config() (ver ai_provider/
    api/internal_ai.py), asi que aqui ya no hace falta desanidar 'provider' a mano.

    Async (httpx.AsyncClient, no httpx.get sincrono): el Dockerfile corre uvicorn sin
    --workers (ver LLM_TIMEOUT_SECONDS arriba) -- una llamada sincrona bloquearia el
    unico event loop del proceso completo, no solo este turno."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{DJANGO_INTERNAL_API_URL}/internal/ai/provider-config/",
                params={"channel": channel},
            )
        if resp.status_code != 200:
            logger.warning("[llm_factory] provider-config respondio %d, cae a LOCAL_MODEL_CHAIN", resp.status_code)
            return None
        data = resp.json()
        primary = data.get("primary")
        if not primary:
            return None
        return [primary, *(data.get("fallbacks") or [])]
    except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
        logger.warning("[llm_factory] fallo consultando config dinamica (%s), cae a LOCAL_MODEL_CHAIN", exc)
        return None


class RuntimeConfigResolver:
    """FASE 19 (plan 'AI Provider Runtime', 2026-08-13): nombre formal para lo que
    antes eran funciones sueltas (_fetch_dynamic_chain + el cuerpo de
    get_dynamic_llm) -- mismo comportamiento, mismo cache a nivel de modulo
    (_dynamic_chain_cache/_DYNAMIC_CHAIN_CACHE_TTL_SECONDS, no movido a la clase
    para no romper los tests existentes que lo inspeccionan directo via
    llm_factory._dynamic_chain_cache). get_dynamic_llm() (usada por main.py y por
    la suite de tests actual) queda como wrapper delgado sobre resolve().

    FASE 20: ademas del TTL de 15s, cada resolucion chequea un contador de
    generacion en Redis (_get_runtime_generation) -- si Django incremento el
    contador desde la ultima lectura (una mutacion real en /panel/soporte), se
    fuerza un refetch inmediato sin esperar el resto del TTL. El TTL sigue siendo
    la red de seguridad si Redis no esta disponible o la clave todavia no existe."""

    @staticmethod
    async def resolve(channel: str = "support_chat") -> BaseChatModel:
        now = time.monotonic()
        remote_generation = await _get_runtime_generation(channel)
        generation_changed = (
            remote_generation is not None
            and _dynamic_chain_cache["generation"] is not None
            and remote_generation != _dynamic_chain_cache["generation"]
        )
        if generation_changed or now - _dynamic_chain_cache["fetched_at"] > _DYNAMIC_CHAIN_CACHE_TTL_SECONDS:
            _dynamic_chain_cache["entries"] = await _fetch_dynamic_chain(channel)
            _dynamic_chain_cache["fetched_at"] = now
            _dynamic_chain_cache["generation"] = remote_generation

        entries = _dynamic_chain_cache["entries"]
        source = "dinamica (ai_provider)"
        if not entries:
            entries = parse_local_model_chain(LOCAL_MODEL_CHAIN)
            source = "LOCAL_MODEL_CHAIN (bootstrap/fallback)"
        if not entries:
            raise ValueError("Ni la config dinamica ni LOCAL_MODEL_CHAIN tienen entradas validas.")

        models = [_build_model(entry) for entry in entries]
        primary, *fallbacks = models
        logger.info("[llm] /chat usando config %s (%d motores)", source, len(entries))
        if not fallbacks:
            return primary
        return primary.with_fallbacks(fallbacks)


async def get_dynamic_llm(channel: str = "support_chat") -> BaseChatModel:
    """Resuelve el LLM real para un turno de /chat -- wrapper compatible hacia atras
    sobre RuntimeConfigResolver.resolve() (FASE 19). Cache de
    _DYNAMIC_CHAIN_CACHE_TTL_SECONDS en memoria del proceso: un cambio guardado en
    /panel/soporte se refleja en el siguiente turno sin reiniciar el contenedor
    (dentro de la ventana del cache; ver FASE 20 para invalidacion inmediata via
    Redis). Si no hay config real o Django es inalcanzable, cae a LOCAL_MODEL_CHAIN
    (bootstrap/fallback/emergencia -- regla explicita del plan maestro)."""
    return await RuntimeConfigResolver.resolve(channel)
