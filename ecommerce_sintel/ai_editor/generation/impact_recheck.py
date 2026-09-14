"""
`capture_impact_baseline()` / `recheck_impact()` -- FASE 35 "Impact
Recheck" (plan "AI Change Proposal Engine", 2026-08-11).

Regla del prompt maestro: "Despues del patch, calculate_change_impact()
debe ejecutarse nuevamente. Comparar predicted impact vs actual impact.
Si el impacto real es mayor que el permitido: BLOCK. No promover."

**Bug real encontrado y corregido durante la verificacion de esta
fase**: un primer diseno aproximaba el impacto "predicho" sumando 3
buckets de `ChangeContext.resolution` (`contracts`/`frontend_consumers`/
`backend_dependencies`, mismo truco que usa `approval.gate.
build_change_summary()` para `total_affected`) -- pero esa suma EXCLUYE
tests/documentation/configuration/otros, que si cuentan en el
`total_affected` real de `calculate_change_impact()`. Comparar esa
aproximacion (siempre MENOR) contra un `total_affected` real (siempre
MAYOR) producia `BLOCK` falso en TODOS los casos, incluso sin drift real
del grafo -- verificado con datos reales: predicho=13 (aproximado) vs
actual=42 (real) sobre `EquipmentViewSet.check_availability`, sin que
nada hubiera cambiado en el grafo entre ambas llamadas.

**Corregido con un diseno de 2 pasos, no una aproximacion**:
`capture_impact_baseline(context)` llama `calculate_impact()` UNA VEZ
(mismos numeros reales que usa el resto del sistema, nunca
reconstruidos a mano) y devuelve un `ImpactBaseline` inmutable -- se
llama idealmente apenas se resuelve el `ChangeContext` (POST-GRAPH 3).
`recheck_impact(baseline)` vuelve a llamar `calculate_impact()` sobre el
MISMO target, mas tarde (justo antes de promover), y compara
manzanas-con-manzanas contra el `ImpactBaseline` guardado.

**Honestidad sobre que "actual impact" significa aca**: el grafo
(`project_knowledge_graph`) es una foto ESTATICA de la ultima `cli
audit` -- nada en este pipeline lo reconstruye automaticamente despues
de aplicar un patch (mismo motivo estructural documentado en
`generation.reconciliation`: el sandbox es parcial). Esta funcion NO
mide "el impacto real de MI cambio recien aplicado" -- mide **DRIFT DEL
GRAFO** entre el momento en que se capturo el baseline y el momento del
recheck: si alguien mas corrio `cli audit` mientras tanto (el grafo se
reconstruyo por un cambio concurrente de otra persona) y el riesgo/
impacto del target subio, esto lo detecta -- analogo al chequeo de
fingerprint de archivo que ya hace `promote_to_workspace()`, pero para
datos DERIVADOS DEL GRAFO en vez de contenido de archivo.
"""
import datetime
from dataclasses import dataclass

from ai_editor import graph_client

_RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "UNKNOWN": -1}

STATUS_PASS = "PASS"
STATUS_BLOCK = "BLOCK"


@dataclass
class ImpactBaseline:
    target: str
    risk: str
    total_affected: int
    captured_at: str = ""

    def to_dict(self) -> dict:
        return {
            "target": self.target, "risk": self.risk,
            "total_affected": self.total_affected, "captured_at": self.captured_at,
        }


@dataclass
class ImpactRecheckReport:
    target: str
    status: str
    predicted_risk: str
    predicted_total_affected: int
    actual_risk: str
    actual_total_affected: int
    detail: str

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "status": self.status,
            "predicted": {"risk": self.predicted_risk, "total_affected": self.predicted_total_affected},
            "actual": {"risk": self.actual_risk, "total_affected": self.actual_total_affected},
            "detail": self.detail,
        }


def capture_impact_baseline(context) -> ImpactBaseline | None:
    """Llamar apenas se tiene un `ChangeContext` real (POST-GRAPH 3) --
    UNA sola llamada real a `calculate_impact()`, guardada tal cual, sin
    aproximaciones. Devuelve `None` si `context` no tiene un
    `primary_target` con nombre (nada que consultar)."""
    context_dict = context.to_dict() if hasattr(context, "to_dict") else dict(context)
    primary_target = context_dict.get("primary_target") or {}
    target_name = primary_target.get("name")
    if not target_name:
        return None

    impact = graph_client.calculate_impact(target_name)
    if not impact.get("found"):
        return None

    return ImpactBaseline(
        target=target_name, risk=impact.get("risk", "UNKNOWN"),
        total_affected=impact.get("total_affected", 0),
        captured_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )


def recheck_impact(baseline: ImpactBaseline) -> ImpactRecheckReport:
    """Vuelve a consultar `calculate_impact()` sobre `baseline.target`
    AHORA y compara contra lo capturado antes. `BLOCK` solo si el riesgo
    ES ESTRICTAMENTE mayor (`LOW < MEDIUM < HIGH`) o el conteo de nodos
    afectados aumento -- un impacto IGUAL o MENOR nunca bloquea."""
    if baseline is None:
        return ImpactRecheckReport(
            target="(desconocido)", status=STATUS_BLOCK,
            predicted_risk="UNKNOWN", predicted_total_affected=0,
            actual_risk="UNKNOWN", actual_total_affected=0,
            detail="No hay ImpactBaseline -- capture_impact_baseline() no encontro un target "
                    "real al planear, no hay contra que comparar.",
        )

    actual = graph_client.calculate_impact(baseline.target)
    if not actual.get("found"):
        return ImpactRecheckReport(
            target=baseline.target, status=STATUS_BLOCK,
            predicted_risk=baseline.risk, predicted_total_affected=baseline.total_affected,
            actual_risk="UNKNOWN", actual_total_affected=0,
            detail=f"'{baseline.target}' ya no se encuentra en el grafo actual -- el grafo "
                    "cambio desde que se capturo el baseline, no se puede confirmar el impacto.",
        )

    actual_risk = actual.get("risk", "UNKNOWN")
    actual_total = actual.get("total_affected", 0)

    risk_increased = _RISK_ORDER.get(actual_risk, -1) > _RISK_ORDER.get(baseline.risk, -1)
    total_increased = actual_total > baseline.total_affected

    if risk_increased or total_increased:
        return ImpactRecheckReport(
            target=baseline.target, status=STATUS_BLOCK,
            predicted_risk=baseline.risk, predicted_total_affected=baseline.total_affected,
            actual_risk=actual_risk, actual_total_affected=actual_total,
            detail=f"El grafo cambio desde que se capturo el baseline -- riesgo/impacto de "
                    f"'{baseline.target}' subio de {baseline.risk}/{baseline.total_affected} a "
                    f"{actual_risk}/{actual_total}. No promover sin re-planificar contra el "
                    "estado actual.",
        )

    return ImpactRecheckReport(
        target=baseline.target, status=STATUS_PASS,
        predicted_risk=baseline.risk, predicted_total_affected=baseline.total_affected,
        actual_risk=actual_risk, actual_total_affected=actual_total,
        detail="El riesgo/impacto actual no supera el baseline capturado al planear.",
    )


__all__ = [
    "capture_impact_baseline", "recheck_impact",
    "ImpactBaseline", "ImpactRecheckReport",
    "STATUS_PASS", "STATUS_BLOCK",
]
