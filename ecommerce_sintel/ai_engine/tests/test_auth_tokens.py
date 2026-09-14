"""
auth.py::decode_django_jwt -- token expirado/invalido/malformado (Gap 4, Fase 31,
agregado 2026-08-08). Hueco real detectado en la auditoria: existia manejo de
codigo para esto (HTTPException 401) pero ningun test dedicado.
"""
import datetime

import jwt
import pytest
from fastapi import HTTPException

from auth import decode_django_jwt
from config import JWT_SECRET_KEY


def _make_token(secret: str = JWT_SECRET_KEY, **overrides) -> str:
    payload = {
        "token_type": "access",
        "user_id": 1,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15),
    }
    payload.update(overrides)
    return jwt.encode(payload, secret, algorithm="HS256")


def test_token_valido_decodifica_ok():
    token = _make_token()
    payload = decode_django_jwt(token)
    assert payload["user_id"] == 1
    assert payload["token_type"] == "access"


def test_token_expirado_rechazado():
    token = _make_token(exp=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1))
    with pytest.raises(HTTPException) as exc_info:
        decode_django_jwt(token)
    assert exc_info.value.status_code == 401


def test_token_firmado_con_secreto_incorrecto_rechazado():
    token = _make_token(secret="un-secreto-que-no-es-el-de-django")
    with pytest.raises(HTTPException) as exc_info:
        decode_django_jwt(token)
    assert exc_info.value.status_code == 401


def test_token_malformado_rechazado():
    with pytest.raises(HTTPException) as exc_info:
        decode_django_jwt("esto-no-es-un-jwt-valido")
    assert exc_info.value.status_code == 401


def test_token_refresh_rechazado_donde_se_exige_access():
    """SimpleJWT emite token_type='refresh' para el refresh token -- el AI Engine
    nunca debe aceptar uno de esos como si fuera credencial de sesion."""
    token = _make_token(token_type="refresh")
    with pytest.raises(HTTPException) as exc_info:
        decode_django_jwt(token)
    assert exc_info.value.status_code == 401


def test_token_sin_user_id_rechazado():
    payload = {
        "token_type": "access",
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15),
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
    with pytest.raises(HTTPException) as exc_info:
        decode_django_jwt(token)
    assert exc_info.value.status_code == 401
