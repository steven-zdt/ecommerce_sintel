"""Tools de solo lectura del dominio payment (Fase 2 AI Core)."""
from tools.http_bridge import django_internal_get
from tools.metadata import ToolContext, ToolMetadata
from tools.registry import register_tool

PAYMENT_STATUS_METADATA = ToolMetadata(
    name="PaymentStatusTool",
    description=(
        "Consulta el estado de los pagos del cliente autenticado (todos o uno por uuid de "
        "transaccion). Devuelve solo status/status_label -- NO el motivo de un rechazo "
        "(gap #2 del plan, decision pendiente del usuario)."
    ),
    owner="payment",
    capabilities=["consultar_pago"],
    permissions=["IsAuthenticatedActiveUser"],
    risk="low",
    audit_level="summary",
    args_schema={
        "type": "object",
        "properties": {
            "tx": {"type": "string", "description": "UUID de una transaccion especifica (opcional)"},
            "limit": {"type": "integer", "description": "Cuantas transacciones recientes listar (default 5)"},
        },
    },
)


@register_tool(PAYMENT_STATUS_METADATA)
async def payment_status_tool(ctx: ToolContext, tx: str | None = None, limit: int = 5) -> dict:
    """Reusa la query owner-safe de transaction_status SIN el sync a Wompi (sin side-effects)."""
    params: dict = {"limit": limit}
    if tx:
        params = {"tx": tx}
    return await django_internal_get(
        ctx.token, "/payments/", params, timeout_ms=PAYMENT_STATUS_METADATA.timeout_ms,
    )
