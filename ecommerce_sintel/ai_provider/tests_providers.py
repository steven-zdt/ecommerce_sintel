"""
ai_provider/tests_providers.py

Plan "AI Provider Runtime" FASE 7-12: BaseProviderAdapter + Ollama/OpenAI-
compatible/Anthropic adapters, AIProviderConnectionTestService, model_discovery.
Archivo separado de tests.py (FASE 1-6) por dominio -- ambos son descubiertos
por `manage.py test ai_provider` (empiezan con 'test').
"""
from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase

from ai_provider.models import AIProvider
from ai_provider.services.connection_test import AIProviderConnectionTestService
from ai_provider.services.model_discovery import discover_models
from ai_provider.services.providers import get_adapter
from ai_provider.services.providers.anthropic import AnthropicAdapter
from ai_provider.services.providers.base import (
    ERROR_CONNECTION_REFUSED, ERROR_DNS, ERROR_TIMEOUT, ERROR_UNAUTHORIZED, SUCCESS,
)
from ai_provider.services.providers.ollama import OllamaAdapter, _classify_connection_error
from ai_provider.services.providers.openai_compatible import OpenAICompatibleAdapter


def _mock_response(status_code=200, json_data=None, text=''):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    return resp


class TestGetAdapter(TestCase):
    def test_returns_correct_adapter_per_kind(self):
        ollama = AIProvider(name='o', kind=AIProvider.KIND_OLLAMA_NATIVE, base_url='http://x:11434')
        openai = AIProvider(name='oa', kind=AIProvider.KIND_OPENAI_COMPATIBLE, base_url='http://x:1234/v1')
        anthropic = AIProvider(name='an', kind=AIProvider.KIND_ANTHROPIC)
        self.assertIsInstance(get_adapter(ollama), OllamaAdapter)
        self.assertIsInstance(get_adapter(openai), OpenAICompatibleAdapter)
        self.assertIsInstance(get_adapter(anthropic), AnthropicAdapter)


class TestErrorClassification(TestCase):
    def test_dns_failure_classified_correctly(self):
        exc = requests.exceptions.ConnectionError('Failed to resolve: Name or service not known')
        self.assertEqual(_classify_connection_error(exc), ERROR_DNS)

    def test_connection_refused_classified_correctly(self):
        exc = requests.exceptions.ConnectionError('Connection refused')
        self.assertEqual(_classify_connection_error(exc), ERROR_CONNECTION_REFUSED)


class TestOllamaAdapter(TestCase):
    def test_connection_success(self):
        provider = AIProvider(name='ollama real', kind=AIProvider.KIND_OLLAMA_NATIVE, base_url='http://sintel_ollama:11434')
        result = OllamaAdapter(provider).test_connection()
        # Ollama esta arriba en este entorno de certificacion -- no se mockea, es una
        # llamada real al contenedor sintel_ollama.
        self.assertEqual(result.error_code, SUCCESS)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.latency_ms)

    def test_connection_timeout_classified(self):
        provider = AIProvider(name='ollama timeout', kind=AIProvider.KIND_OLLAMA_NATIVE, base_url='http://x:11434')
        with patch('requests.get', side_effect=requests.exceptions.Timeout('timed out')):
            result = OllamaAdapter(provider).test_connection()
        self.assertEqual(result.error_code, ERROR_TIMEOUT)
        self.assertFalse(result.success)

    def test_list_models_parses_real_ollama_tags_shape(self):
        provider = AIProvider(name='ollama', kind=AIProvider.KIND_OLLAMA_NATIVE, base_url='http://x:11434')
        payload = {'models': [{'name': 'llama3.1:8b'}, {'name': 'qwen2.5-coder:1.5b'}]}
        with patch('requests.get', return_value=_mock_response(200, payload)):
            models = OllamaAdapter(provider).list_models()
        self.assertEqual(models, [
            {'model_id': 'llama3.1:8b', 'display_name': 'llama3.1:8b'},
            {'model_id': 'qwen2.5-coder:1.5b', 'display_name': 'qwen2.5-coder:1.5b'},
        ])

    def test_never_raises_on_malformed_response(self):
        provider = AIProvider(name='ollama', kind=AIProvider.KIND_OLLAMA_NATIVE, base_url='http://x:11434')
        with patch('requests.get', return_value=_mock_response(200, {'unexpected': 'shape'})):
            models = OllamaAdapter(provider).list_models()
        self.assertEqual(models, [])


class TestOpenAICompatibleAdapter(TestCase):
    def test_unauthorized_classified_correctly(self):
        provider = AIProvider(name='lm studio', kind=AIProvider.KIND_OPENAI_COMPATIBLE, base_url='http://x:1234/v1', api_key='wrong-key')
        with patch('requests.get', return_value=_mock_response(401)):
            result = OpenAICompatibleAdapter(provider).test_connection()
        self.assertEqual(result.error_code, ERROR_UNAUTHORIZED)
        self.assertFalse(result.success)

    def test_list_models_parses_openai_shape(self):
        provider = AIProvider(name='lm studio', kind=AIProvider.KIND_OPENAI_COMPATIBLE, base_url='http://x:1234/v1')
        payload = {'data': [{'id': 'local-model-a'}, {'id': 'local-model-b'}]}
        with patch('requests.get', return_value=_mock_response(200, payload)):
            models = OpenAICompatibleAdapter(provider).list_models()
        self.assertEqual(models, [
            {'model_id': 'local-model-a', 'display_name': 'local-model-a'},
            {'model_id': 'local-model-b', 'display_name': 'local-model-b'},
        ])

    def test_sends_bearer_token_when_api_key_present(self):
        provider = AIProvider(name='openai', kind=AIProvider.KIND_OPENAI_COMPATIBLE, base_url='https://api.openai.com/v1', api_key='sk-real')
        with patch('requests.get', return_value=_mock_response(200, {'data': []})) as mock_get:
            OpenAICompatibleAdapter(provider).test_connection()
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs['headers'], {'Authorization': 'Bearer sk-real'})


class TestAnthropicAdapter(TestCase):
    def test_list_models_always_empty_no_dynamic_discovery(self):
        provider = AIProvider(name='claude', kind=AIProvider.KIND_ANTHROPIC, api_key='sk-ant-x')
        self.assertEqual(AnthropicAdapter(provider).list_models(), [])

    def test_validate_model_accepts_any_non_empty_identifier(self):
        provider = AIProvider(name='claude', kind=AIProvider.KIND_ANTHROPIC, api_key='sk-ant-x')
        adapter = AnthropicAdapter(provider)
        self.assertTrue(adapter.validate_model('claude-sonnet-5'))
        self.assertFalse(adapter.validate_model(''))

    def test_sends_x_api_key_header_never_bearer(self):
        provider = AIProvider(name='claude', kind=AIProvider.KIND_ANTHROPIC, api_key='sk-ant-real')
        with patch('requests.get', return_value=_mock_response(200, {})) as mock_get:
            AnthropicAdapter(provider).test_connection()
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs['headers']['x-api-key'], 'sk-ant-real')
        self.assertNotIn('Authorization', kwargs['headers'])


class TestConnectionTestServiceAndDiscovery(TestCase):
    def test_service_delegates_to_correct_adapter(self):
        provider = AIProvider(name='ollama', kind=AIProvider.KIND_OLLAMA_NATIVE, base_url='http://sintel_ollama:11434')
        result = AIProviderConnectionTestService.test(provider)
        self.assertEqual(result.provider, 'ollama')
        self.assertTrue(result.success)

    def test_discover_models_delegates_to_correct_adapter(self):
        provider = AIProvider(name='ollama', kind=AIProvider.KIND_OLLAMA_NATIVE, base_url='http://sintel_ollama:11434')
        models = discover_models(provider)
        self.assertIsInstance(models, list)
        # Motor real -- confirmado en la campaña previa que trae al menos llama3.1:8b.
        self.assertTrue(any(m['model_id'] == 'llama3.1:8b' for m in models))


class TestConnectionFailureMessages(TestCase):
    """Mensajes especificos en lugar de un generico 'No se pudo establecer conexion' (2026-09-25). Escritos, no ejecutados."""

    def test_localhost_se_explica_como_url_de_contenedor(self):
        from ai_provider.services.providers.base import ERROR_LOOPBACK_URL, connection_failure
        for url in ('http://127.0.0.1:1234/v1', 'http://localhost:11434', 'http://[::1]:1234/v1'):
            code, message = connection_failure(url, 'CONNECTION_REFUSED')
            self.assertEqual(code, ERROR_LOOPBACK_URL)
            self.assertIn('host.docker.internal', message)

    def test_cada_causa_tiene_mensaje_propio_y_accionable(self):
        from ai_provider.services.providers.base import (
            ERROR_CONNECTION_REFUSED, ERROR_DNS, ERROR_NETWORK_UNREACHABLE, ERROR_UNKNOWN, connection_failure,
        )
        messages = set()
        for code in (ERROR_DNS, ERROR_CONNECTION_REFUSED, ERROR_NETWORK_UNREACHABLE, ERROR_UNKNOWN):
            got_code, message = connection_failure('http://host.docker.internal:1234/v1', code)
            self.assertEqual(got_code, code)
            self.assertNotEqual(message, 'No se pudo establecer conexion.')
            messages.add(message)
        self.assertEqual(len(messages), 4)

    def test_red_inalcanzable_se_clasifica(self):
        from ai_provider.services.providers.base import ERROR_NETWORK_UNREACHABLE
        from ai_provider.services.providers.ollama import _classify_connection_error
        exc = requests.exceptions.ConnectionError('[Errno 101] Network is unreachable')
        self.assertEqual(_classify_connection_error(exc), ERROR_NETWORK_UNREACHABLE)
