"""
PLAN_LLMDINAMICO sec. 3/4/5/10/16 (2026-09-25) -- salud, capacidades, tipos nuevos, servidores MCP y auth/TLS de los adapters.
Escritos, no ejecutados por instruccion del usuario (verificados con un script funcional contra dev). Sin red: `requests` se simula.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import requests
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from ai_provider.models import AIModel, AIProvider, MCPServer
from ai_provider.services import health, mcp_servers
from ai_provider.services.activation import ActivationCheckFailed, validate_model_for_activation
from ai_provider.services.commands import AIModelCommands, AIProviderCommands
from ai_provider.services.providers import get_adapter
from ai_provider.services.providers.base import ConnectionTestResult

pytestmark = pytest.mark.django_db


def _resp(status=200, payload=None, headers=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload if payload is not None else {}
    r.headers = headers or {'Content-Type': 'application/json'}
    r.text = ''
    r.raise_for_status.side_effect = None if status < 400 else requests.HTTPError(str(status))
    return r


def _provider(kind=AIProvider.KIND_OPENAI_COMPATIBLE, url='http://host.docker.internal:1234/v1', **extra):
    return AIProviderCommands.create_provider({'name': f'p-{kind}-{len(url)}', 'kind': kind, 'base_url': url, **extra})


# ---------------- salud ----------------
@pytest.mark.parametrize('ok,code,latency,active,expected', [
    (True, 'SUCCESS', 50, True, 'HEALTHY'),
    (True, 'SUCCESS', 9000, True, 'DEGRADED'),
    (False, 'CONNECTION_REFUSED', None, True, 'UNAVAILABLE'),
    (False, 'TIMEOUT', None, True, 'UNAVAILABLE'),
    (False, 'DNS', None, True, 'MISCONFIGURED'),
    (False, 'LOOPBACK_URL', None, True, 'MISCONFIGURED'),
    (False, 'UNAUTHORIZED', 10, True, 'MISCONFIGURED'),
    (True, 'SUCCESS', 50, False, 'DISABLED'),
])
def test_clasificacion_de_salud(ok, code, latency, active, expected):
    provider = SimpleNamespace(is_active=active)
    assert health.classify_health(provider, ok, code, latency) == expected


def test_check_health_persiste_estado_sin_secretos():
    p = _provider(api_key='SECRETO-H')
    fake = ConnectionTestResult(True, p.name, p.base_url, None, 12, 200, 'SUCCESS', '')
    with patch('ai_provider.services.health.get_adapter') as ga:
        ga.return_value.test_connection.return_value = fake
        report = health.check_provider_health(p)
    p.refresh_from_db()
    assert p.health_status == 'HEALTHY' and p.last_health_at is not None and p.last_test_ok is True
    assert 'SECRETO-H' not in str(report)


# ---------------- tipos nuevos ----------------
def test_gemini_no_exige_url_y_valida_la_url_si_se_da():
    ok = AIProviderCommands.create_provider({'name': 'g1', 'kind': 'gemini', 'api_key': 'k'})
    assert ok.kind in AIProvider.RUNNABLE_KINDS
    with pytest.raises(Exception):
        AIProviderCommands.create_provider({'name': 'g2', 'kind': 'gemini', 'base_url': 'http://169.254.169.254'})


@pytest.mark.parametrize('kind', ['generic-rest', 'custom'])
def test_tipos_solo_registro_no_son_ejecutables_como_primario(kind):
    p = _provider(kind=kind, url=f'http://host.docker.internal:1{len(kind)}00')
    m = AIModelCommands.add_model(p, 'm')
    assert kind not in AIProvider.RUNNABLE_KINDS
    with pytest.raises(ActivationCheckFailed) as exc:
        validate_model_for_activation(m)
    assert exc.value.report['error_code'] == 'KIND_NOT_RUNNABLE'


def test_gemini_lista_solo_modelos_con_generate_content_y_usa_cabecera_no_url():
    p = AIProviderCommands.create_provider({'name': 'g3', 'kind': 'gemini', 'api_key': 'KEY-G'})
    payload = {'models': [{'name': 'models/gemini-x', 'displayName': 'X', 'supportedGenerationMethods': ['generateContent']},
                          {'name': 'models/embed', 'supportedGenerationMethods': ['embedContent']}]}
    with patch('requests.get', return_value=_resp(200, payload)) as g:
        models = get_adapter(p).list_models()
    assert [m['model_id'] for m in models] == ['gemini-x']
    _, kwargs = g.call_args
    assert kwargs['headers'] == {'x-goog-api-key': 'KEY-G'} and 'KEY-G' not in g.call_args[0][0]


# ---------------- auth / TLS / timeouts ----------------
def test_auth_bearer_header_y_none():
    p = _provider(api_key='K')
    with patch('requests.get', return_value=_resp(200, {'data': []})) as g:
        get_adapter(p).test_connection()
    assert g.call_args.kwargs['headers'] == {'Authorization': 'Bearer K'}
    p.auth_type, p.api_key_header = 'header', 'x-custom'
    with patch('requests.get', return_value=_resp(200, {'data': []})) as g:
        get_adapter(p).test_connection()
    assert g.call_args.kwargs['headers'] == {'x-custom': 'K'}
    p.auth_type = 'none'
    with patch('requests.get', return_value=_resp(200, {'data': []})) as g:
        get_adapter(p).test_connection()
    assert g.call_args.kwargs['headers'] == {}


def test_tls_timeout_de_conexion_y_sin_redirects_se_aplican():
    p = _provider()
    p.verify_tls, p.connect_timeout = False, 3
    with patch('requests.get', return_value=_resp(200, {'data': []})) as g:
        get_adapter(p).test_connection()
    kw = g.call_args.kwargs
    assert kw['verify'] is False and kw['timeout'][0] == 3 and kw['allow_redirects'] is False


def test_endpoint_path_configurable_para_descubrir_modelos():
    p = _provider(endpoint_path='catalogo/modelos')
    with patch('requests.get', return_value=_resp(200, {'data': [{'id': 'a'}]})) as g:
        assert get_adapter(p).list_models() == [{'model_id': 'a', 'display_name': 'a'}]
    assert g.call_args.args[0].endswith('/v1/catalogo/modelos')


# ---------------- capacidades ----------------
def test_ollama_declara_capacidades_en_api_show():
    p = _provider(kind='ollama-nativo', url='http://sintel_ollama:11434')
    with patch('requests.post', return_value=_resp(200, {'capabilities': ['completion', 'tools', 'thinking']})):
        caps = get_adapter(p).detect_capabilities('qwen3.5:9b')
    assert caps['tool_calling'] is True and caps['reasoning'] is True and caps['vision'] is False and caps['streaming'] is True


def test_ollama_antiguo_sin_capabilities_queda_desconocido_no_inventado():
    p = _provider(kind='ollama-nativo', url='http://sintel_ollama:11434')
    with patch('requests.post', return_value=_resp(200, {'details': {}})):
        caps = get_adapter(p).detect_capabilities('viejo')
    assert all(v is None for v in caps.values())


def test_lm_studio_declara_tool_use_y_tipo():
    p = _provider()
    with patch('requests.get', return_value=_resp(200, {'type': 'vlm', 'capabilities': ['tool_use']})):
        caps = get_adapter(p).detect_capabilities('qwen/qwen3.5-9b')
    assert caps['tool_calling'] is True and caps['vision'] is True


def test_proveedor_sin_respuesta_no_pisa_lo_ya_sabido():
    p = _provider()
    m = AIModelCommands.add_model(p, 'm')
    AIModelCommands.update_model(m, {'capabilities': {'tool_calling': True}})
    with patch('requests.get', side_effect=requests.ConnectionError('x')):
        m = AIModelCommands.detect_capabilities(m)
    assert m.capabilities['tool_calling'] is True


def test_capacidades_manuales_se_validan():
    p = _provider()
    m = AIModelCommands.add_model(p, 'm')
    with pytest.raises(Exception):
        AIModelCommands.update_model(m, {'capabilities': {'volar': True}})
    with pytest.raises(Exception):
        AIModelCommands.update_model(m, {'capabilities': {'tool_calling': 'si'}})


def test_activacion_bloquea_tool_calling_false_y_avisa_si_es_desconocido():
    p = _provider()
    m = AIModelCommands.add_model(p, 'm')
    ok_ping = ConnectionTestResult(True, p.name, p.base_url, None, 5, 200, 'SUCCESS', '')
    with patch('ai_provider.services.activation.get_adapter') as ga:
        ga.return_value.test_connection.return_value = ok_ping
        ga.return_value.list_models.return_value = [{'model_id': 'm'}]
        report = validate_model_for_activation(m)
        assert report['ok'] and any('tool calling' in w for w in report['warnings'])
        AIModelCommands.update_model(m, {'capabilities': {'tool_calling': False}})
        with pytest.raises(ActivationCheckFailed) as exc:
            validate_model_for_activation(m)
        assert exc.value.report['error_code'] == 'TOOL_CALLING_UNSUPPORTED'
        # el canal de embeddings NO exige tool calling
        assert validate_model_for_activation(m, channel='embeddings')['ok']


# ---------------- MCP ----------------
def _mcp(**extra):
    return MCPServerFactory(**extra)


def MCPServerFactory(**extra):
    return mcp_servers.MCPServerCommands.create_server({'name': f'mcp-{len(extra)}', 'server_url': 'http://sintel_mcp:8000/mcp', **extra})


def test_mcp_rechaza_loopback_y_metadata():
    for url in ('http://localhost:9000', 'http://127.0.0.1:9000', 'http://169.254.169.254/x', 'ftp://x'):
        with pytest.raises(Exception):
            mcp_servers.MCPServerCommands.create_server({'name': 'm', 'server_url': url})


def test_mcp_handshake_ok_cuenta_tools_y_guarda_capacidades():
    s = _mcp(api_key='SECRETO-MCP', auth_type='bearer')
    init = _resp(200, {'result': {'protocolVersion': '2025-03-26', 'capabilities': {'tools': {}, 'prompts': {}}, 'serverInfo': {'name': 'x', 'version': '1'}}},
                 headers={'Content-Type': 'application/json', 'Mcp-Session-Id': 'sess'})
    tools = _resp(200, {'result': {'tools': [{'name': 'a'}, {'name': 'b'}]}})
    with patch('requests.post', side_effect=[init, _resp(202), tools]) as post:
        report = mcp_servers.MCPServerCommands.test_server(s)
    s.refresh_from_db()
    assert report['ok'] and s.status == 'HEALTHY' and s.tools_count == 2 and set(s.capabilities) == {'tools', 'prompts'}
    assert post.call_args_list[0].kwargs['headers']['Authorization'] == 'Bearer SECRETO-MCP'
    assert post.call_args_list[2].kwargs['headers']['Mcp-Session-Id'] == 'sess'
    assert 'SECRETO-MCP' not in str(report)


def test_mcp_respuesta_sse_se_interpreta():
    s = _mcp()
    body = 'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-03-26","capabilities":{"tools":{}}}}\n\n'
    init = _resp(200, headers={'Content-Type': 'text/event-stream'})
    init.text = body
    with patch('requests.post', side_effect=[init, _resp(202), _resp(200, {'result': {'tools': []}})]):
        assert mcp_servers.probe_mcp_server(s)['ok']


@pytest.mark.parametrize('status,expected', [(401, 'MISCONFIGURED'), (500, 'UNAVAILABLE')])
def test_mcp_errores_http_se_clasifican(status, expected):
    s = _mcp()
    with patch('requests.post', return_value=_resp(status)):
        report = mcp_servers.probe_mcp_server(s)
    assert not report['ok'] and report['status'] == expected


def test_mcp_desactivado_y_transporte_sse_no_se_prueban():
    s = _mcp(is_active=False)
    assert mcp_servers.probe_mcp_server(s)['status'] == 'DISABLED'
    s2 = _mcp(transport='sse', name='sse-1')
    assert mcp_servers.probe_mcp_server(s2)['error_code'] == 'UNSUPPORTED_TRANSPORT'


def test_mcp_no_es_proveedor_de_inferencia():
    assert _mcp().exposes_model_invocation is False


# ---------------- API ----------------
def _admin():
    c = APIClient(HTTP_HOST='localhost')
    c.force_authenticate(user=get_user_model().objects.create_user(email='adm-mcp@example.com', password='x', is_staff=True, is_superuser=True))
    return c


def test_api_mcp_nunca_devuelve_la_key_y_customer_no_accede():
    c = _admin()
    r = c.post('/api/v1/dashboard/ai-mcp-servers/', {'name': 'api-mcp', 'server_url': 'http://sintel_mcp:8000/mcp', 'auth_type': 'bearer', 'api_key': 'SECRETO-API'}, format='json')
    assert r.status_code == 201 and 'SECRETO-API' not in r.content.decode() and r.json()['has_api_key'] is True
    assert 'SECRETO-API' not in c.get('/api/v1/dashboard/ai-mcp-servers/').content.decode()
    cust = APIClient(HTTP_HOST='localhost')
    cust.force_authenticate(user=get_user_model().objects.create_user(email='cli-mcp@example.com', password='x'))
    assert cust.get('/api/v1/dashboard/ai-mcp-servers/').status_code in (401, 403)
    assert cust.post('/api/v1/dashboard/ai-providers/00000000-0000-0000-0000-000000000000/health/').status_code in (401, 403)


def test_api_model_settings_valida_rangos_y_capacidades():
    c = _admin()
    p = _provider()
    m = AIModelCommands.add_model(p, 'm')
    url = f'/api/v1/dashboard/ai-providers/{p.uuid}/model-settings/{m.uuid}/'
    assert c.patch(url, {'top_p': 7}, format='json').status_code == 400
    assert c.patch(url, {'capabilities': {'volar': True}}, format='json').status_code == 400
    r = c.patch(url, {'temperature': 0.3, 'top_p': 0.9, 'capabilities': {'tool_calling': True}}, format='json')
    assert r.status_code == 200 and r.json()['top_p'] == 0.9 and r.json()['capabilities']['tool_calling'] is True


def test_api_fallback_es_determinista():
    c = _admin()
    p1, p2 = _provider(), _provider(url='http://host.docker.internal:11434', kind='ollama-nativo')
    m1, m2 = AIModelCommands.add_model(p1, 'a'), AIModelCommands.add_model(p2, 'b')
    c.post('/api/v1/dashboard/ai-channel-config/set-primary/', {'model_uuid': str(m1.uuid), 'force': True}, format='json')
    assert c.post(f'/api/v1/dashboard/ai-providers/{p1.uuid}/fallback/', {'model_uuid': str(m1.uuid)}, format='json').status_code == 400  # el primario
    assert c.post(f'/api/v1/dashboard/ai-providers/{p2.uuid}/fallback/', {'model_uuid': str(m2.uuid)}, format='json').status_code == 200
    assert c.post(f'/api/v1/dashboard/ai-providers/{p2.uuid}/fallback/', {'model_uuid': str(m2.uuid)}, format='json').status_code == 400  # repetido
    assert c.post(f'/api/v1/dashboard/ai-providers/{p1.uuid}/fallback/', {'model_uuid': str(m2.uuid)}, format='json').status_code == 400  # otro proveedor


def test_endpoint_interno_entrega_generation_provider_uuid_y_overrides_del_canal():
    from ai_provider.models import AIChannelConfig
    from ai_provider.services.commands import AIChannelConfigCommands
    p = _provider()
    m = AIModelCommands.add_model(p, 'm')
    AIModelCommands.update_model(m, {'temperature': 0.7, 'top_p': 0.8})
    cfg, _ = AIChannelConfig.objects.get_or_create(channel='support_chat')
    AIChannelConfigCommands.set_primary(cfg, m)
    cfg.temperature = 0.1
    cfg.timeout = 45
    cfg.save()
    data = APIClient(HTTP_HOST='localhost').get('/api/v1/internal/ai/provider-config/?channel=support_chat').json()
    primary = data['primary']
    assert primary['provider_uuid'] == str(p.uuid) and primary['generation'] == {'temperature': 0.1, 'top_p': 0.8, 'max_tokens': None}
    assert primary['timeout'] == 45 and data['config_version'] >= 1
