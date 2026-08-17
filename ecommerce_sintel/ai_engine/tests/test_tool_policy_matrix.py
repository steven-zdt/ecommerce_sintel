"""
Matriz sistematica de Policy por Tool (Gap 5, Fase 32, agregado 2026-08-08).

Hueco real detectado en la auditoria: test_policy_layer.py solo cubria 3 de
~30 Tools registradas a mano. Este archivo generaliza esa verificacion a TODAS
las capabilities activas del CapabilityRegistry real -- para cada una, la
decision de node_evaluate_policy debe coincidir exactamente con lo que su
propia ToolMetadata declara (permissions/requires_confirmation), sin excepcion.
Si alguien agrega una Tool nueva con requires_confirmation=True pero
node_evaluate_policy alguna vez deja de respetarlo, este test lo detecta solo
-- no hace falta acordarse de escribir un caso nuevo a mano.
"""
import pytest

import tools as tool_registry
from action_graph import node_evaluate_policy
from capabilities import CapabilityRegistry


def _all_active_capability_ids() -> list[str]:
    return [c.capability_id for c in CapabilityRegistry.list_active()]


@pytest.mark.parametrize("capability_id", _all_active_capability_ids())
async def test_policy_decision_coincide_con_metadata_declarada_no_staff(capability_id):
    cap = CapabilityRegistry.get(capability_id)
    tool = tool_registry.get_tool(cap.tool_name)
    assert tool is not None, f"{capability_id} apunta a una Tool no registrada: {cap.tool_name}"
    metadata = tool.metadata

    # user_id sintetico y unico por capability -- aisla el rate limiter (Redis,
    # flusheado por el fixture autouse de conftest.py antes de cada test) de este
    # caso frente a cualquier otro test/caso.
    state = {
        "pending_write": {"name": capability_id, "args": {}},
        "user_context": {"user_id": f"matrix-nostaff-{capability_id}", "is_staff": False},
    }
    result = await node_evaluate_policy(state, {})
    decision = result["policy_decision"]

    if "IsAdminUser" in metadata.permissions:
        assert decision == "deny", f"{capability_id} es admin-only pero no bloqueo a un usuario normal"
    elif metadata.requires_confirmation:
        assert decision == "confirm", f"{capability_id} declara requires_confirmation pero no pidio confirmar"
    else:
        assert decision == "allow", f"{capability_id} deberia permitirse directo y no lo hizo"


@pytest.mark.parametrize("capability_id", _all_active_capability_ids())
async def test_admin_only_capabilities_si_permiten_a_staff(capability_id):
    """El otro lado del mismo caso: una capability admin-only SI debe dejar
    avanzar (a confirm/allow segun su propia metadata) cuando el usuario es
    staff -- el deny no debe ser un bloqueo ciego, solo por-permiso."""
    cap = CapabilityRegistry.get(capability_id)
    tool = tool_registry.get_tool(cap.tool_name)
    metadata = tool.metadata
    if "IsAdminUser" not in metadata.permissions:
        pytest.skip(f"{capability_id} no es admin-only")

    state = {
        "pending_write": {"name": capability_id, "args": {}},
        "user_context": {"user_id": f"matrix-staff-{capability_id}", "is_staff": True},
    }
    result = await node_evaluate_policy(state, {})
    assert result["policy_decision"] != "deny"


def test_todas_las_capabilities_activas_resuelven_a_una_tool_registrada():
    """Guardia de integridad del registro completo: ninguna capability activa
    puede apuntar a un tool_name que no exista -- si pasa, _execute_capability
    fallaria en produccion con un error confuso en vez de uno claro aqui."""
    ids = _all_active_capability_ids()
    assert ids, "CapabilityRegistry.list_active() no devolvio ninguna capability"
    for capability_id in ids:
        cap = CapabilityRegistry.get(capability_id)
        assert tool_registry.get_tool(cap.tool_name) is not None, (
            f"{capability_id} -> tool_name={cap.tool_name} no registrado"
        )
