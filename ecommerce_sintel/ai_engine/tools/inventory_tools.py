"""Tools de solo lectura del dominio inventory (Fase 2 AI Core)."""
from tools.http_bridge import django_internal_get
from tools.metadata import ToolContext, ToolMetadata
from tools.registry import register_tool

STOCK_CHECK_METADATA = ToolMetadata(
    name="StockCheckTool",
    description="Consulta el stock actual de una variante (producto, equipo o servicio) por uuid.",
    owner="inventory",
    capabilities=["consultar_stock"],
    permissions=["IsAuthenticatedActiveUser"],
    risk="low",
    audit_level="none",
    args_schema={
        "type": "object",
        "properties": {
            "variant": {"type": "string", "description": "UUID de la variante"},
            "type": {"type": "string", "enum": ["product", "equipment", "service"],
                     "description": "Tipo de variante (default product)"},
        },
        "required": ["variant"],
    },
)


@register_tool(STOCK_CHECK_METADATA)
async def stock_check_tool(ctx: ToolContext, variant: str, type: str = "product") -> dict:
    """Envuelve InventorySelector.get_stock_for_variant() (kardex, no el campo legacy)."""
    return await django_internal_get(
        ctx.token,
        "/inventory/stock/",
        {"variant": variant, "type": type},
        timeout_ms=STOCK_CHECK_METADATA.timeout_ms,
    )
