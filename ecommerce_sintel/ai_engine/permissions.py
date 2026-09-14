"""
Chequeo `IsAdminUser` de la Policy Layer -- extraido de `action_graph.py`
(mision "ADK-SINTEL", ADK-13, 2026-09-14) por el mismo motivo real que
`routing.py`/`model_chain.py`/`rate_limit.py`: la logica en si es pura
(ningun import de LangChain/LangGraph/red), pero vivia duplicada en DOS
sitios de `action_graph.py` (`node_select_and_execute_tools` para lecturas,
`node_evaluate_policy` para escrituras) y, igual que el rate limiter
(ver `rate_limit.py`), nunca se porto a `ai_engine_adk`.

Hallazgo de la auditoria ADK-12/13 (ver AUDITORIA/ADK_CUTOVER_PLAN.md
seccion 6.3): las Tools con `ToolMetadata.permissions = ["IsAdminUser"]`
(`core_tools.py`, `marketing_tools.py`, una de `renting_tools.py`) no
tenian este gate en `ai_engine_adk` -- severidad estimada baja porque las
Tools que proxean a Django (`tools/http_bridge.py`) vuelven a validar del
lado de Django, que es la autoridad final; pero una Tool sin ese segundo
gate (ninguna hoy, cualquiera futura) dependeria solo de este chequeo.

Extraccion mecanica -- CERO cambio de comportamiento: mismo criterio,
mismo mensaje de error donde aplica.
"""


def user_lacks_admin_permission(permissions: list[str], user: dict) -> bool:
    """True si la Tool exige `IsAdminUser` (`ToolMetadata.permissions`) y el
    usuario real (`ToolContext.user`/`user_context`, resuelto por Django) no
    es staff. `permissions`/`user` vacios nunca bloquean (mismo criterio que
    antes: solo bloquea si el requisito EXISTE y el usuario NO lo cumple)."""
    return "IsAdminUser" in permissions and not user.get("is_staff")
