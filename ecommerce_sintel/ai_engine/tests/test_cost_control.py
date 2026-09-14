"""
cost_control.py -- limite diario agregado por usuario (Gap 3, Fase 23, agregado
2026-08-08). Usa el Redis real del contenedor (mismo que redis_checkpointer.py,
CHECKPOINTER_REDIS_URL) -- no se fake-ea, es la unica forma de probar el
comportamiento distribuido real que motivo este modulo.
"""
import uuid

from cost_control import _client, _daily_key, check_and_increment_daily_turns


async def _cleanup(user_id):
    client = _client()
    try:
        await client.delete(_daily_key(user_id))
    finally:
        await client.aclose()


async def test_permite_turnos_dentro_del_limite():
    user_id = f"test-cost-{uuid.uuid4().hex[:8]}"
    try:
        for _ in range(3):
            assert await check_and_increment_daily_turns(user_id, limit=5) is True
    finally:
        await _cleanup(user_id)


async def test_bloquea_al_superar_el_limite():
    user_id = f"test-cost-{uuid.uuid4().hex[:8]}"
    try:
        for _ in range(3):
            assert await check_and_increment_daily_turns(user_id, limit=3) is True
        # el 4to turno ya supera el limite de 3
        assert await check_and_increment_daily_turns(user_id, limit=3) is False
    finally:
        await _cleanup(user_id)


async def test_usuarios_distintos_no_comparten_contador():
    user_a = f"test-cost-a-{uuid.uuid4().hex[:8]}"
    user_b = f"test-cost-b-{uuid.uuid4().hex[:8]}"
    try:
        for _ in range(2):
            assert await check_and_increment_daily_turns(user_a, limit=2) is True
        assert await check_and_increment_daily_turns(user_a, limit=2) is False
        # user_b arranca en 0, no deberia estar bloqueado por el consumo de user_a
        assert await check_and_increment_daily_turns(user_b, limit=2) is True
    finally:
        await _cleanup(user_a)
        await _cleanup(user_b)
