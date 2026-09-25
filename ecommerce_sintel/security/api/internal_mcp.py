"""
security/api/internal_mcp.py -- canje de token MCP por JWT corto (PROMPT MCP, FASE 2). Ruta /api/v1/internal/mcp/exchange/ (nginx no proxea /internal/ hacia afuera).

La credencial es el propio token MCP (por eso AllowAny a nivel DRF). Cada rechazo responde 401 generico y queda auditado; hay limite por IP. El JWT devuelto tiene el claim `via=mcp`.
"""
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from security.services.mcp_tokens import McpTokenCommands, McpTokenError


class McpTokenExchangeView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []  # ni sesion ni JWT: solo el token MCP del cuerpo

    def post(self, request):
        try:
            data = McpTokenCommands.exchange(str(request.data.get('token', '')), request=request)
        except McpTokenError:
            return Response({'error': 'invalid_token'}, status=401)
        return Response(data)
