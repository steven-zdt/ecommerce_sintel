"""
Proxy Django -> ai_engine_adk para el Admin AI Assistant (panel /panel/asistente).

Mismo patron que support/services/ai_bridge.py (que ya usa settings.AI_ENGINE_URL
para el chat de soporte del cliente, real desde el cutover a ai_engine_adk): Django
acuna un access token efimero del ADMIN real (nunca se persiste) para autenticar la
llamada -- el routing determinista de ai_engine_adk (ver ai_engine/routing.py,
intent "catalog_admin") y el permiso IsAdminUser de cada Tool (ver
ai_engine/tools/catalog_tools.py + shop/api/internal_ai.py) son la autoridad real,
esta vista solo transporta.

No hay endpoint publico para esto -- requiere ADMIN_PERMISSIONS como el resto de
`dashboard`, igual que cualquier otro ViewSet de este BFF.
"""
import logging
import time

import requests
from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from support.services.ai_bridge import AI_CHAT_TIMEOUT_SECONDS
from users.api.permissions import IsAdminUser

logger = logging.getLogger(__name__)

ADMIN_PERMISSIONS = [permissions.IsAuthenticated, IsAdminUser]


class AdminAiAssistantChatView(APIView):
    """
    POST /api/v1/dashboard/ai-assistant/chat/

    Body: {"message": str, "conversation_id": str|null, "confirm": bool|null}
    Devuelve tal cual el contrato de ai_engine_adk (ver ai_engine_adk/main.py
    ChatResponse): response/agent/intent/tool_calls/tool_results/
    needs_confirmation/confirmation/metrics -- el frontend decide como
    renderizar cada pieza (ver AiAssistantView.vue).
    """
    permission_classes = ADMIN_PERMISSIONS

    def post(self, request):
        # Congelado a pedido explicito del usuario (2026-09-16) hasta nueva orden --
        # ver settings.ADMIN_AI_ASSISTANT_ENABLED. El resto del codigo (Tools, agente,
        # rutas /internal/ai/catalog/*, UI en /panel/asistente) sigue intacto, solo
        # este gateway lo bloquea -- reactivar es cambiar esta unica variable.
        if not (getattr(settings, 'AI_GLOBAL_ENABLED', True) and settings.ADMIN_AI_ASSISTANT_ENABLED):
            return Response(
                {'error': 'El Asistente IA esta deshabilitado temporalmente por el administrador.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        message = (request.data.get('message') or '').strip()
        conversation_id = request.data.get('conversation_id')
        confirm = request.data.get('confirm')
        # `confirm` no-None = este turno RESUME una confirmacion pendiente (ver
        # sintel_root_workflow.py::run_sintel_turn) -- no es un mensaje nuevo, message
        # puede venir vacio.
        if not message and confirm is None:
            return Response({'error': 'message requerido.'}, status=status.HTTP_400_BAD_REQUEST)

        from rest_framework_simplejwt.tokens import AccessToken
        token = str(AccessToken.for_user(request.user))
        from support.services.ai_bridge import build_ai_headers  # F2: JWT + X-AI-Service-Token

        start = time.monotonic()
        try:
            resp = requests.post(
                f"{settings.AI_ENGINE_URL}/chat",
                # 'source': 'admin' -- ver ChatRequest.source (ai_engine_adk/main.py) y
                # el docstring de resolve_turn_agent (sintel_root_workflow.py). Sin esto,
                # un mensaje que no matchea el regex de catalog_admin cae en un agente de
                # CLIENTE (bug real encontrado 2026-09-23: SupportAgent abrio un ticket
                # real tratando al admin como comprador).
                json={'message': message, 'conversation_id': conversation_id, 'confirm': confirm, 'source': 'admin'},
                headers=build_ai_headers(token, conversation_id),
                timeout=AI_CHAT_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.warning(
                '[ADMIN_AI_ASSISTANT] motor inalcanzable user=%s latency_ms=%d error=%s: %s',
                request.user.email, latency_ms, type(exc).__name__, exc,
            )
            return Response(
                {'error': 'El asistente no esta disponible en este momento. Intenta de nuevo en unos segundos.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if resp.status_code != 200:
            logger.warning(
                '[ADMIN_AI_ASSISTANT] respuesta inesperada user=%s status=%d body=%s',
                request.user.email, resp.status_code, resp.text[:300],
            )
            return Response(
                {'error': 'El asistente no pudo procesar la solicitud.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(resp.json())
