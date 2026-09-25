"""
ai_provider/tests.py

FASE 1 del plan maestro "CONFIGURACION DINAMICA DE MODELOS LOCALES PARA CHAT
SUPPORT" (2026-08-13). Cubre: cifrado real en reposo (no solo mockeado -- lee
la columna cruda via SQL para confirmar que Postgres nunca ve la key en texto
plano), Selectors/Commands, y la resolucion de la cadena primary+fallback que
consumira el endpoint interno de AI Engine (FASE 2).
"""
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient

from ai_provider.models import AIChannelConfig, AIModel, AIProvider
from ai_provider.services.commands import AIChannelConfigCommands, AIModelCommands, AIProviderCommands
from ai_provider.services.selectors import AIChannelConfigSelector, AIProviderSelector

User = get_user_model()


class EncryptedApiKeyTests(TestCase):
    def test_api_key_is_encrypted_at_rest_in_postgres(self):
        provider = AIProvider.objects.create(
            name='LM Studio local', kind=AIProvider.KIND_OPENAI_COMPATIBLE,
            base_url='http://host.docker.internal:1234/v1', api_key='sk-real-secret-value-12345',
        )
        with connection.cursor() as cur:
            cur.execute('SELECT api_key FROM ai_provider_aiprovider WHERE id = %s', [provider.id])
            raw_value = cur.fetchone()[0]
        self.assertNotIn('sk-real-secret-value-12345', raw_value)
        self.assertNotEqual(raw_value, '')

        provider.refresh_from_db()
        self.assertEqual(provider.api_key, 'sk-real-secret-value-12345')

    def test_empty_api_key_stays_empty(self):
        provider = AIProvider.objects.create(
            name='Ollama local', kind=AIProvider.KIND_OLLAMA_NATIVE,
            base_url='http://sintel_ollama:11434', api_key='',
        )
        provider.refresh_from_db()
        self.assertEqual(provider.api_key, '')


class AIProviderValidationTests(TestCase):
    def test_base_url_required_for_ollama_and_openai_compatible(self):
        provider = AIProvider(name='sin url', kind=AIProvider.KIND_OLLAMA_NATIVE, base_url='')
        with self.assertRaises(Exception):
            provider.full_clean()

    def test_base_url_not_required_for_anthropic(self):
        provider = AIProvider(name='claude', kind=AIProvider.KIND_ANTHROPIC, base_url='', api_key='sk-ant-x')
        provider.full_clean()  # no debe lanzar

    def test_single_label_docker_hostname_is_valid_url(self):
        """Regresion real (plan 'AI Provider Runtime' FASE 2): la primera version de
        esta validacion usaba django.core.validators.URLValidator, que exige un
        dominio con TLD -- rechazaba exactamente 'http://sintel_ollama:11434', el
        proveedor real mas usado en este proyecto durante toda la campaña previa.
        Encontrado por el suite de tests existente (test_record_test_result, etc.)
        al fallar en masa tras agregar la validacion."""
        provider = AIProvider(
            name='ollama docker real', kind=AIProvider.KIND_OLLAMA_NATIVE,
            base_url='http://sintel_ollama:11434',
        )
        provider.full_clean()  # no debe lanzar

    def test_url_without_scheme_is_rejected(self):
        provider = AIProvider(
            name='sin esquema', kind=AIProvider.KIND_OLLAMA_NATIVE, base_url='sintel_ollama:11434',
        )
        with self.assertRaises(Exception):
            provider.full_clean()


class AIProviderCommandsTests(TestCase):
    def test_create_and_update_provider_via_commands(self):
        provider = AIProviderCommands.create_provider({
            'name': 'Ollama Windows', 'kind': AIProvider.KIND_OLLAMA_NATIVE,
            'base_url': 'http://host.docker.internal:11434', 'is_active': True,
        })
        self.assertTrue(provider.pk)

        updated = AIProviderCommands.update_provider(provider, {'is_active': False, 'display_order': 5})
        self.assertFalse(updated.is_active)
        self.assertEqual(updated.display_order, 5)

    def test_update_with_blank_api_key_does_not_erase_existing_key(self):
        provider = AIProviderCommands.create_provider({
            'name': 'openai real', 'kind': AIProvider.KIND_OPENAI_COMPATIBLE,
            'base_url': 'https://api.openai.com/v1', 'api_key': 'sk-original-key',
        })
        AIProviderCommands.update_provider(provider, {'display_order': 1, 'api_key': ''})
        provider.refresh_from_db()
        self.assertEqual(provider.api_key, 'sk-original-key')

    def test_delete_provider_is_soft(self):
        provider = AIProviderCommands.create_provider({
            'name': 'a borrar', 'kind': AIProvider.KIND_ANTHROPIC, 'base_url': '', 'api_key': 'sk-ant',
        })
        AIProviderCommands.delete_provider(provider)
        provider.refresh_from_db()
        self.assertTrue(provider.is_deleted)
        self.assertNotIn(provider, AIProviderSelector.list_providers())

    def test_record_test_result(self):
        provider = AIProviderCommands.create_provider({
            'name': 'probar', 'kind': AIProvider.KIND_OLLAMA_NATIVE, 'base_url': 'http://x:11434',
        })
        AIProviderCommands.record_test_result(provider, ok=True, latency_ms=120, error='')
        provider.refresh_from_db()
        self.assertTrue(provider.last_test_ok)
        self.assertEqual(provider.last_test_latency_ms, 120)
        self.assertIsNotNone(provider.last_tested_at)


class AIChannelConfigResolutionTests(TestCase):
    def setUp(self):
        self.provider = AIProvider.objects.create(
            name='ollama', kind=AIProvider.KIND_OLLAMA_NATIVE, base_url='http://sintel_ollama:11434',
        )
        self.primary = AIModelCommands.add_model(self.provider, 'llama3.1:8b')
        self.fallback1 = AIModelCommands.add_model(self.provider, 'qwen2.5:7b')
        self.fallback2 = AIModelCommands.add_model(self.provider, 'phi3:mini')
        self.user = User.objects.create_user(email='admin.chain@sintel.internal', password='x', is_staff=True)

    def test_resolved_chain_orders_primary_then_fallbacks(self):
        config = AIChannelConfigSelector.get_or_create_config()
        AIChannelConfigCommands.set_primary(config, self.primary, user=self.user)
        AIChannelConfigCommands.set_fallback_chain(config, [self.fallback1, self.fallback2], user=self.user)

        chain = AIChannelConfigSelector.get_resolved_chain()
        self.assertEqual([m.model_id for m in chain], ['llama3.1:8b', 'qwen2.5:7b', 'phi3:mini'])

    def test_resolved_chain_skips_inactive_provider(self):
        config = AIChannelConfigSelector.get_or_create_config()
        AIChannelConfigCommands.set_primary(config, self.primary, user=self.user)
        AIChannelConfigCommands.set_fallback_chain(config, [self.fallback1], user=self.user)

        self.provider.is_active = False
        self.provider.save(update_fields=['is_active'])

        chain = AIChannelConfigSelector.get_resolved_chain()
        self.assertEqual(chain, [])

    def test_resolved_chain_skips_inactive_model_but_keeps_rest(self):
        config = AIChannelConfigSelector.get_or_create_config()
        AIChannelConfigCommands.set_primary(config, self.primary, user=self.user)
        AIChannelConfigCommands.set_fallback_chain(config, [self.fallback1, self.fallback2], user=self.user)

        self.fallback1.is_active = False
        self.fallback1.save(update_fields=['is_active'])

        chain = AIChannelConfigSelector.get_resolved_chain()
        self.assertEqual([m.model_id for m in chain], ['llama3.1:8b', 'phi3:mini'])

    def test_empty_config_resolves_to_empty_chain(self):
        chain = AIChannelConfigSelector.get_resolved_chain()
        self.assertEqual(chain, [])

    def test_disabled_channel_resolves_to_empty_chain_even_with_valid_primary(self):
        """FASE 19: fix real -- ver comentario junto a AIChannelConfig.enabled en
        models.py, documentado desde FASE 4/18 pero nunca cableado en esta funcion."""
        config = AIChannelConfigSelector.get_or_create_config()
        AIChannelConfigCommands.set_primary(config, self.primary, user=self.user)
        AIChannelConfigCommands.set_fallback_chain(config, [self.fallback1], user=self.user)
        AIChannelConfigCommands.set_enabled(config, False, user=self.user)

        chain = AIChannelConfigSelector.get_resolved_chain()
        self.assertEqual(chain, [])


class AIModelUniqueConstraintTests(TestCase):
    def test_duplicate_model_id_on_same_provider_is_rejected(self):
        provider = AIProvider.objects.create(
            name='dup test', kind=AIProvider.KIND_OLLAMA_NATIVE, base_url='http://x:11434',
        )
        AIModel.objects.create(provider=provider, model_id='llama3.1:8b')
        with self.assertRaises(Exception):
            AIModel.objects.create(provider=provider, model_id='llama3.1:8b')


class InternalProviderConfigViewTests(TestCase):
    """FASE 2 -- endpoint que AI Engine consulta (sin JWT de usuario, ver docstring
    de ai_provider/api/internal_ai.py). No requiere autenticacion (AllowAny) a
    proposito -- se prueba con un APIClient anonimo, no autenticado."""

    def setUp(self):
        self.client = APIClient()

    def test_empty_config_returns_null_primary_not_error(self):
        resp = self.client.get('/api/v1/internal/ai/provider-config/?channel=support_chat')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {'channel': 'support_chat', 'enabled': True, 'config_version': 1, 'primary': None, 'fallbacks': []},
        )

    def test_resolved_chain_shape_matches_llm_factory_entry_format(self):
        """FASE 15/19: el shape ahora es el que produce BaseProviderAdapter.
        build_runtime_config() -- name/kind/base_url/model/api_key_env/api_key_value,
        sin 'model_id'/'provider' anidado (llm_factory.py consume 'primary' tal cual,
        sin remapear)."""
        provider = AIProvider.objects.create(
            name='ollama test', kind=AIProvider.KIND_OLLAMA_NATIVE,
            base_url='http://sintel_ollama:11434', api_key='',
        )
        model = AIModelCommands.add_model(provider, 'llama3.1:8b', display_name='Llama 3.1 8B')
        config = AIChannelConfigSelector.get_or_create_config()
        AIChannelConfigCommands.set_primary(config, model)

        resp = self.client.get('/api/v1/internal/ai/provider-config/?channel=support_chat')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['channel'], 'support_chat')
        self.assertTrue(data['enabled'])
        self.assertEqual(data['fallbacks'], [])
        primary = data['primary']
        self.assertEqual(primary['model'], 'llama3.1:8b')
        self.assertEqual(primary['kind'], AIProvider.KIND_OLLAMA_NATIVE)
        self.assertEqual(primary['base_url'], 'http://sintel_ollama:11434')
        self.assertIsNone(primary['api_key_value'])

    def test_api_key_is_returned_decrypted_to_this_internal_consumer(self):
        provider = AIProvider.objects.create(
            name='openai test', kind=AIProvider.KIND_OPENAI_COMPATIBLE,
            base_url='https://api.openai.com/v1', api_key='sk-real-secret',
        )
        model = AIModelCommands.add_model(provider, 'gpt-4o-mini')
        config = AIChannelConfigSelector.get_or_create_config()
        AIChannelConfigCommands.set_primary(config, model)

        resp = self.client.get('/api/v1/internal/ai/provider-config/?channel=support_chat')
        primary = resp.json()['primary']
        self.assertEqual(primary['api_key_value'], 'sk-real-secret')

    def test_defaults_to_support_chat_channel_when_not_specified(self):
        resp = self.client.get('/api/v1/internal/ai/provider-config/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['channel'], 'support_chat')

    def test_disabled_channel_returns_null_primary_even_with_config(self):
        """FASE 19: fix de un gap real -- antes de este fix, config.enabled=False no
        tenia ningun efecto sobre get_resolved_chain()/este endpoint (ver
        AIChannelConfigSelector.get_resolved_chain, comentario junto al campo
        AIChannelConfig.enabled en models.py, documentado desde FASE 4/18 pero nunca
        cableado)."""
        provider = AIProvider.objects.create(
            name='ollama disabled test', kind=AIProvider.KIND_OLLAMA_NATIVE, base_url='http://x:11434',
        )
        model = AIModelCommands.add_model(provider, 'llama3.1:8b')
        config = AIChannelConfigSelector.get_or_create_config()
        AIChannelConfigCommands.set_primary(config, model)
        AIChannelConfigCommands.set_enabled(config, False)

        resp = self.client.get('/api/v1/internal/ai/provider-config/?channel=support_chat')
        data = resp.json()
        self.assertFalse(data['enabled'])
        self.assertIsNone(data['primary'])
        self.assertEqual(data['fallbacks'], [])


class AdminAIProviderAPITests(TestCase):
    """FASE 3 -- /api/v1/dashboard/ai-providers/. Solo admin, api_key nunca sale en
    la respuesta de lectura."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(email='admin.aiprov@sintel.internal', password='Test12345!')
        self.customer = User.objects.create_user(email='cliente.aiprov@sintel.internal', password='Test12345!')

    def test_list_requires_admin(self):
        resp = self.client.get('/api/v1/dashboard/ai-providers/')
        self.assertEqual(resp.status_code, 401)

        self.client.force_authenticate(user=self.customer)
        resp = self.client.get('/api/v1/dashboard/ai-providers/')
        self.assertEqual(resp.status_code, 403)

    def test_create_provider_never_returns_api_key_in_response(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post('/api/v1/dashboard/ai-providers/', {
            'name': 'LM Studio Windows', 'kind': AIProvider.KIND_OPENAI_COMPATIBLE,
            'base_url': 'http://host.docker.internal:1234/v1', 'api_key': 'sk-super-secreto',
        })
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertNotIn('api_key', resp.json())
        self.assertTrue(resp.json()['has_api_key'])

        provider = AIProvider.objects.get(uuid=resp.json()['uuid'])
        self.assertEqual(provider.api_key, 'sk-super-secreto')

    def test_update_with_no_api_key_field_keeps_existing_key(self):
        self.client.force_authenticate(user=self.admin)
        provider = AIProviderCommands.create_provider({
            'name': 'openai', 'kind': AIProvider.KIND_OPENAI_COMPATIBLE,
            'base_url': 'https://api.openai.com/v1', 'api_key': 'sk-original',
        })
        resp = self.client.patch(f'/api/v1/dashboard/ai-providers/{provider.uuid}/', {'display_order': 3})
        self.assertEqual(resp.status_code, 200, resp.content)
        provider.refresh_from_db()
        self.assertEqual(provider.api_key, 'sk-original')
        self.assertEqual(provider.display_order, 3)

    def test_delete_is_soft_and_disappears_from_list(self):
        self.client.force_authenticate(user=self.admin)
        provider = AIProviderCommands.create_provider({
            'name': 'a borrar via api', 'kind': AIProvider.KIND_ANTHROPIC, 'api_key': 'sk-ant',
        })
        resp = self.client.delete(f'/api/v1/dashboard/ai-providers/{provider.uuid}/')
        self.assertEqual(resp.status_code, 204)

        resp = self.client.get('/api/v1/dashboard/ai-providers/')
        self.assertNotIn(str(provider.uuid), [p['uuid'] for p in resp.json()])

    def test_test_connection_action_persists_result(self):
        self.client.force_authenticate(user=self.admin)
        provider = AIProviderCommands.create_provider({
            'name': 'ollama probe', 'kind': AIProvider.KIND_OLLAMA_NATIVE, 'base_url': 'http://sintel_ollama:11434',
        })
        resp = self.client.post(f'/api/v1/dashboard/ai-providers/{provider.uuid}/test-connection/')
        self.assertEqual(resp.status_code, 200, resp.content)
        # Motor real esta arriba en este entorno de certificacion (docker-compose) --
        # se corrobora que el resultado se persistio, sea cual sea (no se fuerza ok=True
        # para no acoplar el test a que sintel_ollama este siempre disponible).
        provider.refresh_from_db()
        self.assertIsNotNone(provider.last_tested_at)
        self.assertIsNotNone(provider.last_test_ok)

    def test_add_model_and_set_as_primary(self):
        self.client.force_authenticate(user=self.admin)
        provider = AIProviderCommands.create_provider({
            'name': 'ollama models', 'kind': AIProvider.KIND_OLLAMA_NATIVE, 'base_url': 'http://x:11434',
        })
        resp = self.client.post(f'/api/v1/dashboard/ai-providers/{provider.uuid}/models/', {'model_id': 'phi3:mini'})
        self.assertEqual(resp.status_code, 201, resp.content)
        model_uuid = resp.json()['uuid']

        resp = self.client.post('/api/v1/dashboard/ai-channel-config/set-primary/', {'model_uuid': model_uuid, 'force': True})
        # force=True: el proveedor de este test (http://x:11434) no existe; la validacion previa se prueba en tests_activation.py
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()['primary_model']['model_id'], 'phi3:mini')

    def test_set_fallback_chain_preserves_order(self):
        self.client.force_authenticate(user=self.admin)
        provider = AIProviderCommands.create_provider({
            'name': 'chain test', 'kind': AIProvider.KIND_OLLAMA_NATIVE, 'base_url': 'http://x:11434',
        })
        m1 = AIModelCommands.add_model(provider, 'a')
        m2 = AIModelCommands.add_model(provider, 'b')

        resp = self.client.post('/api/v1/dashboard/ai-channel-config/set-fallback-chain/', {
            'model_uuids': [str(m2.uuid), str(m1.uuid)],
        }, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual([f['model_id'] for f in resp.json()['fallbacks']], ['b', 'a'])

    def test_activate_deactivate_set_default_actions(self):
        self.client.force_authenticate(user=self.admin)
        provider = AIProviderCommands.create_provider({
            'name': 'toggle test', 'kind': AIProvider.KIND_OLLAMA_NATIVE, 'base_url': 'http://x:11434',
            'is_active': False,
        })

        resp = self.client.post(f'/api/v1/dashboard/ai-providers/{provider.uuid}/activate/')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()['is_active'])

        resp = self.client.post(f'/api/v1/dashboard/ai-providers/{provider.uuid}/deactivate/')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertFalse(resp.json()['is_active'])

        resp = self.client.post(f'/api/v1/dashboard/ai-providers/{provider.uuid}/set-default/')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()['is_default'])

    def test_set_default_deactivates_previous_default(self):
        p1 = AIProviderCommands.create_provider({'name': 'p1', 'kind': AIProvider.KIND_OLLAMA_NATIVE, 'base_url': 'http://x:11434'})
        p2 = AIProviderCommands.create_provider({'name': 'p2', 'kind': AIProvider.KIND_OLLAMA_NATIVE, 'base_url': 'http://y:11434'})
        AIProviderCommands.set_default(p1)
        AIProviderCommands.set_default(p2)
        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertFalse(p1.is_default)
        self.assertTrue(p2.is_default)


class AIProviderAuditTests(TestCase):
    """FASE 34 (plan actual) -- gap real encontrado en AI_PROVIDER_RUNTIME_AUDIT.md
    seccion 11: ninguna accion administrativa dejaba SecurityEvent antes de esto."""

    def setUp(self):
        self.admin = User.objects.create_superuser(email='audit.admin@sintel.internal', password='Test12345!')

    def test_create_provider_logs_security_event(self):
        from security.models import SecurityEvent
        provider = AIProviderCommands.create_provider(
            {'name': 'audited', 'kind': AIProvider.KIND_OLLAMA_NATIVE, 'base_url': 'http://x:11434'}, user=self.admin,
        )
        event = SecurityEvent.objects.filter(event_type=SecurityEvent.AI_PROVIDER_CREATED).latest('created_at')
        self.assertEqual(event.user, self.admin)
        self.assertEqual(event.metadata['provider_uuid'], str(provider.uuid))
        self.assertNotIn('api_key', event.metadata)

    def test_delete_provider_logs_generic_admin_delete_event(self):
        from security.models import SecurityEvent
        provider = AIProviderCommands.create_provider(
            {'name': 'to delete', 'kind': AIProvider.KIND_ANTHROPIC, 'api_key': 'sk-ant-x'}, user=self.admin,
        )
        AIProviderCommands.delete_provider(provider, user=self.admin)
        event = SecurityEvent.objects.filter(event_type=SecurityEvent.ADMIN_RESOURCE_DELETED).latest('created_at')
        self.assertEqual(event.metadata['resource'], 'AIProvider')
        self.assertNotIn('api_key', str(event.metadata))
        self.assertNotIn('sk-ant-x', str(event.metadata))

    def test_update_provider_never_logs_raw_api_key(self):
        from security.models import SecurityEvent
        provider = AIProviderCommands.create_provider(
            {'name': 'secret holder', 'kind': AIProvider.KIND_ANTHROPIC, 'api_key': 'sk-ant-super-secret'}, user=self.admin,
        )
        AIProviderCommands.update_provider(provider, {'api_key': 'sk-ant-new-value'}, user=self.admin)
        events = SecurityEvent.objects.filter(event_type=SecurityEvent.AI_PROVIDER_UPDATED)
        for event in events:
            self.assertNotIn('sk-ant-new-value', str(event.metadata))
            self.assertNotIn('sk-ant-super-secret', str(event.metadata))
        latest = events.latest('created_at')
        self.assertTrue(latest.metadata['api_key_changed'])

    def test_channel_config_change_logs_event(self):
        from security.models import SecurityEvent
        provider = AIProviderCommands.create_provider({'name': 'chan', 'kind': AIProvider.KIND_OLLAMA_NATIVE, 'base_url': 'http://x:11434'}, user=self.admin)
        model = AIModelCommands.add_model(provider, 'm1', user=self.admin)
        config = AIChannelConfigSelector.get_or_create_config()
        AIChannelConfigCommands.set_primary(config, model, user=self.admin)
        event = SecurityEvent.objects.filter(event_type=SecurityEvent.AI_CHANNEL_CHANGED).latest('created_at')
        self.assertEqual(event.metadata['action'], 'set_primary')
        self.assertEqual(event.metadata['model_id'], 'm1')
