"""
Fase 12 AI Core -- Validacion funcional del Copilot de Soporte.

Primer test suite de `support`. A diferencia de otros `tests.py` del repo (que
usan `TransactionTestCase` sincrono, ej. `notifications/tests.py`), aqui se
prueba un WebSocket consumer real (`SupportChatConsumer`) con
`channels.testing.WebsocketCommunicator`, que corre en su propio hilo/loop --
requiere funciones async (`pytest-asyncio`, ya instalado sin uso previo en el
repo) y envolver cada acceso al ORM con `channels.db.database_sync_to_async`
(equivalente al motivo por el que `notifications` usa `TransactionTestCase` en
vez de `TestCase`: las escrituras deben ser visibles fuera de la transaccion
atomica de un solo hilo). `CHANNEL_LAYERS` usa Redis real (no hace falta un
`InMemoryChannelLayer` de test): estos tests corren dentro del contenedor
Docker (`docker compose exec django pytest support/tests.py`), donde Redis ya
esta arriba.

`ai_bridge.ask_ai_async()` (el unico punto de contacto del consumer con el AI Engine
real -- ver auditoria E2E 2026-08-17, `ask_ai_async` reemplazo a `ask_ai`/`requests.post`
en este path especificamente para no bloquear el thread pool compartido de Channels) se
mockea siempre a nivel de `httpx.AsyncClient` -- mismo borde HTTP que antes se mockeaba
via `requests.post`, ver helper `_setup_ai_mock()`. WhatsApp (Celery, `notifications/
tasks.py`) sigue usando el `ask_ai()` sincrono y se sigue mockeando via
`support.services.ai_bridge.requests.post` (ver `notifications/tests.py`). La ejecucion
real de Tools, latencia y disponibilidad se valida aparte con
`ai_engine/e2e_http/e2e_support_ai_chat_test.ps1` contra el stack vivo.
"""
import asyncio
import json
import time
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken

from support.channels_auth import JWTAuthMiddlewareStack
from support.routing import support_websocket_patterns
from support.models import ChatRoom, ChatMessage, ChatRoomContext, SupportTicket
from orders.models import Order

application = JWTAuthMiddlewareStack(URLRouter(support_websocket_patterns))

MOCK_METRICS = {
    'agent': 'SupportAgent', 'intent': 'unknown', 'llm_calls': 1,
    'llm_tokens_in': 120, 'llm_tokens_out': 30, 'tool_calls': 0,
    'tool_errors': 0, 'tools': [], 'fallback_used': False, 'handoff': None,
    'needs_confirmation': False, 'write_executed': False, 'duration_ms': 5,
}


# ── Helpers (envuelven ORM/creacion de tokens para uso desde tests async) ────

@database_sync_to_async
def _create_user(email, **kwargs):
    return get_user_model().objects.create_user(email=email, password='TestPass123!', **kwargs)


@database_sync_to_async
def _create_order(user, total=100000):
    return Order.objects.create(user=user, total_amount=total)


@database_sync_to_async
def _get_open_room(user):
    return ChatRoom.objects.get(user=user, status=ChatRoom.STATUS_OPEN)


@database_sync_to_async
def _count_open_rooms(user):
    return ChatRoom.objects.filter(user=user, status=ChatRoom.STATUS_OPEN).count()


@database_sync_to_async
def _count_contexts(room):
    return ChatRoomContext.objects.filter(room=room).count()


@database_sync_to_async
def _count_bot_messages():
    return ChatMessage.objects.filter(sender__email=settings.AI_BOT_EMAIL).count()


@database_sync_to_async
def _refresh(instance):
    instance.refresh_from_db()
    return instance


def _mock_response(payload: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.text = json.dumps(payload)
    return resp


def _setup_ai_mock(mock_async_client_cls) -> AsyncMock:
    """Configura el MagicMock que reemplaza httpx.AsyncClient (via @patch('httpx.AsyncClient'))
    para que 'async with httpx.AsyncClient(...) as client' funcione, y devuelve el AsyncMock
    de client.post a configurar con .return_value/.side_effect -- mismo rol que mock_post
    tenia antes con requests.post (ver ask_ai_async en support/services/ai_bridge.py)."""
    mock_client = mock_async_client_cls.return_value
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock()
    return mock_client.post


async def _connect_ws(user, extra_qs: str = ""):
    token = str(AccessToken.for_user(user))
    path = f"/ws/support/chat/?token={token}"
    if extra_qs:
        path += f"&{extra_qs}"
    from channels.testing import WebsocketCommunicator
    communicator = WebsocketCommunicator(application, path)
    connected, _ = await communicator.connect()
    assert connected, f"WebSocket no conecto para {user.email}"
    return communicator


# ── 1. Inicio de conversacion ────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_inicio_conversacion_crea_sala_y_envia_historial():
    user = await _create_user('cliente.inicio@test.sintel')

    comm = await _connect_ws(user)
    history = json.loads(await comm.receive_from(timeout=5))
    assert history['type'] == 'history'
    assert history['messages'] == []
    assert await _count_open_rooms(user) == 1
    await comm.disconnect()

    # Reconectar reutiliza la sala OPEN existente, no crea una segunda.
    comm2 = await _connect_ws(user)
    await comm2.receive_from(timeout=5)
    assert await _count_open_rooms(user) == 1
    await comm2.disconnect()


# ── 1b. Heartbeat ping/pong (repaso de backlog A2, AUDITORIA/18_AUDITORIA_PRODUCCION_
# RESILIENCIA_WS.md, 2026-08-03) -- antes no habia ningun heartbeat de aplicacion.

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_ping_responde_pong_sin_afectar_flood_limit():
    from support.services.commands import MESSAGE_FLOOD_LIMIT

    user = await _create_user('cliente.ping@test.sintel')
    comm = await _connect_ws(user)
    await comm.receive_from(timeout=5)  # history

    # Muchos mas pings que el limite de flood de mensajes -- el ping no debe consumirlo.
    for _ in range(MESSAGE_FLOOD_LIMIT + 5):
        await comm.send_to(text_data=json.dumps({'type': 'ping'}))
        pong = json.loads(await comm.receive_from(timeout=5))
        assert pong == {'type': 'pong'}

    # El flood limit sigue intacto: un mensaje de chat normal todavia se acepta.
    await comm.send_to(text_data=json.dumps({'message': 'sigo teniendo cupo'}))
    echo = json.loads(await comm.receive_from(timeout=5))
    assert echo['message'] == 'sigo teniendo cupo'

    await comm.disconnect()


# ── 2. Recuperacion de contexto del cliente ──────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_recuperacion_contexto_order_propia_y_ajena():
    owner = await _create_user('cliente.contexto@test.sintel')
    other = await _create_user('otro.cliente@test.sintel')
    own_order = await _create_order(owner)
    other_order = await _create_order(other)

    # Contexto propio: se vincula.
    comm = await _connect_ws(owner, f"context_type=ORDER&context_uuid={own_order.uuid}")
    history = json.loads(await comm.receive_from(timeout=5))
    assert len(history['contexts']) == 1
    assert history['contexts'][0]['uuid'] == str(own_order.uuid)
    room = await _get_open_room(owner)
    assert await _count_contexts(room) == 1
    await comm.disconnect()

    # Contexto ajeno (orden de otro usuario): NO se vincula, sigue en 1.
    comm2 = await _connect_ws(owner, f"context_type=ORDER&context_uuid={other_order.uuid}")
    await comm2.receive_from(timeout=5)
    assert await _count_contexts(room) == 1
    await comm2.disconnect()


# ── 3. Respuesta de IA + persistencia de telemetria (Fase 8) ────────────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@patch('httpx.AsyncClient')
async def test_respuesta_ia_persiste_texto_y_metrics(mock_async_client_cls):
    mock_post = _setup_ai_mock(mock_async_client_cls)
    user = await _create_user('cliente.ia@test.sintel')
    mock_post.return_value = _mock_response({
        'conversation_id': 'x', 'intent': 'unknown', 'agent': 'SupportAgent',
        'tool_calls': [], 'tool_results': [], 'needs_confirmation': False,
        'confirmation': None, 'response': 'Hola, en que puedo ayudarte?',
        'metrics': MOCK_METRICS,
    })

    with override_settings(AI_SUPPORT_CHAT_ENABLED=True):
        comm = await _connect_ws(user)
        await comm.receive_from(timeout=5)  # history
        await comm.send_to(text_data=json.dumps({'message': 'hola'}))
        await comm.receive_from(timeout=5)  # eco del propio mensaje
        ai_raw = json.loads(await comm.receive_from(timeout=10))
        assert ai_raw['message'] == 'Hola, en que puedo ayudarte?'
        await comm.disconnect()

    bot_msg = await database_sync_to_async(
        lambda: ChatMessage.objects.get(sender__email=settings.AI_BOT_EMAIL)
    )()
    assert bot_msg.ai_metrics == MOCK_METRICS


# ── 4. Flujo de confirmacion (Tool de escritura) ─────────────────────────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@patch('httpx.AsyncClient')
async def test_flujo_confirmacion_escritura_dos_turnos(mock_async_client_cls):
    mock_post = _setup_ai_mock(mock_async_client_cls)
    user = await _create_user('cliente.confirma@test.sintel')
    metrics_pending = {**MOCK_METRICS, 'needs_confirmation': True}
    metrics_done = {**MOCK_METRICS, 'needs_confirmation': False, 'write_executed': True}
    mock_post.side_effect = [
        _mock_response({
            'conversation_id': 'x', 'intent': 'unknown', 'agent': 'SalesAgent',
            'tool_calls': [], 'tool_results': [], 'needs_confirmation': True,
            'confirmation': {'question': 'Confirmas crear la cotizacion?'},
            'response': 'Confirmas crear la cotizacion?', 'metrics': metrics_pending,
        }),
        _mock_response({
            'conversation_id': 'x', 'intent': 'unknown', 'agent': 'SalesAgent',
            'tool_calls': [], 'tool_results': [], 'needs_confirmation': False,
            'confirmation': None, 'response': 'Listo, cotizacion creada.',
            'metrics': metrics_done,
        }),
    ]

    with override_settings(AI_SUPPORT_CHAT_ENABLED=True):
        comm = await _connect_ws(user)
        await comm.receive_from(timeout=5)  # history

        await comm.send_to(text_data=json.dumps({'message': 'crea una cotizacion'}))
        await comm.receive_from(timeout=5)  # eco
        turn1 = json.loads(await comm.receive_from(timeout=10))
        assert 'Confirmas' in turn1['message']

        await comm.send_to(text_data=json.dumps({'message': 'si'}))
        await comm.receive_from(timeout=5)  # eco
        turn2 = json.loads(await comm.receive_from(timeout=10))
        assert turn2['message'] == 'Listo, cotizacion creada.'
        await comm.disconnect()

    bot_msgs = await database_sync_to_async(
        lambda: list(ChatMessage.objects.filter(sender__email=settings.AI_BOT_EMAIL).order_by('created_at'))
    )()
    assert len(bot_msgs) == 2
    assert bot_msgs[0].ai_metrics['needs_confirmation'] is True
    assert bot_msgs[1].ai_metrics['write_executed'] is True


# ── 5. Escalamiento a humano (Human Handoff) ─────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@patch('httpx.AsyncClient')
async def test_human_handoff_pausa_sala_y_detiene_ia(mock_async_client_cls):
    mock_post = _setup_ai_mock(mock_async_client_cls)
    user = await _create_user('cliente.handoff@test.sintel')
    mock_post.return_value = _mock_response({
        'conversation_id': 'x', 'intent': 'unknown', 'agent': 'SupportAgent',
        'tool_calls': [], 'response': 'Te transfiero con un agente humano.',
        'tool_results': [{'capability': 'abrir_ticket_soporte', 'result': {'ticket_id': 1}}],
        'needs_confirmation': False, 'confirmation': None,
        'metrics': {**MOCK_METRICS, 'handoff': 'SupportAgent->Human'},
    })

    with override_settings(AI_SUPPORT_CHAT_ENABLED=True):
        comm = await _connect_ws(user)
        await comm.receive_from(timeout=5)  # history
        await comm.send_to(text_data=json.dumps({'message': 'quiero hablar con alguien'}))
        await comm.receive_from(timeout=5)  # eco
        await comm.receive_from(timeout=10)  # respuesta IA (escalando)

        room = await _get_open_room(user)
        room = await _refresh(room)
        assert room.ai_paused is True

        # Segundo mensaje del cliente: la IA ya no debe responder (sala pausada).
        await comm.send_to(text_data=json.dumps({'message': 'hola de nuevo'}))
        await comm.receive_from(timeout=5)  # eco del segundo mensaje humano
        with pytest.raises(asyncio.TimeoutError):
            await comm.receive_from(timeout=2)  # no debe llegar una 2da respuesta IA
        # No se llama a comm.disconnect() aca: tras un timeout esperado en
        # receive_from(), el future interno del comunicator queda cancelado y
        # un disconnect() posterior solo repropaga ese CancelledError (artefacto
        # de limpieza de channels.testing, no un bug de la app).

    assert mock_post.call_count == 1


# ── 5b. Reactivacion de la IA tras cerrar el handoff (auditoria E2E AI Engine,
# 2026-08-17 -- hallazgo: no existe ningun comando que ponga ai_paused=False sobre
# la MISMA sala; se grep-eo support/api/ y support/services/commands.py completos
# y la unica escritura de ai_paused es True. La reactivacion real ocurre porque
# ChatCommands.get_or_create_room() solo reusa salas OPEN -- una vez que un admin
# cierra el ticket (close_room, status=CLOSED), el siguiente mensaje del cliente
# crea una sala NUEVA con ai_paused=False por default. Este test prueba ese
# camino real, no un mecanismo de "reanudar" que no existe en el codigo.) ───────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@patch('httpx.AsyncClient')
async def test_ia_se_reactiva_en_sala_nueva_tras_cerrar_el_ticket(mock_async_client_cls):
    from support.services.commands import ChatCommands

    mock_post = _setup_ai_mock(mock_async_client_cls)
    user = await _create_user('cliente.reactivacion@test.sintel')
    mock_post.return_value = _mock_response({
        'conversation_id': 'x', 'intent': 'unknown', 'agent': 'SupportAgent',
        'tool_calls': [], 'response': 'Te transfiero con un agente humano.',
        'tool_results': [{'capability': 'abrir_ticket_soporte', 'result': {'ticket_id': 1}}],
        'needs_confirmation': False, 'confirmation': None,
        'metrics': {**MOCK_METRICS, 'handoff': 'SupportAgent->Human'},
    })

    with override_settings(AI_SUPPORT_CHAT_ENABLED=True):
        comm = await _connect_ws(user)
        await comm.receive_from(timeout=5)  # history
        await comm.send_to(text_data=json.dumps({'message': 'quiero hablar con alguien'}))
        await comm.receive_from(timeout=5)  # eco
        await comm.receive_from(timeout=10)  # respuesta IA (escalando)

        old_room = await _get_open_room(user)
        old_room = await _refresh(old_room)
        assert old_room.ai_paused is True
        await comm.disconnect()

        # El admin resuelve y cierra el ticket -- unico camino real de "reactivacion"
        # que existe hoy en el codigo (ver nota arriba).
        await database_sync_to_async(ChatCommands.close_room)(old_room)

        # Nueva conexion del cliente: get_or_create_room ya no encuentra la sala
        # anterior (CLOSED) y crea una sala OPEN nueva, ai_paused=False por default.
        mock_post.return_value = _mock_response({
            'conversation_id': 'y', 'intent': 'unknown', 'agent': 'SupportAgent',
            'tool_calls': [], 'tool_results': [], 'needs_confirmation': False,
            'confirmation': None, 'response': 'Hola de nuevo, en que te ayudo?',
            'metrics': MOCK_METRICS,
        })
        comm2 = await _connect_ws(user)
        await comm2.receive_from(timeout=5)  # history (sala nueva, vacia)

        new_room = await _get_open_room(user)
        assert new_room.uuid != old_room.uuid
        assert new_room.ai_paused is False

        await comm2.send_to(text_data=json.dumps({'message': 'hola de nuevo'}))
        await comm2.receive_from(timeout=5)  # eco
        ai_reply = json.loads(await comm2.receive_from(timeout=10))
        assert ai_reply['message'] == 'Hola de nuevo, en que te ayudo?'
        await comm2.disconnect()

    assert mock_post.call_count == 2


# ── 6. Persistencia del historial tras reconexion ────────────────────────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_persistencia_historial_tras_reconexion():
    # AI_SUPPORT_CHAT_ENABLED puede ser True en el entorno real (.env) -- se
    # fuerza a False aqui porque este test no mockea ai_bridge y no debe
    # disparar una llamada real al AI Engine en segundo plano.
    with override_settings(AI_SUPPORT_CHAT_ENABLED=False):
        user = await _create_user('cliente.historial@test.sintel')
        comm = await _connect_ws(user)
        await comm.receive_from(timeout=5)  # history vacio
        await comm.send_to(text_data=json.dumps({'message': 'primer mensaje'}))
        await comm.receive_from(timeout=5)  # eco
        await comm.disconnect()

        comm2 = await _connect_ws(user)
        history = json.loads(await comm2.receive_from(timeout=5))
        assert len(history['messages']) == 1
        assert history['messages'][0]['message'] == 'primer mensaje'
        await comm2.disconnect()


# ── 7. Sincronizacion Dashboard admin <-> widget cliente ─────────────────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_sincronizacion_dashboard_admin_y_widget_cliente():
    # Igual que en el test de persistencia: se fuerza AI_SUPPORT_CHAT_ENABLED a
    # False porque este test no mockea ai_bridge y el mensaje del cliente no
    # debe disparar una respuesta real de la IA que se mezcle con la respuesta
    # manual del admin en el mismo grupo.
    with override_settings(AI_SUPPORT_CHAT_ENABLED=False):
        client_user = await _create_user('cliente.sync@test.sintel')
        admin_user = await _create_user('admin.sync@test.sintel', is_staff=True, is_superuser=True)

        client_comm = await _connect_ws(client_user)
        await client_comm.receive_from(timeout=5)  # history
        admin_comm = await _connect_ws(admin_user)

        await client_comm.send_to(text_data=json.dumps({'message': 'hola admin'}))
        await client_comm.receive_from(timeout=5)  # eco propio del cliente

        admin_event = json.loads(await admin_comm.receive_from(timeout=5))
        assert admin_event['type'] == 'chat_message'
        assert admin_event['message'] == 'hola admin'
        room = await _get_open_room(client_user)
        assert admin_event['room_uuid'] == str(room.uuid)

        await admin_comm.send_to(text_data=json.dumps({
            'message': 'hola cliente', 'room_uuid': str(room.uuid),
        }))
        await admin_comm.receive_from(timeout=5)  # eco propio del admin

        client_event = json.loads(await client_comm.receive_from(timeout=5))
        assert client_event['message'] == 'hola cliente'
        assert client_event['is_admin'] is True

        await client_comm.disconnect()
        await admin_comm.disconnect()


# ── 7a. El admin ve la respuesta de la IA en vivo (cierra brecha residual de la
# certificacion E2E 2026-08-13, Paso 18 "PARCIAL" -- la entrega real a
# 'support_admins' con una segunda sesion admin conectada en simultaneo no habia
# sido verificada, solo confirmada por lectura de codigo) ────────────────────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@patch('httpx.AsyncClient')
async def test_admin_ve_respuesta_de_ia_en_vivo(mock_async_client_cls):
    mock_post = _setup_ai_mock(mock_async_client_cls)
    mock_post.return_value = _mock_response({
        'conversation_id': 'x', 'intent': 'unknown', 'agent': 'SupportAgent',
        'tool_calls': [], 'tool_results': [], 'needs_confirmation': False,
        'confirmation': None, 'response': 'Respuesta de la IA para el admin.',
        'metrics': MOCK_METRICS,
    })

    client_user = await _create_user('cliente.admin_ve_ia@test.sintel')
    admin_user = await _create_user('admin.ve_ia@test.sintel', is_staff=True, is_superuser=True)

    with override_settings(AI_SUPPORT_CHAT_ENABLED=True):
        client_comm = await _connect_ws(client_user)
        await client_comm.receive_from(timeout=5)  # history
        admin_comm = await _connect_ws(admin_user)

        await client_comm.send_to(text_data=json.dumps({'message': 'hola, necesito ayuda'}))
        await client_comm.receive_from(timeout=5)  # eco propio del cliente

        # El admin ve primero el mensaje del cliente (group_send de la rama cliente)...
        admin_event_1 = json.loads(await admin_comm.receive_from(timeout=5))
        assert admin_event_1['message'] == 'hola, necesito ayuda'
        assert admin_event_1['is_admin'] is False

        # ...y luego, sin que el admin haya escrito nada, la respuesta de la IA en
        # vivo -- _ai_reply() hace group_send a 'support_admins' ademas de
        # chat_{user.uuid}, precisamente para esta supervision humana en tiempo real.
        admin_event_2 = json.loads(await admin_comm.receive_from(timeout=10))
        assert admin_event_2['message'] == 'Respuesta de la IA para el admin.'
        assert admin_event_2['is_admin'] is True

        await client_comm.disconnect()
        await admin_comm.disconnect()


# ── 7b. Respuesta de agente humano se reenvia por WhatsApp (Fase 16,
# AUDITORIA/30_AUDITORIA_PRUEBAS_E2E.md, 2026-08-03) -- antes SOLO se difundia por WS; un
# cliente que hablaba unicamente por WhatsApp (sin el widget abierto) nunca la recibia.

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_respuesta_de_admin_dispara_reenvio_por_whatsapp():
    with override_settings(AI_SUPPORT_CHAT_ENABLED=False):
        client_user = await _create_user('cliente.wa.bridge@test.sintel')
        admin_user = await _create_user('admin.wa.bridge@test.sintel', is_staff=True, is_superuser=True)

        client_comm = await _connect_ws(client_user)
        await client_comm.receive_from(timeout=5)  # history
        admin_comm = await _connect_ws(admin_user)

        await client_comm.send_to(text_data=json.dumps({'message': 'hola, escribo por WhatsApp'}))
        await client_comm.receive_from(timeout=5)  # eco propio del cliente
        await admin_comm.receive_from(timeout=5)  # el admin ve el mensaje del cliente

        room = await _get_open_room(client_user)

        with patch('notifications.tasks.send_whatsapp_agent_reply_task.delay') as mock_delay:
            await admin_comm.send_to(text_data=json.dumps({
                'message': 'ya te ayudo con eso', 'room_uuid': str(room.uuid),
            }))
            await admin_comm.receive_from(timeout=5)  # eco propio del admin
            await client_comm.receive_from(timeout=5)  # el cliente ve la respuesta por WS

        mock_delay.assert_called_once_with(user_id=client_user.id, text='ya te ayudo con eso')

        await client_comm.disconnect()
        await admin_comm.disconnect()


# ── 8. Concurrencia -- multiples chats simultaneos ───────────────────────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@patch('httpx.AsyncClient')
async def test_concurrencia_multiples_chats_simultaneos(mock_async_client_cls):
    mock_post = _setup_ai_mock(mock_async_client_cls)
    # N=5 (no 8/10): en este entorno Docker/Windows el I/O de Postgres bajo
    # carga concurrente es medible (ver TRUNCATE entre tests, varios segundos
    # reales) -- 5 conexiones simultaneas siguen demostrando enrutamiento
    # correcto sin cruces, con menos contencion de thread pool que hacia el
    # test intermitente por timeout (nunca por un cruce real de sala).
    #
    # NOTA (Fase 12, verificado 2026-07-20): en este host este test fallo por
    # TimeoutError en ~1 de cada 5 corridas incluso con timeout=45s, siempre
    # esperando la respuesta IA de alguno de los N -- NUNCA por la aserción de
    # "cruce de sala" (la correctitud de enrutamiento nunca fallo en ~15
    # corridas). Es I/O real del entorno (Docker Desktop/Windows), no un bug
    # de `support`/`ai_engine`: si este test falla, reintentar antes de asumir
    # una regresion real.
    N = 5
    mock_post.return_value = _mock_response({
        'conversation_id': 'x', 'intent': 'unknown', 'agent': 'SupportAgent',
        'tool_calls': [], 'tool_results': [], 'needs_confirmation': False,
        'confirmation': None, 'response': 'Respuesta automatica de prueba.',
        'metrics': MOCK_METRICS,
    })
    users = [await _create_user(f'concurrente{i}@test.sintel') for i in range(N)]

    async def _flow(user):
        # Timeouts generosos (no una SLA de performance): con N conexiones
        # concurrentes, cada una con varias escrituras via
        # database_sync_to_async, el thread pool + I/O de Postgres puede
        # encolar bajo carga -- esto valida correctitud de enrutamiento
        # (sin cruces), no latencia.
        comm = await _connect_ws(user)
        await comm.receive_from(timeout=15)  # history
        await comm.send_to(text_data=json.dumps({'message': 'hola'}))
        await comm.receive_from(timeout=15)  # eco
        ai_event = json.loads(await comm.receive_from(timeout=45))
        room = await _get_open_room(user)
        assert ai_event['room_uuid'] == str(room.uuid), (
            f"cruce de sala detectado para {user.email}: "
            f"esperaba {room.uuid}, llego {ai_event['room_uuid']}"
        )
        await comm.disconnect()
        return room.uuid

    with override_settings(AI_SUPPORT_CHAT_ENABLED=True):
        room_uuids = await asyncio.gather(*[_flow(u) for u in users])

    assert len(set(room_uuids)) == N  # cada sala es unica, sin cruces
    assert await _count_bot_messages() == N


# ── 8b. La IA lenta no debe serializarse via el thread pool compartido de
# sync_to_async (auditoria E2E AI Engine, 2026-08-17 -- ver ask_ai_async en
# support/services/ai_bridge.py) ─────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_ia_lenta_no_serializa_via_thread_pool_compartido():
    """
    Antes de este fix, ask_ai() (requests.post sincrono) corria envuelto en
    @database_sync_to_async dentro del consumer -- eso ocupa un worker del thread
    pool COMPARTIDO de asgiref/Channels durante TODA la duracion de la llamada HTTP
    (hasta AI_CHAT_TIMEOUT_SECONDS=300s). Con mas turnos de IA concurrentes que el
    tamano de ese pool, los turnos en exceso quedarian literalmente en cola (tiempo
    total ~ N/pool_size * delay), no en paralelo real -- exactamente el "B2" que el
    prompt maestro de esta auditoria senala como bloqueador. ask_ai_async()
    (httpx.AsyncClient) espera en el event loop sin ocupar ningun thread del pool:
    N turnos concurrentes deben completarse en ~delay, no ~N*delay.
    """
    N = 12  # mayor al tamano tipico del thread pool de sync_to_async en este proceso
    DELAY_SECONDS = 0.5

    async def _slow_ai_reply(user, message, conversation_id):
        await asyncio.sleep(DELAY_SECONDS)
        return {
            'conversation_id': conversation_id, 'intent': 'unknown', 'agent': 'SupportAgent',
            'tool_calls': [], 'tool_results': [], 'needs_confirmation': False,
            'confirmation': None, 'response': 'Respuesta lenta de prueba.', 'metrics': MOCK_METRICS,
        }

    users = [await _create_user(f'lenta{i}@test.sintel') for i in range(N)]

    async def _flow(user):
        comm = await _connect_ws(user)
        await comm.receive_from(timeout=15)  # history
        await comm.send_to(text_data=json.dumps({'message': 'hola'}))
        await comm.receive_from(timeout=15)  # eco
        ai_event = json.loads(await comm.receive_from(timeout=15))
        await comm.disconnect()
        return ai_event

    with patch('support.services.ai_bridge.ask_ai_async', side_effect=_slow_ai_reply):
        with override_settings(AI_SUPPORT_CHAT_ENABLED=True):
            start = time.monotonic()
            results = await asyncio.gather(*[_flow(u) for u in users])
            elapsed = time.monotonic() - start

    assert all(r['message'] == 'Respuesta lenta de prueba.' for r in results)
    # Si estuviera serializado por un thread pool compartido saturado, N*DELAY
    # (12 * 0.5s = 6s) seria el piso realista bajo saturacion; en paralelo real
    # debe rondar DELAY_SECONDS, con margen generoso para I/O real del entorno.
    assert elapsed < N * DELAY_SECONDS * 0.5, (
        f"parece serializado via thread pool: elapsed={elapsed:.2f}s para N={N} delay={DELAY_SECONDS}s"
    )


# ── 9. Analytics de conversaciones (Fase 9 AI Core -- Aprendizaje) ──────────
# Sincrono (sin WebSocket): ChatAnalyticsSelector solo lee ChatRoom/ChatMessage
# ya persistidos, no necesita Channels ni pytest-asyncio.

@pytest.mark.django_db
def test_analytics_summary_agrega_datos_reales():
    from support.services.selectors import ChatAnalyticsSelector

    User = get_user_model()
    user = User.objects.create_user(email='cliente.analytics@test.sintel', password='x')
    bot = User.objects.create_user(email='bot.analytics@test.sintel', password='x', is_active=False)

    room1 = ChatRoom.objects.create(user=user)
    room2 = ChatRoom.objects.create(user=User.objects.create_user(email='otro.analytics@test.sintel', password='x'))

    def _msg(room, **metrics_overrides):
        base = {
            'agent': 'SupportAgent', 'intent': 'unknown', 'llm_calls': 1,
            'llm_tokens_in': 0, 'llm_tokens_out': 0, 'tool_calls': 0,
            'tool_errors': 0, 'tools': [], 'fallback_used': False, 'handoff': None,
            'needs_confirmation': False, 'write_executed': False, 'duration_ms': 0,
        }
        base.update(metrics_overrides)
        return ChatMessage.objects.create(room=room, sender=bot, message='respuesta', ai_metrics=base)

    _msg(room1, intent='order_status', duration_ms=1000, llm_tokens_in=100, llm_tokens_out=20,
         tools=[{'tool': 'OrderStatusTool', 'ms': 50, 'ok': True}])
    _msg(room1, intent='order_status', duration_ms=2000, llm_tokens_in=200, llm_tokens_out=40,
         fallback_used=True, tools=[{'tool': 'OrderStatusTool', 'ms': 60, 'ok': True}])
    _msg(room2, intent='quotation_request', duration_ms=3000, llm_tokens_in=300, llm_tokens_out=60,
         handoff='SalesAgent->Human', tools=[{'tool': 'QuoteTemplatesTool', 'ms': 70, 'ok': True}])
    # Mensaje humano (ai_metrics=None) -- no debe contarse como turno de IA.
    ChatMessage.objects.create(room=room1, sender=user, message='hola', ai_metrics=None)

    summary = ChatAnalyticsSelector.get_summary(days=30)

    assert summary['total_conversations'] == 2
    assert summary['total_ai_turns'] == 3
    assert summary['avg_duration_ms'] == 2000.0
    assert summary['avg_tokens_in'] == 200.0
    assert summary['avg_tokens_out'] == 40.0
    assert summary['fallback_rate'] == round(1 / 3, 4)
    assert summary['handoff_rate'] == round(1 / 3, 4)
    assert {'intent': 'order_status', 'count': 2} in summary['intent_breakdown']
    assert {'intent': 'quotation_request', 'count': 1} in summary['intent_breakdown']
    assert {'tool': 'OrderStatusTool', 'count': 2} in summary['top_tools']
    assert {'intent': 'order_status', 'fallback_count': 1} in summary['frequent_issues']


# ── 10. CSAT -- calificar una conversacion cerrada ───────────────────────────
# Sincrono (sin WebSocket): ChatCommands.rate_conversation solo escribe en BD.

@pytest.mark.django_db
def test_rate_conversation_exito_y_validaciones():
    from support.services.commands import ChatCommands

    User = get_user_model()
    owner = User.objects.create_user(email='cliente.csat@test.sintel', password='x')
    other = User.objects.create_user(email='otro.csat@test.sintel', password='x')

    room_open = ChatRoom.objects.create(user=owner)
    with pytest.raises(ValueError, match='cerrada'):
        ChatCommands.rate_conversation(room_open, owner, rating=5)

    room = ChatRoom.objects.create(user=owner, status=ChatRoom.STATUS_CLOSED)

    with pytest.raises(ValueError, match='no es tuya'):
        ChatCommands.rate_conversation(room, other, rating=5)

    rated = ChatCommands.rate_conversation(room, owner, rating=4, comment='Buena atencion')
    assert rated.csat_rating == 4
    assert rated.csat_comment == 'Buena atencion'
    assert rated.csat_rated_at is not None

    with pytest.raises(ValueError, match='ya fue calificada'):
        ChatCommands.rate_conversation(room, owner, rating=1)


# ── 11. CSAT -- aviso en tiempo real de cierre de sala (room_closed) ─────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_room_closed_avisa_al_cliente_por_ws():
    from support.services.commands import ChatCommands

    user = await _create_user('cliente.roomclosed@test.sintel')
    comm = await _connect_ws(user)
    await comm.receive_from(timeout=5)  # history

    room = await _get_open_room(user)
    await database_sync_to_async(ChatCommands.close_room)(room)

    closed_event = json.loads(await comm.receive_from(timeout=5))
    assert closed_event['type'] == 'room_closed'
    assert closed_event['room_uuid'] == str(room.uuid)
    await comm.disconnect()


# ── 11b. Cliente no puede seguir escribiendo en una sala ya CLOSED (B2,
# auditoria enterprise 2026-07-31) -- antes solo la rama admin de receive()
# validaba status=OPEN.

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_cliente_no_puede_escribir_en_sala_cerrada():
    from support.services.commands import ChatCommands

    user = await _create_user('cliente.salacerrada@test.sintel')
    comm = await _connect_ws(user)
    await comm.receive_from(timeout=5)  # history

    room = await _get_open_room(user)
    await database_sync_to_async(ChatCommands.close_room)(room)
    await comm.receive_from(timeout=5)  # aviso room_closed (ya probado en el test anterior)

    await comm.send_to(text_data=json.dumps({'message': 'sigo escribiendo igual'}))
    with pytest.raises(asyncio.TimeoutError):
        await comm.receive_from(timeout=2)  # ni eco ni error -- el mensaje se ignora

    messages = await database_sync_to_async(
        lambda: list(ChatMessage.objects.filter(room=room, sender=user))
    )()
    assert len(messages) == 0


# ── 12. CSAT -- endpoint REST real (E1, auditoria enterprise 2026-07-31) ────
# A diferencia del test #10 (que llama ChatCommands.rate_conversation directo),
# esto pasa por la vista/URL/permisos reales -- en particular el fix de
# disclosure D-04 (auditoria previa: una sala ajena debia dar 404, no 400/200
# despues de revelar que "existe"), que hasta ahora no tenia ningun test de
# regresion protegiendolo.

@pytest.mark.django_db
def test_rate_conversation_endpoint_anonimo_rechazado():
    client = APIClient()
    room = ChatRoom.objects.create(
        user=get_user_model().objects.create_user(email='csat.anon@test.sintel', password='x'),
        status=ChatRoom.STATUS_CLOSED,
    )
    url = reverse('support-rate-conversation', kwargs={'room_uuid': str(room.uuid)})
    response = client.post(url, {'rating': 5}, format='json')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_rate_conversation_endpoint_sala_ajena_da_404_sin_distincion():
    # D-04: el lookup esta scoped a request.user desde el inicio -- una sala
    # que SI existe pero es de otro usuario debe dar exactamente el mismo 404
    # que una sala inexistente (sin filtrar si "existe" vs "no existe").
    User = get_user_model()
    owner = User.objects.create_user(email='csat.owner@test.sintel', password='x')
    other = User.objects.create_user(email='csat.other@test.sintel', password='x')
    room = ChatRoom.objects.create(user=owner, status=ChatRoom.STATUS_CLOSED)

    client = APIClient()
    client.force_authenticate(user=other)
    url = reverse('support-rate-conversation', kwargs={'room_uuid': str(room.uuid)})
    response = client.post(url, {'rating': 5}, format='json')

    assert response.status_code == status.HTTP_404_NOT_FOUND
    room.refresh_from_db()
    assert room.csat_rating is None  # el intento ajeno no debe haber calificado nada


@pytest.mark.django_db
def test_rate_conversation_endpoint_exito_y_validacion():
    owner = get_user_model().objects.create_user(email='csat.exito@test.sintel', password='x')
    room = ChatRoom.objects.create(user=owner, status=ChatRoom.STATUS_CLOSED)

    client = APIClient()
    client.force_authenticate(user=owner)
    url = reverse('support-rate-conversation', kwargs={'room_uuid': str(room.uuid)})

    # Rating invalido (fuera de 1-5): el serializer lo rechaza antes de llegar
    # al service layer.
    bad = client.post(url, {'rating': 9}, format='json')
    assert bad.status_code == status.HTTP_400_BAD_REQUEST

    ok = client.post(url, {'rating': 5, 'comment': 'Excelente atencion'}, format='json')
    assert ok.status_code == status.HTTP_200_OK
    assert ok.data['csat_rating'] == 5
    room.refresh_from_db()
    assert room.csat_rating == 5

    # Ya calificada: el ValueError del service layer se traduce a 400 real por
    # la vista, no a un 500.
    again = client.post(url, {'rating': 1}, format='json')
    assert again.status_code == status.HTTP_400_BAD_REQUEST


# ── 13. Human Handoff interno -- AiOpenSupportTicketView (E2, auditoria
# enterprise 2026-07-31). Sin cobertura previa en todo el repo (ni este
# endpoint ni ningun otro bajo el namespace internal_ai).

@pytest.mark.django_db
def test_ai_open_support_ticket_requiere_message():
    user = get_user_model().objects.create_user(email='handoff.sinmsg@test.sintel', password='x')
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(reverse('internal_ai:ai-support-ticket'), {}, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_ai_open_support_ticket_crea_sala_pausa_ia_y_notifica():
    from security.models import SecurityEvent

    user = get_user_model().objects.create_user(email='handoff.exito@test.sintel', password='x')
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        reverse('internal_ai:ai-support-ticket'),
        {'message': 'Necesito hablar con un humano', 'history': [
            {'user': 'hola', 'assistant': 'como puedo ayudarte'},
        ]},
        format='json',
    )

    assert response.status_code == status.HTTP_201_CREATED
    room = ChatRoom.objects.get(user=user)
    assert room.ai_paused is True  # Human Handoff: la IA deja de responder aca
    assert response.data['ticket']['room_uuid'] == str(room.uuid)

    messages = list(ChatMessage.objects.filter(room=room).order_by('created_at'))
    # 1 mensaje de transcript (bot, por history) + 1 del usuario (el mensaje real).
    assert len(messages) == 2
    assert messages[0].sender.email == settings.AI_BOT_EMAIL
    assert 'Transcripcion' in messages[0].message
    assert messages[1].sender_id == user.id
    assert messages[1].message == 'Necesito hablar con un humano'

    assert SecurityEvent.objects.filter(
        event_type=SecurityEvent.AI_ACTION_EXECUTED,
        metadata__room_uuid=str(room.uuid),
    ).exists()


@pytest.mark.django_db
def test_ai_open_support_ticket_adjunta_orden_propia_y_rechaza_ajena():
    User = get_user_model()
    owner = User.objects.create_user(email='handoff.owner@test.sintel', password='x')
    other = User.objects.create_user(email='handoff.other@test.sintel', password='x')
    own_order = Order.objects.create(user=owner, total_amount=50000)
    other_order = Order.objects.create(user=other, total_amount=50000)

    client = APIClient()
    client.force_authenticate(user=owner)
    url = reverse('internal_ai:ai-support-ticket')

    ok = client.post(url, {'message': 'ayuda con mi pedido', 'order_uuid': str(own_order.uuid)}, format='json')
    assert ok.status_code == status.HTTP_201_CREATED
    assert ok.data['ticket']['attached_context'] == f'orden {own_order.uuid}'
    room = ChatRoom.objects.get(user=owner)
    assert ChatRoomContext.objects.filter(room=room, context_type=ChatRoomContext.CONTEXT_ORDER, order=own_order).exists()

    # Orden de otro usuario: 404, sin importar que el pedido exista de verdad.
    forbidden = client.post(url, {'message': 'ayuda', 'order_uuid': str(other_order.uuid)}, format='json')
    assert forbidden.status_code == status.HTTP_404_NOT_FOUND


# ── 13b. SupportTicket real -- creado por AiOpenSupportTicketView (2026-09-15).
# El ticket es una entidad separada de ChatRoom (ver support/models.py::SupportTicket
# docstring); antes de esto el "ticket" que veia el operador era solo ChatRoom+
# ai_paused=True, sin asunto/numero/contacto propios.

@pytest.mark.django_db
def test_ai_open_support_ticket_crea_supportticket_con_numero_asunto_y_contacto():
    from accounts.models import UserProfile

    user = get_user_model().objects.create_user(email='ticket.completo@test.sintel', password='x')
    UserProfile.objects.create(user=user, phone_number='+573001112233')
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        reverse('internal_ai:ai-support-ticket'),
        {'message': 'El pago no se aplico a mi pedido',
         'subject': 'Pago no aplicado', 'summary': 'Cliente reporta pago descontado sin confirmar pedido.'},
        format='json',
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['ticket']['ticket_number'].startswith('SUP-')
    assert response.data['ticket']['subject'] == 'Pago no aplicado'

    room = ChatRoom.objects.get(user=user)
    ticket = SupportTicket.objects.get(chat_room=room)
    assert ticket.ticket_number == response.data['ticket']['ticket_number']
    assert ticket.subject == 'Pago no aplicado'
    assert ticket.summary == 'Cliente reporta pago descontado sin confirmar pedido.'
    assert ticket.status == SupportTicket.STATUS_NEW
    # Snapshot al momento de creacion, no una FK viva al perfil.
    assert ticket.contact_phone == '+573001112233'
    assert ticket.contact_email == user.email


@pytest.mark.django_db
def test_ai_open_support_ticket_sin_profile_no_rompe():
    """Un usuario sin UserProfile (nunca creado) no debe romper la creacion del
    ticket -- contact_phone simplemente queda vacio, nunca un 500."""
    user = get_user_model().objects.create_user(email='ticket.sinperfil@test.sintel', password='x')
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        reverse('internal_ai:ai-support-ticket'), {'message': 'necesito ayuda'}, format='json',
    )

    assert response.status_code == status.HTTP_201_CREATED
    ticket = SupportTicket.objects.get(ticket_number=response.data['ticket']['ticket_number'])
    assert ticket.contact_phone == ''
    assert ticket.contact_email == user.email


@pytest.mark.django_db
def test_ai_open_support_ticket_reusa_ticket_existente_sin_pisar_subject():
    """Dos mensajes del cliente sobre la misma sala ya escalada (ai_paused=True)
    no deben crear un segundo SupportTicket -- y si el segundo mensaje llega sin
    subject/summary, no debe borrar lo que ya se habia guardado."""
    user = get_user_model().objects.create_user(email='ticket.reusa@test.sintel', password='x')
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse('internal_ai:ai-support-ticket')

    first = client.post(url, {'message': 'primer mensaje', 'subject': 'Asunto original'}, format='json')
    second = client.post(url, {'message': 'segundo mensaje'}, format='json')

    assert first.data['ticket']['ticket_number'] == second.data['ticket']['ticket_number']
    assert SupportTicket.objects.filter(chat_room__user=user).count() == 1
    ticket = SupportTicket.objects.get(chat_room__user=user)
    assert ticket.subject == 'Asunto original'


# ── 14. Cron de tickets escalados sin seguimiento (E3, auditoria enterprise
# 2026-07-31). Sin cobertura previa -- se mockea NotificationCommands.dispatch_notification
# (el envio real por canal, ya cubierto en notifications/tests.py) para probar solo la
# logica propia de esta tarea: seleccion de salas candidatas + dedupe.

@pytest.mark.django_db
@patch('notifications.services.commands.NotificationCommands.dispatch_notification')
def test_notify_unattended_escalated_tickets_selecciona_y_deduplica(mock_dispatch):
    from support.tasks import notify_unattended_escalated_tickets, _UNATTENDED_THRESHOLD_HOURS
    from django.utils import timezone
    from datetime import timedelta

    User = get_user_model()
    old_time = timezone.now() - timedelta(hours=_UNATTENDED_THRESHOLD_HOURS + 1)
    recent_time = timezone.now() - timedelta(minutes=5)

    def _room(email, *, ai_paused, status_, updated_at):
        user = User.objects.create_user(email=email, password='x')
        room = ChatRoom.objects.create(user=user, ai_paused=ai_paused, status=status_)
        ChatRoom.objects.filter(pk=room.pk).update(updated_at=updated_at)  # auto_now bypass
        return room

    # Candidata real: OPEN, escalada (ai_paused=True), inactiva hace mas del umbral.
    candidate = _room('cron.candidata@test.sintel', ai_paused=True, status_=ChatRoom.STATUS_OPEN, updated_at=old_time)
    # NO candidata: escalada pero con actividad reciente (dentro del umbral).
    _room('cron.reciente@test.sintel', ai_paused=True, status_=ChatRoom.STATUS_OPEN, updated_at=recent_time)
    # NO candidata: inactiva hace rato pero nunca se escalo (ai_paused=False).
    _room('cron.sinescalar@test.sintel', ai_paused=False, status_=ChatRoom.STATUS_OPEN, updated_at=old_time)
    # NO candidata: escalada e inactiva, pero la sala ya esta CLOSED.
    _room('cron.cerrada@test.sintel', ai_paused=True, status_=ChatRoom.STATUS_CLOSED, updated_at=old_time)

    notify_unattended_escalated_tickets()

    assert mock_dispatch.call_count == 1
    called_user = mock_dispatch.call_args.args[0] if mock_dispatch.call_args.args else mock_dispatch.call_args.kwargs['user']
    assert called_user.id == candidate.user_id

    # Segunda corrida (misma condicion sigue cumpliendose): dedupe real via
    # NotificationLog -- no debe volver a notificar la misma sala.
    notify_unattended_escalated_tickets()
    assert mock_dispatch.call_count == 1


# ── 15. Multi-pestana/multi-dispositivo -- mensajes propios en vivo a las demas
# conexiones (C2, AUDITORIA/18_AUDITORIA_PRODUCCION_RESILIENCIA_WS.md, 2026-08-01).
# Antes el eco del propio mensaje era un self.send() unicast -- reproducible en
# produccion sin ninguna dependencia de IA: si el mismo usuario/admin tenia el chat
# abierto en 2 conexiones, la otra nunca se enteraba en vivo.

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_cliente_multi_pestana_recibe_su_propio_mensaje_en_ambas():
    with override_settings(AI_SUPPORT_CHAT_ENABLED=False):
        user = await _create_user('cliente.multipestana@test.sintel')
        tab_a = await _connect_ws(user)
        await tab_a.receive_from(timeout=5)  # history (crea la sala)
        tab_b = await _connect_ws(user)
        await tab_b.receive_from(timeout=5)  # history (misma sala OPEN reutilizada)

        await tab_a.send_to(text_data=json.dumps({'message': 'hola desde tab A'}))

        event_a = json.loads(await tab_a.receive_from(timeout=5))
        event_b = json.loads(await tab_b.receive_from(timeout=5))
        assert event_a['message'] == 'hola desde tab A'
        assert event_b['message'] == 'hola desde tab A'  # antes: timeout, nunca llegaba

        await tab_a.disconnect()
        await tab_b.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_admin_multi_pestana_recibe_su_propia_respuesta_en_ambas():
    with override_settings(AI_SUPPORT_CHAT_ENABLED=False):
        client_user = await _create_user('cliente.admindup@test.sintel')
        admin_user = await _create_user('admin.multipestana@test.sintel', is_staff=True, is_superuser=True)

        client_comm = await _connect_ws(client_user)
        await client_comm.receive_from(timeout=5)  # history
        room = await _get_open_room(client_user)

        admin_tab_a = await _connect_ws(admin_user)
        admin_tab_b = await _connect_ws(admin_user)

        await admin_tab_a.send_to(text_data=json.dumps({
            'message': 'respuesta del admin', 'room_uuid': str(room.uuid),
        }))

        event_a = json.loads(await admin_tab_a.receive_from(timeout=5))
        event_b = json.loads(await admin_tab_b.receive_from(timeout=5))
        assert event_a['message'] == 'respuesta del admin'
        assert event_b['message'] == 'respuesta del admin'  # antes: timeout, nunca llegaba

        await client_comm.disconnect()
        await admin_tab_a.disconnect()
        await admin_tab_b.disconnect()


# ── 16. Customer 360 -- cotizaciones (Fase 7, AUDITORIA/21_AUDITORIA_CUSTOMER360.md,
# 2026-08-01). Antes Customer360Selector.build() no incluia cotizaciones en absoluto,
# pese a que el brief de Customer 360 las pide explicitamente y
# quotes.services.selectors.QuotationSelector.list_for_user ya existe con el mismo
# patron que orders/rentals. Sincrono (sin WebSocket): el selector solo lee datos ya
# persistidos.

@pytest.mark.django_db
def test_customer360_incluye_cotizaciones_del_cliente():
    from datetime import date, timedelta
    from decimal import Decimal
    from quotes.models import Quotation
    from support.services.customer360 import Customer360Selector

    User = get_user_model()
    owner = User.objects.create_user(email='cliente.c360@test.sintel', password='x')
    other = User.objects.create_user(email='otro.c360@test.sintel', password='x')

    own_quote = Quotation.objects.create(
        user=owner, client_name='Cliente 360', client_email=owner.email,
        valid_until=date.today() + timedelta(days=30), total_amount=Decimal('150000.00'),
    )
    Quotation.objects.create(
        user=other, client_name='Otro cliente', client_email=other.email,
        valid_until=date.today() + timedelta(days=30),
    )

    data = Customer360Selector.build(owner)

    assert len(data['quotations']) == 1
    assert data['quotations'][0]['uuid'] == str(own_quote.uuid)
    assert data['quotations'][0]['status'] == Quotation.STATUS_DRAFT
    assert data['quotations'][0]['total_amount'] == '150000.00'
    assert any(e['type'] == 'quotation' and e['uuid'] == str(own_quote.uuid) for e in data['timeline'])


# ── 16b. Customer 360 -- ordenes de operacion (Fase 14, AUDITORIA/28_AUDITORIA_OPERATIONS.md,
# 2026-08-03). Mismo gap ya corregido en Fase 7 para cotizaciones --
# operations.services.selectors.OperationSelector.list_for_user ya existia, Customer360
# simplemente no lo usaba.

@pytest.mark.django_db
def test_customer360_incluye_ordenes_de_operacion_del_cliente():
    from decimal import Decimal
    from orders.models import Order
    from operations.models import OperationTicket, OperationAssignment
    from operations.services.commands import OperationCommands
    from support.services.customer360 import Customer360Selector

    User = get_user_model()
    owner = User.objects.create_user(email='cliente.ops.c360@test.sintel', password='x')
    other = User.objects.create_user(email='otro.ops.c360@test.sintel', password='x')
    technician = User.objects.create_user(email='tecnico.ops.c360@test.sintel', password='x')

    order = Order.objects.create(user=owner, status='paid', total_amount=Decimal('200.00'))
    other_order = Order.objects.create(user=other, status='paid', total_amount=Decimal('150.00'))
    ticket = OperationCommands.ensure_tickets_for_order(order)[0]
    OperationCommands.ensure_tickets_for_order(other_order)
    OperationAssignment.objects.create(
        ticket=ticket, assignee=technician, role=OperationAssignment.ROLE_TECHNICIAN,
        status=OperationAssignment.STATUS_ACTIVE,
    )

    data = Customer360Selector.build(owner)

    assert len(data['operations']) == 1
    assert data['operations'][0]['uuid'] == str(ticket.uuid)
    assert data['operations'][0]['ticket_number'] == ticket.ticket_number
    assert data['operations'][0]['technician'] == technician.email
    assert any(e['type'] == 'operation' and e['uuid'] == str(ticket.uuid) for e in data['timeline'])


# ── 17. Flood/tamano de mensaje por WS (Fase 11, AUDITORIA/23_AUDITORIA_SEGURIDAD.md,
# 2026-08-01). Antes receive() no tenia NINGUN limite de frecuencia ni de tamano --
# distinto del rate-limit de turnos de IA (Fase 1 C1), que solo protege las respuestas
# del LLM, no la escritura cruda en BD ni el group_send a todos los admins.

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_mensaje_se_trunca_al_limite_maximo():
    from support.services.commands import MAX_MESSAGE_LENGTH

    with override_settings(AI_SUPPORT_CHAT_ENABLED=False):
        user = await _create_user('cliente.mensajelargo@test.sintel')
        comm = await _connect_ws(user)
        await comm.receive_from(timeout=5)  # history

        overlong = 'a' * (MAX_MESSAGE_LENGTH + 500)
        await comm.send_to(text_data=json.dumps({'message': overlong}))
        echo = json.loads(await comm.receive_from(timeout=5))
        assert len(echo['message']) == MAX_MESSAGE_LENGTH

        room = await _get_open_room(user)
        saved = await database_sync_to_async(lambda: ChatMessage.objects.get(room=room))()
        assert len(saved.message) == MAX_MESSAGE_LENGTH

        await comm.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_flood_de_mensajes_se_limita_por_usuario():
    from django.core.cache import cache
    from support.services.commands import MESSAGE_FLOOD_LIMIT

    with override_settings(AI_SUPPORT_CHAT_ENABLED=False):
        user = await _create_user('cliente.flood@test.sintel')
        # Redis (a diferencia de Postgres) no se resetea entre tests -- si Postgres reutiliza
        # el mismo PK de un usuario de una corrida anterior (TransactionTestCase reinicia
        # secuencias), la clave de flood podria arrancar con conteo residual. Limpieza
        # explicita para que el test sea determinista sin importar el historial de corridas.
        await database_sync_to_async(cache.delete)(f'support_msg_flood:{user.id}')
        comm = await _connect_ws(user)
        await comm.receive_from(timeout=5)  # history

        # Bien por encima del limite. Se drena el eco de cada mensaje aceptado (igual que
        # haria un cliente real) -- los descartados por flood no generan ningun eco, asi
        # que a partir del mensaje MESSAGE_FLOOD_LIMIT+1 no hay nada que recibir.
        accepted = 0
        for i in range(MESSAGE_FLOOD_LIMIT + 5):
            await comm.send_to(text_data=json.dumps({'message': f'mensaje {i}'}))
            if i < MESSAGE_FLOOD_LIMIT:
                echo = json.loads(await comm.receive_from(timeout=5))
                assert echo['message'] == f'mensaje {i}'
                accepted += 1
        assert accepted == MESSAGE_FLOOD_LIMIT

        # Confirma que los intentos de mas realmente no generaron ningun eco adicional.
        with pytest.raises(asyncio.TimeoutError):
            await comm.receive_from(timeout=2)

        room = await _get_open_room(user)
        count = await database_sync_to_async(
            lambda: ChatMessage.objects.filter(room=room, sender=user).count()
        )()
        assert count == MESSAGE_FLOOD_LIMIT


# ── 18. SupportTicketCommands / SupportTicketSelector (2026-09-15) ──────────
# Sincrono (sin WebSocket): solo ORM + service layer.

@pytest.mark.django_db
def test_supportticket_create_ticket_genera_numero_secuencial_unico():
    from support.services.commands import SupportTicketCommands

    User = get_user_model()
    room1 = ChatRoom.objects.create(user=User.objects.create_user(email='num1@test.sintel', password='x'))
    room2 = ChatRoom.objects.create(user=User.objects.create_user(email='num2@test.sintel', password='x'))

    t1 = SupportTicketCommands.create_ticket(room1)
    t2 = SupportTicketCommands.create_ticket(room2)

    assert t1.ticket_number == f'SUP-{t1.pk:06d}'
    assert t2.ticket_number == f'SUP-{t2.pk:06d}'
    assert t1.ticket_number != t2.ticket_number


@pytest.mark.django_db
def test_supportticket_create_ticket_idempotente_por_sala():
    from support.services.commands import SupportTicketCommands

    room = ChatRoom.objects.create(user=get_user_model().objects.create_user(email='idem@test.sintel', password='x'))

    first = SupportTicketCommands.create_ticket(room, subject='Primero', summary='Resumen original')
    second = SupportTicketCommands.create_ticket(room, subject='Segundo intento', summary='')

    assert first.pk == second.pk
    assert SupportTicket.objects.filter(chat_room=room).count() == 1
    second.refresh_from_db()
    # subject NO se pisa porque ya tenia valor; summary tampoco (vino vacio).
    assert second.subject == 'Primero'
    assert second.summary == 'Resumen original'


@pytest.mark.django_db
def test_supportticket_assign_change_status_set_priority():
    from support.services.commands import SupportTicketCommands

    User = get_user_model()
    room = ChatRoom.objects.create(user=User.objects.create_user(email='estados@test.sintel', password='x'))
    admin = User.objects.create_user(email='admin.estados@test.sintel', password='x', is_staff=True, is_superuser=True)
    ticket = SupportTicketCommands.create_ticket(room)
    assert ticket.status == SupportTicket.STATUS_NEW

    ticket = SupportTicketCommands.assign_ticket(ticket, admin)
    assert ticket.assigned_admin_id == admin.id
    assert ticket.status == SupportTicket.STATUS_OPEN  # NEW -> OPEN automatico al asignar

    ticket = SupportTicketCommands.set_priority(ticket, SupportTicket.PRIORITY_URGENT)
    assert ticket.priority == SupportTicket.PRIORITY_URGENT

    ticket = SupportTicketCommands.change_status(ticket, SupportTicket.STATUS_RESOLVED)
    assert ticket.resolved_at is not None
    ticket = SupportTicketCommands.change_status(ticket, SupportTicket.STATUS_CLOSED)
    assert ticket.closed_at is not None

    with pytest.raises(ValueError):
        SupportTicketCommands.change_status(ticket, 'NOT_A_REAL_STATUS')
    with pytest.raises(ValueError):
        SupportTicketCommands.set_priority(ticket, 'NOT_A_REAL_PRIORITY')


@pytest.mark.django_db
def test_supportticket_selector_list_for_admin_filtra():
    from support.services.commands import SupportTicketCommands
    from support.services.selectors import SupportTicketSelector

    User = get_user_model()
    admin = User.objects.create_user(email='admin.filtro@test.sintel', password='x', is_staff=True, is_superuser=True)
    room_open = ChatRoom.objects.create(user=User.objects.create_user(email='filtro1@test.sintel', password='x'))
    room_closed = ChatRoom.objects.create(user=User.objects.create_user(email='filtro2@test.sintel', password='x'))

    open_ticket = SupportTicketCommands.create_ticket(room_open)
    SupportTicketCommands.assign_ticket(open_ticket, admin)
    closed_ticket = SupportTicketCommands.create_ticket(room_closed)
    SupportTicketCommands.change_status(closed_ticket, SupportTicket.STATUS_CLOSED)

    assert list(SupportTicketSelector.list_for_admin(status=SupportTicket.STATUS_CLOSED)) == [closed_ticket]
    assert list(SupportTicketSelector.list_for_admin(assigned_admin_id=admin.id)) == [open_ticket]
    assert SupportTicketSelector.get_by_chat_room(room_open) == open_ticket
    assert SupportTicketSelector.get_by_chat_room(room_closed) == closed_ticket
