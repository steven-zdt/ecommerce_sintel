"""
API REST de `ai_engine_adk` -- servicio NUEVO de orquestacion via Google ADK
(mision "ADK-SINTEL", ADK-11 Cutover). Ver AUDITORIA/ADK_CUTOVER_PLAN.md.

Desplegado JUNTO al servicio OLD (`ai_engine/`, puerto 8100) -- este proceso
corre en un puerto propio (8101) y NO recibe trafico real de clientes hasta
que `settings.AI_ENGINE_URL` (Django) se cambie explicitamente (paso NO
ejecutado en esta fase, requiere autorizacion propia -- ver el plan).

Mismo contrato HTTP que `ai_engine/main.py::ChatRequest`/`ChatResponse`
(consumido por `support/services/ai_bridge.py::ask_ai()`/`ask_ai_async()`)
para que el swap de `AI_ENGINE_URL` sea un cambio de una sola variable, sin
tocar Django.

Arranque:
    uvicorn main:app --host 0.0.0.0 --port 8101
"""
import asyncio
import logging

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

import observability_logging as obs
from auth import get_validated_token, require_service_token
from sintel_root_workflow import IdentityResolutionError, run_sintel_turn

# HARDENING F9: filtros de contexto (request_id) y redaccion de secretos en TODOS los logs; JSON solo con LOG_FORMAT=json.
obs.configure_root(logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(
    title="Sintel AI Engine (ADK)",
    version="1.0.0",
    description="Motor cognitivo Google ADK para Sintel E-Commerce REST v5 -- ver AUDITORIA/ADK_CUTOVER_PLAN.md",
)


class ChatRequest(BaseModel):
    # Mismo limite que el sistema OLD (main.py real) -- mismo motivo real
    # (G1, AUDITORIA/16): sin techo, un proveedor de pago detras de
    # LOCAL_MODEL_CHAIN es un riesgo de costo directo.
    message: str = Field(max_length=4000)
    conversation_id: str | None = None
    confirm: bool | None = None
    # Fase 2 de PLAN_SINTEL_ADMIN_AI_ADK_PANEL_LOOP.md (Admin AI Gateway) --
    # "admin" | "customer" (default). Mismo /chat sirve al widget de soporte
    # del cliente Y a /panel/asistente -- este campo es lo unico que le dice
    # a resolve_turn_agent() (sintel_root_workflow.py) que nunca debe caer
    # en un agente de cara al cliente para una llamada del panel admin. Ver
    # el bug real que esto corrige en el docstring de resolve_turn_agent.
    source: str = "customer"
    # HARDENING F7 (2026-09-24): canal de origen, SOLO para atribuir la memoria ("web" | "whatsapp" | "unknown").
    channel: str = "web"


class ChatResponse(BaseModel):
    conversation_id: str
    intent: str
    agent: str | None = None
    tool_calls: list
    tool_results: list
    needs_confirmation: bool = False
    confirmation: dict | None = None
    response: str
    metrics: dict | None = None


# HARDENING F2: la dependencia del decorador corre ANTES que la del JWT (secreto de servicio primero).
@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(require_service_token)])
async def chat(req: ChatRequest, request: Request, token: str = Depends(get_validated_token)):
    """Root Workflow real (Google ADK) -- ver sintel_root_workflow.py."""
    import config as ai_config

    # HARDENING F9: correlacion. X-Request-ID / X-Session-Id vienen de Django (validados; si faltan o son
    # invalidos se genera el id aqui, como antes). Todo log del turno (F3-F8 incluidos) los lleva via ContextFilter.
    request_id = obs.valid_id(request.headers.get("x-request-id")) or obs.new_request_id("req")
    session_id = request.headers.get("x-session-id") or req.conversation_id
    ctx_tokens = obs.set_context(request_id=request_id, session_id=session_id)
    try:
        return await _chat_turn(req, token, ai_config)
    finally:
        obs.reset_context(ctx_tokens)


async def _chat_turn(req: ChatRequest, token: str, ai_config):
    channel = req.channel if req.channel in ("web", "whatsapp") else "unknown"
    try:
        # HARDENING F3/C1: tiempo maximo TOTAL del turno (antes solo habia 90 s por llamada al LLM en el ADK
        # y 300 s en Django). Al vencer, respuesta segura con handoff, sin dejar el socket colgado.
        result = await asyncio.wait_for(
            run_sintel_turn(
                message=req.message, token=token,
                conversation_id=req.conversation_id, confirm=req.confirm,
                source=req.source, channel=channel,
            ),
            timeout=ai_config.AI_TURN_MAX_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "ai_operation_event=turn_timeout conversation_id=%s max_seconds=%s",
            req.conversation_id, ai_config.AI_TURN_MAX_SECONDS,
        )
        obs.emit_turn_metrics(
            {"engine_unavailable": True, "turn_timeout": True}, status="timeout", source=req.source, channel=channel,
        )
        return ChatResponse(
            conversation_id=req.conversation_id or "",
            intent="unknown", agent=None, tool_calls=[], tool_results=[],
            needs_confirmation=False, confirmation=None,
            response="En este momento nuestro asistente no esta disponible. Un agente humano revisara tu mensaje pronto.",
            metrics={"engine_unavailable": True, "turn_timeout": True},
        )
    except IdentityResolutionError as exc:
        raise HTTPException(401, f"Identidad invalida: {exc}")
    except Exception:
        # Mismo criterio de degradacion con gracia que el sistema OLD real
        # (main.py): nunca un 500 crudo sin cuerpo util -- ai_bridge.py ya
        # trata cualquier status != 200 como "motor no disponible".
        logger.exception(
            "[chat] error no controlado en run_sintel_turn, conversation_id=%s",
            req.conversation_id,
        )
        obs.emit_turn_metrics({"engine_unavailable": True}, status="degraded", source=req.source, channel=channel)
        return ChatResponse(
            conversation_id=req.conversation_id or "",
            intent="unknown", agent=None, tool_calls=[], tool_results=[],
            needs_confirmation=False, confirmation=None,
            response="En este momento nuestro asistente no esta disponible. Un agente humano revisara tu mensaje pronto.",
            metrics={"engine_unavailable": True},
        )
    turn_metrics = result.get("metrics") or {}
    obs.emit_turn_metrics(
        {**turn_metrics, "agent": result.get("agent"), "intent": result.get("intent"),
         "tool_calls": len(result.get("tool_calls") or []),
         "needs_confirmation": bool(result.get("needs_confirmation"))},
        status="degraded" if turn_metrics.get("engine_unavailable") else "ok", source=req.source, channel=channel,
    )
    return ChatResponse(
        conversation_id=result["conversation_id"],
        intent=result["intent"],
        agent=result["agent"],
        tool_calls=result["tool_calls"],
        tool_results=result["tool_results"],
        needs_confirmation=result["needs_confirmation"],
        confirmation=result["confirmation"],
        response=result["response"],
        # Mision RAG Enterprise (2026-09-16, FASE 11): cerrado para las
        # senales de RAG (retrieval_used/knowledge_state/grounding_result/
        # duration_ms) -- ver sintel_root_workflow.py::run_sintel_turn().
        # Token/costo del LLM siguen sin medirse (gap preexistente aparte).
        metrics=result.get("metrics"),
    )


@app.get("/health")
async def health():
    """Liveness -- deliberadamente sin llamada de red nueva (mismo criterio
    que el sistema OLD real: un healthcheck que depende de red puede
    volverse su propio punto de falla)."""
    return {"status": "ok", "orchestrator": "google-adk"}
