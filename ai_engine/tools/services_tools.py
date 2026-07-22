"""Tools de solo lectura del dominio technical_services (Fase 2 AI Core)."""
from tools.http_bridge import django_internal_get
from tools.metadata import ToolContext, ToolMetadata
from tools.registry import register_tool

SERVICE_STATUS_METADATA = ToolMetadata(
    name="ServiceStatusTool",
    description=(
        "Consulta el estado operativo de los servicios tecnicos del cliente autenticado "
        "(tecnico asignado, fecha programada, avance)."
    ),
    owner="technical_services",
    capabilities=["consultar_servicio"],
    permissions=["IsAuthenticatedActiveUser"],
    risk="low",
    audit_level="summary",
    args_schema={
        "type": "object",
        "properties": {
            "order": {"type": "string", "description": "UUID de la orden asociada (opcional)"},
            "limit": {"type": "integer", "description": "Cuantas operaciones recientes listar (default 5)"},
        },
    },
)


@register_tool(SERVICE_STATUS_METADATA)
async def service_status_tool(ctx: ToolContext, order: str | None = None, limit: int = 5) -> dict:
    """
    Envuelve ServiceOperationSelector + owner-check manual en Django (gap #4:
    el selector no filtra por dueno; el endpoint interno agrega order__user).
    """
    params: dict = {"limit": limit}
    if order:
        params = {"order": order}
    return await django_internal_get(
        ctx.token, "/services/", params, timeout_ms=SERVICE_STATUS_METADATA.timeout_ms,
    )
