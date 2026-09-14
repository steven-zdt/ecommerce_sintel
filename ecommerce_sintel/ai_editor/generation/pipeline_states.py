"""
Estados formales del pipeline -- FASE 50 "Failure Recovery" (plan "AI
Change Proposal Engine", 2026-08-11).

Regla del prompt maestro: "Definir estados: RECEIVED, RESOLVED, PLANNED,
GENERATING, PROPOSED, VALIDATING, SANDBOXED, TESTING, RECONCILING,
APPROVAL_REQUIRED, APPROVED, PROMOTED, REJECTED, FAILED, ROLLED_BACK. No
utilizar estados ambiguos."

**Los 15 estados, cada uno mapeado al dato REAL que ya lo determina** --
ninguno es un estado "vivido" por una maquina de estados nueva (no existe
un objeto `Pipeline` que orqueste todo esto de punta a punta todavia,
eso es FASE 53 "Autonomous Controlled Loop"); esto es una funcion de
CLASIFICACION honesta sobre los resultados que YA existen en cada punto
del pipeline, para que un caller (o un futuro CLI/UI) tenga un vocabulario
unico y sin ambiguedad para reportar "donde esta" un cambio en curso.
"""
from dataclasses import dataclass

RECEIVED = "RECEIVED"
RESOLVED = "RESOLVED"
PLANNED = "PLANNED"
GENERATING = "GENERATING"
PROPOSED = "PROPOSED"
VALIDATING = "VALIDATING"
SANDBOXED = "SANDBOXED"
TESTING = "TESTING"
RECONCILING = "RECONCILING"
APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
APPROVED = "APPROVED"
PROMOTED = "PROMOTED"
REJECTED = "REJECTED"
FAILED = "FAILED"
ROLLED_BACK = "ROLLED_BACK"

ALL_STATES = (
    RECEIVED, RESOLVED, PLANNED, GENERATING, PROPOSED, VALIDATING, SANDBOXED,
    TESTING, RECONCILING, APPROVAL_REQUIRED, APPROVED, PROMOTED, REJECTED,
    FAILED, ROLLED_BACK,
)


@dataclass
class PipelineStatus:
    state: str
    detail: str

    def to_dict(self) -> dict:
        return {"state": self.state, "detail": self.detail}


def classify_pipeline_state(
    intent=None, context=None, plan=None, generation_result=None,
    sandbox_loop_result=None, promotion_outcome=None, rollback_result=None,
) -> PipelineStatus:
    """Clasifica el estado ACTUAL de un cambio a partir de los objetos
    reales que ya existen en cada punto del pipeline -- se evalua en
    orden INVERSO (del estado mas avanzado al mas temprano) para que el
    estado devuelto sea siempre el mas reciente alcanzado. Todos los
    parametros son opcionales; con ninguno, el estado es `RECEIVED`
    (nada paso todavia)."""
    if rollback_result is not None and getattr(rollback_result, "status", None) == "ROLLED_BACK":
        return PipelineStatus(ROLLED_BACK, "El cambio se promovio y despues se revirtio.")

    if promotion_outcome is not None:
        if promotion_outcome.promoted:
            return PipelineStatus(PROMOTED, "El cambio se promovio al workspace real.")
        if promotion_outcome.approval is not None and promotion_outcome.approval.decision == "REJECT":
            return PipelineStatus(REJECTED, "Un humano rechazo la propuesta explicitamente.")
        if promotion_outcome.blocked_reason:
            return PipelineStatus(FAILED, f"Bloqueado antes de promover: {promotion_outcome.blocked_reason}")
        return PipelineStatus(APPROVAL_REQUIRED, "Esperando revision humana.")

    if sandbox_loop_result is not None:
        if sandbox_loop_result.ready_for_approval:
            return PipelineStatus(APPROVAL_REQUIRED, "Aplicado y validado -- listo para revision humana.")
        if sandbox_loop_result.apply_result.applied:
            return PipelineStatus(TESTING, "Aplicado sobre el sandbox, sintaxis fallo o no corrio.")
        return PipelineStatus(FAILED, "La propuesta no paso la validacion previa (FASE 29).")

    if generation_result is not None:
        if generation_result.status == "PROPOSED":
            return PipelineStatus(PROPOSED, "El LLM genero una propuesta estructurada valida.")
        if generation_result.status == "REJECTED":
            return PipelineStatus(FAILED, "La respuesta del LLM no paso la validacion de forma (FASE 28).")
        if generation_result.status == "ERROR":
            return PipelineStatus(FAILED, "Fallo la llamada al LLM (red/HTTP).")
        return PipelineStatus(GENERATING, "Generacion en curso.")

    if plan is not None:
        plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan)
        if plan_dict.get("status") == "PLANNED":
            return PipelineStatus(PLANNED, "ChangePlan armado y validado contra el repo real.")
        return PipelineStatus(FAILED, "El ChangePlan quedo BLOCKED.")

    if context is not None:
        context_dict = context.to_dict() if hasattr(context, "to_dict") else dict(context)
        if context_dict.get("status") == "RESOLVED":
            return PipelineStatus(RESOLVED, "El target se resolvio exactamente contra el grafo real.")
        return PipelineStatus(FAILED, "El ChangeContext no se resolvio (UNRESOLVED/PARTIALLY_RESOLVED).")

    if intent is not None:
        return PipelineStatus(RECEIVED, "Solicitud recibida, todavia sin resolver contra el grafo.")

    return PipelineStatus(RECEIVED, "Nada del pipeline se ha ejecutado todavia.")


__all__ = ["classify_pipeline_state", "PipelineStatus", "ALL_STATES"] + list(ALL_STATES)
