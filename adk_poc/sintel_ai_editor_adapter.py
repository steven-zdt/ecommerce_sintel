"""
ADK-09 -- Human-in-the-loop adapter para `ai_editor`.

Regla dura del plan (seccion 9): "ADK debe usar require_confirmation en
cualquier escritura real; ADK NUNCA debe llegar a promote_to_workspace()
directamente -- debe seguir detras de validation/risk-gate/human-approval/
promotion-guard."

## Alcance real (ver hallazgo de ADK-07, AUDITORIA/ADK_MIGRATION_AUDIT.md
## seccion 8sexies, ANTES de leer el resto de este docstring)

`ai_editor.agent.run_autonomous_change_loop()` YA orquesta el pipeline
completo de PROPUESTA de cambio (intent -> resolver -> planner ->
generation -> sandbox validation -> reportes de calidad/arquitectura/
dependencias/contratos/tests/documentacion) de forma segura, con su propia
regla de seguridad garantizada ESTRUCTURALMENTE: el paquete `ai_editor.
agent` completo NUNCA importa `generation.promotion` ni `repository.
promote` -- el resultado mas "avanzado" que puede producir es
`APPROVAL_REQUIRED`. Este adapter NO reimplementa ese pipeline como Tools
ADK sueltas (violaria "no duplicar") -- expone la MISMA funcion real.

Dos Tools, con gating DISTINTO a proposito:

1. `propose_code_change` -- envuelve `run_autonomous_change_loop()`
   DIRECTO, sin `require_confirmation`. Es seguro de correr libremente: por
   la regla estructural de arriba, esta funcion NUNCA puede escribir sobre
   `WORKSPACE_ROOT` real (`ecommerce_sintel/`, el repo Django VIVO --
   confirmado leyendo `ai_editor/workspace.py`), solo sobre un sandbox
   aislado.
2. `promote_code_change` -- el UNICO punto de todo este adapter que puede
   llegar a `generation.promotion.review_and_promote()` (la funcion real
   que SI escribe sobre `WORKSPACE_ROOT` real, si sus propios 4 gates
   internos lo permiten -- decision==APPROVE, confirm=True, validacion
   nivel 1, fingerprints por archivo; ver ADK-00). Envuelta con
   `FunctionTool(require_confirmation=True)` -- mismo mecanismo ya probado
   funcional en ADK-02 (`RequestKycUpgradeTool`): ADK pausa la ejecucion
   ANTES de invocar el wrapper hasta que un humano confirme explicitamente
   (`ToolConfirmation(confirmed=True)`).

`AgentRunResult` (el resultado real de `run_autonomous_change_loop`)
contiene objetos Python vivos (`sandbox_loop_result`, `context`, `plan` --
no serializables para que un LLM los reenvie como argumentos). Se guardan
en `_PENDING_PROPOSALS`, un registro de proceso indexado por
`proposal_id` -- mismo patron que `sintel_adapter._EPHEMERAL_TOKENS`
(ADK-08): efimero, nunca pasa por `Session.state` de ADK (una propuesta de
cambio de codigo no es secreta como un JWT, pero SI es demasiado grande/no
serializable para vivir en state -- la razon de fondo es distinta, el
patron de aislamiento es el mismo).

**Limite deliberado de alcance de ADK-09**: no se ejecuta el loop
`run_autonomous_change_loop()` REAL contra un LLM en los tests de este
adapter -- es, por diseno propio del pipeline (ver `loop.py`), una cadena
larga de llamadas LLM + validacion de sandbox (la propia FASE 53 lo llama
"primera vez que se ejecuta contra un LLM real" en TODO el desarrollo de
ese plan de 60 fases). Los tests de este adapter prueban el MECANISMO de
gating (propose sin confirmacion, promote SI la exige, nunca se le puede
pasar por alto) con `review_and_promote` mockeado -- igual que ADK-02
nunca invoco la escritura real de `RequestKycUpgradeTool`.
"""
import uuid
from typing import Literal

from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext as AdkToolContext

_PENDING_PROPOSALS: dict[str, object] = {}


def propose_code_change(request: str) -> dict:
    """Corre el pipeline REAL de propuesta de cambio. Seguro de ejecutar
    sin confirmacion -- ver docstring del modulo, regla estructural de
    `ai_editor.agent`."""
    from ai_editor.agent import run_autonomous_change_loop

    result = run_autonomous_change_loop(request)
    proposal_id = uuid.uuid4().hex[:12]
    _PENDING_PROPOSALS[proposal_id] = result
    return {
        "proposal_id": proposal_id,
        "status": result.status,
        "human_review_text": result.human_review_text,
        "warnings": result.warnings,
    }


async def promote_code_change(
    *, proposal_id: str, decision: Literal["APPROVE", "REJECT"],
    reviewer_note: str | None = None, tool_context: AdkToolContext,
) -> dict:
    """Promueve (o rechaza) una propuesta YA generada por
    `propose_code_change`. UNICO punto de este adapter que puede llegar a
    `review_and_promote` -- registrado como `FunctionTool(require_
    confirmation=True)`, asi que ADK ya pauso este wrapper hasta
    confirmacion humana antes de que esta linea se ejecute."""
    from ai_editor.generation.promotion import review_and_promote
    from ai_editor.workspace import WORKSPACE_ROOT

    result = _PENDING_PROPOSALS.get(proposal_id)
    if result is None:
        return {"error": f"proposal_id '{proposal_id}' no existe o ya se resolvio."}

    outcome = review_and_promote(
        result.sandbox_loop_result, result.context, result.plan, WORKSPACE_ROOT,
        decision=decision, reviewer_note=reviewer_note, confirm=True,
    )
    _PENDING_PROPOSALS.pop(proposal_id, None)
    return {"promoted": bool(getattr(outcome, "promoted", False)), "detail": str(outcome)}


def build_ai_editor_hitl_tools() -> list[FunctionTool]:
    """`propose_code_change` sin gate; `promote_code_change` gateado --
    ver docstring del modulo para el porque de cada uno."""
    return [
        FunctionTool(propose_code_change),
        FunctionTool(promote_code_change, require_confirmation=True),
    ]
