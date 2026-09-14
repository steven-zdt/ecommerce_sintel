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
import logging

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from auth import get_validated_token
from sintel_root_workflow import IdentityResolutionError, run_sintel_turn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
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


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, token: str = Depends(get_validated_token)):
    """Root Workflow real (Google ADK) -- ver sintel_root_workflow.py."""
    try:
        result = await run_sintel_turn(
            message=req.message, token=token,
            conversation_id=req.conversation_id, confirm=req.confirm,
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
        return ChatResponse(
            conversation_id=req.conversation_id or "",
            intent="unknown", agent=None, tool_calls=[], tool_results=[],
            needs_confirmation=False, confirmation=None,
            response="En este momento nuestro asistente no esta disponible. Un agente humano revisara tu mensaje pronto.",
            metrics={"engine_unavailable": True},
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
        metrics=None,  # TurnMetrics real: pendiente, ver AUDITORIA/ADK_CUTOVER_PLAN.md
    )


@app.get("/health")
async def health():
    """Liveness -- deliberadamente sin llamada de red nueva (mismo criterio
    que el sistema OLD real: un healthcheck que depende de red puede
    volverse su propio punto de falla)."""
    return {"status": "ok", "orchestrator": "google-adk"}
