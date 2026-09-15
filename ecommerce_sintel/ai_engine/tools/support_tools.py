"""
Tools del dominio support (Fase 4 AI Core).

OpenSupportTicketTool es ademas la resolucion del gap #1 (decision del
usuario, 2026-07-16): cambiar fechas de un alquiler NO es self-service --
el Action Graph escala esos casos aqui, adjuntando el alquiler como
contexto para el operador humano.
"""
from tools.http_bridge import django_internal_post
from tools.metadata import ToolContext, ToolMetadata
from tools.registry import register_tool

OPEN_SUPPORT_TICKET_METADATA = ToolMetadata(
    name="OpenSupportTicketTool",
    description=(
        "Abre (o reusa) la sala de soporte del cliente y deja un mensaje para un agente "
        "humano. Usar para reclamos, casos que el asistente no puede resolver, y cambios "
        "de fechas de alquiler (que requieren un humano). Puede adjuntar el pedido o "
        "alquiler relacionado."
    ),
    owner="support",
    capabilities=["abrir_ticket_soporte"],
    permissions=["IsAuthenticatedActiveUser"],
    risk="low",
    audit_level="full",
    rate_limit="10/hour/user",
    requires_confirmation=False,   # no destructivo -- pero se avisa que atendera un humano
    side_effects=True,
    args_schema={
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Resumen del caso para el agente humano"},
            "subject": {"type": "string", "description": "Asunto corto del caso (maximo ~10 palabras), para que el operador humano lo identifique de un vistazo en la cola de tickets."},
            "summary": {"type": "string", "description": "Resumen breve y objetivo del caso para el operador humano -- solo lo que el cliente reporto, nunca inventar datos que el cliente no dio."},
            "order_uuid": {"type": "string", "description": "UUID del pedido relacionado (opcional)"},
            "rental_uuid": {"type": "string", "description": "UUID del alquiler relacionado (opcional)"},
        },
        "required": ["message"],
    },
)


@register_tool(OPEN_SUPPORT_TICKET_METADATA)
async def open_support_ticket_tool(ctx: ToolContext, message: str,
                                   subject: str | None = None,
                                   summary: str | None = None,
                                   order_uuid: str | None = None,
                                   rental_uuid: str | None = None,
                                   history: list | None = None) -> dict:
    """
    Envuelve ChatCommands.get_or_create_room + save_message + attach_context +
    SupportTicketCommands.create_ticket (subject/summary opcionales, 2026-09-15).
    `history` NO esta en el args_schema: lo inyecta execute_write desde el
    estado del grafo (Human Handoff, Fase 7) -- el LLM jamas lo controla.
    """
    body: dict = {"message": message}
    if subject:
        body["subject"] = subject
    if summary:
        body["summary"] = summary
    if order_uuid:
        body["order_uuid"] = order_uuid
    if rental_uuid:
        body["rental_uuid"] = rental_uuid
    if history:
        body["history"] = history
    return await django_internal_post(
        ctx.token, "/support/ticket/", body, timeout_ms=OPEN_SUPPORT_TICKET_METADATA.timeout_ms,
    )
