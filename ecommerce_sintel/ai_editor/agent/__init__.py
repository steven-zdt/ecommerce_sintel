"""
`ai_editor.agent` -- FASE 51 "AI Editor Agent" + FASE 52 "Agent Policy" +
FASE 53 "Autonomous Controlled Loop" (plan "AI Change Proposal Engine",
2026-08-11).

Ultimo paso ANTES de la revision humana: recibe una solicitud en texto
libre y corre, en una sola llamada, TODO el pipeline ya construido en
`generation/` (FASE 24-50) mas los modulos previos (`intent/`,
`resolver/`, `planner/`) -- sin agregar logica de decision nueva, solo
composicion (`loop.py`). El resultado mas avanzado que este paquete puede
producir es `APPROVAL_REQUIRED` -- nunca promueve, nunca escribe sobre
`WORKSPACE_ROOT` real (ver docstring de `loop.py`, seccion "REGLA FINAL
DE SEGURIDAD").

    policy.py -- `AgentPolicy`: limites (max_retries, provider). Sin
                 flag de "auto-promover" -- esa capacidad no existe en
                 este paquete, no hace falta apagarla.
    schema.py -- `AgentRunResult`: consolida TODOS los reportes reales
                 que produjo una corrida (cada uno el objeto REAL de su
                 fase, `None` si el loop se detuvo antes).
    loop.py   -- `run_autonomous_change_loop(request, policy=None,
                 intent=None)`: el orquestador end-to-end.

Uso:
    from ai_editor.agent import run_autonomous_change_loop, AgentPolicy
    result = run_autonomous_change_loop("agregar validacion X a Y")
    if result.status == "APPROVAL_REQUIRED":
        print(result.human_review_text)
        # promover requiere una llamada APARTE, humana:
        # from ai_editor.generation import review_and_promote
        # review_and_promote(result.sandbox_loop_result, result.context,
        #                     result.plan, workspace_root, decision="APPROVE", confirm=True)
        # ... y despues limpiar: result.sandbox_loop_result.sandbox.cleanup()
"""
from ai_editor.agent.loop import run_autonomous_change_loop
from ai_editor.agent.policy import AgentPolicy
from ai_editor.agent.schema import AgentRunResult

__all__ = ["run_autonomous_change_loop", "AgentPolicy", "AgentRunResult"]
