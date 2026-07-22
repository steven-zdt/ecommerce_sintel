"""
Autenticacion del AI Engine — Fase 1 del AI Core.

Valida el JWT REAL emitido por Django (rest_framework_simplejwt, HS256,
SIGNING_KEY compartida via variable de entorno JWT_SECRET_KEY). Este modulo
NUNCA emite tokens propios ni reimplementa SimpleJWT: solo decodifica y
verifica firma/expiracion con PyJWT, y resuelve la identidad completa
llamando al endpoint interno de Django (/api/v1/internal/ai-context/) con el
mismo token reenviado -- la logica de perfiles (ProfileResolver) vive solo
en Django.

Uso como dependencia FastAPI:

    from auth import get_user_context

    @router.get("/algo")
    async def endpoint(user_context: dict = Depends(get_user_context)):
        ...
"""
import logging

import httpx
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import DJANGO_INTERNAL_API_URL, JWT_SECRET_KEY

logger = logging.getLogger("auth")

# auto_error=False para poder devolver un 401 explicito y en espanol
# (el default de FastAPI seria 403 con "Not authenticated").
_bearer_scheme = HTTPBearer(auto_error=False)

_AI_CONTEXT_PATH = "/internal/ai-context/"
_HTTP_TIMEOUT_SECONDS = 10


def decode_django_jwt(token: str) -> dict:
    """
    Decodifica y verifica un access token de SimpleJWT.

    Verifica firma HS256 + expiracion y exige los claims que SimpleJWT
    siempre emite (token_type == "access", user_id). Lanza HTTPException
    401 ante cualquier token invalido; 503 si el motor no tiene la clave.
    """
    if not JWT_SECRET_KEY:
        # Sin la clave compartida el motor no puede validar a nadie:
        # fallar cerrado, nunca dejar pasar.
        raise HTTPException(503, "JWT_SECRET_KEY no configurada en el AI Engine.")
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Token invalido.")
    if payload.get("token_type") != "access":
        raise HTTPException(401, "Se requiere un access token (no refresh).")
    if payload.get("user_id") is None:
        raise HTTPException(401, "Token sin claim user_id.")
    return payload


async def get_validated_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """
    Dependencia base: exige header Authorization: Bearer <JWT> y valida el
    token localmente (firma/expiracion). Request sin JWT -> 401 explicito,
    nunca un 200 anonimo.
    """
    if credentials is None:
        raise HTTPException(
            401,
            "Autenticacion requerida: header Authorization: Bearer <JWT de Django>.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    decode_django_jwt(credentials.credentials)
    return credentials.credentials


async def fetch_user_context(token: str) -> dict:
    """
    Customer Context Builder (v1): resuelve el JWT ya validado a un
    usuario/perfil real reenviandolo al endpoint interno de Django.
    Devuelve el dict tal cual lo arma Django (user_id, uuid, email,
    full_name, user_type, is_staff, is_superuser, is_verified, kyc_status).
    Usado por la dependencia get_user_context Y por el nodo
    resolve_customer_context del Action Graph (Fase 3) -- una sola logica.
    """
    url = f"{DJANGO_INTERNAL_API_URL}{_AI_CONTEXT_PATH}"
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
    except httpx.HTTPError as exc:
        logger.error("[auth] Django inalcanzable en %s: %s", url, exc)
        raise HTTPException(502, "No se pudo contactar a Django para resolver la identidad.")
    if resp.status_code in (401, 403):
        # Django es la autoridad final: si el rechaza (usuario inactivo,
        # token revocado), el motor rechaza tambien.
        raise HTTPException(401, "Django rechazo el token o el usuario no esta activo.")
    if resp.status_code != 200:
        logger.error("[auth] Respuesta inesperada de Django (%s): %s", resp.status_code, resp.text[:300])
        raise HTTPException(502, "Error resolviendo el contexto de usuario en Django.")
    return resp.json()


async def get_user_context(token: str = Depends(get_validated_token)) -> dict:
    """Dependencia FastAPI: token validado -> contexto resuelto por Django."""
    return await fetch_user_context(token)
