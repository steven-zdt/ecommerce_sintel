"""
HARDENING F17 (2026-09-24) -- enrutamiento canary y veredicto. ESCRITO PERO NO EJECUTADO (regla: el usuario ejecuta los tests a mano).
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from support.management.commands.ai_canary_report import _split_by_track, verdict
from support.services import ai_bridge, engine_routing

STABLE_URL = 'http://stable:8101'
CANARY_URL = 'http://canary:8101'


def U(pk, email='cliente@example.com'):
    return SimpleNamespace(pk=pk, id=pk, email=email)


@override_settings(AI_ENGINE_URL=STABLE_URL, AI_CANARY_ENGINE_URL='', AI_CANARY_USER_EMAILS='a@x.com', AI_CANARY_PERCENT=100)
class CanaryOffTests(SimpleTestCase):
    def test_sin_url_de_canary_todo_va_a_stable_aunque_haya_porcentaje_o_lista(self):
        self.assertEqual(engine_routing.resolve_engine(U(1, 'a@x.com')), (STABLE_URL, 'stable'))
        self.assertEqual(engine_routing.resolve_engine(U(2)), (STABLE_URL, 'stable'))


@override_settings(AI_ENGINE_URL=STABLE_URL, AI_CANARY_ENGINE_URL=CANARY_URL, AI_CANARY_USER_EMAILS=' Interno@Sintel.co , otro@sintel.co ',
                   AI_CANARY_PERCENT=0)
class CanaryInternalUsersTests(SimpleTestCase):
    def test_los_usuarios_internos_siempre_van_a_canary_sin_distinguir_mayusculas(self):
        self.assertEqual(engine_routing.resolve_engine(U(1, 'interno@sintel.co')), (CANARY_URL, 'canary'))
        self.assertEqual(engine_routing.resolve_engine(U(2, 'OTRO@SINTEL.CO'))[1], 'canary')

    def test_el_resto_va_a_stable_con_0_por_ciento(self):
        self.assertEqual(engine_routing.resolve_engine(U(3))[1], 'stable')


@override_settings(AI_ENGINE_URL=STABLE_URL, AI_CANARY_ENGINE_URL=CANARY_URL, AI_CANARY_USER_EMAILS='')
class CanaryPercentTests(SimpleTestCase):
    def test_asignacion_determinista_por_usuario(self):
        with override_settings(AI_CANARY_PERCENT=30):
            first = [engine_routing.track_for(U(i)) for i in range(200)]
            second = [engine_routing.track_for(U(i)) for i in range(200)]
        self.assertEqual(first, second)

    def test_el_porcentaje_aproxima_la_fraccion_y_es_monotono(self):
        users = [U(i) for i in range(2000)]
        with override_settings(AI_CANARY_PERCENT=10):
            ten = {u.pk for u in users if engine_routing.track_for(u) == 'canary'}
        with override_settings(AI_CANARY_PERCENT=25):
            quarter = {u.pk for u in users if engine_routing.track_for(u) == 'canary'}
        with override_settings(AI_CANARY_PERCENT=100):
            everyone = {u.pk for u in users if engine_routing.track_for(u) == 'canary'}
        self.assertTrue(120 <= len(ten) <= 280)
        self.assertTrue(ten <= quarter)  # subir el porcentaje NO saca a nadie del canary
        self.assertEqual(len(everyone), 2000)


@override_settings(AI_ENGINE_URL=STABLE_URL, AI_CANARY_ENGINE_URL=CANARY_URL, AI_CANARY_USER_EMAILS='cliente@example.com',
                   AI_SERVICE_TOKEN='')
class AskAiTrackTests(SimpleTestCase):
    def _ok(self):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {'response': 'hola', 'metrics': {}, 'tool_calls': []}
        resp.text = '{}'
        return resp

    @patch('rest_framework_simplejwt.tokens.AccessToken.for_user', return_value='jwt')
    @patch('support.services.ai_bridge.requests.post')
    def test_la_respuesta_lleva_engine_track_y_usa_la_url_del_canary(self, mock_post, _tok):
        mock_post.return_value = self._ok()
        data = ai_bridge.ask_ai(U(1), 'hola', 'room-1')
        self.assertEqual(mock_post.call_args.args[0], f'{CANARY_URL}/chat')
        self.assertEqual(data['metrics']['engine_track'], 'canary')

    @patch('rest_framework_simplejwt.tokens.AccessToken.for_user', return_value='jwt')
    @patch('support.services.ai_bridge.requests.post')
    def test_si_el_canary_no_acepta_la_conexion_se_atiende_con_stable(self, mock_post, _tok):
        import requests

        mock_post.side_effect = [requests.ConnectionError('refused'), self._ok()]
        data = ai_bridge.ask_ai(U(1), 'hola', 'room-1')
        self.assertEqual([c.args[0] for c in mock_post.call_args_list], [f'{CANARY_URL}/chat', f'{STABLE_URL}/chat'])
        self.assertEqual(data['metrics']['engine_track'], 'stable')

    @patch('rest_framework_simplejwt.tokens.AccessToken.for_user', return_value='jwt')
    @patch('support.services.ai_bridge.requests.post')
    def test_un_timeout_del_canary_NO_se_reintenta_en_stable(self, mock_post, _tok):
        import requests

        mock_post.side_effect = requests.Timeout('lento')  # el turno pudo ejecutarse: no se duplica
        self.assertIsNone(ai_bridge.ask_ai(U(1), 'hola', 'room-1'))
        self.assertEqual(mock_post.call_count, 1)


class VerdictTests(SimpleTestCase):
    BASE = {'attempts': 100, 'degraded_rate': 0.01, 'p95_duration_ms': 60000, 'security_flag_rate': 0.0, 'provider_fallback_rate': 0.0}
    KW = dict(min_turns=30, max_degraded_delta=0.02, max_p95_ratio=1.3, max_security_delta=0.01)

    def test_hold_con_pocos_datos(self):
        self.assertEqual(verdict(self.BASE, {**self.BASE, 'attempts': 5}, **self.KW)[0], 'HOLD')

    def test_proceed_sin_regresion(self):
        self.assertEqual(verdict(self.BASE, dict(self.BASE), **self.KW)[0], 'PROCEED')

    def test_rollback_por_degradacion_latencia_o_seguridad(self):
        self.assertEqual(verdict(self.BASE, {**self.BASE, 'degraded_rate': 0.10}, **self.KW)[0], 'ROLLBACK')
        self.assertEqual(verdict(self.BASE, {**self.BASE, 'p95_duration_ms': 100000}, **self.KW)[0], 'ROLLBACK')
        self.assertEqual(verdict(self.BASE, {**self.BASE, 'security_flag_rate': 0.05}, **self.KW)[0], 'ROLLBACK')

    def test_split_por_track_trata_la_falta_de_clave_como_stable(self):
        tracks = _split_by_track([{'engine_track': 'canary'}, {'engine_track': 'stable'}, {}, 'basura'])
        self.assertEqual((len(tracks['canary']), len(tracks['stable'])), (1, 2))
