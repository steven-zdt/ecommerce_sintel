"""
API REST del motor cognitivo Sintel AI Engine (chatbot de soporte + RAG).

FASE 4a (mision de simplificacion arquitectonica, 2026-09-14): se retiro el
pipeline de generacion/validacion de codigo (`/generate`, `/validate`,
`/plan`, `/impact`, `/breakage`, `/graph/node`, `/graph/impact` y los
modulos graph.py/chains.py/chains_frontend.py/guardrails.py/
guardrails_frontend.py/planner.py) -- confirmado sin ningun consumidor
externo (grep global) y superseded por `ai_editor/` + `project_knowledge_graph/`,
ya construidos y certificados (FASE61).

FASE 4b (misma mision): se retiro ChromaDB por completo (`/ingest`,
vectorstore_factory.py, embeddings_factory.py, bootstrap.py, loaders.py,
splitters.py) -- el RAG del chat (`/chat`) ya no vive en este proceso desde
FASE 3, consulta el endpoint interno de Django `ai_knowledge`
(PostgreSQL+pgvector) via retrievers.py::retrieve_knowledge_for_chat. Este
motor ya no mantiene ningun estado de conocimiento propio en memoria.

FASE 5 (misma mision, 2026-09-14): se retiraron `/memory`, `/search`,
`/indices`, `/manifest/{app}`, `/refresh`, `/refresh/detect` y los modulos
que los sostenian (memory_builder.py, specialized_retrieval.py,
ai_manifest.py, incremental_updater.py) junto con los artefactos JSON que
leian/escribian (PROJECT_MAP.json, DEPENDENCY_GRAPH.json,
KNOWLEDGE_GRAPH.json, GLOBAL_MEMORY.json, AI_MANIFESTS/, APP_MEMORY/,
MASTER_MANIFEST.json) -- eran indices/memoria/manifiestos construidos
exclusivamente para alimentar el pipeline de generacion de codigo retirado
en FASE 4a; sin ese pipeline, no tenian ningun consumidor (confirmado con
grep global de todo el repo, incluyendo scripts y docs operativos).

Este proceso ahora expone unicamente `/chat`, `/health`, y las rutas del AI
Gateway (`/api/v1/ai/*`, `gateway.py`). Ver
AUDITORIA/ARCHITECTURE_SIMPLIFICATION_AUDIT.md para el detalle completo.

Arranque:
    uvicorn main:app --host 0.0.0.0 --port 8100 --reload
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
import httpx

from auth import get_validated_token, decode_django_jwt
from action_graph import run_action_chat

from llm_factory import get_llm, get_dynamic_llm
from gateway import ai_router
from config import LOCAL_MODEL_CHAIN, OLLAMA_BASE_URL
from llm_factory import parse_local_model_chain

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

_STATE: dict = {}


async def _ensure_ollama_models() -> None:
    """
    Pre-carga en Ollama los modelos que se van a necesitar antes de la primera peticion
    real, para evitar el timeout de la primera llamada. Nivel A (auditoria 2026-08-07):
    ya no hay un unico LLM_PROVIDER que revisar -- se recorre LOCAL_MODEL_CHAIN y se
    pre-carga cada entrada 'ollama-nativo'. Motores openai-compatible/anthropic no
    necesitan pre-carga: son servicios externos al proceso, no procesos que este mismo
    Ollama tenga que arrancar.

    FASE 4b (2026-09-14): ya no pre-carga el modelo de embeddings -- este proceso no
    calcula embeddings desde que el RAG se movio a Django/ai_knowledge (FASE 1/3); el
    modelo de embeddings que SI importa (el que usa EmbeddingService del lado Django)
    se pre-carga o no segun ese proceso, no este.
    """
    targets: list[tuple[str, str]] = []
    for entry in parse_local_model_chain(LOCAL_MODEL_CHAIN):
        if entry["kind"] == "ollama-nativo":
            targets.append((entry["base_url"], entry["model"]))

    seen: set[tuple[str, str]] = set()
    async with httpx.AsyncClient(timeout=300) as client:
        for base_url, model in targets:
            key = (base_url, model)
            if key in seen:
                continue
            seen.add(key)
            try:
                logger.info("[startup] Pre-cargando modelo Ollama '%s' @ %s...", model, base_url)
                resp = await client.post(
                    f"{base_url}/api/pull",
                    json={"name": model, "stream": False},
                )
                resp.raise_for_status()
                logger.info("[startup] Modelo '%s' listo.", model)
            except Exception as exc:
                logger.warning("[startup] No se pudo pre-cargar '%s' @ %s: %s", model, base_url, exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[startup] Inicializando motor cognitivo...")
    try:
        await _ensure_ollama_models()  # no-op limpio si LOCAL_MODEL_CHAIN no tiene entradas ollama-nativo
        llm              = get_llm()
        _STATE["llm"]    = llm

        logger.info("[startup] Motor listo.")
    except Exception as exc:
        logger.error("[startup] Error critico durante init: %s", exc)
        raise
    yield
    logger.info("[shutdown] Motor cognitivo detenido.")


app = FastAPI(
    title="Sintel AI Engine",
    version="1.0.0",
    description="Motor cognitivo LangChain + LangGraph para Sintel E-Commerce REST v5",
    lifespan=lifespan,
)

# AI Gateway (Fase 1 AI Core): rutas /api/v1/ai/* con JWT de Django obligatorio.
# Los endpoints historicos de generacion de codigo de abajo no cambian.
app.include_router(ai_router)


# ─── Endpoints ───────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    # G1 (AUDITORIA/16, 2026-08-01): antes sin ningun limite en toda la cadena
    # support(consumers.py) -> ChatRequest -> LLM. Inofensivo hoy con Ollama local (costo
    # marginal ~0), pero un riesgo de costo real y directo si se activa un proveedor de pago
    # (LLM_PROVIDER=openai/anthropic, ya soportado en llm_factory.py) sin este techo.
    message: str = Field(max_length=4000)
    conversation_id: str | None = None
    # Fase 4: resolucion explicita de una confirmacion pendiente (tambien se
    # acepta un mensaje "si"/"no" simple en el mismo hilo).
    confirm: bool | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    intent: str
    agent: str | None = None
    tool_calls: list
    tool_results: list
    needs_confirmation: bool = False
    confirmation: dict | None = None
    response: str
    # Fase 8 AI Core: telemetria del turno (ver ai_engine/observability.py::TurnMetrics),
    # antes solo se emitia a un log JSON y se descartaba.
    metrics: dict | None = None


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, token: str = Depends(get_validated_token)):
    """
    Action Graph (Fase 3 AI Core): el LLM decide que capability de LECTURA
    usar y responde con datos reales del usuario autenticado. No reemplaza
    /generate -- es el grafo paralelo de acciones de negocio.
    """
    if not _STATE.get("llm"):
        raise HTTPException(503, "Motor no inicializado. Esperar al lifespan startup.")
    payload = decode_django_jwt(token)
    try:
        # FASE 4 (plan "CONFIGURACION DINAMICA DE MODELOS LOCALES", 2026-08-13):
        # get_dynamic_llm() consulta ai_provider (Postgres via Django) en vez de usar
        # el LLM fijo de _STATE construido una sola vez al arrancar -- cae sola a
        # LOCAL_MODEL_CHAIN/_STATE['llm'] si no hay config real o Django no responde,
        # asi que el guard de arriba (_STATE['llm'] inicializado) sigue siendo valido
        # como senal de que el proceso arranco bien.
        chat_llm = await get_dynamic_llm()
        result = await run_action_chat(
            message=req.message,
            conversation_id=req.conversation_id,
            token=token,
            user_id=payload["user_id"],
            llm=chat_llm,
            confirm=req.confirm,
        )
    except Exception:
        # Certificacion del chat (2026-08-07): con un solo motor en
        # LOCAL_MODEL_CHAIN (sin fallback configurado), una caida del motor
        # (ej. httpx.ConnectError si el contenedor se detiene) no tenia
        # ningun catch en este endpoint -- se propagaba como 500 crudo sin
        # cuerpo util. ai_bridge.py (Django) ya trata cualquier status != 200
        # como "motor no disponible" y degrada con gracia del lado del
        # usuario (mensaje + Human Handoff implicito), pero el 500 crudo
        # rompia la traza [AI_BRIDGE] con un cuerpo vacio en vez de un
        # error explicito, y cualquier otro consumidor de /chat (debug
        # manual, futuros clientes) se llevaba una excepcion sin contexto.
        logger.exception("[chat] error no controlado en run_action_chat, conversation_id=%s", req.conversation_id)
        return ChatResponse(
            conversation_id=req.conversation_id or "",
            intent="unknown",
            agent=None,
            tool_calls=[],
            tool_results=[],
            needs_confirmation=False,
            confirmation=None,
            response="En este momento nuestro asistente no esta disponible. Un agente humano revisara tu mensaje pronto.",
            metrics={"engine_unavailable": True},
        )
    return ChatResponse(**result)


@app.get("/health")
async def health():
    """
    Fase 10 (auditoria de puesta en produccion, 2026-08-17): antes devolvia
    "status": "ok" fijo -- no distinguia liveness (el proceso esta vivo) de
    readiness real de sus dependencias. `llm` siempre queda poblado si el
    proceso llego a aceptar requests (el lifespan lo construye fuera del
    bloque tolerante a fallos). Deliberadamente sin hacer una llamada de red
    nueva aqui -- un healthcheck que depende de red puede volverse su propio
    punto de falla bajo latencia/saturacion; reporta el estado ya conocido de
    `_STATE`.

    FASE 4b (2026-09-14): ya no reporta `rag_ready`/`chunks_indexed` -- este
    proceso no mantiene estado de RAG propio (ver retrievers.py). La salud
    del RAG es responsabilidad de Django/ai_knowledge, no de este healthcheck.
    """
    llm_ok = _STATE.get("llm") is not None
    return {
        "status": "ok" if llm_ok else "starting",
        "llm_ready": llm_ok,
    }
