"""
PLAN_LLMDINAMICO F1/F7/F18 (2026-09-25) -- config_version, historial y rollback. Escritos, no ejecutados por instruccion del usuario.
"""
import pytest

from ai_provider.models import AIChannelConfig, AIConfigRevision
from ai_provider.services import revisions
from ai_provider.services.commands import AIChannelConfigCommands, AIModelCommands, AIProviderCommands
from ai_provider.services.revisions import RollbackError

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup():
    a = AIProviderCommands.create_provider({'name': 'ollama', 'kind': 'ollama-nativo', 'base_url': 'http://sintel_ollama:11434', 'api_key': ''})
    b = AIProviderCommands.create_provider({'name': 'lmstudio', 'kind': 'openai-compatible', 'base_url': 'http://host.docker.internal:1234/v1',
                                            'api_key': 'SECRETO-B'})
    ma = AIModelCommands.add_model(a, 'qwen3.5:9b')
    mb = AIModelCommands.add_model(b, 'qwen-lm')
    config, _ = AIChannelConfig.objects.get_or_create(channel='support_chat')
    return a, b, ma, mb, config


def test_cada_cambio_de_canal_sube_config_version_y_guarda_snapshot(setup):
    a, b, ma, mb, config = setup
    v0 = config.config_version
    AIChannelConfigCommands.set_primary(config, ma)
    AIChannelConfigCommands.set_fallback_chain(config, [mb])
    config.refresh_from_db()
    assert config.config_version == v0 + 2
    rev = AIConfigRevision.objects.get(scope='channel', target_uuid=config.uuid, version=config.config_version)
    assert rev.snapshot['primary_model_uuid'] == str(ma.uuid) and rev.snapshot['fallback_model_uuids'] == [str(mb.uuid)]


def test_snapshots_nunca_contienen_la_api_key(setup):
    a, b, ma, mb, config = setup
    AIProviderCommands.update_provider(b, {'base_url': 'http://host.docker.internal:1235/v1'})
    for rev in AIConfigRevision.objects.all():
        assert 'SECRETO-B' not in repr(rev.snapshot)
    assert AIConfigRevision.objects.filter(scope='provider', target_uuid=b.uuid).latest('version').snapshot['has_api_key'] is True


def test_rollback_de_canal_restaura_primario_y_fallbacks(setup):
    a, b, ma, mb, config = setup
    AIChannelConfigCommands.set_primary(config, ma)
    AIChannelConfigCommands.set_fallback_chain(config, [mb])
    good = AIChannelConfig.objects.get(pk=config.pk).config_version
    AIChannelConfigCommands.set_primary(config, mb)
    AIChannelConfigCommands.set_fallback_chain(config, [])
    restored = revisions.rollback_channel(config, good)
    assert restored.primary_model_id == ma.id
    assert [f.model_id for f in restored.fallbacks.order_by('order')] == [mb.id]
    assert restored.config_version > good  # el rollback es un cambio nuevo, no reescribe el historial
    assert AIConfigRevision.objects.filter(scope='channel', target_uuid=config.uuid, action=f'rollback_to_v{good}').exists()


def test_rollback_de_canal_es_todo_o_nada_si_un_modelo_fue_borrado(setup):
    a, b, ma, mb, config = setup
    AIChannelConfigCommands.set_primary(config, ma)
    AIChannelConfigCommands.set_fallback_chain(config, [mb])
    target = AIChannelConfig.objects.get(pk=config.pk).config_version
    AIModelCommands.delete_model(mb)
    AIChannelConfigCommands.set_fallback_chain(config, [])
    before = AIChannelConfig.objects.get(pk=config.pk).config_version
    with pytest.raises(RollbackError):
        revisions.rollback_channel(config, target)
    assert AIChannelConfig.objects.get(pk=config.pk).config_version == before


def test_rollback_version_inexistente(setup):
    with pytest.raises(RollbackError):
        revisions.rollback_channel(setup[4], 9999)


def test_rollback_de_proveedor_restaura_campos_y_conserva_la_key(setup):
    a, b, ma, mb, config = setup
    AIProviderCommands.update_provider(b, {'base_url': 'http://host.docker.internal:9999/v1', 'api_key': 'NUEVA-KEY'})
    revisions.rollback_provider(b, 1)
    b.refresh_from_db()
    assert b.base_url == 'http://host.docker.internal:1234/v1'
    assert b.api_key == 'NUEVA-KEY'  # el rollback no toca secretos


def test_rollback_de_proveedor_revalida_la_url_ssrf(setup):
    a, b, ma, mb, config = setup
    rev = AIConfigRevision.objects.get(scope='provider', target_uuid=b.uuid, version=1)
    rev.snapshot = {**rev.snapshot, 'base_url': 'http://169.254.169.254/v1'}
    rev.save()
    with pytest.raises(RollbackError):
        revisions.rollback_provider(b, 1)


def test_alta_de_proveedor_guarda_version_1(setup):
    a = setup[0]
    assert a.config_version == 1
    assert AIConfigRevision.objects.filter(scope='provider', target_uuid=a.uuid, version=1, action='created').exists()
