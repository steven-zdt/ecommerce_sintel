"""
HARDENING F2 (2026-09-24): Django envia el secreto de servicio `X-AI-Service-Token` al ADK.

Ver ai_engine_adk/.AGENT/HARDENING_F2_PROPOSAL_2026-09-24.md. El lado receptor (ADK) se prueba en
ai_engine_adk/tests/test_service_token.py. Aqui se comprueba que TODOS los llamadores de `/chat` de Django
(widget/WhatsApp via `ask_ai`/`ask_ai_async` y el Admin AI Assistant) mandan el header cuando esta configurado
y NO lo mandan (ni fallan) cuando no lo esta -- para poder desplegar en dos pasos sin cortar el chat.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import SimpleTestCase, override_settings

from support.services import ai_bridge


class _User:
    email = 'cliente@example.com'


def _ok_response():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {'response': 'hola', 'metrics': {}, 'tool_calls': []}
    resp.text = '{}'
    return resp


class BuildAiHeadersTests(SimpleTestCase):
    @override_settings(AI_SERVICE_TOKEN='secreto-de-prueba')
    def test_incluye_jwt_y_secreto_de_servicio(self):
        headers = ai_bridge.build_ai_headers('jwt123')
        self.assertEqual(headers['Authorization'], 'Bearer jwt123')
        self.assertEqual(headers['X-AI-Service-Token'], 'secreto-de-prueba')

    @override_settings(AI_SERVICE_TOKEN='')
    def test_sin_secreto_configurado_solo_jwt(self):
        headers = ai_bridge.build_ai_headers('jwt123')
        self.assertEqual(headers, {'Authorization': 'Bearer jwt123'})


class AskAiSendsServiceTokenTests(SimpleTestCase):
    @override_settings(AI_SERVICE_TOKEN='secreto-de-prueba')
    @patch('rest_framework_simplejwt.tokens.AccessToken.for_user', return_value='jwt123')
    @patch('support.services.ai_bridge.requests.post')
    def test_ask_ai_sync_envia_header(self, mock_post, _tok):
        mock_post.return_value = _ok_response()
        ai_bridge.ask_ai(_User(), 'hola', 'room-1')
        headers = mock_post.call_args.kwargs['headers']
        self.assertEqual(headers['X-AI-Service-Token'], 'secreto-de-prueba')
        self.assertEqual(headers['Authorization'], 'Bearer jwt123')

    @override_settings(AI_SERVICE_TOKEN='secreto-de-prueba')
    @patch('rest_framework_simplejwt.tokens.AccessToken.for_user', return_value='jwt123')
    @patch('httpx.AsyncClient')
    def test_ask_ai_async_envia_header(self, mock_client_cls, _tok):
        client = mock_client_cls.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.post = AsyncMock(return_value=_ok_response())
        asyncio.run(ai_bridge.ask_ai_async(_User(), 'hola', 'room-1'))
        headers = client.post.call_args.kwargs['headers']
        self.assertEqual(headers['X-AI-Service-Token'], 'secreto-de-prueba')

    @override_settings(AI_SERVICE_TOKEN='')
    @patch('rest_framework_simplejwt.tokens.AccessToken.for_user', return_value='jwt123')
    @patch('support.services.ai_bridge.requests.post')
    def test_sin_secreto_no_manda_header_y_no_falla(self, mock_post, _tok):
        mock_post.return_value = _ok_response()
        ai_bridge.ask_ai(_User(), 'hola', 'room-1')
        self.assertNotIn('X-AI-Service-Token', mock_post.call_args.kwargs['headers'])
