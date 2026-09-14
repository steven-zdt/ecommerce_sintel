"""
`reconcile_graph()` -- POST-GRAPH 9 "Graph Reconciliation" (rediseno "AI
Editor Runtime", 2026-08-11). **NOT_IMPLEMENTED explicito, no fabricado.**

Dos motivos reales, no uno solo:
1. El mismo limite estructural que Niveles 2/4 de POST-GRAPH 8: el
   sandbox (POST-GRAPH 7) es una copia PARCIAL de archivos, no el proyecto
   completo -- reconstruir `project_knowledge_graph` ahi (para comparar
   "grafo antes" vs "grafo despues") no es posible con el diseno actual.
2. Razon ADICIONAL especifica de esta fase: "Graph Reconciliation" existe
   para detectar que un PATCH introdujo dependencias/archivos/simbolos
   NO previstos por el plan original -- un riesgo real cuando el
   contenido del patch lo escribio un LLM de forma autonoma. Hoy
   `ai_editor.patch` NO genera contenido real (POST-GRAPH 6, alcance
   deliberado) -- cada `PatchOperation` que existe hoy la construyo
   explicitamente un humano o un test, nunca un LLM. No hay todavia un
   escenario real donde pueda aparecer impacto "inesperado" que
   reconciliar contra el grafo. Construir esto ahora seria simular una
   capacidad sin nada real que valide su comportamiento.

Se deja la funcion con la MISMA forma de resultado que
`ai_editor.validation.engine.ValidationReport` (status +
razon explicita) para que el llamador pueda tratarla de forma consistente
sin necesitar saber si una fase esta implementada o no.
"""
from dataclasses import dataclass

STATUS_NOT_IMPLEMENTED = "NOT_IMPLEMENTED"

RECONCILIATION_NOT_IMPLEMENTED_REASON = (
    "Requiere (1) un sandbox completo capaz de reconstruir el grafo (el sandbox parcial actual "
    "no alcanza, mismo motivo que Niveles 2/4 de Validation Engine) y (2) una capacidad real de "
    "generacion de codigo cuyo output pueda divergir de lo planeado (ai_editor.patch no genera "
    "contenido real todavia, POST-GRAPH 6) -- sin ambas, no existe un escenario real de 'impacto "
    "inesperado' que reconciliar. No se fabrica un resultado."
)


@dataclass
class ReconciliationResult:
    status: str = STATUS_NOT_IMPLEMENTED
    reason: str = RECONCILIATION_NOT_IMPLEMENTED_REASON

    def to_dict(self) -> dict:
        return {"status": self.status, "reason": self.reason}


def reconcile_graph(plan) -> ReconciliationResult:
    """Firma estable para cuando esto se implemente de verdad -- hoy
    siempre devuelve `NOT_IMPLEMENTED`, sin importar `plan`."""
    return ReconciliationResult()
