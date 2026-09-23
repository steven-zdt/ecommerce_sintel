"""
Tools de Catalogo (Producto) del AI Core -- Admin AI Assistant, vertical
piloto (Fase 3, 2026-09-16). Ver ai_engine/.AGENT/ADMIN_AI_ASSISTANT_FASE0_MATRIZ.md
y ADMIN_AI_ASSISTANT_FASE1_TOOLS_CATALOGO.md para el diseno completo de la
vertical (matriz de capacidades real + catalogo de Tools/riesgo).

Alcance de ESTA fase: solo Nivel 0-2 de Product (listar, ver, crear
borrador, editar). Category/Brand/Tax y set_published_state/delete
(Nivel 3/4) quedan para una fase posterior -- mismo patron, deliberadamente
no construidos aun para mantener esta entrega revisable.

Regla dura (Decision 1/2 del catalogo de Tools): CatalogProductCreateDraftTool
SIEMPRE crea con is_active=False y stock=0 -- forzado del lado de Django
(shop/api/internal_ai.py), no solo aqui, sin importar lo que pida el LLM.
Publicar (`is_active=True`) no tiene Tool todavia: no es una regla de
prompt, es fisicamente imposible desde este agente hasta que exista
CatalogProductSetPublishedStateTool (Nivel 3, con requires_confirmation=True).
"""
from tools.http_bridge import django_internal_get, django_internal_post
from tools.metadata import ToolContext, ToolMetadata
from tools.registry import register_tool

# ─── Lectura (Nivel 0) ──────────────────────────────────────────────────────

CATALOG_PRODUCT_LIST_METADATA = ToolMetadata(
    name="CatalogProductListTool",
    description="Lista productos del catalogo (admin), con filtros opcionales de busqueda, estado activo y destacado.",
    owner="shop",
    capabilities=["listar_productos"],
    permissions=["IsAdminUser"],
    risk="low",
    audit_level="none",
    args_schema={
        "type": "object",
        "properties": {
            "search":      {"type": "string", "description": "Texto a buscar en nombre o descripcion corta."},
            "is_active":   {"type": "boolean", "description": "Filtrar por publicado (true) o borrador (false)."},
            "is_featured": {"type": "boolean", "description": "Filtrar por productos destacados."},
            "limit":       {"type": "integer", "description": "Maximo de resultados (por defecto 20, tope 50)."},
        },
    },
)


@register_tool(CATALOG_PRODUCT_LIST_METADATA)
async def catalog_product_list_tool(ctx: ToolContext, **kwargs) -> dict:
    """Envuelve ProductSelector.list_all_for_admin()."""
    params = {k: v for k, v in kwargs.items() if v is not None}
    return await django_internal_get(
        ctx.token, "/catalog/products/", params=params,
        timeout_ms=CATALOG_PRODUCT_LIST_METADATA.timeout_ms,
    )


CATALOG_PRODUCT_GET_METADATA = ToolMetadata(
    name="CatalogProductGetTool",
    description="Obtiene el detalle completo de un producto del catalogo por su UUID.",
    owner="shop",
    capabilities=["ver_producto"],
    permissions=["IsAdminUser"],
    risk="low",
    audit_level="none",
    args_schema={
        "type": "object",
        "required": ["uuid"],
        "properties": {"uuid": {"type": "string", "description": "UUID del producto."}},
    },
)


@register_tool(CATALOG_PRODUCT_GET_METADATA)
async def catalog_product_get_tool(ctx: ToolContext, uuid: str) -> dict:
    """Envuelve ProductSelector.get_by_uuid()."""
    return await django_internal_get(
        ctx.token, "/catalog/products/get/", params={"uuid": uuid},
        timeout_ms=CATALOG_PRODUCT_GET_METADATA.timeout_ms,
    )


# ─── Escritura (Nivel 1-2) ──────────────────────────────────────────────────

CATALOG_PRODUCT_CREATE_DRAFT_METADATA = ToolMetadata(
    name="CatalogProductCreateDraftTool",
    description=(
        "Crea un producto NUEVO como borrador (sin publicar, sin stock). El producto "
        "queda oculto del catalogo publico hasta que un administrador lo publique "
        "manualmente desde el panel -- esta Tool nunca publica ni carga stock."
    ),
    owner="shop",
    capabilities=["crear_borrador_producto"],
    permissions=["IsAdminUser"],
    risk="medium",
    audit_level="full",
    side_effects=True,
    args_schema={
        "type": "object",
        "required": ["name", "category", "price"],
        "properties": {
            "name":              {"type": "string",  "description": "Nombre del producto."},
            "category":          {"type": "string",  "description": "UUID de la categoria."},
            "price":             {"type": "number",  "description": "Precio base de la variante por defecto."},
            "brand":             {"type": "string",  "description": "UUID de la marca (opcional)."},
            "condition":         {"type": "string",  "description": "new | used | refurbished (por defecto new)."},
            "short_description": {"type": "string",  "description": "Resumen corto para tarjetas de producto."},
            "description":       {"type": "string",  "description": "Descripcion comercial completa."},
            "scope":             {"type": "string",  "description": "Alcance del producto incluido."},
            "warranty":          {"type": "string",  "description": "Texto de garantia."},
            "is_featured":       {"type": "boolean", "description": "Marcar como producto destacado."},
            "meta_title":        {"type": "string",  "description": "Meta title SEO."},
            "meta_description":  {"type": "string",  "description": "Meta description SEO."},
        },
    },
)


@register_tool(CATALOG_PRODUCT_CREATE_DRAFT_METADATA)
async def catalog_product_create_draft_tool(ctx: ToolContext, name: str, category: str, price, **kwargs) -> dict:
    """Envuelve ProductCommands.create_product() -- is_active/stock forzados del lado de Django."""
    body = {"name": name, "category": category, "price": price, **kwargs}
    return await django_internal_post(
        ctx.token, "/catalog/products/create-draft/", body=body,
        timeout_ms=CATALOG_PRODUCT_CREATE_DRAFT_METADATA.timeout_ms,
    )


CATALOG_PRODUCT_UPDATE_DRAFT_METADATA = ToolMetadata(
    name="CatalogProductUpdateDraftTool",
    description=(
        "Actualiza contenido, categoria/marca, precio o stock de un producto EXISTENTE "
        "(borrador o ya publicado). Nunca cambia si el producto esta publicado o no -- "
        "eso requiere una accion separada que el administrador debe confirmar en el panel."
    ),
    owner="shop",
    capabilities=["editar_borrador_producto"],
    permissions=["IsAdminUser"],
    risk="medium",
    audit_level="full",
    side_effects=True,
    args_schema={
        "type": "object",
        "required": ["uuid"],
        "properties": {
            "uuid":              {"type": "string",  "description": "UUID del producto a actualizar."},
            "name":              {"type": "string",  "description": "Nuevo nombre."},
            "category":          {"type": "string",  "description": "UUID de la nueva categoria."},
            "brand":             {"type": "string",  "description": "UUID de la nueva marca."},
            "condition":         {"type": "string",  "description": "new | used | refurbished."},
            "short_description": {"type": "string",  "description": "Nuevo resumen corto."},
            "description":       {"type": "string",  "description": "Nueva descripcion comercial."},
            "scope":             {"type": "string",  "description": "Nuevo alcance."},
            "warranty":          {"type": "string",  "description": "Nuevo texto de garantia."},
            "is_featured":       {"type": "boolean", "description": "Marcar/desmarcar como destacado."},
            "meta_title":        {"type": "string",  "description": "Nuevo meta title SEO."},
            "meta_description":  {"type": "string",  "description": "Nuevo meta description SEO."},
            "price":             {"type": "number",  "description": "Nuevo precio de la variante por defecto."},
            "discounted_price":  {"type": "number",  "description": "Nuevo precio con descuento."},
            "stock":             {"type": "integer", "description": "Nuevo stock de la variante por defecto (movimiento auditado en Inventory)."},
        },
    },
)


@register_tool(CATALOG_PRODUCT_UPDATE_DRAFT_METADATA)
async def catalog_product_update_draft_tool(ctx: ToolContext, uuid: str, **kwargs) -> dict:
    """Envuelve ProductCommands.update_product() -- is_active nunca se acepta (ver Django)."""
    body = {"uuid": uuid, **kwargs}
    return await django_internal_post(
        ctx.token, "/catalog/products/update-draft/", body=body,
        timeout_ms=CATALOG_PRODUCT_UPDATE_DRAFT_METADATA.timeout_ms,
    )


# ─── Publicacion (Nivel 3, HITL obligatorio) ────────────────────────────────

CATALOG_PRODUCT_SET_PUBLISHED_STATE_METADATA = ToolMetadata(
    name="CatalogProductSetPublishedStateTool",
    description=(
        "Publica (visible al publico) o despublica (oculta del catalogo publico) un "
        "producto existente. Esta es la UNICA forma de cambiar si un producto esta "
        "publicado -- create_draft y update_draft nunca lo tocan. Requiere que el "
        "administrador confirme explicitamente antes de ejecutarse."
    ),
    owner="shop",
    capabilities=["publicar_producto"],
    permissions=["IsAdminUser"],
    risk="high",
    audit_level="full",
    requires_confirmation=True,
    side_effects=True,
    args_schema={
        "type": "object",
        "required": ["uuid", "is_active"],
        "properties": {
            "uuid":      {"type": "string",  "description": "UUID del producto a publicar o despublicar."},
            "is_active": {"type": "boolean", "description": "true para publicar (visible al publico), false para despublicar (ocultar)."},
        },
    },
)


@register_tool(CATALOG_PRODUCT_SET_PUBLISHED_STATE_METADATA)
async def catalog_product_set_published_state_tool(ctx: ToolContext, uuid: str, is_active: bool) -> dict:
    """Envuelve ProductCommands.update_product({'is_active': ...}) -- unico campo permitido."""
    return await django_internal_post(
        ctx.token, "/catalog/products/set-published-state/",
        body={"uuid": uuid, "is_active": is_active},
        timeout_ms=CATALOG_PRODUCT_SET_PUBLISHED_STATE_METADATA.timeout_ms,
    )


# ─── Category (mismo patron que Product) ───────────────────────────────────

CATALOG_CATEGORY_LIST_METADATA = ToolMetadata(
    name="CatalogCategoryListTool", description="Lista categorias del catalogo (admin), con busqueda opcional.",
    owner="shop", capabilities=["listar_categorias"], permissions=["IsAdminUser"], risk="low", audit_level="none",
    args_schema={"type": "object", "properties": {
        "search": {"type": "string", "description": "Texto a buscar en el nombre."},
        "limit":  {"type": "integer", "description": "Maximo de resultados (por defecto 20, tope 50)."},
    }},
)


@register_tool(CATALOG_CATEGORY_LIST_METADATA)
async def catalog_category_list_tool(ctx: ToolContext, **kwargs) -> dict:
    params = {k: v for k, v in kwargs.items() if v is not None}
    return await django_internal_get(ctx.token, "/catalog/categories/", params=params, timeout_ms=CATALOG_CATEGORY_LIST_METADATA.timeout_ms)


CATALOG_CATEGORY_GET_METADATA = ToolMetadata(
    name="CatalogCategoryGetTool", description="Obtiene el detalle de una categoria por su UUID.",
    owner="shop", capabilities=["ver_categoria"], permissions=["IsAdminUser"], risk="low", audit_level="none",
    args_schema={"type": "object", "required": ["uuid"], "properties": {"uuid": {"type": "string", "description": "UUID de la categoria."}}},
)


@register_tool(CATALOG_CATEGORY_GET_METADATA)
async def catalog_category_get_tool(ctx: ToolContext, uuid: str) -> dict:
    return await django_internal_get(ctx.token, "/catalog/categories/get/", params={"uuid": uuid}, timeout_ms=CATALOG_CATEGORY_GET_METADATA.timeout_ms)


CATALOG_CATEGORY_CREATE_DRAFT_METADATA = ToolMetadata(
    name="CatalogCategoryCreateDraftTool",
    description="Crea una categoria NUEVA como borrador (sin publicar). Nunca publica.",
    owner="shop", capabilities=["crear_borrador_categoria"], permissions=["IsAdminUser"], risk="medium",
    audit_level="full", side_effects=True,
    args_schema={"type": "object", "required": ["name"], "properties": {
        "name":             {"type": "string", "description": "Nombre de la categoria."},
        "description":      {"type": "string", "description": "Descripcion de la categoria."},
        "parent":           {"type": "string", "description": "UUID de la categoria padre (opcional)."},
        "meta_title":       {"type": "string", "description": "Meta title SEO."},
        "meta_description": {"type": "string", "description": "Meta description SEO."},
    }},
)


@register_tool(CATALOG_CATEGORY_CREATE_DRAFT_METADATA)
async def catalog_category_create_draft_tool(ctx: ToolContext, name: str, **kwargs) -> dict:
    return await django_internal_post(
        ctx.token, "/catalog/categories/create-draft/", body={"name": name, **kwargs},
        timeout_ms=CATALOG_CATEGORY_CREATE_DRAFT_METADATA.timeout_ms,
    )


CATALOG_CATEGORY_UPDATE_METADATA = ToolMetadata(
    name="CatalogCategoryUpdateTool",
    description="Actualiza nombre, descripcion, categoria padre o SEO de una categoria existente. Nunca publica ni despublica.",
    owner="shop", capabilities=["editar_categoria"], permissions=["IsAdminUser"], risk="medium",
    audit_level="full", side_effects=True,
    args_schema={"type": "object", "required": ["uuid"], "properties": {
        "uuid":             {"type": "string", "description": "UUID de la categoria."},
        "name":             {"type": "string", "description": "Nuevo nombre."},
        "description":      {"type": "string", "description": "Nueva descripcion."},
        "parent":           {"type": "string", "description": "UUID de la nueva categoria padre."},
        "meta_title":       {"type": "string", "description": "Nuevo meta title SEO."},
        "meta_description": {"type": "string", "description": "Nuevo meta description SEO."},
    }},
)


@register_tool(CATALOG_CATEGORY_UPDATE_METADATA)
async def catalog_category_update_tool(ctx: ToolContext, uuid: str, **kwargs) -> dict:
    return await django_internal_post(
        ctx.token, "/catalog/categories/update/", body={"uuid": uuid, **kwargs},
        timeout_ms=CATALOG_CATEGORY_UPDATE_METADATA.timeout_ms,
    )


CATALOG_CATEGORY_SET_PUBLISHED_STATE_METADATA = ToolMetadata(
    name="CatalogCategorySetPublishedStateTool",
    description="Publica o despublica una categoria existente. Requiere confirmacion explicita del administrador.",
    owner="shop", capabilities=["publicar_categoria"], permissions=["IsAdminUser"], risk="high",
    audit_level="full", requires_confirmation=True, side_effects=True,
    args_schema={"type": "object", "required": ["uuid", "is_active"], "properties": {
        "uuid":      {"type": "string", "description": "UUID de la categoria."},
        "is_active": {"type": "boolean", "description": "true para publicar, false para despublicar."},
    }},
)


@register_tool(CATALOG_CATEGORY_SET_PUBLISHED_STATE_METADATA)
async def catalog_category_set_published_state_tool(ctx: ToolContext, uuid: str, is_active: bool) -> dict:
    return await django_internal_post(
        ctx.token, "/catalog/categories/set-published-state/", body={"uuid": uuid, "is_active": is_active},
        timeout_ms=CATALOG_CATEGORY_SET_PUBLISHED_STATE_METADATA.timeout_ms,
    )


# ─── Brand (mismo patron, sin parent/meta) ──────────────────────────────────

CATALOG_BRAND_LIST_METADATA = ToolMetadata(
    name="CatalogBrandListTool", description="Lista marcas del catalogo (admin), con busqueda opcional.",
    owner="shop", capabilities=["listar_marcas"], permissions=["IsAdminUser"], risk="low", audit_level="none",
    args_schema={"type": "object", "properties": {
        "search": {"type": "string", "description": "Texto a buscar en el nombre."},
        "limit":  {"type": "integer", "description": "Maximo de resultados (por defecto 20, tope 50)."},
    }},
)


@register_tool(CATALOG_BRAND_LIST_METADATA)
async def catalog_brand_list_tool(ctx: ToolContext, **kwargs) -> dict:
    params = {k: v for k, v in kwargs.items() if v is not None}
    return await django_internal_get(ctx.token, "/catalog/brands/", params=params, timeout_ms=CATALOG_BRAND_LIST_METADATA.timeout_ms)


CATALOG_BRAND_GET_METADATA = ToolMetadata(
    name="CatalogBrandGetTool", description="Obtiene el detalle de una marca por su UUID.",
    owner="shop", capabilities=["ver_marca"], permissions=["IsAdminUser"], risk="low", audit_level="none",
    args_schema={"type": "object", "required": ["uuid"], "properties": {"uuid": {"type": "string", "description": "UUID de la marca."}}},
)


@register_tool(CATALOG_BRAND_GET_METADATA)
async def catalog_brand_get_tool(ctx: ToolContext, uuid: str) -> dict:
    return await django_internal_get(ctx.token, "/catalog/brands/get/", params={"uuid": uuid}, timeout_ms=CATALOG_BRAND_GET_METADATA.timeout_ms)


CATALOG_BRAND_CREATE_DRAFT_METADATA = ToolMetadata(
    name="CatalogBrandCreateDraftTool",
    description="Crea una marca NUEVA como borrador (sin publicar). Nunca publica.",
    owner="shop", capabilities=["crear_borrador_marca"], permissions=["IsAdminUser"], risk="medium",
    audit_level="full", side_effects=True,
    args_schema={"type": "object", "required": ["name"], "properties": {"name": {"type": "string", "description": "Nombre de la marca."}}},
)


@register_tool(CATALOG_BRAND_CREATE_DRAFT_METADATA)
async def catalog_brand_create_draft_tool(ctx: ToolContext, name: str) -> dict:
    return await django_internal_post(ctx.token, "/catalog/brands/create-draft/", body={"name": name}, timeout_ms=CATALOG_BRAND_CREATE_DRAFT_METADATA.timeout_ms)


CATALOG_BRAND_UPDATE_METADATA = ToolMetadata(
    name="CatalogBrandUpdateTool", description="Actualiza el nombre de una marca existente. Nunca publica ni despublica.",
    owner="shop", capabilities=["editar_marca"], permissions=["IsAdminUser"], risk="medium",
    audit_level="full", side_effects=True,
    args_schema={"type": "object", "required": ["uuid", "name"], "properties": {
        "uuid": {"type": "string", "description": "UUID de la marca."},
        "name": {"type": "string", "description": "Nuevo nombre."},
    }},
)


@register_tool(CATALOG_BRAND_UPDATE_METADATA)
async def catalog_brand_update_tool(ctx: ToolContext, uuid: str, name: str) -> dict:
    return await django_internal_post(ctx.token, "/catalog/brands/update/", body={"uuid": uuid, "name": name}, timeout_ms=CATALOG_BRAND_UPDATE_METADATA.timeout_ms)


CATALOG_BRAND_SET_PUBLISHED_STATE_METADATA = ToolMetadata(
    name="CatalogBrandSetPublishedStateTool",
    description="Publica o despublica una marca existente. Requiere confirmacion explicita del administrador.",
    owner="shop", capabilities=["publicar_marca"], permissions=["IsAdminUser"], risk="high",
    audit_level="full", requires_confirmation=True, side_effects=True,
    args_schema={"type": "object", "required": ["uuid", "is_active"], "properties": {
        "uuid":      {"type": "string", "description": "UUID de la marca."},
        "is_active": {"type": "boolean", "description": "true para publicar, false para despublicar."},
    }},
)


@register_tool(CATALOG_BRAND_SET_PUBLISHED_STATE_METADATA)
async def catalog_brand_set_published_state_tool(ctx: ToolContext, uuid: str, is_active: bool) -> dict:
    return await django_internal_post(
        ctx.token, "/catalog/brands/set-published-state/", body={"uuid": uuid, "is_active": is_active},
        timeout_ms=CATALOG_BRAND_SET_PUBLISHED_STATE_METADATA.timeout_ms,
    )


# ─── Tax (Decision 3, Fase 1: sin borrador, update es Nivel 3 con HITL) ────

CATALOG_TAX_LIST_METADATA = ToolMetadata(
    name="CatalogTaxListTool", description="Lista los impuestos configurados en el catalogo.",
    owner="shop", capabilities=["listar_impuestos"], permissions=["IsAdminUser"], risk="low", audit_level="none",
    args_schema={"type": "object", "properties": {}},
)


@register_tool(CATALOG_TAX_LIST_METADATA)
async def catalog_tax_list_tool(ctx: ToolContext) -> dict:
    return await django_internal_get(ctx.token, "/catalog/taxes/", timeout_ms=CATALOG_TAX_LIST_METADATA.timeout_ms)


CATALOG_TAX_GET_METADATA = ToolMetadata(
    name="CatalogTaxGetTool", description="Obtiene el detalle de un impuesto por su UUID.",
    owner="shop", capabilities=["ver_impuesto"], permissions=["IsAdminUser"], risk="low", audit_level="none",
    args_schema={"type": "object", "required": ["uuid"], "properties": {"uuid": {"type": "string", "description": "UUID del impuesto."}}},
)


@register_tool(CATALOG_TAX_GET_METADATA)
async def catalog_tax_get_tool(ctx: ToolContext, uuid: str) -> dict:
    return await django_internal_get(ctx.token, "/catalog/taxes/get/", params={"uuid": uuid}, timeout_ms=CATALOG_TAX_GET_METADATA.timeout_ms)


CATALOG_TAX_CREATE_METADATA = ToolMetadata(
    name="CatalogTaxCreateTool",
    description=(
        "Crea un impuesto NUEVO, activo de inmediato -- un impuesto no tiene estado de "
        "borrador (o existe con un valor correcto, o no existe). Requiere confirmacion "
        "explicita del administrador porque queda disponible de inmediato para asignarse "
        "a productos."
    ),
    owner="shop", capabilities=["crear_impuesto"], permissions=["IsAdminUser"], risk="high",
    audit_level="full", requires_confirmation=True, side_effects=True,
    args_schema={"type": "object", "required": ["name", "tax_type", "value"], "properties": {
        "name":     {"type": "string", "description": "Nombre del impuesto (ej. IVA)."},
        "tax_type": {"type": "string", "description": "Tipo de impuesto."},
        "value":    {"type": "number", "description": "Valor/porcentaje del impuesto."},
    }},
)


@register_tool(CATALOG_TAX_CREATE_METADATA)
async def catalog_tax_create_tool(ctx: ToolContext, name: str, tax_type: str, value) -> dict:
    return await django_internal_post(
        ctx.token, "/catalog/taxes/create/", body={"name": name, "tax_type": tax_type, "value": value},
        timeout_ms=CATALOG_TAX_CREATE_METADATA.timeout_ms,
    )


CATALOG_TAX_UPDATE_METADATA = ToolMetadata(
    name="CatalogTaxUpdateTool",
    description=(
        "Actualiza un impuesto EXISTENTE (nombre, tipo, valor o si esta activo). Cambiar "
        "el valor recalcula el precio final de TODO el catalogo asociado de forma "
        "retroactiva e inmediata -- requiere confirmacion explicita del administrador."
    ),
    owner="shop", capabilities=["editar_impuesto"], permissions=["IsAdminUser"], risk="high",
    audit_level="full", requires_confirmation=True, side_effects=True,
    args_schema={"type": "object", "required": ["uuid"], "properties": {
        "uuid":      {"type": "string",  "description": "UUID del impuesto."},
        "name":      {"type": "string",  "description": "Nuevo nombre."},
        "tax_type":  {"type": "string",  "description": "Nuevo tipo."},
        "value":     {"type": "number",  "description": "Nuevo valor/porcentaje."},
        "is_active": {"type": "boolean", "description": "Activar o desactivar el impuesto."},
    }},
)


@register_tool(CATALOG_TAX_UPDATE_METADATA)
async def catalog_tax_update_tool(ctx: ToolContext, uuid: str, **kwargs) -> dict:
    return await django_internal_post(
        ctx.token, "/catalog/taxes/update/", body={"uuid": uuid, **kwargs},
        timeout_ms=CATALOG_TAX_UPDATE_METADATA.timeout_ms,
    )
