"""
dashboard/tests_mcp_whoami.py -- endpoint de identidad del MCP (PROMPT MCP, FASE 2). Escritos, no ejecutados por instruccion del usuario (verificado con curl contra dev:
admin 200, sin token 401, customer 403).
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
URL = '/api/v1/dashboard/mcp/whoami/'


def _client(**user_kwargs):
    client = APIClient(HTTP_HOST='localhost')
    user = get_user_model().objects.create_user(email=user_kwargs.pop('email'), password='x', **user_kwargs)
    client.force_authenticate(user=user)
    return client, user


def test_admin_recibe_su_identidad_sin_datos_sensibles():
    client, user = _client(email='mcp-admin@example.com', is_staff=True, is_superuser=True)
    resp = client.get(URL)
    assert resp.status_code == 200
    body = resp.json()
    assert body == {'uuid': str(user.uuid), 'email': 'mcp-admin@example.com', 'is_admin': True, 'is_staff': True, 'is_superuser': True}


def test_sin_token_401_customer_403_y_staff_sin_superuser_403():
    assert APIClient(HTTP_HOST='localhost').get(URL).status_code == 401
    assert _client(email='mcp-cust@example.com')[0].get(URL).status_code == 403
    assert _client(email='mcp-staff@example.com', is_staff=True)[0].get(URL).status_code == 403


def test_endpoint_es_solo_lectura():
    client, _ = _client(email='mcp-admin2@example.com', is_staff=True, is_superuser=True)
    for method in ('post', 'patch', 'put', 'delete'):
        assert getattr(client, method)(URL).status_code == 405
