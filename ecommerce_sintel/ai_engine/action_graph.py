"""
Action Graph del AI Core (Fase 3) — orquestacion de Tools de negocio.

Grafo PARALELO al de generacion de codigo: no importa nada de graph.py ni
comparte su estado (SintelCodeState); solo reusa la infraestructura ya
existente (llm_factory via _STATE, retrievers.retrieve_context_for_task
para conocimiento/FAQ, planner-style regex para intencion).

Flujo:
    resolve_customer_context -> detect_intent -> optimize_context
        -> (intent de conocimiento) retrieve_knowledge -> generate_response
        -> (intent de datos)  select_and_execute_tools -> validate_tool_result -> generate_response

Reglas duras respetadas aqui:
- El LLM SOLO ve Capabilities (capabilities/registry.py), nunca una Tool.
- Ninguna regla de negocio vive en el prompt: las Tools/Selectors deciden.
- El JWT del usuario viaja por config["configurable"], NUNCA dentro del
  estado (el checkpointer persiste el estado; un token no se persiste).
- Solo Tools de lectura en esta fase; needs_confirmation queda declarado
  para la Fase 4 (interrupt antes de cualquier escritura).
"""
import json
import logging
import operator
import re
import time
import uuid as uuid_lib
from collections import defaultdict, deque
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from config import CHECKPOINTER_REDIS_URL
from redis_checkpointer import RedisCheckpointSaver

import tools as tool_registry
from agents import AgentRegistry
from auth import fetch_user_context
from capabilities import CapabilityRegistry
from observability import TurnMetrics, metrics_from_config
from retrievers import retrieve_context_for_task
from tools import ToolContext

logger = logging.getLogger("action_graph")

MAX_CONTEXT_CHARS = 6000      # presupuesto explicito del Context Optimizer
MAX_HISTORY_TURNS = 3
MAX_KNOWLEDGE_CHUNKS = 6


class SintelActionState(TypedDict, total=False):
    user_context: dict
    message: str
    conversation_id: str
    intent: str
    optimized_context: str
    tool_calls: list
    tool_results: list
    needs_confirmation: bool
    final_response: str
    history: Annotated[list, operator.add]
    # Fase 4 — Policy Layer / confirmacion
    pending_write: dict | None      # {"name": capability_id, "args": {...}} en espera
    policy_decision: str            # allow | deny | confirm
    # Fase 6 — multiagente
    agent: str                      # Agent Profile activo del turno
    handoff: str | None             # "AgenteA->AgenteB" si hubo derivacion en el turno


# ---------------------------------------------------------------------------
# Intencion de negocio (mismo patron regex que planner.py::detect_intent,
# pero con intents de negocio, no de codigo)
# ---------------------------------------------------------------------------

BUSINESS_INTENT_PATTERNS = {
    # Orden importa: los intents mas especificos van primero (el nodo toma el
    # primer intent de datos que matchee).
    "rental_change":          re.compile(r"\b(cambiar|mover|reprogramar|correr|modificar)\b.{0,40}\b(fecha|fechas)\b|\b(fecha|fechas)\b.{0,40}\b(alquiler|renta)\w*", re.I),
    "rental_cancel":          re.compile(r"\b(cancelar?|anular?)\b.{0,40}\b(alquiler|renta|solicitud)\w*", re.I),
    "support":                re.compile(r"\b(soporte|reclamo|queja|hablar con (una persona|alguien|un humano|un agente)|ticket|pqr)\b", re.I),
    "quote":                  re.compile(r"\b(cotiza|cotizacion|cotización|presupuesto)\w*", re.I),
    "kyc_upgrade":            re.compile(r"\b(convertirme|volverme|ser) (en )?(profesional|tecnico|técnico|contratista|especialista)\b|\bupgrade\b|\bperfil profesional\b", re.I),
    "order_status":           re.compile(r"\b(pedido|orden|compra|envio|envío|entrega|paquete|tracking|rastre)\w*", re.I),
    "rental_status":          re.compile(r"\b(mi alquiler|mis alquileres|mi renta|mis rentas|solicitud de alquiler)\b", re.I),
    "renting_search":         re.compile(r"\b(alquilar|rentar|reservar|equipo|camara|cámara|disponib)\w*", re.I),
    "payment":                re.compile(r"\b(pago|pague|pagué|transaccion|transacción|tarjeta|rechaz|declin)\w*", re.I),
    "service_status":         re.compile(r"\b(servicio|tecnico|técnico|instalacion|instalación|reparacion|reparación|asignad|asignaron|visita)\w*", re.I),
    "kyc":                    re.compile(r"\b(verificacion|verificación|identidad|kyc|mis documentos)\b", re.I),
    "stock":                  re.compile(r"\b(stock|inventario|unidades)\b", re.I),
    "promos":                 re.compile(r"\b(promocion|promoción|oferta|descuento|rebaja)\w*", re.I),
    "knowledge":              re.compile(r"\b(como funciona|cómo funciona|politica|política|garantia|garantía|que es|qué es|horario|terminos|términos|compatible)\w*", re.I),
    # Fase 8: intents de automatizacion de negocio
    "marketing_admin":        re.compile(r"\b(dashboard|revenue|ingresos|ventas totales|campan|campaña|reactivar|stock inactivo|clientes objetivo|targets|metricas|conversion)\w*", re.I),
    "personal_recommendation":re.compile(r"\b(que me recomiendas|que recomiendan|recomendacion|recomendación|suger|productos para mi|servicios para mi|para mi perfil|cross.?sell|up.?sell)\w*", re.I),
    "maintenance_check":      re.compile(r"\b(mantenimiento|bloqueo|bloqueado|fuera de servicio|equipo dani|equipo bloqueado|preventivo|correctivo)\b.{0,40}\b(equipo|camara|cámara|variante)\w*|\b(equipo|camara|cámara)\b.{0,40}\b(mantenimiento|bloqueo|bloqueado)\b", re.I),
    "core_content":           re.compile(r"\b(home|inicio|banner|navbar|menu de navegacion|footer|pie de pagina|marca|slider|slogan|boton del home|enlace del menu|configurar el sitio|editar el sitio)\w*", re.I),
    # [AGREGADO 2026-08-04, Etapa 2 de AUDITORIA_KNOWLEDGE_GRAPH_SSOT_2026-08-04.md]
    # Conecta GraphImpactAnalysisTool (tools/graph_tools.py, ya registrada desde
    # AUDITORIA/14 Fase 9 pero deliberadamente sin intent -- ver comentario historico
    # en agents/profiles/admin_agent.yaml) al router regex en vivo. Patron deliberadamente
    # especifico (lenguaje de "impacto"/"que se rompe"/"que depende de" sobre una entidad
    # de codigo) para minimizar falsos positivos contra trafico real de clientes -- no se
    # puede probar contra trafico real antes de desplegar, asi que se prefirio angosto y
    # ampliarlo despues con evidencia, no al reves. Requiere IsAdminUser (verificado ahora
    # tambien para lecturas en node_select_and_execute_tools, no solo para escrituras --
    # ver el fix de permisos aplicado junto con este intent).
    "architecture_impact":   re.compile(r"\b(que se rompe|que rompe|que afecta|impacto)\b.{0,40}\b(cambio|cambia|cambiar|modifico|modifica|modificar)\b|\b(radio de impacto|analizar impacto|impacto arquitect)\w*|\b(que depende de|quien usa|quien consume)\b.{0,40}\b(modelo|endpoint|viewset|serializer|componente)\w*", re.I),
}

# Capabilities que el Context Optimizer ofrece al LLM segun la intencion --
# recortar las opciones del turno ES optimizar el contexto (Componente 4).
# "rental_change" implementa la decision del usuario sobre el gap #1
# (2026-07-16): cambiar fechas NUNCA es self-service -> escalar a soporte.
INTENT_CAPABILITIES = {
    "rental_change":           ["abrir_ticket_soporte", "buscar_alquiler"],
    "rental_cancel":           ["cancelar_alquiler", "buscar_alquiler"],
    "support":                 ["abrir_ticket_soporte"],
    "quote":                   ["consultar_plantillas_cotizacion", "iniciar_cotizacion"],
    "kyc_upgrade":             ["solicitar_upgrade_profesional", "consultar_kyc"],
    "order_status":            ["buscar_pedido"],
    "rental_status":           ["buscar_alquiler"],
    "renting_search":          ["buscar_equipos", "verificar_disponibilidad", "crear_alquiler"],
    "payment":                 ["consultar_pago"],
    "service_status":          ["consultar_servicio", "buscar_pedido"],
    "kyc":                     ["consultar_kyc"],
    "stock":                   ["consultar_stock", "buscar_equipos"],
    "promos":                  ["consultar_promociones"],
    # Fase 8
    "marketing_admin":         ["ver_dashboard_marketing", "alertas_stock_inactivo", "targets_campana"],
    "personal_recommendation": ["recomendar_al_cliente", "consultar_promociones"],
    "maintenance_check":       ["verificar_mantenimiento"],
    "core_content":            ["ver_config_home", "ver_navbar", "ver_footer", "ver_brand_slider",
                                "editar_banner", "crear_banner", "editar_navbar", "crear_navbar_link",
                                "editar_brand_slider"],
    "architecture_impact":     ["analizar_impacto_arquitectura"],
}

# Capability de fallback deterministico si el LLM no emite tool_calls para
# una intencion de datos (solo capabilities de LECTURA sin argumentos --
# una escritura JAMAS se dispara por fallback).
INTENT_FALLBACK_CAPABILITY = {
    "rental_change":           "buscar_alquiler",
    "rental_cancel":           "buscar_alquiler",
    "quote":                   "consultar_plantillas_cotizacion",
    "kyc_upgrade":             "consultar_kyc",
    "order_status":            "buscar_pedido",
    "rental_status":           "buscar_alquiler",
    "renting_search":          "buscar_equipos",
    "payment":                 "consultar_pago",
    "service_status":          "consultar_servicio",
    "kyc":                     "consultar_kyc",
    "promos":                  "consultar_promociones",
    # Fase 8 (solo lectura como fallback — escrituras nunca por fallback)
    "marketing_admin":         "ver_dashboard_marketing",
    "personal_recommendation": "recomendar_al_cliente",
    "maintenance_check":       "verificar_mantenimiento",
    "core_content":            "ver_config_home",
}


def detect_business_intents(message: str) -> list[str]:
    intents = [name for name, pat in BUSINESS_INTENT_PATTERNS.items() if pat.search(message)]
    return intents or ["unknown"]


# ---------------------------------------------------------------------------
# Nodos
# ---------------------------------------------------------------------------

def _token_from_config(config: dict) -> str:
    return (config.get("configurable") or {}).get("token", "")


async def node_resolve_customer_context(state: SintelActionState, config: dict) -> dict:
    """Fase 1: resuelve el JWT a usuario/perfil real via Django. Nunca local."""
    user_context = await fetch_user_context(_token_from_config(config))
    return {"user_context": user_context, "needs_confirmation": False}


async def node_detect_intent(state: SintelActionState, config: dict) -> dict:
    intents = detect_business_intents(state["message"])
    data_intents = [i for i in intents if i in INTENT_CAPABILITIES]
    # Si hay intencion de datos, gana sobre conocimiento (Componente 10:
    # datos vivos via Selectors, el RAG solo para politica/FAQ).
    intent = data_intents[0] if data_intents else ("knowledge" if "knowledge" in intents else "unknown")

    # Fase 6: router intencion -> agente + handoff por reglas de escalamiento
    # del propio profile (ej. queja detectada -> SupportAgent).
    agent = AgentRegistry.route(intent)
    escalated = AgentRegistry.apply_escalation(agent, state.get("message", ""))
    handoff = None
    if escalated.name != agent.name:
        handoff = f"{agent.name}->{escalated.name}"
        agent = escalated

    metrics = metrics_from_config(config)
    if metrics:
        metrics.data["intent"] = intent
        metrics.data["agent"] = agent.name
        metrics.data["handoff"] = handoff

    logger.info("[action] intents=%s -> intent=%s agent=%s handoff=%s",
                intents, intent, agent.name, handoff)
    return {"intent": intent, "agent": agent.name, "handoff": handoff}


# Intents que se benefician del CRM Context (Componente 9, Fase 5):
# personalizacion (promos/busqueda) y creacion de solicitudes (el LLM puede
# proponer direccion/contacto reales del cliente en vez de preguntarlo todo).
# NUNCA se trae todo en cada turno -- regla dura del Customer Context Builder.
_CRM_CONTEXT_INTENTS = {"renting_search", "promos", "quote", "personal_recommendation"}


def _crm_summary(crm: dict) -> str:
    marketing = crm.get("marketing") or {}
    lines = [
        "Perfil de compra: total gastado {t}, {n} pedidos pagados, preferencia '{p}'.".format(
            t=marketing.get("total_spent", "0"), n=marketing.get("orders_count", 0),
            p=marketing.get("preference", "-"),
        )
    ]
    addresses = crm.get("addresses") or []
    if addresses:
        default = next((a for a in addresses if a.get("is_default")), addresses[0])
        lines.append(
            f"Direccion habitual: {default.get('full_name')} -- {default.get('city')}, "
            f"{default.get('state')} (tel {default.get('phone_number')})."
        )
    cards = crm.get("payment_methods") or []
    if cards:
        lines.append("Tarjetas guardadas: " + ", ".join(
            f"{c.get('brand')} *{c.get('last4')}" + (" (predeterminada)" if c.get("is_default") else "")
            for c in cards
        ) + ".")
    return "\n".join(lines)


async def node_optimize_context(state: SintelActionState, config: dict) -> dict:
    """Componente 4: solo lo relevante del turno, con presupuesto explicito."""
    user = state.get("user_context", {})
    parts = [
        f"Cliente: {user.get('full_name') or user.get('email')} (tipo {user.get('user_type')}).",
    ]

    # CRM Context (Fase 5): solo para intents que lo aprovechan. El endpoint
    # de Django ya cachea en Redis (TTL 5 min) -- Cache Inteligente.
    if state.get("intent") in _CRM_CONTEXT_INTENTS:
        from tools.http_bridge import django_internal_get
        crm = await django_internal_get(_token_from_config(config), "/customer-context/")
        if not crm.get("error"):
            parts.append(_crm_summary(crm))

    history = state.get("history") or []
    for turn in history[-MAX_HISTORY_TURNS:]:
        parts.append(f"Turno previo -- Usuario: {turn.get('user', '')[:200]} | Asistente: {turn.get('assistant', '')[:200]}")
    optimized = "\n".join(parts)[:MAX_CONTEXT_CHARS]
    return {"optimized_context": optimized}


async def node_retrieve_knowledge(state: SintelActionState, config: dict) -> dict:
    """Reusa retrievers.py tal cual para preguntas de politica/FAQ/documentacion."""
    resources = (config.get("configurable") or {}).get("resources", {})
    vectorstore, all_docs = resources.get("vectorstore"), resources.get("all_docs")
    if vectorstore is None or not all_docs:
        return {"tool_results": [{"error": "Base de conocimiento no disponible.", "status_code": 503}]}
    docs = retrieve_context_for_task(state["message"], vectorstore, all_docs)[:MAX_KNOWLEDGE_CHUNKS]
    knowledge = "\n---\n".join(d.page_content[:800] for d in docs)[:MAX_CONTEXT_CHARS]
    return {
        "optimized_context": f"{state.get('optimized_context', '')}\n\nConocimiento relevante:\n{knowledge}"[:MAX_CONTEXT_CHARS * 2],
        "tool_calls": [],
        "tool_results": [],
    }


# Saneo de argumentos generados por el LLM: un modelo pequeno puede emitir
# placeholders ("hoy", "UUID de la variante") -- una llamada con args
# invalidos se descarta y se usa el fallback deterministico, para que la
# respuesta se base en datos reales y no en un error evitable.
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
_MSG_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_UUID_ARG_NAMES = {"variant", "tx", "uuid", "order", "equipment_variant", "template",
                   "order_uuid", "rental_uuid"}
_DATE_ARG_NAMES = {"start", "end", "start_date", "end_date"}


def _sanitize_args(args: dict, schema: dict) -> dict | None:
    """Devuelve args limpios (solo claves del schema, formatos validos) o None si la llamada no es ejecutable.

    FASE 7 (auditoria de Tools, 2026-08-07): el LLM a veces arma su tool_call incluyendo
    explicitamente `{"order_uuid": null}` para un parametro opcional que no aplica, en vez de
    omitir la clave -- ambas formas son equivalentes segun el args_schema (el parametro no
    esta en `required`). Sin este filtro, un valor None caia en el chequeo de formato
    UUID/fecha (`str(None) == "None"`, nunca matchea el regex) y la llamada entera se
    descartaba como "invalida" -- para Tools de lectura, en silencio total (ver el `continue`
    en el loop que llama a esta funcion), enmascarado solo por el fallback deterministico.
    """
    properties = (schema or {}).get("properties", {})
    clean = {k: v for k, v in (args or {}).items() if k in properties and v is not None}
    for key, value in list(clean.items()):
        text = str(value)
        if key in _UUID_ARG_NAMES and not _UUID_RE.match(text):
            return None
        if key in _DATE_ARG_NAMES and not _DATE_RE.match(text):
            return None
    for required in (schema or {}).get("required", []):
        if required not in clean:
            return None
    return clean


def _capability_schema(capability_id: str) -> dict:
    cap = CapabilityRegistry.get(capability_id)
    tool = tool_registry.get_tool(cap.tool_name) if cap else None
    return (tool.metadata.args_schema if tool else None) or {"type": "object", "properties": {}}


def _capability_specs(capability_ids: list[str]) -> list[dict]:
    """El LLM ve capability_id + descripcion de negocio; los args vienen del ToolMetadata."""
    specs = []
    for cap in CapabilityRegistry.list_active():
        if cap.capability_id not in capability_ids:
            continue
        tool = tool_registry.get_tool(cap.tool_name)
        schema = (tool.metadata.args_schema if tool else None) or {"type": "object", "properties": {}}
        specs.append({
            "type": "function",
            "function": {
                "name": cap.capability_id,
                "description": cap.description_for_llm,
                "parameters": schema,
            },
        })
    return specs


async def _execute_capability(capability_id: str, args: dict, ctx: ToolContext,
                              metrics: TurnMetrics | None = None) -> dict:
    tool_name = CapabilityRegistry.resolve_tool_name(capability_id)
    if tool_name is None:
        return {"error": f"Capability desconocida: {capability_id}", "status_code": 404}
    started = time.monotonic()
    result = await tool_registry.invoke(tool_name, ctx, args)
    if metrics:
        ok = not (isinstance(result, dict) and result.get("error"))
        metrics.record_tool(tool_name, int((time.monotonic() - started) * 1000), ok)
    return {"capability": capability_id, "tool": tool_name, "args": args, "result": result}


async def node_select_and_execute_tools(state: SintelActionState, config: dict) -> dict:
    """Primera vez en el proyecto que se usa llm.bind_tools() -- solo lectura."""
    configurable = config.get("configurable") or {}
    llm = configurable.get("resources", {}).get("llm")
    ctx = ToolContext(user=state.get("user_context", {}), token=configurable.get("token", ""))

    metrics = metrics_from_config(config)

    # Fase 6: el scope del Agent Profile es el limite duro de que capabilities
    # ve el LLM este turno; la lista por intent sigue siendo el optimizador.
    capability_ids = INTENT_CAPABILITIES.get(state.get("intent", ""), [])
    agent = AgentRegistry.get(state.get("agent", ""))
    if agent is not None:
        allowed = set(agent.capacidades)
        scoped = [c for c in capability_ids if c in allowed]
        capability_ids = scoped or sorted(allowed)
    elif not capability_ids:
        capability_ids = [c.capability_id for c in CapabilityRegistry.list_active()]
    specs = _capability_specs(capability_ids)

    tool_calls: list[dict] = []
    if llm is not None:
        try:
            bound = llm.bind_tools(specs)
            ai_msg = await bound.ainvoke([
                SystemMessage(content=(
                    "Eres el asistente de Sintel. Decide que capacidad usar para responder "
                    "con datos reales del cliente. Si la pregunta requiere fechas o uuids que "
                    "no tienes, usa primero una capacidad de busqueda. Nunca inventes datos.\n"
                    + state.get("optimized_context", "")
                )),
                HumanMessage(content=state["message"]),
            ])
            if metrics:
                metrics.record_llm(ai_msg)
            tool_calls = [
                {"name": tc["name"], "args": tc.get("args") or {}}
                for tc in (getattr(ai_msg, "tool_calls", None) or [])
            ]
        except Exception as exc:
            logger.warning("[action] bind_tools/ainvoke fallo (%s) -- usando fallback deterministico", exc)

    def _metadata_for(capability_id: str):
        cap = CapabilityRegistry.get(capability_id)
        tool = tool_registry.get_tool(cap.tool_name) if cap else None
        return tool.metadata if tool else None

    executed: list[dict] = []
    results: list[dict] = []
    pending_write: dict | None = None
    for tc in tool_calls[:4]:
        if tc["name"] not in capability_ids:
            continue
        metadata = _metadata_for(tc["name"])
        schema = _capability_schema(tc["name"])

        if metadata is not None and metadata.side_effects:
            # Escritura: NUNCA se ejecuta aqui -- va a la Policy Layer.
            # Formatos invalidos (uuid/fecha placeholder) o requeridos
            # ausentes se reportan como resultado sintetico para que el LLM
            # pida los datos al cliente ANTES de pedir confirmacion.
            # FASE 7 (auditoria de Tools, 2026-08-07): mismo criterio que _sanitize_args()
            # arriba -- un valor None explicito en un parametro opcional (ej. el LLM manda
            # {"order_uuid": null} en vez de omitir la clave) no debe tratarse como "formato
            # invalido". Antes, esto generaba un error de cara al usuario pidiendo un dato que
            # en realidad nunca era requerido (reproducido en vivo: "Necesito ayuda" -> el
            # agente pedia order_uuid/rental_uuid en vez de preguntar el problema).
            properties = set((schema or {}).get("properties", {}))
            partial = {k: v for k, v in (tc["args"] or {}).items() if k in properties and v is not None}
            bad_format = [
                k for k, v in partial.items()
                if (k in _UUID_ARG_NAMES and not _UUID_RE.match(str(v)))
                or (k in _DATE_ARG_NAMES and not _DATE_RE.match(str(v)))
            ]
            missing = [r for r in (schema or {}).get("required", []) if r not in partial]
            if bad_format or missing:
                results.append({
                    "capability": tc["name"], "args": partial,
                    "result": {"error": "Faltan o son invalidos estos datos: "
                                        + ", ".join(sorted(set(missing + bad_format)))
                                        + ". Pedirlos al cliente antes de continuar.",
                               "status_code": 400},
                })
            elif pending_write is None:
                pending_write = {"name": tc["name"], "args": partial}
            continue

        # [CORREGIDO 2026-08-04] Lectura sin permisos.IsAdminUser aplicado -- a
        # diferencia de la escritura (evaluate_policy, arriba) y del endpoint de
        # debug (gateway/router.py, mismo chequeo), esta rama NUNCA validaba
        # metadata.permissions antes de ejecutar. Para Tools que proxean a Django
        # (tools/http_bridge.py) el endpoint interno vuelve a validar y es la
        # autoridad final -- gap solo de defensa en profundidad, ya documentado
        # (F1, AUDITORIA/16). Pero GraphImpactAnalysisTool (tools/graph_tools.py)
        # consulta el Knowledge Graph EN MEMORIA, sin HTTP, sin JWT, sin ningun
        # endpoint de Django detras -- para ese caso especifico este era el UNICO
        # gate posible, y estaba ausente. Se descubrio al conectar el intent de
        # Etapa 2 (ver AUDITORIA_KNOWLEDGE_GRAPH_SSOT_2026-08-04.md, addendum) y
        # se corrigio ANTES de hacer alcanzable la Tool desde `/chat`.
        if metadata is not None and "IsAdminUser" in metadata.permissions and not ctx.user.get("is_staff"):
            results.append({
                "capability": tc["name"], "args": {},
                "result": {"error": "Esta accion es solo para administradores.", "status_code": 403},
            })
            continue

        clean_args = _sanitize_args(tc["args"], schema)
        if clean_args is None:
            logger.info("[action] llamada descartada por args invalidos: %s %s", tc["name"], tc["args"])
            continue
        results.append(await _execute_capability(tc["name"], clean_args, ctx, metrics))
        executed.append({"name": tc["name"], "args": clean_args})

    def _succeeded(item: dict) -> bool:
        result = item.get("result", {})
        return not (isinstance(result, dict) and result.get("error"))

    # Fallback deterministico SOLO de lectura: si no hay escritura pendiente y
    # ninguna llamada ejecutable sobrevivio (o todas fallaron), se consulta la
    # capability base de la intencion sin argumentos.
    if pending_write is None and not any(_succeeded(r) for r in results):
        fallback = INTENT_FALLBACK_CAPABILITY.get(state.get("intent", ""))
        already = any(e["name"] == fallback and not e["args"] for e in executed)
        if fallback and fallback in capability_ids and not already:
            results.append(await _execute_capability(fallback, {}, ctx, metrics))
            executed.append({"name": fallback, "args": {}})
            if metrics:
                metrics.data["fallback_used"] = True

    # Asistencia deterministica para intents de escritura inequivocos, cuando
    # el LLM no armo la llamada: cancelar con uuid explicito en el mensaje, y
    # el escalamiento a soporte del gap #1 (cambiar fechas) / intent soporte /
    # handoff por queja (Fase 6). La Policy Layer sigue aplicando igual.
    if pending_write is None:
        intent = state.get("intent", "")
        uuid_in_msg = _MSG_UUID_RE.search(state.get("message") or "")
        if intent == "rental_cancel" and uuid_in_msg:
            pending_write = {"name": "cancelar_alquiler", "args": {"uuid": uuid_in_msg.group(0)}}
        elif intent in ("rental_change", "support") or state.get("handoff"):
            ticket_args: dict = {"message": (state.get("message") or "")[:500]}
            if intent == "rental_change" and uuid_in_msg:
                ticket_args["rental_uuid"] = uuid_in_msg.group(0)
            pending_write = {"name": "abrir_ticket_soporte", "args": ticket_args}

    if pending_write is not None:
        executed.append({"name": pending_write["name"], "args": pending_write["args"],
                         "pending_confirmation": True})
    return {"tool_calls": executed, "tool_results": results, "pending_write": pending_write}


# ---------------------------------------------------------------------------
# Policy Layer (Componente 5) + confirmacion humana + audit (Fase 4)
# ---------------------------------------------------------------------------

# Rate limiter en memoria por (user_id, tool): la Policy Layer aplica el
# ToolMetadata.rate_limit ("N/hour/user" | "N/day/user"). La autorizacion
# real (permission classes) la aplica Django en el endpoint interno -- aqui
# solo hay defensa temprana, nunca la unica.
_RATE_WINDOWS = {"hour": 3600, "day": 86400}
_RATE_HITS: dict[tuple, deque] = defaultdict(deque)


def _rate_limit_exceeded(user_id, tool_name: str, rate_limit: str) -> bool:
    try:
        count_raw, window_name, _scope = rate_limit.split("/")
        limit, window = int(count_raw), _RATE_WINDOWS[window_name]
    except (ValueError, KeyError):
        return False
    now = time.monotonic()
    hits = _RATE_HITS[(user_id, tool_name)]
    while hits and now - hits[0] > window:
        hits.popleft()
    if len(hits) >= limit:
        return True
    hits.append(now)
    return False


def _pending_metadata(state: SintelActionState):
    pending = state.get("pending_write") or {}
    cap = CapabilityRegistry.get(pending.get("name", ""))
    tool = tool_registry.get_tool(cap.tool_name) if cap else None
    return (cap, tool.metadata if tool else None)


async def node_evaluate_policy(state: SintelActionState, config: dict) -> dict:
    """
    Policy Layer: nunca reinventa reglas de negocio -- las permission classes
    reales se aplican en el endpoint interno de Django. Aqui se decide:
    deny (admin-only sin staff / rate limit), confirm (metadata lo exige) o
    allow (escritura no destructiva, ej. ticket de soporte).
    """
    cap, metadata = _pending_metadata(state)
    user = state.get("user_context", {})
    if cap is None or metadata is None:
        return {"policy_decision": "deny",
                "optimized_context": state.get("optimized_context", "") + "\nAviso: accion desconocida, denegada."}
    if "IsAdminUser" in metadata.permissions and not user.get("is_staff"):
        return {"policy_decision": "deny",
                "optimized_context": state.get("optimized_context", "") + "\nAviso: accion solo para administradores, denegada."}
    if metadata.rate_limit and _rate_limit_exceeded(user.get("user_id"), metadata.name, metadata.rate_limit):
        logger.warning("[policy] rate limit %s para user=%s", metadata.name, user.get("user_id"))
        return {"policy_decision": "deny",
                "optimized_context": state.get("optimized_context", "") + "\nAviso: limite de intentos alcanzado para esta accion, intentar mas tarde."}
    if metadata.requires_confirmation:
        return {"policy_decision": "confirm", "needs_confirmation": True}
    return {"policy_decision": "allow"}


async def node_request_confirmation(state: SintelActionState, config: dict) -> dict:
    """
    Pausa el grafo con interrupt() hasta que el usuario confirme EN la
    conversacion (Restriccion Dura: ninguna accion irreversible sin
    confirmacion explicita). El resume value (bool) decide el camino.
    """
    pending = state.get("pending_write") or {}
    cap, metadata = _pending_metadata(state)
    answer = interrupt({
        "action": pending.get("name"),
        "summary": cap.description_for_llm if cap else "",
        "args": pending.get("args", {}),
        "risk": metadata.risk if metadata else "unknown",
        "question": (
            f"Vas a ejecutar: {cap.description_for_llm if cap else pending.get('name')} "
            f"con estos datos: {json.dumps(pending.get('args', {}), ensure_ascii=False, default=str)}. "
            "Responde 'si' para confirmar o 'no' para cancelar."
        ),
    })
    confirmed = bool(answer)
    if not confirmed:
        return {
            "policy_decision": "deny",
            "needs_confirmation": False,
            "pending_write": None,
            "tool_results": (state.get("tool_results") or []) + [{
                "capability": pending.get("name"),
                "result": {"action_executed": False,
                           "detail": "EL CLIENTE RESPONDIO NO: la accion NO se ejecuto. "
                                     "Todo queda exactamente igual que antes (nada fue "
                                     "cancelado ni creado)."},
            }],
        }
    return {"policy_decision": "allow", "needs_confirmation": False}


async def node_execute_write(state: SintelActionState, config: dict) -> dict:
    """Ejecuta LA escritura pendiente (una por turno) ya aprobada por la Policy Layer."""
    configurable = config.get("configurable") or {}
    ctx = ToolContext(user=state.get("user_context", {}), token=configurable.get("token", ""))
    pending = state.get("pending_write") or {}
    if not pending:
        return {"pending_write": None}
    metrics = metrics_from_config(config)
    if metrics:
        metrics.data["write_executed"] = True
    args = dict(pending["args"])
    if pending["name"] == "abrir_ticket_soporte":
        # Human Handoff (Fase 7): el operador humano recibe la conversacion
        # previa con el AI -- inyectado por el grafo, nunca por el LLM.
        history = state.get("history") or []
        if history:
            args["history"] = history[-6:]
    result = await _execute_capability(pending["name"], args, ctx, metrics)
    # Marca deterministica para generate_response: exito => action_executed=true
    # (el LLM nunca decide por su cuenta si una accion ocurrio o no).
    inner = result.get("result")
    if isinstance(inner, dict) and not inner.get("error"):
        inner["action_executed"] = True
    return {
        "pending_write": None,
        "tool_results": (state.get("tool_results") or []) + [result],
    }


async def node_audit_log(state: SintelActionState, config: dict) -> dict:
    """
    Audit del lado del motor (estructurado). El registro durable vive en
    Django: cada endpoint interno de escritura crea un SecurityEvent
    AI_ACTION_EXECUTED con el usuario real del JWT.
    """
    user = state.get("user_context", {})
    for item in state.get("tool_results") or []:
        if not isinstance(item, dict) or "capability" not in item:
            continue
        result = item.get("result", {})
        status = "error" if (isinstance(result, dict) and result.get("error")) else (
            "cancelled" if (isinstance(result, dict) and result.get("cancelled")) else "ok"
        )
        logger.info(
            "[audit] user=%s(%s) capability=%s args_keys=%s status=%s",
            user.get("user_id"), user.get("email"), item.get("capability"),
            sorted((item.get("args") or {}).keys()), status,
        )
    return {}


async def node_validate_tool_result(state: SintelActionState, config: dict) -> dict:
    """Marca errores/vacios para que la respuesta final sea honesta, nunca inventada."""
    notes = []
    for item in state.get("tool_results") or []:
        result = item.get("result", {}) if isinstance(item, dict) else {}
        if isinstance(result, dict) and result.get("error"):
            notes.append(f"{item.get('capability')}: {result['error']}")
    if not (state.get("tool_results") or []) and not state.get("pending_write"):
        notes.append("No se ejecuto ninguna herramienta -- responder pidiendo mas detalle, sin inventar.")
    return {"optimized_context": state.get("optimized_context", "") + ("\nAvisos: " + "; ".join(notes) if notes else "")}


async def node_generate_response(state: SintelActionState, config: dict) -> dict:
    llm = (config.get("configurable") or {}).get("resources", {}).get("llm")
    tool_results_json = json.dumps(state.get("tool_results") or [], ensure_ascii=False, default=str)[:8000]
    # Fase 6: persona del Agent Profile activo (personalidad/tono declarados
    # en YAML -- nunca reglas de negocio, solo estilo de comunicacion).
    agent = AgentRegistry.get(state.get("agent", ""))
    persona = (
        f"Actuas como {agent.name} ({agent.description}). Personalidad: {agent.personalidad}. "
        f"Tono: {agent.tono}.\n" if agent else ""
    )
    handoff_note = (
        "La conversacion fue derivada a soporte en este turno -- reconoce la molestia "
        "del cliente antes de responder.\n" if state.get("handoff") else ""
    )
    system = (
        persona + handoff_note +
        "Eres el asistente de atencion al cliente de Sintel (Colombia). Responde en espanol, "
        "breve y concreto. REGLAS: responde UNICAMENTE con los datos del bloque RESULTADOS "
        "(y el contexto); si no hay datos suficientes, dilo honestamente y ofrece escalar a "
        "soporte; nunca inventes estados, fechas ni montos. Sobre acciones ejecutadas: "
        "action_executed=true significa que la accion SI se realizo con exito -- "
        "confirmasela al cliente con sus datos, NUNCA digas que no se realizo; "
        "action_executed=false significa que el cliente no confirmo y nada cambio. "
        "Si ningun resultado trae action_executed, no menciones acciones. Si preguntan el "
        "MOTIVO de un pago rechazado, explica que solo conoces el estado y que soporte "
        "puede revisar el detalle.\n\n"
        f"Contexto:\n{state.get('optimized_context', '')}\n\nRESULTADOS:\n{tool_results_json}"
    )
    if llm is None:
        final = "El motor no esta inicializado todavia. Intenta de nuevo en unos minutos."
    else:
        ai_msg = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=state["message"])])
        metrics = metrics_from_config(config)
        if metrics:
            metrics.record_llm(ai_msg)
        final = (ai_msg.content or "").strip() or "No tengo datos suficientes para responder eso ahora mismo."
    return {
        "final_response": final,
        "history": [{"user": state["message"], "assistant": final}],
    }


# ---------------------------------------------------------------------------
# Construccion y entrada publica
# ---------------------------------------------------------------------------

def _route_after_optimize(state: SintelActionState) -> str:
    return "retrieve_knowledge" if state.get("intent") == "knowledge" else "select_and_execute_tools"


def _route_after_validate(state: SintelActionState) -> str:
    return "evaluate_policy" if state.get("pending_write") else "generate_response"


def _route_after_policy(state: SintelActionState) -> str:
    decision = state.get("policy_decision", "deny")
    if decision == "confirm":
        return "request_confirmation"
    if decision == "allow":
        return "execute_write"
    return "generate_response"


def _route_after_confirmation(state: SintelActionState) -> str:
    return "execute_write" if state.get("policy_decision") == "allow" else "generate_response"


# B2 (AUDITORIA/16_AUDITORIA_AI_ENGINE_SYNC.md, 2026-08-01): antes MemorySaver() (RAM del
# proceso, se perdia todo en cada reinicio). Ahora persiste en el Redis del proyecto -- ver
# redis_checkpointer.py para por que no se uso el paquete oficial langgraph-checkpoint-redis.
_CHECKPOINTER = RedisCheckpointSaver(CHECKPOINTER_REDIS_URL)
_GRAPH = None


def get_action_graph():
    global _GRAPH
    if _GRAPH is None:
        g = StateGraph(SintelActionState)
        g.add_node("resolve_customer_context", node_resolve_customer_context)
        g.add_node("detect_intent", node_detect_intent)
        g.add_node("optimize_context", node_optimize_context)
        g.add_node("retrieve_knowledge", node_retrieve_knowledge)
        g.add_node("select_and_execute_tools", node_select_and_execute_tools)
        g.add_node("validate_tool_result", node_validate_tool_result)
        g.add_node("evaluate_policy", node_evaluate_policy)
        g.add_node("request_confirmation", node_request_confirmation)
        g.add_node("execute_write", node_execute_write)
        g.add_node("audit_log", node_audit_log)
        g.add_node("generate_response", node_generate_response)

        g.set_entry_point("resolve_customer_context")
        g.add_edge("resolve_customer_context", "detect_intent")
        g.add_edge("detect_intent", "optimize_context")
        g.add_conditional_edges("optimize_context", _route_after_optimize,
                                ["retrieve_knowledge", "select_and_execute_tools"])
        g.add_edge("retrieve_knowledge", "generate_response")
        g.add_edge("select_and_execute_tools", "validate_tool_result")
        # Fase 4: escritura pendiente -> Policy Layer -> (confirmar | ejecutar | denegar)
        g.add_conditional_edges("validate_tool_result", _route_after_validate,
                                ["evaluate_policy", "generate_response"])
        g.add_conditional_edges("evaluate_policy", _route_after_policy,
                                ["request_confirmation", "execute_write", "generate_response"])
        g.add_conditional_edges("request_confirmation", _route_after_confirmation,
                                ["execute_write", "generate_response"])
        g.add_edge("execute_write", "audit_log")
        g.add_edge("audit_log", "generate_response")
        g.add_edge("generate_response", END)

        _GRAPH = g.compile(checkpointer=_CHECKPOINTER)
    return _GRAPH


_AFFIRM_RE = re.compile(r"^\s*(si|sí|s[ií] confirmo|confirmo|confirmar|dale|ok|okay|de acuerdo|hazlo|adelante)\s*[.!]*\s*$", re.I)
_NEGATE_RE = re.compile(r"^\s*(no|no confirmo|cancela|cancelar|mejor no|detente|para)\s*[.!]*\s*$", re.I)


def _pending_interrupt(graph, config) -> dict | None:
    """Devuelve el payload del interrupt pendiente del thread, si existe."""
    try:
        snapshot = graph.get_state(config)
    except Exception:
        # D1 (AUDITORIA/16, 2026-08-01): esto se llama en CADA turno de /chat (antes y despues
        # de procesar). Un fallo real del checkpointer se trataba igual que "no hay interrupcion
        # pendiente", sin ningun rastro -- mismo patron ya corregido hoy en
        # support/channels_auth.py y support/services/customer360.py del lado Django.
        logger.warning("[_pending_interrupt] fallo leyendo estado del checkpointer", exc_info=True)
        return None
    for task in getattr(snapshot, "tasks", ()) or ():
        for intr in getattr(task, "interrupts", ()) or ():
            return getattr(intr, "value", None) or {}
    return None


async def run_action_chat(message: str, conversation_id: str | None, token: str,
                          user_id, llm, vectorstore, all_docs,
                          confirm: bool | None = None) -> dict:
    """
    Punto de entrada para POST /chat. El thread del checkpointer se namespacea
    por user_id (del JWT ya validado) para que nadie retome la conversacion
    de otro usuario adivinando el conversation_id.

    Confirmaciones (Fase 4): si el grafo quedo pausado en request_confirmation,
    el turno se reanuda con `confirm` explicito (true/false) o con un mensaje
    afirmativo/negativo simple ("si"/"no"). Cualquier otro mensaje se trata
    como nueva peticion (la accion pendiente se descarta).
    """
    from langgraph.types import Command

    conversation_id = conversation_id or uuid_lib.uuid4().hex[:12]
    graph = get_action_graph()
    metrics = TurnMetrics(conversation_id, user_id)
    config = {
        "configurable": {
            "thread_id": f"{user_id}:{conversation_id}",
            "token": token,
            "resources": {"llm": llm, "vectorstore": vectorstore, "all_docs": all_docs},
            "metrics": metrics,
        }
    }

    pending = _pending_interrupt(graph, config)
    resume_value: bool | None = confirm
    if pending is not None and resume_value is None:
        if _AFFIRM_RE.match(message or ""):
            resume_value = True
        elif _NEGATE_RE.match(message or ""):
            resume_value = False

    if pending is not None and resume_value is not None:
        state = await graph.ainvoke(Command(resume=resume_value), config=config)
    else:
        state = await graph.ainvoke(
            {"message": message, "conversation_id": conversation_id,
             "pending_write": None, "policy_decision": "", "needs_confirmation": False},
            config=config,
        )

    # Deteccion del interrupt: en langgraph 0.2.x el resultado de ainvoke()
    # NO trae la clave "__interrupt__" -- hay que consultar el checkpoint del
    # thread (get_state), igual que hace _pending_interrupt para el resume.
    interrupts = state.get("__interrupt__") or []
    payload = getattr(interrupts[0], "value", None) if interrupts else None
    if payload is None:
        payload = _pending_interrupt(graph, config)
    if payload is not None:
        metrics.data["needs_confirmation"] = True
        metrics.data["agent"] = metrics.data.get("agent") or state.get("agent")
        metrics.data["intent"] = metrics.data.get("intent") or state.get("intent")
        metrics.emit()
        return {
            "conversation_id": conversation_id,
            "intent": state.get("intent", "unknown"),
            "agent": state.get("agent"),
            "tool_calls": state.get("tool_calls") or [],
            "tool_results": state.get("tool_results") or [],
            "needs_confirmation": True,
            "confirmation": payload,
            "response": payload.get("question", "Confirma la accion con 'si' o 'no'."),
            "metrics": metrics.data,
        }

    metrics.data["agent"] = metrics.data.get("agent") or state.get("agent")
    metrics.data["intent"] = metrics.data.get("intent") or state.get("intent")
    metrics.emit()
    return {
        "conversation_id": conversation_id,
        "intent": state.get("intent", "unknown"),
        "agent": state.get("agent"),
        "tool_calls": state.get("tool_calls") or [],
        "tool_results": state.get("tool_results") or [],
        "needs_confirmation": False,
        "confirmation": None,
        "response": state.get("final_response", ""),
        "metrics": metrics.data,
    }
