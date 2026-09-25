"""
PLAN_LLMDINAMICO FASE 3 (2026-09-25) -- guard SSRF de la URL de un proveedor. Escritos, no ejecutados por instruccion del usuario.
Sin red: resolve_dns=False, o socket simulado.
"""
import pytest
from django.core.exceptions import ValidationError

from ai_provider.models import AIProvider
from ai_provider.services import url_guard
from ai_provider.services.url_guard import UnsafeProviderURL, validate_provider_url


@pytest.mark.parametrize('url', [
    'http://169.254.169.254/latest/meta-data', 'http://[fd00:ec2::254]/', 'http://metadata.google.internal/computeMetadata/v1/',
    'http://100.100.100.200/', 'http://169.254.10.10:11434', 'http://0.0.0.0:11434', 'http://[::ffff:169.254.169.254]/',
    'http://127.0.0.1:2375/containers/json', 'http://user:pass@sintel_ollama:11434', 'file:///etc/passwd', 'gopher://x/', 'ftp://x/',
    'unix:///var/run/docker.sock', 'http://',
])
def test_urls_peligrosas_se_bloquean(url):
    with pytest.raises(UnsafeProviderURL):
        validate_provider_url(url, resolve_dns=False)


@pytest.mark.parametrize('url', [
    'http://sintel_ollama:11434', 'http://host.docker.internal:1234/v1', 'http://127.0.0.1:8420/v1', 'http://192.168.1.20:11434',
    'https://provider.example/v1', 'http://localhost:11434',
])
def test_urls_legitimas_locales_y_remotas_se_permiten(url):
    assert validate_provider_url(url, resolve_dns=False) == url


def test_host_que_resuelve_a_metadatos_se_bloquea(monkeypatch):
    monkeypatch.setattr(url_guard, '_resolve', lambda host: {'169.254.169.254'})
    with pytest.raises(UnsafeProviderURL):
        validate_provider_url('http://inocente.example/v1')


def test_host_que_no_resuelve_se_acepta_al_guardar(monkeypatch):
    monkeypatch.setattr(url_guard, '_resolve', lambda host: set())
    assert validate_provider_url('http://aun-no-existe:11434')


def test_modelo_rechaza_url_ssrf_en_clean():
    provider = AIProvider(name='malo', kind=AIProvider.KIND_OPENAI_COMPATIBLE, base_url='http://169.254.169.254/v1')
    with pytest.raises(ValidationError) as exc:
        provider.clean()
    assert 'base_url' in exc.value.message_dict


def test_mensaje_de_error_no_filtra_la_url_con_credenciales():
    with pytest.raises(UnsafeProviderURL) as exc:
        validate_provider_url('http://admin:SECRETO@sintel_ollama:11434', resolve_dns=False)
    assert 'SECRETO' not in str(exc.value)


# ----- endpoint interno: token de servicio ADK -> Django
from django.test import RequestFactory, override_settings  # noqa: E402

from ai_provider.api.internal_ai import AiProviderConfigView  # noqa: E402


@pytest.mark.django_db
@override_settings(AI_SERVICE_TOKEN='tok-ok', AI_SERVICE_TOKEN_PREVIOUS='tok-viejo', AI_PROVIDER_CONFIG_TOKEN_REQUIRED=True)
def test_endpoint_interno_enforce_rechaza_sin_token_y_acepta_con_token_o_previo():
    view = AiProviderConfigView.as_view()
    rf = RequestFactory()
    assert view(rf.get('/x/')).status_code == 403
    assert view(rf.get('/x/', HTTP_X_AI_SERVICE_TOKEN='otro')).status_code == 403
    assert view(rf.get('/x/', HTTP_X_AI_SERVICE_TOKEN='tok-ok')).status_code == 200
    assert view(rf.get('/x/', HTTP_X_AI_SERVICE_TOKEN='tok-viejo')).status_code == 200


@pytest.mark.django_db
@override_settings(AI_SERVICE_TOKEN='tok-ok', AI_PROVIDER_CONFIG_TOKEN_REQUIRED=False)
def test_endpoint_interno_monitor_deja_pasar_y_loguea(caplog):
    with caplog.at_level('WARNING'):
        resp = AiProviderConfigView.as_view()(RequestFactory().get('/x/'))
    assert resp.status_code == 200
    assert 'ai_provider_config_token_invalid mode=monitor' in caplog.text and 'tok-ok' not in caplog.text


# ----- INCIDENTE 2026-09-25: localhost dentro de Docker
from django.test import override_settings as _override  # noqa: E402


@pytest.mark.parametrize('url', ['http://localhost:1234/v1', 'http://127.0.0.1:1234/v1', 'http://[::1]:11434', 'http://0.0.0.0:1234/v1'])
def test_modelo_rechaza_loopback_al_guardar(url):
    provider = AIProvider(name='lm', kind=AIProvider.KIND_OPENAI_COMPATIBLE, base_url=url)
    with pytest.raises(ValidationError) as exc:
        provider.clean()
    assert 'host.docker.internal' in exc.value.message_dict['base_url'][0]


@_override(AI_PROVIDER_ALLOW_LOOPBACK=True)
def test_loopback_permitido_solo_con_el_flag_explicito():
    AIProvider(name='lm', kind=AIProvider.KIND_OPENAI_COMPATIBLE, base_url='http://localhost:1234/v1').clean()


def test_host_docker_internal_sigue_permitido():
    AIProvider(name='lm', kind=AIProvider.KIND_OPENAI_COMPATIBLE, base_url='http://host.docker.internal:1234/v1').clean()
