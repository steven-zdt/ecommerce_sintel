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
