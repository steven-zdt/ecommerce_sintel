"""
Clasificacion de una tool MCP como allow / confirm / deny ANTES de ejecutarla.

Espeja la semantica de la Policy Layer del Action Graph
(ai_engine/action_graph.py::node_evaluate_policy): READ -> allow, WRITE ->
confirm, cambios de cuenta/facturacion/pago -> deny. La aprobacion humana real
(interrupt de LangGraph) vive en el Action Graph -- aqui solo se decide si la
llamada siquiera se intenta.

FASE 10: `allow_writes=False` => cualquier tool que no sea claramente de lectura
se deniega. Los writes se habilitan en las FASE 16-18, una por una, con su
capability CONFIRM.
"""

# Prefijos/tokens de nombre de tool que indican LECTURA pura.
_READ_HINTS = (
    "get_", "get-", "list_", "list-", "search_", "search-", "read_", "read-",
    "fetch_", "fetch-", "export_", "export-", "preview_", "describe_", "find_",
    "query_", "summar", "insight", "report", "analyz", "analiz", "status",
    "check_", "inspect_",
)

# Tokens que SIEMPRE se deniegan, aunque `allow_writes` sea True: tocan dinero,
# metodo de pago o la cuenta en si. Nunca via agente.
_DENY_ALWAYS = (
    "billing", "invoice", "payment_method", "paymentmethod", "funding",
    "credit_card", "creditcard", "account_delete", "delete_account",
    "close_account", "spend_cap", "spending_limit", "transfer",
)

# Tokens de ESCRITURA (relevantes cuando allow_writes=True; con allow_writes=False
# no hace falta enumerarlos, cae al else).
_WRITE_HINTS = (
    "create_", "update_", "delete_", "remove_", "pause_", "resume_", "set_",
    "duplicate_", "archive_", "publish_", "upload_", "enable_", "disable_",
    "assign_", "add_", "edit_", "start_", "stop_", "activate_", "deactivate_",
)


def classify_mcp_tool(server_key: str, tool_name: str, *, allow_writes: bool) -> str:
    """Devuelve 'allow' | 'confirm' | 'deny'."""
    name = (tool_name or "").strip().lower()
    if not name:
        return "deny"

    if any(tok in name for tok in _DENY_ALWAYS):
        return "deny"

    is_read = any(name.startswith(h) or (f"_{h.strip('_-')}" in name) for h in _READ_HINTS)
    if is_read and not any(name.startswith(w) for w in _WRITE_HINTS):
        return "allow"

    if not allow_writes:
        # FASE 10: nada que no sea lectura clara se ejecuta.
        return "deny"

    # allow_writes=True (FASE 16+): escritura conocida -> confirm; desconocida -> deny.
    if any(name.startswith(w) for w in _WRITE_HINTS):
        return "confirm"
    return "deny"
