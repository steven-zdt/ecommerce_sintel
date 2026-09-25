"""
dashboard/api/mcp_views.py -- PROMPT_IMPLEMENTAR_MCP_ECOMMERCE_ADMIN_CODE_AGENT_SINTEL, FASE 2 (2026-09-25).

Identidad para el servidor MCP (`mcp_server/`). El MCP NO tiene RBAC propio: valida el bearer de su cliente preguntandole a Django quien es. Este endpoint solo
responde a un admin real (IsAdminUser = is_staff AND is_superuser, la misma regla del panel) y solo LEE: nunca crea ni modifica nada.

`/api/v1/auth/profile/` no sirve para esto porque no expone `is_superuser`; probar un endpoint admin dedicado es la unica forma de que la autoridad final siga
siendo Django. Devuelve 401 (token invalido/expirado) o 403 (autenticado pero no admin) por la maquinaria normal de DRF.
"""
from rest_framework.response import Response
from rest_framework.views import APIView

from dashboard.api.views import ADMIN_PERMISSIONS


class AdminMcpWhoAmIView(APIView):
    """GET /api/v1/dashboard/mcp/whoami/ -> {uuid, email, is_admin, is_staff, is_superuser}. Sin efectos secundarios ni datos sensibles."""
    permission_classes = ADMIN_PERMISSIONS

    def get(self, request):
        user = request.user
        return Response({
            'uuid': str(user.uuid),
            'email': user.email,
            'is_admin': True,  # si llego aqui, IsAdminUser ya lo confirmo
            'is_staff': bool(user.is_staff),
            'is_superuser': bool(user.is_superuser),
        })


# ---------------------------------------------------------------------------------------------------------------------
# Tokens personales del MCP (PROMPT MCP, FASE 2): el admin los gestiona desde el panel/API con SU sesion normal.
# ---------------------------------------------------------------------------------------------------------------------
from django.core.exceptions import ValidationError as DjangoValidationError  # noqa: E402
from django.http import Http404  # noqa: E402
from rest_framework import serializers, status, viewsets  # noqa: E402
from rest_framework.exceptions import ValidationError as DRFValidationError  # noqa: E402

from security.models import McpAccessToken  # noqa: E402
from security.services.mcp_tokens import McpTokenCommands, McpTokenError, McpTokenSelectors  # noqa: E402


class McpTokenSerializer(serializers.Serializer):
    """Lectura: NUNCA incluye el token ni su hash, solo el prefijo para identificarlo."""
    uuid = serializers.UUIDField()
    name = serializers.CharField()
    token_prefix = serializers.CharField()
    created_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField()
    last_used_at = serializers.DateTimeField()
    revoked_at = serializers.DateTimeField()
    is_active = serializers.BooleanField()


class McpTokenCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    days = serializers.IntegerField(required=False, min_value=1)


class AdminMcpTokenViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/mcp-tokens/ -- tokens personales del servidor MCP del admin AUTENTICADO (nunca de otro usuario).
    POST devuelve el token en claro UNA sola vez; despues solo se ve su prefijo. DELETE = revocar (el token deja de canjearse).
    Un JWT obtenido por un cliente MCP (claim via=mcp) NO puede crear ni revocar tokens.
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        return Response(McpTokenSerializer(McpTokenSelectors.list_for_user(request.user), many=True).data)

    def create(self, request):
        serializer = McpTokenCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token, plaintext = McpTokenCommands.create_token(request.user, serializer.validated_data['name'], serializer.validated_data.get('days'), request=request)
        except McpTokenError as exc:
            raise DRFValidationError({'detail': str(exc)})
        return Response({**McpTokenSerializer(token).data, 'token': plaintext,
                         'warning': 'Guarda este token ahora: no se volvera a mostrar.'}, status=status.HTTP_201_CREATED)

    def destroy(self, request, uuid=None):
        try:
            token = McpTokenSelectors.get_for_user(request.user, uuid)
        except (McpAccessToken.DoesNotExist, ValueError, DjangoValidationError):  # uuid mal formado o token de OTRO usuario => 404 (sin distinguir)
            raise Http404
        try:
            McpTokenCommands.revoke_token(token, request.user, request=request)
        except McpTokenError as exc:
            raise DRFValidationError({'detail': str(exc)})
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------------------------------------------------
# Auditoria durable de acciones del MCP (PROMPT MCP, sec. 15): el MCP registra cada escritura tambien aqui (SecurityEvent MCP_ACTION),
# ademas de sus logs. Es append-only y la llama el propio servidor MCP con el token del cliente (el usuario del evento es el admin real).
# ---------------------------------------------------------------------------------------------------------------------
from rest_framework.views import APIView as _APIView  # noqa: E402

from security.models import SecurityEvent  # noqa: E402
from security.services.commands import SecurityCommands  # noqa: E402

_AUDIT_ALLOWED = ('tool', 'resource', 'operation', 'target', 'risk', 'confirmation', 'result', 'request_id', 'trace_id')


class AdminMcpAuditView(_APIView):
    """POST /api/v1/dashboard/mcp/audit/ -- SOLO admins. Guarda una lista blanca de campos cortos: nunca valores de los datos ni secretos."""
    permission_classes = ADMIN_PERMISSIONS

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        metadata = {k: str(data.get(k, ''))[:80] for k in _AUDIT_ALLOWED if data.get(k) not in (None, '')}
        fields = data.get('changed_fields')
        if isinstance(fields, list):
            metadata['changed_fields'] = [str(f)[:60] for f in fields[:40]]
        metadata['via_mcp'] = True
        SecurityCommands.log_event(SecurityEvent.MCP_ACTION, request=request, user=request.user, metadata=metadata)
        return Response({'ok': True}, status=status.HTTP_201_CREATED)
