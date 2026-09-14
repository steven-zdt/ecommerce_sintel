"""
shared/fields.py

Campo Django cifrado en reposo, agregado para el plan maestro "CONFIGURACION
DINAMICA DE MODELOS LOCALES PARA CHAT SUPPORT" (FASE 1, 2026-08-13). No existia
ningun mecanismo de cifrado en el proyecto (auditado explicitamente en FASE 0:
0 resultados para Fernet/cryptography/django-cryptography en codigo propio) --
`cryptography` ya es dependencia TRANSITIVA (via autobahn/google-auth/pyOpenSSL),
asi que se usa directo con Fernet en vez de sumar `django-cryptography` como
dependencia nueva (menos superficie, sin rebuild de Docker necesario).

Vive en `shared` porque, igual que `SingletonMixin`, es generico y reutilizable
entre apps -- no es dato de negocio de ninguna app especifica.
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _get_fernet() -> Fernet:
    # AI_PROVIDER_ENCRYPTION_KEY es la clave dedicada recomendada en produccion; si no
    # esta configurada, se deriva de SECRET_KEY como fallback de arranque (nunca falla
    # en dev). Fernet exige 32 bytes url-safe base64 -- se deriva deterministicamente
    # de cualquier string via sha256 para no exigirle al operador pre-formatear la clave.
    raw_key = getattr(settings, 'AI_PROVIDER_ENCRYPTION_KEY', '') or settings.SECRET_KEY
    digest = hashlib.sha256(raw_key.encode('utf-8')).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


class EncryptedTextField(models.TextField):
    """
    TextField cifrado en reposo con Fernet (AES128-CBC + HMAC, autenticado). El valor
    en Postgres nunca queda en texto plano; se descifra transparentemente al leer via
    ORM. Si la clave rota o el dato esta corrupto, `from_db_value` devuelve '' en vez
    de propagar la excepcion -- nunca se debe exponer un valor parcialmente descifrado.
    """

    def get_prep_value(self, value):
        if not value:
            return value
        return _get_fernet().encrypt(str(value).encode('utf-8')).decode('utf-8')

    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        try:
            return _get_fernet().decrypt(value.encode('utf-8')).decode('utf-8')
        except InvalidToken:
            return ''
