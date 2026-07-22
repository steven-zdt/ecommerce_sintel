"""Tools del dominio kyc (Fase 2: lectura; Fase 4: solicitud de upgrade)."""
from tools.http_bridge import django_internal_get, django_internal_post
from tools.metadata import ToolContext, ToolMetadata
from tools.registry import register_tool

KYC_STATUS_METADATA = ToolMetadata(
    name="KycStatusTool",
    description="Consulta el estado de verificacion de identidad (KYC) del cliente autenticado.",
    owner="kyc",
    capabilities=["consultar_kyc"],
    permissions=["IsAuthenticatedActiveUser"],
    risk="low",
    audit_level="summary",
    args_schema={"type": "object", "properties": {}},
)


@register_tool(KYC_STATUS_METADATA)
async def kyc_status_tool(ctx: ToolContext) -> dict:
    """Envuelve KycSelector.get_own_verification() (self-service por diseno)."""
    return await django_internal_get(
        ctx.token, "/kyc/", timeout_ms=KYC_STATUS_METADATA.timeout_ms,
    )


REQUEST_KYC_UPGRADE_METADATA = ToolMetadata(
    name="RequestKycUpgradeTool",
    description=(
        "Solicita el upgrade a perfil profesional (TECHNICIAN/PROFESSIONAL/SPECIALIST/"
        "CONTRACTOR). Reabre la verificacion KYC a PENDING; luego el cliente debe subir "
        "documentos en mi-cuenta/verificacion."
    ),
    owner="kyc",
    capabilities=["solicitar_upgrade_profesional"],
    permissions=["IsAuthenticatedActiveUser"],
    risk="medium",
    audit_level="full",
    rate_limit="3/hour/user",
    requires_confirmation=True,
    side_effects=True,
    args_schema={
        "type": "object",
        "properties": {
            "requested_user_type": {
                "type": "string",
                "enum": ["CONTRACTOR", "PROFESSIONAL", "SPECIALIST", "TECHNICIAN"],
                "description": "Tipo profesional deseado",
            },
        },
        "required": ["requested_user_type"],
    },
)


@register_tool(REQUEST_KYC_UPGRADE_METADATA)
async def request_kyc_upgrade_tool(ctx: ToolContext, requested_user_type: str) -> dict:
    """Envuelve KycCommands.request_upgrade() (misma semantica que auth/request-upgrade/)."""
    return await django_internal_post(
        ctx.token, "/kyc/request-upgrade/", {"requested_user_type": requested_user_type},
        timeout_ms=REQUEST_KYC_UPGRADE_METADATA.timeout_ms,
    )
