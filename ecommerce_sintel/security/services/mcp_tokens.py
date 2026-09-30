"""
security/services/mcp_tokens.py -- tokens personales del servidor MCP (PROMPT MCP, FASE 2).

Flujo:
  1. Un admin crea un token (`McpTokenCommands.create_token`) -> recibe `smcp_...` UNA vez (solo se guarda su hash).
  2. El servidor MCP canjea el token (`exchange`) por un JWT de acceso CORTO del mismo admin (15 min) con el claim `via=mcp`; con ese JWT llama a la API: Django aplica sus permisos.
  3. Revocar o caducar el token (o que el usuario deje de ser admin/activo) impide nuevos canjes.
Fronteras: un JWT con `via=mcp` NO puede crear ni revocar tokens ni (mas adelante) aprobar cambios de codigo: esas decisiones exigen un admin humano con sesion normal.
"""
import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from security.models import McpAccessToken, SecurityEvent
from security.services.commands import SecurityCommands

TOKEN_PREFIX = 'smcp_'
DEFAULT_DAYS = 30
MAX_DAYS = 90
DEFAULT_WRITE_MINUTES = 60
MAX_WRITE_MINUTES = 8 * 60
EXCHANGE_LIMIT_PER_MINUTE = 30
LAST_USED_WRITE_INTERVAL = timedelta(minutes=1)
MCP_CLAIM = 'via'
MCP_CLAIM_VALUE = 'mcp'


class McpTokenError(Exception):
    """Error de negocio con mensaje apto para el admin (nunca revela por que un token concreto fue rechazado)."""


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def _is_admin(user) -> bool:
    return bool(user and user.is_active and user.is_staff and user.is_superuser)


def is_mcp_authenticated(request) -> bool:
    """True si la peticion llego con un JWT canjeado por el MCP (claim via=mcp)."""
    auth = getattr(request, 'auth', None)
    try:
        return bool(auth is not None and auth.get(MCP_CLAIM) == MCP_CLAIM_VALUE)
    except Exception:  # noqa: BLE001 - un `auth` sin .get (sesion, otro backend) no es MCP
        return False


class McpTokenCommands:
    @staticmethod
    @transaction.atomic
    def create_token(user, name: str, days: int | None = None, request=None) -> tuple[McpAccessToken, str]:
        if not _is_admin(user):
            raise McpTokenError('Solo un administrador puede crear tokens MCP.')
        if request is not None and is_mcp_authenticated(request):
            raise McpTokenError('Un cliente MCP no puede crear tokens MCP (usa una sesion normal del panel).')
        name = (name or '').strip()
        if not name or len(name) > 100:
            raise McpTokenError('El nombre es obligatorio (maximo 100 caracteres).')
        days = DEFAULT_DAYS if days is None else int(days)
        max_days = int(getattr(settings, 'MCP_TOKEN_MAX_DAYS', MAX_DAYS))
        if not 1 <= days <= max_days:
            raise McpTokenError(f'La vigencia debe estar entre 1 y {max_days} dias.')
        plaintext = TOKEN_PREFIX + secrets.token_urlsafe(32)
        token = McpAccessToken.objects.create(
            user=user, name=name, token_prefix=plaintext[:12], token_hash=_hash(plaintext), expires_at=timezone.now() + timedelta(days=days))
        SecurityCommands.log_event(SecurityEvent.MCP_TOKEN_CREATED, request=request, user=user,
                                   metadata={'token_uuid': str(token.uuid), 'name': name, 'days': days})
        return token, plaintext

    @staticmethod
    @transaction.atomic
    def revoke_token(token: McpAccessToken, by_user, request=None) -> McpAccessToken:
        if request is not None and is_mcp_authenticated(request):
            raise McpTokenError('Un cliente MCP no puede revocar tokens MCP.')
        if token.revoked_at is None:
            token.revoked_at = timezone.now()
            token.save(update_fields=['revoked_at', 'updated_at'])
            SecurityCommands.log_event(SecurityEvent.MCP_TOKEN_REVOKED, request=request, user=by_user,
                                       metadata={'token_uuid': str(token.uuid), 'name': token.name})
        return token

    @staticmethod
    @transaction.atomic
    def set_write(token: McpAccessToken, by_user, enabled: bool, minutes: int | None = None, request=None) -> McpAccessToken:
        """Interruptor de escritura (perfil ADMIN_CRUD en el MCP) con caducidad automatica. Solo un admin con sesion normal: un cliente MCP no se lo puede dar a si mismo."""
        if request is not None and is_mcp_authenticated(request):
            raise McpTokenError('Un cliente MCP no puede activar ni desactivar su propia escritura (usa una sesion normal del panel).')
        if not _is_admin(by_user) or token.user_id != by_user.pk:
            raise McpTokenError('Solo el administrador dueno del token puede cambiar su escritura.')
        if not token.is_active:
            raise McpTokenError('El token esta revocado o vencido.')
        if enabled:
            minutes = DEFAULT_WRITE_MINUTES if minutes is None else int(minutes)
            if not 1 <= minutes <= MAX_WRITE_MINUTES:
                raise McpTokenError(f'La ventana de escritura debe estar entre 1 y {MAX_WRITE_MINUTES} minutos.')
            token.write_enabled_until = min(timezone.now() + timedelta(minutes=minutes), token.expires_at)
            event = SecurityEvent.MCP_WRITE_ENABLED
        else:
            token.write_enabled_until = None
            event = SecurityEvent.MCP_WRITE_DISABLED
        token.save(update_fields=['write_enabled_until', 'updated_at'])
        SecurityCommands.log_event(event, request=request, user=by_user, metadata={
            'token_uuid': str(token.uuid), 'name': token.name, 'minutes': minutes if enabled else 0})
        return token

    @staticmethod
    def _rate_limited(request) -> bool:
        ip = (request.META.get('HTTP_X_FORWARDED_FOR', '') or request.META.get('REMOTE_ADDR', '') or 'unknown').split(',')[0].strip()
        key = f'mcp_exchange:{ip}'
        cache.add(key, 0, timeout=60)
        try:
            return cache.incr(key) > EXCHANGE_LIMIT_PER_MINUTE
        except ValueError:
            return False

    @staticmethod
    def exchange(plaintext: str, request=None) -> dict:
        """Canjea un token MCP por un JWT de acceso corto. Todo rechazo devuelve el MISMO error generico (sin distinguir causa) y queda auditado."""
        def fail(reason: str):
            SecurityCommands.log_event(SecurityEvent.MCP_TOKEN_EXCHANGE_FAILED, request=request, severity=SecurityEvent.SEVERITY_WARNING, metadata={'reason': reason})
            raise McpTokenError('Token MCP invalido.')

        if request is not None and McpTokenCommands._rate_limited(request):
            fail('rate_limited')
        if not isinstance(plaintext, str) or not plaintext.startswith(TOKEN_PREFIX) or len(plaintext) > 200:
            fail('formato')
        digest = _hash(plaintext)
        token = McpAccessToken.objects.select_related('user').filter(token_hash=digest, is_deleted=False).first()
        # comparacion en tiempo constante del hash encontrado (la busqueda ya es por hash; esto evita dejar una via de sincronizacion si el motor cambia)
        if token is None or not hmac.compare_digest(token.token_hash, digest):
            fail('desconocido')
        if token.revoked_at is not None:
            fail('revocado')
        if token.expires_at <= timezone.now():
            fail('caducado')
        if not _is_admin(token.user):
            fail('usuario_sin_permisos')

        now = timezone.now()
        if token.last_used_at is None or now - token.last_used_at > LAST_USED_WRITE_INTERVAL:
            McpAccessToken.objects.filter(pk=token.pk).update(last_used_at=now)
        from rest_framework_simplejwt.tokens import AccessToken
        access = AccessToken.for_user(token.user)
        access[MCP_CLAIM] = MCP_CLAIM_VALUE
        access['mcp_token'] = str(token.uuid)
        SecurityCommands.log_event(SecurityEvent.MCP_TOKEN_EXCHANGED, request=request, user=token.user, metadata={'token_uuid': str(token.uuid), 'name': token.name})
        lifetime = int(access.lifetime.total_seconds())
        write_until = token.write_enabled_until if token.write_enabled else None
        return {'access': str(access), 'expires_in': lifetime,
                'user': {'uuid': str(token.user.uuid), 'email': token.user.email, 'is_admin': True}, 'token_uuid': str(token.uuid),
                'write_enabled': write_until is not None, 'write_until_ts': int(write_until.timestamp()) if write_until else None}


class McpTokenSelectors:
    @staticmethod
    def list_for_user(user):
        return McpAccessToken.objects.filter(user=user, is_deleted=False).order_by('-created_at')

    @staticmethod
    def get_for_user(user, uuid):
        return McpAccessToken.objects.get(uuid=uuid, user=user, is_deleted=False)
