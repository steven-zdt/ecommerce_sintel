"""
`resolve_change_context()` -- POST-GRAPH 3 "Change Resolver" (rediseno
"AI Editor Runtime", 2026-08-11).

Convierte un `ChangeIntent` (POST-GRAPH 2, ya interpretado y con `domain`
confirmado contra el grafo) en un `ChangeContext` completo, componiendo
UNICAMENTE funciones ya construidas y verificadas de `graph_client`
(POST-GRAPH 1): `find_node()` para confirmar cada entidad mencionada,
`resolve_change()` (Fase 11) para el envelope completo (files/symbols/
contracts/frontend_consumers/backend_dependencies/data_flows/
execution_paths/tests/documentation/configuration/risk/change_order/
validation_plan), `build_context_packet()` (Fase 12) para la version
COMPRIMIDA que de hecho se le pasaria a un LLM (nunca el grafo completo,
regla explicita de POST-GRAPH 3 del prompt maestro).

Regla fundamental del planner (seccion final del prompt maestro), aplicada
aca: "El AI Editor NO puede inventar archivo/simbolo/endpoint/dependencia/
test si el Knowledge Graph no lo confirma." -- cada entidad de
`intent.entities` se resuelve INDIVIDUALMENTE contra el grafo real; la que
no resuelve queda en `unresolved_entities`, nunca se fabrica.

**Defecto real encontrado durante la verificacion de esta misma fase (no
hipotetico)**: `find_node()` (POST-GRAPH 1) usa `resolve_change_target()`,
que hace "exacto-antes-que-fuzzy" pero NO distingue en su resultado cual
de los dos caso fue -- probado con la entidad real `"Equipment"` (mencion
de negocio plausible del dominio Renting, pero NO existe como Model real:
`renting` tiene 0 Models): `find_node("Equipment")` devuelve
`FeaturedEquipmentCardSerializer` (Serializer real, matchea solo porque
"Equipment" es substring de su nombre) -- una respuesta FUZZY, no un
"Equipment" real. Aceptar esto como "confirmado" violaria la regla de
arriba (convertiria un match aproximado en un hecho). Corregido SIN TOCAR
`project_knowledge_graph` (Regla de no reabrir fases cerradas): esta
funcion compara `node["name"]` contra el nombre pedido -- si no coinciden
EXACTO, el match se trata como NO confirmado (va a
`unresolved_entities` con una nota explicita, no a `resolved_entities`/
`primary_target`).

"Segments" que menciona el prompt maestro (TARGET/Files/Symbols/Segments/
Endpoints/...) no es un tipo de nodo nuevo -- ya esta cubierto por
`Symbol.meta.start_line`/`end_line` (mismo criterio documentado en Fase 1
del Site Knowledge Graph: un `CodeSegment` separado seria casi 1:1 con
`Symbol` sin fingerprint semantico real, se dejo fuera a proposito).
"Endpoints" esta cubierto por el campo `contracts` de `resolve_change()`
(incluye nodos `Endpoint`/`Serializer`).
"""
from ai_editor import graph_client
from ai_editor.resolver.schema import (
    STATUS_PARTIALLY_RESOLVED,
    STATUS_RESOLVED,
    STATUS_UNRESOLVED,
    ChangeContext,
)

# Prioridad para elegir el TARGET principal entre varias entidades
# confirmadas -- Symbol es lo mas "accionable" (archivo + rango de lineas
# exacto, lo que necesitara el futuro Patch Engine), App es lo menos
# especifico (util solo como ultimo recurso).
_TYPE_PRIORITY = {
    "Symbol": 0, "Model": 1, "Serializer": 2, "ViewSet": 3, "Endpoint": 4,
    "PiniaStore": 5, "Composable": 6, "FrontendComponent": 7, "App": 99,
}


def _priority(node: dict) -> int:
    return _TYPE_PRIORITY.get(node.get("type"), 50)


def resolve_change_context(intent) -> ChangeContext:
    """`intent` es un `ai_editor.intent.ChangeIntent`. Si `intent.status`
    ya es `NEEDS_CLARIFICATION` (POST-GRAPH 2), no tiene sentido intentar
    resolverlo mas -- se devuelve `UNRESOLVED` de inmediato, sin gastar
    consultas al grafo sobre una intencion que la fase anterior ya marco
    como no confiable."""
    intent_dict = intent.to_dict() if hasattr(intent, "to_dict") else dict(intent)

    if intent_dict.get("status") == "NEEDS_CLARIFICATION":
        return ChangeContext(
            intent=intent_dict, status=STATUS_UNRESOLVED,
            unresolved_entities=list(intent_dict.get("entities") or []),
        )

    candidates = list(intent_dict.get("entities") or [])
    if not candidates and intent_dict.get("domain"):
        candidates = [intent_dict["domain"]]

    resolved_nodes: list[dict] = []
    unresolved: list[str] = []
    for name in candidates:
        node = graph_client.find_node(name)
        if node is None:
            unresolved.append(f"'{name}': no se encontro ningun nodo en el grafo")
        elif node["name"] != name:
            # Match FUZZY (substring), no EXACTO -- no se acepta como
            # confirmado, ver nota de "Defecto real" arriba.
            unresolved.append(
                f"'{name}': solo hay un match aproximado ('{node['name']}', "
                f"tipo {node['type']}), no una coincidencia exacta -- no se confirma"
            )
        else:
            resolved_nodes.append(node)

    if not resolved_nodes:
        return ChangeContext(intent=intent_dict, status=STATUS_UNRESOLVED, unresolved_entities=unresolved)

    resolved_nodes.sort(key=_priority)
    primary = resolved_nodes[0]
    other_resolved = resolved_nodes[1:]

    resolution = graph_client.resolve_change(primary["name"])
    context_packet = graph_client.build_context_packet(primary["name"])

    status = STATUS_RESOLVED if not unresolved else STATUS_PARTIALLY_RESOLVED

    return ChangeContext(
        intent=intent_dict,
        status=status,
        primary_target=primary,
        resolved_entities=other_resolved,
        unresolved_entities=unresolved,
        resolution=resolution if resolution.get("found") else None,
        context_packet=context_packet if context_packet.get("found") else None,
    )
