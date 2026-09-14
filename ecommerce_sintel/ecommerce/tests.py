"""
Test de regresion para C-01 (auditoria enterprise, 2026-07-24).

ecommerce.settings.production no tenia ningun fail-safe contra DEBUG=True --
si DJANGO_SETTINGS_MODULE=ecommerce.settings.production se desplegaba con
DEBUG=True (ej. una variable de entorno mal copiada), Django expondria stack
traces completos, SQL y configuracion interna a cualquier visitante ante un
error 500. La correccion levanta ImproperlyConfigured al importar el modulo
de settings si DEBUG es True, evitando que el proceso arranque siquiera.

Se corre en un subproceso real (no solo `override_settings`) porque el bug
vive en el IMPORT del modulo de settings, no en un valor de configuracion que
se pueda simular en el proceso de test ya arrancado con settings.development.
"""
import os
import subprocess
import sys
import django
from django.test import SimpleTestCase, TestCase


class ProductionSettingsDebugFailSafeTestCase(SimpleTestCase):
    def _run_in_subprocess(self, debug_value):
        env = os.environ.copy()
        env['DJANGO_SETTINGS_MODULE'] = 'ecommerce.settings.production'
        env['DEBUG'] = debug_value
        # Union Colombia (payment/CLAUDE.md) no interviene aqui; solo hace
        # falta que el modulo de settings se pueda IMPORTAR sin reventar por
        # otra causa distinta a DEBUG -- las demas variables ya viven en el
        # entorno del contenedor/CI (ver .github/workflows/ci.yml).
        result = subprocess.run(
            [sys.executable, '-c', 'import django; django.setup()'],
            env=env, capture_output=True, text=True, timeout=30,
        )
        return result

    def test_debug_true_prevents_production_settings_from_loading(self):
        result = self._run_in_subprocess('True')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('ImproperlyConfigured', result.stderr)
        self.assertIn('DEBUG=True es invalido con ecommerce.settings.production', result.stderr)

    def test_debug_false_loads_production_settings_normally(self):
        result = self._run_in_subprocess('False')
        self.assertEqual(result.returncode, 0, msg=result.stderr)


class HealthCheckEndpointTestCase(TestCase):
    """
    Fase 15 (AUDITORIA/29_AUDITORIA_OBSERVABILIDAD.md, 2026-08-03): antes /api/v1/health/
    (consultado por el HEALTHCHECK de docker-compose.prod.yml para el servicio `django`)
    devolvia {"status": "ok"} incondicionalmente -- falso positivo total, no verificaba nada.
    Ahora reusa SecuritySelector.get_health_snapshot() y responde 503 si db/redis fallan, para
    que `curl -f` (usado por el HEALTHCHECK) falle y Docker reinicie el contenedor.
    """

    def test_status_ok_cuando_db_y_redis_estan_sanos(self):
        response = self.client.get('/api/v1/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')
        self.assertTrue(response.json()['db'])
        self.assertTrue(response.json()['redis'])

    def test_status_degraded_503_si_redis_falla(self):
        from unittest.mock import patch
        with patch('security.services.selectors.SecuritySelector.get_health_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {'db': True, 'redis': False, 'celery': True}
            response = self.client.get('/api/v1/health/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['status'], 'degraded')

    def test_status_degraded_503_si_db_falla(self):
        from unittest.mock import patch
        with patch('security.services.selectors.SecuritySelector.get_health_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {'db': False, 'redis': True, 'celery': True}
            response = self.client.get('/api/v1/health/')
        self.assertEqual(response.status_code, 503)

    def test_no_requiere_autenticacion(self):
        # El curl del HEALTHCHECK de Docker no envia credenciales -- debe seguir siendo publico.
        response = self.client.get('/api/v1/health/')
        self.assertNotEqual(response.status_code, 401)
        self.assertNotEqual(response.status_code, 403)
