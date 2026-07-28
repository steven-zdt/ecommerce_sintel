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
from django.test import SimpleTestCase


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
