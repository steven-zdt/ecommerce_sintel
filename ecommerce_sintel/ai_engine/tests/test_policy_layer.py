"""
node_evaluate_policy (action_graph.py) -- Policy Layer (Componente 5, Fase 4).
Usa capabilities/tools REALES ya registradas (abrir_ticket_soporte,
crear_alquiler, verificar_mantenimiento) en vez de fixtures fake, para
probar el comportamiento tal como corre en produccion.
"""
import pytest

from action_graph import node_evaluate_policy, _rate_limit_exceeded


def _state(capability_id: str, is_staff: bool = False, **extra_user):
    return {
        "pending_write": {"name": capability_id, "args": {}},
        "user_context": {"user_id": 1, "is_staff": is_staff, **extra_user},
    }


async def test_allow_escritura_no_destructiva_sin_confirmacion():
    """abrir_ticket_soporte: requires_confirmation=False, sin permiso admin -> allow."""
    result = await node_evaluate_policy(_state("abrir_ticket_soporte"), {})
    assert result["policy_decision"] == "allow"


async def test_confirm_escritura_que_lo_exige():
    """crear_alquiler: requires_confirmation=True -> confirm, no se ejecuta directo."""
    result = await node_evaluate_policy(_state("crear_alquiler"), {})
    assert result["policy_decision"] == "confirm"
    assert result["needs_confirmation"] is True


async def test_deny_admin_only_para_usuario_no_staff():
    """verificar_mantenimiento: IsAdminUser -> deny si el usuario no es staff."""
    result = await node_evaluate_policy(_state("verificar_mantenimiento", is_staff=False), {})
    assert result["policy_decision"] == "deny"


async def test_allow_admin_only_para_usuario_staff():
    """La misma capability admin-only SI se permite avanzar (a confirm/allow segun
    su propia metadata) cuando el usuario es staff -- aqui MaintenanceCheckTool no
    exige confirmacion, así que decide allow directo."""
    result = await node_evaluate_policy(_state("verificar_mantenimiento", is_staff=True), {})
    assert result["policy_decision"] != "deny"


async def test_deny_capability_desconocida():
    result = await node_evaluate_policy(_state("esto_no_existe"), {})
    assert result["policy_decision"] == "deny"


async def test_rate_limit_exceeded_bloquea_al_superar_el_limite():
    """Rate limiter respaldado en Redis por (user_id, tool) (Fase 23, cerrado
    2026-08-17 -- ver cost_control.py para el mismo patron; el fixture autouse de
    conftest.py flushea las claves ai:tool_rate:* antes de cada test): 2/hour
    permite 2 llamadas y bloquea la 3ra dentro de la misma ventana."""
    user_id, tool_name, limit = "rate-test-user", "SomeTool", "2/hour/user"
    assert await _rate_limit_exceeded(user_id, tool_name, limit) is False   # hit 1
    assert await _rate_limit_exceeded(user_id, tool_name, limit) is False   # hit 2
    assert await _rate_limit_exceeded(user_id, tool_name, limit) is True    # hit 3, bloqueado


async def test_rate_limit_formato_invalido_nunca_bloquea():
    """Un rate_limit mal formado no debe tumbar la Policy Layer -- se ignora."""
    assert await _rate_limit_exceeded("u", "t", "no-es-un-rate-limit") is False
