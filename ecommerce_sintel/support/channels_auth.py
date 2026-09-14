import logging
from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


@database_sync_to_async
def _get_user_from_token(token_key: str):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import AnonymousUser
    try:
        from rest_framework_simplejwt.tokens import AccessToken
        token = AccessToken(token_key)
        User = get_user_model()
        user = User.objects.get(pk=token['user_id'], is_active=True)
        # FASE 2 (auditoria WS, 2026-08-07): contraparte del log de rechazo de abajo --
        # sin esto, un "token valido" era indistinguible de "nunca se evaluo el
        # middleware" en los logs. Sin contenido del token, solo el resultado.
        logger.info("[WS][AUTH] token valido user=%s", user.email)
        return user
    except Exception as exc:
        # Antes esto se tragaba en silencio -- WSREJECT en el consumer sin ninguna
        # pista de la causa real (token vencido vs. malformado vs. usuario inactivo
        # vs. otra cosa). Diagnostico real 2026-07-31: loop de "Desconectado" en
        # produccion que no se podia diagnosticar sin esto.
        logger.warning("[support.channels_auth] Token WS rechazado (%s): %s", type(exc).__name__, exc)
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        token_list = params.get('token', [])
        if token_list:
            scope['user'] = await _get_user_from_token(token_list[0])
        else:
            # FASE 2 (auditoria WS, 2026-08-07): sin token en la query string, el scope
            # queda con lo que ya haya puesto AuthMiddlewareStack (sesion/cookie, casi
            # siempre AnonymousUser para el widget SPA) -- deja rastro explicito en vez
            # de que el rechazo en connect() luzca identico a un token invalido.
            logger.info("[WS][AUTH] sin parametro 'token' en query string -- se usa auth de sesion/anonima")
        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    from channels.auth import AuthMiddlewareStack
    return AuthMiddlewareStack(JWTAuthMiddleware(inner))
