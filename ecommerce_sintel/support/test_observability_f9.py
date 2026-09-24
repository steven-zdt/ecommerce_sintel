"""
HARDENING F9 (2026-09-24) -- Django: RequestIDMiddleware, cabeceras de correlacion, percentiles del analytics y
SecurityEvent de senales de IA. ESCRITO PERO NO EJECUTADO (regla vigente: no correr tests sin autorizacion del usuario).
"""
from unittest.mock import MagicMock

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from ecommerce.request_id import RequestIDMiddleware
from security.models import SecurityEvent
from support.services import ai_bridge
from support.services.selectors import ChatAnalyticsSelector


class RequestIDMiddlewareTests(SimpleTestCase):
    def _call(self, **extra):
        mw = RequestIDMiddleware(lambda request: HttpResponse('ok'))
        request = RequestFactory().get('/x', **extra)
        return mw(request), request

    def test_reutiliza_un_id_valido(self):
        response, request = self._call(HTTP_X_REQUEST_ID='abc-12345678')
        self.assertEqual(response['X-Request-ID'], 'abc-12345678')
        self.assertEqual(request.request_id, 'abc-12345678')

    def test_regenera_un_id_invalido(self):
        response, _ = self._call(HTTP_X_REQUEST_ID='con espacios; y basura')
        self.assertTrue(response['X-Request-ID'].startswith('req-'))

    def test_genera_uno_si_falta(self):
        response, _ = self._call()
        self.assertTrue(response['X-Request-ID'].startswith('req-'))

    def test_el_contexto_se_limpia_al_terminar(self):
        from ai_engine_adk import observability_logging as obs
        self._call(HTTP_X_REQUEST_ID='abc-12345678')
        self.assertIsNone(obs.current_request_id())


class BuildHeadersCorrelationTests(SimpleTestCase):
    @override_settings(AI_SERVICE_TOKEN='')
    def test_envia_request_id_y_session_id(self):
        from ai_engine_adk import observability_logging as obs
        tokens = obs.set_context(request_id='ws-abc12345', session_id=None)
        try:
            headers = ai_bridge.build_ai_headers('jwt', 'room-abc12345')
        finally:
            obs.reset_context(tokens)
        self.assertEqual(headers['X-Request-ID'], 'ws-abc12345')
        self.assertEqual(headers['X-Session-Id'], 'room-abc12345')

    @override_settings(AI_SERVICE_TOKEN='')
    def test_sin_contexto_genera_un_id(self):
        self.assertTrue(ai_bridge.build_ai_headers('jwt')['X-Request-ID'].startswith('req-'))


class ObservabilitySummaryTests(SimpleTestCase):
    def test_percentiles_degradacion_fallback_tokens_y_banderas(self):
        metrics = [
            {'duration_ms': d, 'tool_calls': 1, 'llm_tokens_in': 10, 'llm_tokens_out': 5,
             'model_trace': {'provider': 'ollama', 'fallback_used': i == 0}}
            for i, d in enumerate([100, 200, 300, 400, 1000])
        ]
        metrics.append({'engine_unavailable': True})
        metrics.append({'duration_ms': 50, 'output_flags': ['blocked_internal_host'], 'injection_flags': ['override_instructions']})
        out = ChatAnalyticsSelector.summarize_observability(metrics)
        self.assertEqual(out['p50_duration_ms'], 200)
        self.assertEqual(out['p99_duration_ms'], 1000)
        self.assertAlmostEqual(out['degraded_rate'], 1 / 7, places=3)
        self.assertAlmostEqual(out['provider_fallback_rate'], 1 / 6, places=3)
        self.assertEqual(out['tokens_in_total'], 50)
        self.assertEqual(out['output_flag_counts'], {'blocked_internal_host': 1})
        self.assertEqual(out['injection_flag_counts'], {'override_instructions': 1})

    def test_sin_datos(self):
        out = ChatAnalyticsSelector.summarize_observability([])
        self.assertIsNone(out['p50_duration_ms'])
        self.assertEqual(out['degraded_rate'], 0.0)


class AiSecurityEventTests(TestCase):
    def test_registra_bloqueo_y_no_incluye_contenido(self):
        response = {'agent': 'SupportAgent', 'response': 'TEXTO PRIVADO', 'metrics': {
            'request_id': 'req-abc12345', 'output_flags': ['blocked_internal_host', 'truncated'], 'injection_flags': []}}
        ai_bridge.record_ai_security_events(response, 'room-1')
        event = SecurityEvent.objects.get(event_type=SecurityEvent.AI_SECURITY_FLAG)
        self.assertEqual(event.metadata['output_flags'], ['blocked_internal_host'])
        self.assertEqual(event.metadata['request_id'], 'req-abc12345')
        self.assertNotIn('TEXTO PRIVADO', str(event.metadata))

    def test_sin_banderas_de_alto_nivel_no_registra(self):
        ai_bridge.record_ai_security_events({'metrics': {'output_flags': ['truncated', 'reasoning_stripped']}}, 'room-1')
        self.assertFalse(SecurityEvent.objects.filter(event_type=SecurityEvent.AI_SECURITY_FLAG).exists())

    def test_nunca_rompe_el_turno(self):
        ai_bridge.record_ai_security_events(MagicMock(), 'room-1')  # dato invalido: no debe lanzar
