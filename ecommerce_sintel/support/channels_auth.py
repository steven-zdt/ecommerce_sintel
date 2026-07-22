from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async


@database_sync_to_async
def _get_user_from_token(token_key: str):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import AnonymousUser
    try:
        from rest_framework_simplejwt.tokens import AccessToken
        token = AccessToken(token_key)
        User = get_user_model()
        return User.objects.get(pk=token['user_id'], is_active=True)
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        token_list = params.get('token', [])
        if token_list:
            scope['user'] = await _get_user_from_token(token_list[0])
        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    from channels.auth import AuthMiddlewareStack
    return AuthMiddlewareStack(JWTAuthMiddleware(inner))
