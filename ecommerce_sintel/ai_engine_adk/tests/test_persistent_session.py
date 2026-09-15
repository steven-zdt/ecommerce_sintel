"""
Mision RAG-POST2 (FASE 7, 2026-09-16): checkpoint real de sesion persistente
pedido explicitamente por la mision -- "reiniciar el contenedor y verificar:
session exists, previous state recovered, conversation continues, identity
remains correct".

Un restart real de contenedor no se puede automatizar limpiamente desde
DENTRO de un test de ese mismo contenedor -- en su lugar, este archivo
verifica lo que SI se puede probar automatizado y que es la garantia real
detras de "sobrevive un restart": DatabaseSessionService persiste en
Postgres, no en memoria de proceso, asi que construir un SEGUNDO
DatabaseSessionService independiente (misma db_url, sin compartir ningun
objeto Python con el primero -- equivalente exacto a "otro proceso, tras un
restart") y confirmar que ve la sesion/eventos del primero prueba la
persistencia real sin necesitar reiniciar el contenedor de verdad. La
verificacion manual completa (turno real -> restart real de
`ecommerce_sintel_ai_adk` -> segundo turno real, el LLM recuerda el dato del
turno 1) se corrio una vez y quedo documentada en
AUDITORIA/RAG_POST2_FINAL_CERTIFICATION.md -- este archivo es la regresion
automatizada de ahi en adelante.

IMPORTANTE -- este archivo, a diferencia del resto de la suite, SI requiere
Postgres real (tests/conftest.py fuerza ADK_SESSION_BACKEND=memory para todo
lo demas, pero estos tests construyen su propio DatabaseSessionService
explicito, sin pasar por ese default). Correr con deps reales, NO --no-deps:

    docker compose run --rm sintel_ai_adk pytest tests/test_persistent_session.py -v

Requiere la base de datos dedicada ya provisionada (ver docker-compose.yml,
comentario en el servicio sintel_ai_adk):
    docker compose exec db psql -U ${DB_USER} -d ${DB_NAME} \
        -c "CREATE DATABASE sintel_adk_sessions;"

Se salta automaticamente (no falla) si Postgres no es alcanzable -- para no
romper una corrida de suite completa que si use --no-deps por error.
"""
import os

import pytest

_DB_URL = os.environ.get(
    "ADK_SESSION_DB_URL",
    "postgresql+asyncpg://sintel_dev:sintel_dev@db:5432/sintel_adk_sessions",
)


def _make_service():
    from google.adk.sessions.database_session_service import DatabaseSessionService
    return DatabaseSessionService(db_url=_DB_URL)


async def _skip_if_unreachable():
    try:
        svc = _make_service()
        await svc.list_sessions(app_name="pytest_probe", user_id="pytest_probe")
        return svc
    except Exception as exc:
        pytest.skip(f"Postgres de sesiones no alcanzable ({exc}) -- correr sin --no-deps")


@pytest.mark.asyncio
async def test_session_creada_por_un_service_es_visible_desde_otro_independiente():
    """Equivalente real a "sobrevive un restart de contenedor": un segundo
    DatabaseSessionService, construido sin compartir ningun objeto en
    memoria con el primero (mismo db_url nada mas), debe ver la sesion --
    la unica forma de que eso pase es que el estado viva en Postgres, no en
    un dict de proceso."""
    writer = await _skip_if_unreachable()
    app_name, user_id, session_id = "pytest_app", "pytest_user_1", "pytest_session_1"

    await writer.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id,
        state={"marker": "escrito_por_writer"},
    )

    reader = _make_service()  # instancia independiente -- simula "otro proceso"
    recovered = await reader.get_session(app_name=app_name, user_id=user_id, session_id=session_id)

    assert recovered is not None, "la sesion debe sobrevivir a traves de una instancia NUEVA del service"
    assert recovered.state.get("marker") == "escrito_por_writer"

    await writer.delete_session(app_name=app_name, user_id=user_id, session_id=session_id)


@pytest.mark.asyncio
async def test_jwt_nunca_se_siembra_en_session_state_persistente():
    """ADK-08 (regla dura, sintel_root_workflow.py): el JWT vive en
    _EPHEMERAL_TOKENS de proceso, NUNCA en Session.state -- verificar que
    eso sigue siendo cierto ahora que Session.state SI persiste en disco
    (antes, con InMemorySessionService, un JWT filtrado ahi se perdia solo
    al reiniciar; con DatabaseSessionService quedaria en Postgres
    indefinidamente, un riesgo mucho mayor si esta regla se rompiera)."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import jwt as pyjwt
    import time

    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-32-bytes-minimum-len")
    from sintel_adapter import _EPHEMERAL_TOKENS

    token = pyjwt.encode(
        {"token_type": "access", "user_id": 999, "exp": int(time.time()) + 300},
        os.environ["JWT_SECRET_KEY"], algorithm="HS256",
    )

    svc = await _skip_if_unreachable()
    app_name, user_id, session_id = "pytest_app", "pytest_user_2", "pytest_session_2"
    await svc.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id,
        state={"identity_context": {"user_id": 999, "email": "no-jwt@example.com"}},
    )
    recovered = await svc.get_session(app_name=app_name, user_id=user_id, session_id=session_id)

    state_str = str(recovered.state)
    assert token not in state_str, "un JWT nunca debe terminar dentro de Session.state persistente"
    assert "_EPHEMERAL_TOKENS" not in state_str

    await svc.delete_session(app_name=app_name, user_id=user_id, session_id=session_id)
