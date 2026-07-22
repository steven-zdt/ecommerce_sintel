"""Tools de solo lectura del dominio orders (Fase 2 AI Core)."""
from tools.http_bridge import django_internal_get
from tools.metadata import ToolContext, ToolMetadata
from tools.registry import register_tool

ORDER_STATUS_METADATA = ToolMetadata(
    name="OrderStatusTool",
    description="Consulta las ordenes de compra del cliente autenticado (todas o una por uuid).",
    owner="orders",
    capabilities=["buscar_pedido"],
    permissions=["IsAuthenticatedActiveUser"],
    risk="low",
    audit_level="summary",
    args_schema={
        "type": "object",
        "properties": {
            "uuid": {"type": "string", "description": "UUID de una orden especifica (opcional)"},
            "limit": {"type": "integer", "description": "Cuantas ordenes recientes listar (default 5)"},
        },
    },
)


@register_tool(ORDER_STATUS_METADATA)
async def order_status_tool(ctx: ToolContext, uuid: str | None = None, limit: int = 5) -> dict:
    """Envuelve OrderSelector.list_for_user()/get_by_uuid() (owner-check manual en Django)."""
    params: dict = {"limit": limit}
    if uuid:
        params = {"uuid": uuid}
    return await django_internal_get(
        ctx.token, "/orders/", params, timeout_ms=ORDER_STATUS_METADATA.timeout_ms,
    )
