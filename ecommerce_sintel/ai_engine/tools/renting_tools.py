"""Tools del dominio renting (Fase 2: lectura; Fase 4: escritura con confirmacion; Fase 8: mantenimiento)."""
from tools.http_bridge import django_internal_get, django_internal_post
from tools.metadata import ToolContext, ToolMetadata
from tools.registry import register_tool

RENTAL_STATUS_METADATA = ToolMetadata(
    name="RentalStatusTool",
    description="Consulta las solicitudes de alquiler del cliente autenticado (todas o una por uuid).",
    owner="renting",
    capabilities=["buscar_alquiler"],
    permissions=["IsAuthenticatedActiveUser"],
    risk="low",
    audit_level="summary",
    args_schema={
        "type": "object",
        "properties": {
            "uuid": {"type": "string", "description": "UUID de una solicitud especifica (opcional)"},
            "limit": {"type": "integer", "description": "Cuantas solicitudes recientes listar (default 5)"},
        },
    },
)

RENTAL_AVAILABILITY_METADATA = ToolMetadata(
    name="RentalAvailabilityTool",
    description="Verifica disponibilidad de una variante de equipo para un rango de fechas (modo dias).",
    owner="renting",
    capabilities=["verificar_disponibilidad"],
    permissions=["IsAuthenticatedActiveUser"],
    risk="low",
    audit_level="none",
    args_schema={
        "type": "object",
        "properties": {
            "variant": {"type": "string", "description": "UUID de la variante de equipo"},
            "start": {"type": "string", "description": "Fecha inicio YYYY-MM-DD"},
            "end": {"type": "string", "description": "Fecha fin YYYY-MM-DD"},
            "quantity": {"type": "integer", "description": "Unidades requeridas (default 1)"},
        },
        "required": ["variant", "start", "end"],
    },
)

EQUIPMENT_SEARCH_METADATA = ToolMetadata(
    name="EquipmentSearchTool",
    description="Busca equipos de alquiler disponibles (con variantes y precios), opcionalmente por nombre.",
    owner="renting",
    capabilities=["buscar_equipos"],
    permissions=["IsAuthenticatedActiveUser"],
    risk="low",
    audit_level="none",
    args_schema={
        "type": "object",
        "properties": {
            "q": {"type": "string", "description": "Texto a buscar en el nombre del equipo (opcional)"},
            "limit": {"type": "integer", "description": "Maximo de equipos (default 10)"},
        },
    },
)


@register_tool(RENTAL_STATUS_METADATA)
async def rental_status_tool(ctx: ToolContext, uuid: str | None = None, limit: int = 5) -> dict:
    """Envuelve RentalRequestSelector.list_for_user()/get_by_uuid_for_user() (owner-check incluido)."""
    params: dict = {"limit": limit}
    if uuid:
        params = {"uuid": uuid}
    return await django_internal_get(
        ctx.token, "/rentals/", params, timeout_ms=RENTAL_STATUS_METADATA.timeout_ms,
    )


@register_tool(RENTAL_AVAILABILITY_METADATA)
async def rental_availability_tool(ctx: ToolContext, variant: str, start: str, end: str,
                                   quantity: int = 1) -> dict:
    """Envuelve RentingSelector.check_availability() (wrapper de AvailabilityEngine)."""
    return await django_internal_get(
        ctx.token,
        "/renting/availability/",
        {"variant": variant, "start": start, "end": end, "quantity": quantity},
        timeout_ms=RENTAL_AVAILABILITY_METADATA.timeout_ms,
    )


@register_tool(EQUIPMENT_SEARCH_METADATA)
async def equipment_search_tool(ctx: ToolContext, q: str | None = None, limit: int = 10) -> dict:
    """Envuelve RentingSelector.list_available_equipment()."""
    params: dict = {"limit": limit}
    if q:
        params["q"] = q
    return await django_internal_get(
        ctx.token, "/renting/equipment/", params, timeout_ms=EQUIPMENT_SEARCH_METADATA.timeout_ms,
    )


# ─── Fase 4: escritura (Policy Layer + confirmacion obligatoria) ─────────────

CREATE_RENTAL_METADATA = ToolMetadata(
    name="CreateRentalRequestTool",
    description=(
        "Crea una solicitud de alquiler (queda pendiente de pago, no bloquea agenda). "
        "Requiere variante, fechas, ubicacion del proyecto y datos de contacto."
    ),
    owner="renting",
    capabilities=["crear_alquiler"],
    permissions=["IsBuyerOrAdmin"],
    risk="medium",
    audit_level="full",
    rate_limit="10/hour/user",
    requires_confirmation=True,
    side_effects=True,
    timeout_ms=12000,
    args_schema={
        "type": "object",
        "properties": {
            "equipment_variant": {"type": "string", "description": "UUID de la variante de equipo"},
            "start_date": {"type": "string", "description": "Fecha inicio YYYY-MM-DD"},
            "end_date": {"type": "string", "description": "Fecha fin YYYY-MM-DD"},
            "quantity": {"type": "integer", "description": "Unidades (default 1)"},
            "location_address": {"type": "string", "description": "Direccion del proyecto"},
            "location_city": {"type": "string", "description": "Ciudad"},
            "location_department": {"type": "string", "description": "Departamento"},
            "contact_full_name": {"type": "string", "description": "Nombre completo de contacto"},
            "contact_doc_number": {"type": "string", "description": "Numero de documento"},
            "contact_email": {"type": "string", "description": "Email de contacto"},
            "contact_phone": {"type": "string", "description": "Telefono de contacto"},
        },
        "required": ["equipment_variant", "start_date", "end_date", "location_address",
                     "location_city", "location_department", "contact_full_name",
                     "contact_doc_number", "contact_email", "contact_phone"],
    },
)

CANCEL_RENTAL_METADATA = ToolMetadata(
    name="CancelRentalTool",
    description=(
        "Cancela una solicitud de alquiler del cliente (IRREVERSIBLE). Solo solicitudes "
        "aun no pagadas/aprobadas -- las pagadas se escalan a soporte."
    ),
    owner="renting",
    capabilities=["cancelar_alquiler"],
    permissions=["IsBuyerOrAdmin"],
    risk="high",
    audit_level="full",
    rate_limit="5/hour/user",
    requires_confirmation=True,
    side_effects=True,
    args_schema={
        "type": "object",
        "properties": {
            "uuid": {"type": "string", "description": "UUID de la solicitud de alquiler a cancelar"},
        },
        "required": ["uuid"],
    },
)


@register_tool(CREATE_RENTAL_METADATA)
async def create_rental_request_tool(ctx: ToolContext, **args) -> dict:
    """Envuelve RentalRequestCommands.create_request() via el endpoint interno (validacion del wizard)."""
    return await django_internal_post(
        ctx.token, "/rentals/create/", args, timeout_ms=CREATE_RENTAL_METADATA.timeout_ms,
    )


@register_tool(CANCEL_RENTAL_METADATA)
async def cancel_rental_tool(ctx: ToolContext, uuid: str) -> dict:
    """Envuelve RentalRequestCommands.cancel_request() (guard de estados del ViewSet replicado en Django)."""
    return await django_internal_post(
        ctx.token, "/rentals/cancel/", {"uuid": uuid}, timeout_ms=CANCEL_RENTAL_METADATA.timeout_ms,
    )


# --- Fase 8: mantenimiento preventivo (admin) --------------------------------

MAINTENANCE_CHECK_METADATA = ToolMetadata(
    name="MaintenanceCheckTool",
    description="Lista los bloqueos de mantenimiento activos de un equipo de alquiler (admin). Util para informar sobre equipos fuera de servicio y planificar mantenimiento preventivo.",
    owner="renting",
    capabilities=["verificar_mantenimiento"],
    permissions=["IsAdminUser"],
    risk="low",
    audit_level="none",
    args_schema={
        "type": "object",
        "required": ["equipment_uuid"],
        "properties": {
            "equipment_uuid": {"type": "string", "description": "UUID del equipo a consultar."},
        },
    },
)


@register_tool(MAINTENANCE_CHECK_METADATA)
async def maintenance_check_tool(ctx: ToolContext, equipment_uuid: str) -> dict:
    """Envuelve EquipmentBlockSelector.list_for_equipment(active_only=True)."""
    return await django_internal_get(
        ctx.token, "/renting/maintenance/", {"equipment_uuid": equipment_uuid},
        timeout_ms=MAINTENANCE_CHECK_METADATA.timeout_ms,
    )
