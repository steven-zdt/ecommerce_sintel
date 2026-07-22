"""
Tools de Core Content del AI Core (Fase 8).

Permiten al Admin Agent leer y actualizar la configuracion del sitio
(Home Builder, Navbar, Footer, Brand Slider) a traves de los Commands/
Selectors ya existentes en core/services/selectors.py — nunca acceso
directo al ORM, siempre via los endpoints internos de Django.

Restriccion dura: el AI Core nunca escribe Vue/JS ni accede al frontend;
solo invoca Commands ya existentes (Componente 15 del plan).

Todas las Tools de escritura tienen:
  - side_effects=True  -> pasan por Policy Layer siempre
  - requires_confirmation=True -> el usuario admin confirma antes de ejecutar
  - risk="high"
  - permissions=["IsAdminUser"]
"""
from tools.http_bridge import django_internal_get, django_internal_post
from tools.metadata import ToolContext, ToolMetadata
from tools.registry import register_tool

# ─── Lectura ─────────────────────────────────────────────────────────────────

CORE_HOME_METADATA = ToolMetadata(
    name="CoreHomeTool",
    description="Lista los banners y modulos de configuracion de la pagina de inicio (admin).",
    owner="core",
    capabilities=["ver_config_home"],
    permissions=["IsAdminUser"],
    risk="low",
    audit_level="none",
    args_schema={"type": "object", "properties": {}},
)


@register_tool(CORE_HOME_METADATA)
async def core_home_tool(ctx: ToolContext) -> dict:
    """Envuelve HomeConfigSelector.list_banners_for_admin() + list_module_configs()."""
    return await django_internal_get(
        ctx.token, "/core/home/",
        timeout_ms=CORE_HOME_METADATA.timeout_ms,
    )


CORE_NAVBAR_METADATA = ToolMetadata(
    name="CoreNavbarTool",
    description="Lista los enlaces de la barra de navegacion del sitio (admin).",
    owner="core",
    capabilities=["ver_navbar"],
    permissions=["IsAdminUser"],
    risk="low",
    audit_level="none",
    args_schema={"type": "object", "properties": {}},
)


@register_tool(CORE_NAVBAR_METADATA)
async def core_navbar_tool(ctx: ToolContext) -> dict:
    """Envuelve NavbarLinkSelector.list_all()."""
    return await django_internal_get(
        ctx.token, "/core/navbar/",
        timeout_ms=CORE_NAVBAR_METADATA.timeout_ms,
    )


CORE_FOOTER_METADATA = ToolMetadata(
    name="CoreFooterTool",
    description="Lista los grupos y enlaces del footer del sitio (admin).",
    owner="core",
    capabilities=["ver_footer"],
    permissions=["IsAdminUser"],
    risk="low",
    audit_level="none",
    args_schema={"type": "object", "properties": {}},
)


@register_tool(CORE_FOOTER_METADATA)
async def core_footer_tool(ctx: ToolContext) -> dict:
    """Envuelve FooterGroupSelector.list_all() + FooterSelector.list_all_links()."""
    return await django_internal_get(
        ctx.token, "/core/footer/",
        timeout_ms=CORE_FOOTER_METADATA.timeout_ms,
    )


CORE_BRAND_SLIDER_METADATA = ToolMetadata(
    name="CoreBrandSliderTool",
    description="Lista los items del slider de marcas del sitio (admin).",
    owner="core",
    capabilities=["ver_brand_slider"],
    permissions=["IsAdminUser"],
    risk="low",
    audit_level="none",
    args_schema={"type": "object", "properties": {}},
)


@register_tool(CORE_BRAND_SLIDER_METADATA)
async def core_brand_slider_tool(ctx: ToolContext) -> dict:
    """Envuelve BrandSliderSelector.list_items_for_admin() + get_config()."""
    return await django_internal_get(
        ctx.token, "/core/brand-slider/",
        timeout_ms=CORE_BRAND_SLIDER_METADATA.timeout_ms,
    )


# ─── Escritura ───────────────────────────────────────────────────────────────

CORE_BANNER_UPDATE_METADATA = ToolMetadata(
    name="CoreBannerUpdateTool",
    description="Actualiza titulo, subtitulo, enlace o visibilidad de un banner del home. No sube imagenes.",
    owner="core",
    capabilities=["editar_banner"],
    permissions=["IsAdminUser"],
    risk="high",
    audit_level="full",
    requires_confirmation=True,
    side_effects=True,
    args_schema={
        "type": "object",
        "required": ["uuid"],
        "properties": {
            "uuid":          {"type": "string", "description": "UUID del banner a actualizar."},
            "title":         {"type": "string", "description": "Nuevo titulo del banner."},
            "subtitle":      {"type": "string", "description": "Nuevo subtitulo."},
            "link_url":      {"type": "string", "description": "URL del enlace del banner."},
            "link_label":    {"type": "string", "description": "Texto del boton de enlace."},
            "display_order": {"type": "integer", "description": "Orden de visualizacion (0 = primero)."},
            "is_active":     {"type": "boolean", "description": "true para mostrar el banner, false para ocultarlo."},
        },
    },
)


@register_tool(CORE_BANNER_UPDATE_METADATA)
async def core_banner_update_tool(ctx: ToolContext, uuid: str, **kwargs) -> dict:
    """Envuelve HomeConfigCommands.update_banner()."""
    body = {"uuid": uuid, **{k: v for k, v in kwargs.items() if v is not None}}
    return await django_internal_post(
        ctx.token, "/core/banners/update/", body,
        timeout_ms=CORE_BANNER_UPDATE_METADATA.timeout_ms,
    )


CORE_BANNER_CREATE_METADATA = ToolMetadata(
    name="CoreBannerCreateTool",
    description="Crea un nuevo banner de texto en el home. Para agregar imagen, el administrador debe hacerlo desde el panel.",
    owner="core",
    capabilities=["crear_banner"],
    permissions=["IsAdminUser"],
    risk="high",
    audit_level="full",
    requires_confirmation=True,
    side_effects=True,
    args_schema={
        "type": "object",
        "required": ["title"],
        "properties": {
            "title":         {"type": "string", "description": "Titulo del banner (requerido)."},
            "subtitle":      {"type": "string", "description": "Subtitulo opcional."},
            "link_url":      {"type": "string", "description": "URL de destino del boton."},
            "link_label":    {"type": "string", "description": "Texto del boton."},
            "display_order": {"type": "integer", "description": "Orden de visualizacion."},
        },
    },
)


@register_tool(CORE_BANNER_CREATE_METADATA)
async def core_banner_create_tool(ctx: ToolContext, title: str, **kwargs) -> dict:
    """Envuelve HomeConfigCommands.create_banner()."""
    body = {"title": title, **{k: v for k, v in kwargs.items() if v is not None}}
    return await django_internal_post(
        ctx.token, "/core/banners/create/", body,
        timeout_ms=CORE_BANNER_CREATE_METADATA.timeout_ms,
    )


CORE_NAVBAR_UPDATE_METADATA = ToolMetadata(
    name="CoreNavbarLinkUpdateTool",
    description="Actualiza un enlace de la barra de navegacion (label, url, visibilidad, orden).",
    owner="core",
    capabilities=["editar_navbar"],
    permissions=["IsAdminUser"],
    risk="high",
    audit_level="full",
    requires_confirmation=True,
    side_effects=True,
    args_schema={
        "type": "object",
        "required": ["uuid"],
        "properties": {
            "uuid":            {"type": "string", "description": "UUID del enlace a actualizar."},
            "label":           {"type": "string", "description": "Texto visible del enlace."},
            "url":             {"type": "string", "description": "URL de destino."},
            "icon_class":      {"type": "string", "description": "Clase de icono Bootstrap Icons (ej. bi-house)."},
            "display_order":   {"type": "integer", "description": "Orden de visualizacion."},
            "is_visible":      {"type": "boolean", "description": "true para mostrarlo en el menu."},
            "open_in_new_tab": {"type": "boolean", "description": "true para abrir en una pestana nueva."},
        },
    },
)


@register_tool(CORE_NAVBAR_UPDATE_METADATA)
async def core_navbar_link_update_tool(ctx: ToolContext, uuid: str, **kwargs) -> dict:
    """Envuelve NavbarLinkCommands.update()."""
    body = {"uuid": uuid, **{k: v for k, v in kwargs.items() if v is not None}}
    return await django_internal_post(
        ctx.token, "/core/navbar/update/", body,
        timeout_ms=CORE_NAVBAR_UPDATE_METADATA.timeout_ms,
    )


CORE_NAVBAR_CREATE_METADATA = ToolMetadata(
    name="CoreNavbarLinkCreateTool",
    description="Crea un nuevo enlace en la barra de navegacion del sitio.",
    owner="core",
    capabilities=["crear_navbar_link"],
    permissions=["IsAdminUser"],
    risk="high",
    audit_level="full",
    requires_confirmation=True,
    side_effects=True,
    args_schema={
        "type": "object",
        "required": ["label", "url"],
        "properties": {
            "label":           {"type": "string", "description": "Texto visible del enlace (requerido)."},
            "url":             {"type": "string", "description": "URL de destino (requerido)."},
            "icon_class":      {"type": "string", "description": "Clase de icono Bootstrap Icons."},
            "display_order":   {"type": "integer", "description": "Orden de visualizacion."},
            "is_visible":      {"type": "boolean", "description": "Mostrar inmediatamente (default true)."},
            "open_in_new_tab": {"type": "boolean", "description": "Abrir en pestana nueva (default false)."},
        },
    },
)


@register_tool(CORE_NAVBAR_CREATE_METADATA)
async def core_navbar_link_create_tool(ctx: ToolContext, label: str, url: str, **kwargs) -> dict:
    """Envuelve NavbarLinkCommands.create()."""
    body = {"label": label, "url": url, **{k: v for k, v in kwargs.items() if v is not None}}
    return await django_internal_post(
        ctx.token, "/core/navbar/create/", body,
        timeout_ms=CORE_NAVBAR_CREATE_METADATA.timeout_ms,
    )


CORE_BRAND_SLIDER_UPDATE_METADATA = ToolMetadata(
    name="CoreBrandSliderUpdateTool",
    description="Actualiza nombre, sitio web, orden o visibilidad de un item del slider de marcas.",
    owner="core",
    capabilities=["editar_brand_slider"],
    permissions=["IsAdminUser"],
    risk="high",
    audit_level="full",
    requires_confirmation=True,
    side_effects=True,
    args_schema={
        "type": "object",
        "required": ["uuid"],
        "properties": {
            "uuid":          {"type": "string", "description": "UUID del item a actualizar."},
            "name":          {"type": "string", "description": "Nombre de la marca."},
            "website":       {"type": "string", "description": "URL del sitio web de la marca."},
            "display_order": {"type": "integer", "description": "Orden de visualizacion."},
            "is_active":     {"type": "boolean", "description": "true para mostrar la marca en el slider."},
            "open_new_tab":  {"type": "boolean", "description": "Abrir el sitio en pestana nueva."},
        },
    },
)


@register_tool(CORE_BRAND_SLIDER_UPDATE_METADATA)
async def core_brand_slider_update_tool(ctx: ToolContext, uuid: str, **kwargs) -> dict:
    """Envuelve BrandSliderCommands.update_item()."""
    body = {"uuid": uuid, **{k: v for k, v in kwargs.items() if v is not None}}
    return await django_internal_post(
        ctx.token, "/core/brand-slider/update/", body,
        timeout_ms=CORE_BRAND_SLIDER_UPDATE_METADATA.timeout_ms,
    )
