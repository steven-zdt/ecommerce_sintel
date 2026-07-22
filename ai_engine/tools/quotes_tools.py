"""Tools del dominio quotes (Fase 4 AI Core): wizard de cotizacion en dos pasos."""
from tools.http_bridge import django_internal_get, django_internal_post
from tools.metadata import ToolContext, ToolMetadata
from tools.registry import register_tool

QUOTE_TEMPLATES_METADATA = ToolMetadata(
    name="QuoteTemplatesTool",
    description="Lista las plantillas activas de cuestionario de cotizacion (paso 1 del wizard).",
    owner="quotes",
    capabilities=["consultar_plantillas_cotizacion"],
    permissions=["IsAuthenticatedActiveUser"],
    risk="low",
    audit_level="none",
    args_schema={"type": "object", "properties": {}},
)

START_QUOTATION_METADATA = ToolMetadata(
    name="StartQuotationTool",
    description=(
        "Crea una solicitud de cotizacion a partir de una plantilla (sin precios -- un asesor "
        "comercial cotiza despues). Requiere plantilla, nombre, email y documento del solicitante."
    ),
    owner="quotes",
    capabilities=["iniciar_cotizacion"],
    permissions=["IsAuthenticatedActiveUser"],
    risk="medium",
    audit_level="full",
    rate_limit="5/hour/user",
    requires_confirmation=True,
    side_effects=True,
    args_schema={
        "type": "object",
        "properties": {
            "template": {"type": "string", "description": "UUID de la plantilla (ver consultar_plantillas_cotizacion)"},
            "client_name": {"type": "string", "description": "Nombre completo del solicitante"},
            "client_email": {"type": "string", "description": "Email del solicitante"},
            "document_type": {"type": "string", "enum": ["CC", "NIT"], "description": "Tipo de documento"},
            "document_number": {"type": "string", "description": "Numero de documento"},
            "phone": {"type": "string", "description": "Telefono (opcional)"},
            "notes": {"type": "string", "description": "Descripcion libre del requerimiento (opcional)"},
        },
        "required": ["template", "client_name", "client_email", "document_type", "document_number"],
    },
)


@register_tool(QUOTE_TEMPLATES_METADATA)
async def quote_templates_tool(ctx: ToolContext) -> dict:
    """Envuelve QuoteTemplateSelector.list_active()."""
    return await django_internal_get(
        ctx.token, "/quotes/templates/", timeout_ms=QUOTE_TEMPLATES_METADATA.timeout_ms,
    )


@register_tool(START_QUOTATION_METADATA)
async def start_quotation_tool(ctx: ToolContext, **args) -> dict:
    """Envuelve QuotationBuilder.create_from_template() (validacion del cuestionario publico)."""
    return await django_internal_post(
        ctx.token, "/quotes/create/", args, timeout_ms=START_QUOTATION_METADATA.timeout_ms,
    )
