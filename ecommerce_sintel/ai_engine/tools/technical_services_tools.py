"""
Tools de Servicios Tecnicos del AI Core -- Admin AI Assistant, vertical
Servicios (PLAN_SINTEL_ADMIN_ASISTENTE_RAG_FORMULARIOS_LOOP.md, Fase 1-3,
2026-09-23). Mismo patron exacto que catalog_tools.py (vertical Catalogo).

Alcance de esta fase: Nivel 0-2 de TechnicalService (listar, ver, crear
borrador, editar) + lectura de ServiceCategory para resolucion. Nivel 3/4
(publicar/eliminar) quedan para una fase posterior -- mismo criterio real
que ya aplico catalog_tools.py.

Regla dura (mismo criterio que Product): ServiceCreateDraftTool SIEMPRE
crea con is_active=False -- forzado del lado de Django
(technical_services/api/internal_ai.py::AiServiceAdminCreateDraftView), no
solo aqui.

Motivo real de esta vertical (no hipotetico, ver AUDITORIA/
ASSISTANT_BASELINE.md): sin estas Tools, CatalogAgent usaba su propia
logica de PRODUCTO para interpretar "crear un servicio" (pregunto marca/
condicion -- campos que TechnicalService ni siquiera tiene).
"""
from tools.http_bridge import django_internal_get, django_internal_post
from tools.metadata import ToolContext, ToolMetadata
from tools.registry import register_tool

# ─── Lectura (Nivel 0) ──────────────────────────────────────────────────────

SERVICE_LIST_METADATA = ToolMetadata(
    name="ServiceListTool",
    description="Lista servicios tecnicos del catalogo (admin), con filtros opcionales de busqueda y estado activo.",
    owner="technical_services",
    capabilities=["listar_servicios"],
    permissions=["IsAdminUser"],
    risk="low",
    audit_level="none",
    args_schema={
        "type": "object",
        "properties": {
            "search":    {"type": "string",  "description": "Texto a buscar en nombre o descripcion."},
            "is_active": {"type": "boolean", "description": "Filtrar por publicado (true) o borrador (false)."},
            "limit":     {"type": "integer", "description": "Maximo de resultados (por defecto 20, tope 50)."},
        },
    },
)


@register_tool(SERVICE_LIST_METADATA)
async def service_list_tool(ctx: ToolContext, **kwargs) -> dict:
    """Envuelve ServiceSelector.list_all_for_admin()."""
    params = {k: v for k, v in kwargs.items() if v is not None}
    return await django_internal_get(
        ctx.token, "/services/admin/", params=params,
        timeout_ms=SERVICE_LIST_METADATA.timeout_ms,
    )


SERVICE_GET_METADATA = ToolMetadata(
    name="ServiceGetTool",
    description="Obtiene el detalle completo de un servicio tecnico por su UUID, incluida su variante de precio por defecto.",
    owner="technical_services",
    capabilities=["ver_servicio"],
    permissions=["IsAdminUser"],
    risk="low",
    audit_level="none",
    args_schema={
        "type": "object",
        "required": ["uuid"],
        "properties": {"uuid": {"type": "string", "description": "UUID del servicio."}},
    },
)


@register_tool(SERVICE_GET_METADATA)
async def service_get_tool(ctx: ToolContext, uuid: str) -> dict:
    """Envuelve ServiceSelector.get_by_uuid()."""
    return await django_internal_get(
        ctx.token, "/services/admin/get/", params={"uuid": uuid},
        timeout_ms=SERVICE_GET_METADATA.timeout_ms,
    )


SERVICE_CATEGORY_LIST_METADATA = ToolMetadata(
    name="ServiceCategoryListTool",
    description="Lista categorias de servicios tecnicos (admin), con busqueda opcional. Usar para resolver la categoria antes de crear/editar un servicio.",
    owner="technical_services",
    capabilities=["listar_categorias_servicio"],
    permissions=["IsAdminUser"],
    risk="low",
    audit_level="none",
    args_schema={
        "type": "object",
        "properties": {
            "search": {"type": "string",  "description": "Texto a buscar en el nombre."},
            "limit":  {"type": "integer", "description": "Maximo de resultados (por defecto 20, tope 50)."},
        },
    },
)


@register_tool(SERVICE_CATEGORY_LIST_METADATA)
async def service_category_list_tool(ctx: ToolContext, **kwargs) -> dict:
    """Envuelve ServiceCategorySelector.list_all_for_admin()."""
    params = {k: v for k, v in kwargs.items() if v is not None}
    return await django_internal_get(
        ctx.token, "/services/admin/categories/", params=params,
        timeout_ms=SERVICE_CATEGORY_LIST_METADATA.timeout_ms,
    )


# ─── Escritura (Nivel 1-2) ──────────────────────────────────────────────────

SERVICE_CREATE_DRAFT_METADATA = ToolMetadata(
    name="ServiceCreateDraftTool",
    description=(
        "Crea un servicio tecnico NUEVO como borrador (sin publicar). El servicio queda "
        "oculto del catalogo publico hasta que un administrador lo publique manualmente "
        "desde el panel -- esta Tool nunca publica. El precio dado se guarda como precio "
        "fijo (pricing_strategy=FIXED) de la variante por defecto -- NUNCA pedir marca ni "
        "condicion, TechnicalService no tiene esos campos (esos son de Product)."
    ),
    owner="technical_services",
    capabilities=["crear_borrador_servicio"],
    permissions=["IsAdminUser"],
    risk="medium",
    audit_level="full",
    side_effects=True,
    args_schema={
        "type": "object",
        "required": ["name", "price"],
        "properties": {
            "name":            {"type": "string",  "description": "Nombre del servicio."},
            "price":           {"type": "number",  "description": "Precio fijo del servicio (COP)."},
            "category":        {"type": "string",  "description": "UUID de la categoria de servicio (opcional)."},
            "description":     {"type": "string",  "description": "Descripcion comercial del servicio."},
            "scope":           {"type": "string",  "description": "Alcance del servicio incluido."},
            "warranty":        {"type": "string",  "description": "Texto de garantia."},
            "coverage_notes":  {"type": "string",  "description": "Notas de cobertura (zonas, condiciones)."},
            "is_featured":     {"type": "boolean", "description": "Marcar como servicio destacado."},
        },
    },
)


@register_tool(SERVICE_CREATE_DRAFT_METADATA)
async def service_create_draft_tool(ctx: ToolContext, name: str, price, **kwargs) -> dict:
    """Envuelve ServiceAdminOrchestrator.create_service_with_default_variant() -- is_active forzado del lado de Django."""
    body = {"name": name, "price": price, **kwargs}
    return await django_internal_post(
        ctx.token, "/services/admin/create-draft/", body=body,
        timeout_ms=SERVICE_CREATE_DRAFT_METADATA.timeout_ms,
    )


SERVICE_UPDATE_DRAFT_METADATA = ToolMetadata(
    name="ServiceUpdateDraftTool",
    description=(
        "Actualiza contenido, categoria o precio de un servicio EXISTENTE (borrador o "
        "publicado). Nunca cambia si el servicio esta publicado -- eso requiere una accion "
        "separada que el administrador debe confirmar en el panel."
    ),
    owner="technical_services",
    capabilities=["editar_borrador_servicio"],
    permissions=["IsAdminUser"],
    risk="medium",
    audit_level="full",
    side_effects=True,
    args_schema={
        "type": "object",
        "required": ["uuid"],
        "properties": {
            "uuid":           {"type": "string",  "description": "UUID del servicio a actualizar."},
            "name":           {"type": "string",  "description": "Nuevo nombre."},
            "category":       {"type": "string",  "description": "UUID de la nueva categoria."},
            "description":    {"type": "string",  "description": "Nueva descripcion."},
            "scope":          {"type": "string",  "description": "Nuevo alcance."},
            "warranty":       {"type": "string",  "description": "Nuevo texto de garantia."},
            "coverage_notes": {"type": "string",  "description": "Nuevas notas de cobertura."},
            "is_featured":    {"type": "boolean", "description": "Marcar/desmarcar como destacado."},
            "price":          {"type": "number",  "description": "Nuevo precio fijo de la variante por defecto."},
        },
    },
)


@register_tool(SERVICE_UPDATE_DRAFT_METADATA)
async def service_update_draft_tool(ctx: ToolContext, uuid: str, **kwargs) -> dict:
    """Envuelve ServiceAdminOrchestrator.update_service() -- is_active nunca se acepta (ver Django)."""
    body = {"uuid": uuid, **kwargs}
    return await django_internal_post(
        ctx.token, "/services/admin/update-draft/", body=body,
        timeout_ms=SERVICE_UPDATE_DRAFT_METADATA.timeout_ms,
    )
