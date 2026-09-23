"""
Router de intencion de negocio del AI Core -- extraido de `action_graph.py`
(mision "ADK-SINTEL", ADK-11, 2026-09-14) para que sea importable SIN
LangChain/LangGraph.

Motivo real: `action_graph.py` importa `langchain_core`/`langgraph` a nivel
de modulo (necesarios para el grafo LangGraph en si). El nuevo runtime ADK
(`ai_engine_adk/`, ver AUDITORIA/ADK_CUTOVER_PLAN.md) necesita EXACTAMENTE
esta misma logica de routing (mismo codigo, no una copia -- regla de la
mision, "no duplicar") pero NO puede importar `langchain-core`/`langgraph`:
`litellm` (dependencia de ADK) exige `openai>=2.20.0`, y el
`langchain-openai` que el `LOCAL_MODEL_CHAIN` real de este proyecto
necesita exige `openai<2.0.0` -- rangos que no se solapan, confirmado en
`adk_poc/` (ADK-10). Aislar esta logica (pura, sin dependencias pesadas:
solo `re`) en su propio modulo permite que AMBOS runtimes (OLD via
`action_graph.py`, NEW via `ai_engine_adk/`) la importen sin conflicto,
sin que ninguno reimplemente el vocabulario/mapeo real.

Extraccion mecanica -- CERO cambio de comportamiento: mismos patrones
regex, mismo orden de diccionario (el orden importa, ver
`detect_business_intents`), misma funcion, byte-a-byte. Verificado con la
suite real existente `ai_engine/tests/test_intent_detection.py` (fijaba
este vocabulario desde 2026-08-08) antes y despues de mover este codigo,
sin ninguna modificacion a ese archivo de test.
"""
import re

MAX_CONTEXT_CHARS = 6000      # presupuesto explicito del Context Optimizer
MAX_HISTORY_TURNS = 3
MAX_KNOWLEDGE_CHUNKS = 6


# ---------------------------------------------------------------------------
# Intencion de negocio (mismo patron regex que planner.py::detect_intent,
# pero con intents de negocio, no de codigo)
# ---------------------------------------------------------------------------

BUSINESS_INTENT_PATTERNS = {
    # Orden importa: los intents mas especificos van primero (el nodo toma el
    # primer intent de datos que matchee).
    # Admin AI Assistant, vertical piloto Catalogo (Fase 3, 2026-09-16): va PRIMERO
    # a proposito -- verbo de gestion + "producto(s)" es mas especifico que
    # "renting_search" (dispara con una sola palabra suelta como "camara"/"equipo"),
    # y el negocio vende camaras/equipos de CCTV, asi que "crear producto de camaras"
    # matchea ambos patrones. Sin esta prioridad, renting_search (mas abajo en este
    # dict) siempre ganaria y CatalogAgent quedaria practicamente inalcanzable.
    "catalog_admin":          re.compile(
        r"\b(crear|crea|creame|agregar|agrega|agregame|nuevo|nueva|dar de alta)\b.{0,25}\b(producto|categoria|marca|impuesto)\w*"
        r"|\b(editar|edita|actualizar|actualiza|modificar|modifica|cambiar|cambia)\b.{0,25}\b(producto|categoria|marca|impuesto)\w*"
        r"|\b(publicar|publica|despublicar|despublica)\b.{0,25}\b(producto|categoria|marca)\w*"
        r"|\bborrador(es)? de (producto|categoria|marca)\w*"
        r"|\bcatalogo de productos\b",
        re.I,
    ),
    # Admin AI Assistant, vertical Servicios (PLAN_SINTEL_ADMIN_ASISTENTE_RAG_
    # FORMULARIOS_LOOP.md, Fase 1-3, 2026-09-23): mismo razonamiento que
    # catalog_admin arriba -- va PRIMERO a proposito, antes que
    # `service_status` (linea de abajo, dispara con la sola palabra suelta
    # "servicio", intent de CLIENTE). Sin esta prioridad, cualquier mensaje
    # admin que mencione "servicio" caeria en service_status/SupportAgent en
    # vez de service_admin/CatalogAgent.
    "service_admin":          re.compile(
        r"\b(crear|crea|creame|agregar|agrega|agregame|nuevo|nueva|dar de alta)\b.{0,25}\bservicio\w*"
        r"|\b(editar|edita|actualizar|actualiza|modificar|modifica|cambiar|cambia)\b.{0,25}\bservicio\w*"
        r"|\b(publicar|publica|despublicar|despublica)\b.{0,25}\bservicio\w*"
        r"|\bborrador(es)? de servicio\w*",
        re.I,
    ),
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
    # "architecture_impact" (GraphImpactAnalysisTool) retirado 2026-08-10 (FASE 0,
    # desacoplamiento ai_engine <-> project_knowledge_graph) -- era una capacidad de
    # arquitectura/ingenieria expuesta al chat de soporte (agregada 2026-08-04), no algo
    # que un cliente deba poder disparar via chat. ai_engine ya no debe importar
    # project_knowledge_graph en absoluto.
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
    "catalog_admin":           ["listar_productos", "ver_producto", "crear_borrador_producto",
                                "editar_borrador_producto", "publicar_producto",
                                "listar_categorias", "ver_categoria", "crear_borrador_categoria",
                                "editar_categoria", "publicar_categoria",
                                "listar_marcas", "ver_marca", "crear_borrador_marca",
                                "editar_marca", "publicar_marca",
                                "listar_impuestos", "ver_impuesto", "crear_impuesto", "editar_impuesto"],
    "service_admin":           ["listar_servicios", "ver_servicio", "listar_categorias_servicio",
                                "crear_borrador_servicio", "editar_borrador_servicio"],
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
    # Fallback de solo-lectura -- una escritura JAMAS se dispara por fallback.
    "catalog_admin":           "listar_productos",
    "service_admin":           "listar_servicios",
}


def detect_business_intents(message: str) -> list[str]:
    intents = [name for name, pat in BUSINESS_INTENT_PATTERNS.items() if pat.search(message)]
    return intents or ["unknown"]
