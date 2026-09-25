"""
dashboard/tests_code_plane.py -- plano de codigo del MCP (FASE 7-8). Escritos, NO ejecutados por instruccion del usuario; la logica se verifico en dev con scripts funcionales (29 comprobaciones) y con la fase `code` del smoke MCP.
"""
import tempfile
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from ai_editor import change_store as cs

pytestmark = pytest.mark.django_db
D = '/api/v1/dashboard/code/'


@pytest.fixture
def admin():
    return get_user_model().objects.create_user(email='code-plane@example.com', password='x', is_staff=True, is_superuser=True)


def _client(user, mcp=False):
    token = AccessToken.for_user(user)
    if mcp:
        token['via'] = 'mcp'
    api = APIClient(HTTP_HOST='localhost')
    api.credentials(HTTP_AUTHORIZATION='Bearer ' + str(token))
    return api


def _entry(admin):
    loop = NS(ready_for_approval=True, sandbox=NS(copied_files=[], original_fingerprints={}, root=Path(tempfile.mkdtemp()), cleanup=lambda: None), validation_report=None)
    return cs.put(admin.id, 'prueba', NS(status='APPROVAL_REQUIRED', detail='x', sandbox_loop_result=loop, warnings=[]), via_mcp=True)


def test_apagado_por_defecto_devuelve_404(admin, settings):
    settings.AI_EDITOR_CODE_PLANE_ENABLED = False
    resp = _client(admin).get(D + 'analysis/?op=status')
    assert resp.status_code == 404 and resp.json()['detail'] == 'CODE_PLANE_DISABLED'


def test_un_jwt_via_mcp_no_puede_aprobar(admin, settings):
    settings.AI_EDITOR_CODE_PLANE_ENABLED = True
    entry = _entry(admin)
    assert _client(admin, mcp=True).post(D + f'proposals/{entry.change_id}/decision/', {'decision': 'APPROVE'}, format='json').status_code == 403
    assert entry.approval is None


def test_promover_exige_aprobacion_humana(admin, settings):
    settings.AI_EDITOR_CODE_PLANE_ENABLED = True
    entry = _entry(admin)
    assert _client(admin, mcp=True).post(D + f'proposals/{entry.change_id}/promote/', {'confirm': True}, format='json').status_code == 400
    assert _client(admin).post(D + f'proposals/{entry.change_id}/decision/', {'decision': 'APPROVE'}, format='json').status_code == 200
    assert _client(admin, mcp=True).post(D + f'proposals/{entry.change_id}/promote/', {}, format='json').status_code == 409  # sin confirm


def test_operacion_de_analisis_invalida(admin, settings):
    settings.AI_EDITOR_CODE_PLANE_ENABLED = True
    assert _client(admin).get(D + 'analysis/?op=bad&q=x').status_code == 400
