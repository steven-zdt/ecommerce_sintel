"""
security/tests_mcp_tokens.py -- tokens personales del MCP y auditoria durable (PROMPT MCP, FASE 2). Escritos, NO ejecutados por instruccion del usuario; la misma logica se verifico
en dev con un script funcional (29 comprobaciones) y con un cliente MCP real (fase `pat` de mcp_server/scripts/protocol_smoke.py).
"""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from security.models import McpAccessToken, SecurityEvent
from security.services.mcp_tokens import McpTokenCommands, McpTokenError

pytestmark = pytest.mark.django_db
D = '/api/v1/dashboard/'
EXCHANGE = '/api/v1/internal/mcp/exchange/'


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def admin():
    return get_user_model().objects.create_user(email='mcp-tok-admin@example.com', password='x', is_staff=True, is_superuser=True)


def _client(user):
    c = APIClient(HTTP_HOST='localhost')
    c.force_authenticate(user=user)
    return c


def test_solo_se_guarda_el_hash_y_el_token_se_ve_una_vez(admin):
    resp = _client(admin).post(D + 'mcp-tokens/', {'name': 'cli', 'days': 30}, format='json')
    assert resp.status_code == 201
    plain = resp.json()['token']
    row = McpAccessToken.objects.get(uuid=resp.json()['uuid'])
    assert plain.startswith('smcp_') and row.token_hash != plain and len(row.token_hash) == 64
    listing = _client(admin).get(D + 'mcp-tokens/').content.decode()
    assert plain not in listing and row.token_hash not in listing


@pytest.mark.parametrize('days', [0, 91, 9999])
def test_vigencia_fuera_de_rango_rechazada(admin, days):
    assert _client(admin).post(D + 'mcp-tokens/', {'name': 'x', 'days': days}, format='json').status_code == 400


def test_canje_devuelve_jwt_corto_con_claim_via_mcp(admin):
    _, plain = McpTokenCommands.create_token(admin, 'cli', 5)
    resp = APIClient(HTTP_HOST='localhost').post(EXCHANGE, {'token': plain}, format='json')
    assert resp.status_code == 200 and resp.json()['expires_in'] <= 900
    claims = AccessToken(resp.json()['access'])
    assert claims.get('via') == 'mcp' and claims.get('user_id') is not None


@pytest.mark.parametrize('bad', ['', 'no-es-token', 'smcp_' + 'x' * 43])
def test_canje_rechazado_es_generico_y_queda_auditado(bad):
    resp = APIClient(HTTP_HOST='localhost').post(EXCHANGE, {'token': bad}, format='json')
    assert resp.status_code == 401 and resp.json() == {'error': 'invalid_token'}
    assert SecurityEvent.objects.filter(event_type=SecurityEvent.MCP_TOKEN_EXCHANGE_FAILED).exists()


def test_revocado_caducado_y_usuario_sin_permisos_no_canjean(admin):
    api = APIClient(HTTP_HOST='localhost')
    token, plain = McpTokenCommands.create_token(admin, 'cli', 5)
    assert api.post(EXCHANGE, {'token': plain}, format='json').status_code == 200
    McpAccessToken.objects.filter(pk=token.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
    assert api.post(EXCHANGE, {'token': plain}, format='json').status_code == 401
    McpAccessToken.objects.filter(pk=token.pk).update(expires_at=timezone.now() + timedelta(days=1))
    get_user_model().objects.filter(pk=admin.pk).update(is_superuser=False)
    assert api.post(EXCHANGE, {'token': plain}, format='json').status_code == 401
    get_user_model().objects.filter(pk=admin.pk).update(is_superuser=True)
    McpTokenCommands.revoke_token(token, admin)
    assert api.post(EXCHANGE, {'token': plain}, format='json').status_code == 401


def test_un_jwt_via_mcp_no_puede_crear_ni_revocar_tokens(admin):
    token, plain = McpTokenCommands.create_token(admin, 'cli', 5)
    jwt = APIClient(HTTP_HOST='localhost').post(EXCHANGE, {'token': plain}, format='json').json()['access']
    c = APIClient(HTTP_HOST='localhost')
    c.credentials(HTTP_AUTHORIZATION='Bearer ' + jwt)
    assert c.post(D + 'mcp-tokens/', {'name': 'persistencia', 'days': 30}, format='json').status_code == 400
    assert c.delete(D + f'mcp-tokens/{token.uuid}/').status_code == 400
    assert not McpAccessToken.objects.filter(name='persistencia').exists()


def test_otro_admin_y_customer_no_gestionan_tokens_ajenos(admin):
    token, _ = McpTokenCommands.create_token(admin, 'cli', 5)
    other = get_user_model().objects.create_user(email='mcp-tok-other@example.com', password='x', is_staff=True, is_superuser=True)
    assert _client(other).delete(D + f'mcp-tokens/{token.uuid}/').status_code == 404
    cust = get_user_model().objects.create_user(email='mcp-tok-cust@example.com', password='x')
    assert _client(cust).get(D + 'mcp-tokens/').status_code in (401, 403)


def test_eventos_no_guardan_token_ni_hash(admin):
    token, plain = McpTokenCommands.create_token(admin, 'cli', 5)
    APIClient(HTTP_HOST='localhost').post(EXCHANGE, {'token': plain}, format='json')
    meta = str(list(SecurityEvent.objects.filter(event_type__startswith='MCP_TOKEN').values_list('metadata', flat=True)))
    assert plain not in meta and token.token_hash not in meta


def test_canje_tiene_limite_por_ip():
    api = APIClient(HTTP_HOST='localhost')
    codes = {api.post(EXCHANGE, {'token': 'smcp_' + 'y' * 43}, format='json').status_code for _ in range(35)}
    assert codes == {401}
    assert SecurityEvent.objects.filter(event_type=SecurityEvent.MCP_TOKEN_EXCHANGE_FAILED, metadata__reason='rate_limited').exists()


def test_create_token_exige_admin(admin):
    cust = get_user_model().objects.create_user(email='mcp-tok-c2@example.com', password='x')
    with pytest.raises(McpTokenError):
        McpTokenCommands.create_token(cust, 'x', 5)


def test_auditoria_del_mcp_guarda_lista_blanca_sin_valores(admin):
    resp = _client(admin).post(D + 'mcp/audit/', {'tool': 'crud.update', 'resource': 'categories', 'operation': 'update', 'target': 'u', 'result': 'ok',
                                                  'changed_fields': ['description'], 'secreto': 'NO-DEBE-GUARDARSE', 'password': 'x'}, format='json')
    assert resp.status_code == 201
    event = SecurityEvent.objects.filter(event_type=SecurityEvent.MCP_ACTION).latest('created_at')
    assert event.user_id == admin.id and event.metadata['changed_fields'] == ['description'] and event.metadata['via_mcp'] is True
    assert 'NO-DEBE-GUARDARSE' not in str(event.metadata) and 'password' not in event.metadata
    cust = get_user_model().objects.create_user(email='mcp-tok-c3@example.com', password='x')
    assert _client(cust).post(D + 'mcp/audit/', {'tool': 'x'}, format='json').status_code in (401, 403)
