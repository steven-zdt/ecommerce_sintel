"""
ADK-07 -- Knowledge Graph adapter de SINTEL.

Regla dura del plan (seccion 7): reusar `graph_sdk` via `ai_editor.
graph_client` -- UNICA frontera oficial permitida hacia
`project_knowledge_graph` (regla ya existente, verificada por AST en los
tests reales de `ai_editor`: ningun otro submodulo puede importar
`project_knowledge_graph.knowledge_graph.*`/`.internal.*` directo). Este
adapter reutiliza `graph_client` tal cual -- no agrega logica de grafo
nueva, ni serializa jamas el grafo completo al LLM: cada una de las 16
operaciones reales ya devuelve un dict/list ACOTADO (un nodo, un vecindario,
un resumen de app), nunca el grafo entero -- la funcion `get_app_summary`,
la mas "amplia" de las 16, resume una sola app (modelos/viewsets/endpoints/
tests), no las 23 apps ni los 9575 nodos reales del grafo (confirmado con
`get_graph_status()` real, ver mas abajo).

## Hallazgo real importante (cambia el alcance de ADK-09/10/11, no solo ADK-07)

`ai_editor.agent.run_autonomous_change_loop(request, policy=None, intent=None)`
YA EXISTE como orquestador real, completo, end-to-end (FASE 51-53, "AI
Change Proposal Engine") -- compone intent -> resolver -> planner ->
generation -> sandbox validation -> ... -> `APPROVAL_REQUIRED`, con la regla
de seguridad garantizada ESTRUCTURALMENTE (por ausencia de import, no solo
por un flag): `ai_editor.agent` NUNCA importa `generation.promotion` ni
`repository.promote` -- promover requiere una llamada humana SEPARADA,
fuera de este paquete. Esto contradice la lectura inicial de ADK-00 (que
`intent/`/`resolver/`/`planner/` seguian siendo "stubs documentales", segun
el propio docstring de `graph_client/__init__.py`, escrito en una fase
anterior a FASE 51). **Implicacion real para ADK-09/10/11: el rol de ADK
para `ai_editor` no deberia ser reimplementar el pipeline como Tools ADK
sueltas -- deberia ser un wrapper delgado alrededor de
`run_autonomous_change_loop()` ya existente (sesion/eventos/streaming hacia
un chat, HITL sobre `APPROVAL_REQUIRED`), para no duplicar orquestacion ya
construida y certificada.** Documentado tambien en
`AUDITORIA/ADK_MIGRATION_AUDIT.md`.

## Alcance real de ESTE adapter (ADK-07)

Expone un subconjunto de LECTURA de las 16 operaciones de `graph_client`
como `FunctionTool`s de ADK -- utiles para preguntas de ingenieria ad-hoc
("quien llama a X", "que impacto tiene cambiar Y", "que hay en la app Z"),
un caso de uso MAS LIGERO y distinto de la propuesta de cambio de codigo
completa que ya cubre `run_autonomous_change_loop`. Pensado como tools de
un futuro `EngineeringAgent` (mencionado en la arquitectura propuesta por
el usuario, seccion 3 del plan) -- que hoy NO existe como perfil real (a
diferencia de los 9 Support Agent profiles de ADK-04/05).

Todas las funciones reales de `graph_client` son sincronas, sin `ctx`/
identidad (son de solo lectura sobre datos ya construidos del repo, no
sobre datos de un usuario) -- adapter mas simple que `sintel_adapter.py`
(no hay `ToolContext` que reconstruir).
"""
import inspect
from typing import Callable

from google.adk.tools import FunctionTool

# Subconjunto deliberado, de solo lectura, de las 16 operaciones reales de
# graph_client -- las mas utiles para preguntas de ingenieria ad-hoc. NO
# se incluye `resolve_change`/`build_change_plan` (esas son para el
# pipeline de PROPUESTA de cambio, ya cubierto por
# ai_editor.agent.run_autonomous_change_loop, ver docstring del modulo) ni
# operaciones redundantes entre si para este caso de uso.
_ENGINEERING_QA_OPERATIONS = (
    "find_symbol",
    "find_file",
    "find_endpoint",
    "find_consumers",
    "trace_data_flow",
    "find_tests",
    "calculate_impact",
    "get_app_summary",
    "get_graph_status",
)


def adapt_graph_operation(op_name: str) -> FunctionTool:
    """Envuelve UNA operacion real de `ai_editor.graph_client` (por nombre,
    ej. "calculate_impact") como `FunctionTool` de ADK. Import diferido
    (mismo criterio que `sintel_adapter.py`): `ai_editor`/
    `project_knowledge_graph` solo deben existir en sys.path cuando se usa
    este adapter."""
    from ai_editor import graph_client

    if op_name not in _ENGINEERING_QA_OPERATIONS:
        raise ValueError(
            f"'{op_name}' no esta en el subconjunto de lectura permitido para "
            f"preguntas de ingenieria -- ver _ENGINEERING_QA_OPERATIONS."
        )
    real_func: Callable = getattr(graph_client, op_name)

    # Hallazgo real: el `__name__` propio de la funcion real NO siempre
    # coincide con el alias que graph_client/graph_sdk exportan (ej.
    # calculate_impact.__name__ == "calculate_change_impact",
    # get_graph_status.__name__ == "latest_snapshot") -- import/alias no
    # renombra `__name__`. FunctionTool usa `__name__` para el nombre de
    # la tool que ve el LLM, asi que sin este wrapper el LLM veria un
    # nombre distinto al documentado en AUDITORIA/ADK_MIGRATION_AUDIT.md.
    # Se envuelve (no se muta `real_func.__name__` in-place -- eso seria
    # parchear el modulo real de ai_editor desde el POC) solo para fijar
    # el nombre/doc expuestos; la firma y el comportamiento son 100% los
    # reales (mismos args, mismo cuerpo -- delega sin logica nueva).
    def _wrapper(*args, **kwargs):
        return real_func(*args, **kwargs)

    _wrapper.__name__ = op_name
    _wrapper.__doc__ = real_func.__doc__
    _wrapper.__signature__ = inspect.signature(real_func)

    # graph_client expone funciones SINCRONAS reales -- ADK soporta tools
    # sync directo (confirmado en ADK-01: FunctionTool introspecciona la
    # firma real, no exige async). Ningun wrapper de identidad/contexto
    # hace falta aqui (a diferencia de sintel_adapter.py): son consultas de
    # solo lectura sobre el grafo del repo, no datos de un usuario.
    return FunctionTool(_wrapper)


def build_engineering_qa_tools() -> list[FunctionTool]:
    """Todas las tools del subconjunto de ingenieria, listas para un
    LlmAgent (ej. un futuro EngineeringAgent)."""
    return [adapt_graph_operation(name) for name in _ENGINEERING_QA_OPERATIONS]
