"""
PLAN_LLMDINAMICO sec. 7 (2026-09-25) -- validacion previa a activar un primario. Escritos, no ejecutados por instruccion del usuario.
El adapter se simula: sin red.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from ai_provider.models import AIChannelConfig
from ai_provider.services import activation
from ai_provider.services.activation import ActivationCheckFailed, validate_model_for_activation
from ai_provider.services.commands import AIModelCommands, AIProviderCommands
from ai_provider.services.providers.base import ERROR_CONNECTION_REFUSED, SUCCESS, ConnectionTestResult

pytestmark = pytest.mark.django_db


class _FakeAdapter:
    def __init__(self, ok=True, models=None):
        self.ok, self.models = ok, models if models is not None else [{'model_id': 'qwen3.5:9b'}]

    def test_connection(self):
        return ConnectionTestResult(self.ok, 'p', 'http://x', None, 12, 200 if self.ok else None,
                                    SUCCESS if self.ok else ERROR_CONNECTION_REFUSED, '' if self.ok else 'Conexion rechazada.')

    def list_models(self):
        return self.models


@pytest.fixture
def model():
    provider = AIProviderCommands.create_provider({'name': 'ollama', 'kind': 'ollama-nativo', 'base_url': 'http://sintel_ollama:11434'})
    return AIModelCommands.add_model(provider, 'qwen3.5:9b')


def _patch(monkeypatch, **kw):
    monkeypatch.setattr(activation, 'get_adapter', lambda provider: _FakeAdapter(**kw))


def test_validacion_correcta(monkeypatch, model):
    _patch(monkeypatch)
    report = validate_model_for_activation(model)
    assert report['ok'] and 'connectivity' in report['checks'] and 'model_available' in report['checks']


def test_falla_si_no_hay_conectividad(monkeypatch, model):
    _patch(monkeypatch, ok=False)
    with pytest.raises(ActivationCheckFailed) as exc:
        validate_model_for_activation(model)
    assert exc.value.report['error_code'] == ERROR_CONNECTION_REFUSED


def test_falla_si_el_proveedor_no_reporta_el_modelo(monkeypatch, model):
    _patch(monkeypatch, models=[{'model_id': 'otro'}])
    with pytest.raises(ActivationCheckFailed) as exc:
        validate_model_for_activation(model)
    assert exc.value.report['error_code'] == 'MODEL_NOT_FOUND'


def test_proveedor_sin_listado_pasa_con_advertencia(monkeypatch, model):
    _patch(monkeypatch, models=[])
    report = validate_model_for_activation(model)
    assert report['ok'] and report['warnings']


def test_falla_si_el_proveedor_esta_inactivo(monkeypatch, model):
    _patch(monkeypatch)
    AIProviderCommands.deactivate(model.provider)
    model.refresh_from_db()
    with pytest.raises(ActivationCheckFailed) as exc:
        validate_model_for_activation(model)
    assert exc.value.report['error_code'] == 'PROVIDER_INACTIVE'


def _admin_client():
    user = get_user_model().objects.create_user(email='adm@example.com', password='x', is_staff=True, is_superuser=True)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_set_primary_409_y_no_cambia_nada_si_la_validacion_falla(monkeypatch, model):
    _patch(monkeypatch, ok=False)
    resp = _admin_client().post('/api/v1/dashboard/ai-channel-config/set-primary/', {'model_uuid': str(model.uuid)}, format='json')
    assert resp.status_code == 409 and resp.json()['error'] == 'validation_failed'
    assert AIChannelConfig.objects.get(channel='support_chat').primary_model_id is None


def test_set_primary_con_force_omite_la_validacion(monkeypatch, model):
    _patch(monkeypatch, ok=False)
    resp = _admin_client().post('/api/v1/dashboard/ai-channel-config/set-primary/',
                                {'model_uuid': str(model.uuid), 'force': True}, format='json')
    assert resp.status_code == 200 and resp.json()['primary_model']['model_id'] == 'qwen3.5:9b'


def test_set_primary_correcto_sin_force(monkeypatch, model):
    _patch(monkeypatch)
    resp = _admin_client().post('/api/v1/dashboard/ai-channel-config/set-primary/', {'model_uuid': str(model.uuid)}, format='json')
    assert resp.status_code == 200
    assert resp.json()['config_version'] > 1


def test_quitar_el_primario_no_requiere_validacion(monkeypatch, model):
    _patch(monkeypatch, ok=False)
    resp = _admin_client().post('/api/v1/dashboard/ai-channel-config/set-primary/', {'model_uuid': None}, format='json')
    assert resp.status_code == 200 and resp.json()['primary_model'] is None


def test_validate_model_dry_run_no_persiste(monkeypatch, model):
    _patch(monkeypatch)
    resp = _admin_client().post('/api/v1/dashboard/ai-channel-config/validate-model/', {'model_uuid': str(model.uuid)}, format='json')
    assert resp.status_code == 200 and resp.json()['ok']
    config = AIChannelConfig.objects.filter(channel='support_chat').first()
    assert config is None or config.primary_model_id is None


def test_un_customer_no_puede_validar_ni_activar(model):
    user = get_user_model().objects.create_user(email='cli@example.com', password='x')
    client = APIClient()
    client.force_authenticate(user=user)
    for path in ('set-primary', 'validate-model', 'rollback'):
        resp = client.post(f'/api/v1/dashboard/ai-channel-config/{path}/', {'model_uuid': str(model.uuid), 'version': 1}, format='json')
        assert resp.status_code in (401, 403)
    assert client.get('/api/v1/dashboard/ai-channel-config/history/').status_code in (401, 403)
