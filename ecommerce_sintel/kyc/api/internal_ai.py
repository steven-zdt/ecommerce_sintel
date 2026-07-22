"""
Endpoints internos para el AI Engine (Fases 2 y 4 AI Core).

Lectura: KycSelector.get_own_verification (self-service por diseno).
Escritura (Fase 4): KycCommands.request_upgrade reusando
RequestUpgradeSerializer (mismas choices SERVICE_PROVIDER_TYPES que el
endpoint publico auth/request-upgrade/). Auditado en SecurityEvent.
"""
from rest_framework import status as http_status
from rest_framework.views import APIView
from rest_framework.response import Response

from kyc.api.serializers import RequestUpgradeSerializer
from kyc.services.commands import KycCommands
from kyc.services.selectors import KycSelector
from users.api.permissions import IsAuthenticatedActiveUser


class AiKycStatusView(APIView):
    """GET /api/v1/internal/ai/kyc/ -> estado KYC del usuario autenticado."""
    permission_classes = [IsAuthenticatedActiveUser]

    def get(self, request):
        verification = KycSelector.get_own_verification(request.user)
        if verification is None:
            return Response({'verification': None})
        return Response({'verification': {
            'status': verification.status,
            'status_label': verification.get_status_display(),
            'requested_user_type': verification.requested_user_type or None,
            'submitted_at': verification.submitted_at.isoformat() if verification.submitted_at else None,
            'first_approved_at': verification.first_approved_at.isoformat() if verification.first_approved_at else None,
        }})


class AiRequestKycUpgradeView(APIView):
    """
    POST /api/v1/internal/ai/kyc/request-upgrade/ {requested_user_type} (Fase 4)

    Reabre la UserVerification del usuario a PENDING para el upgrade
    profesional -- misma semantica que POST auth/request-upgrade/. El
    command valida el estado (solo APPROVED puede pedir upgrade).
    """
    permission_classes = [IsAuthenticatedActiveUser]

    def post(self, request):
        serializer = RequestUpgradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        verification = KycSelector.get_own_verification(request.user)
        if verification is None:
            return Response({'error': 'El usuario no tiene verificacion KYC.'}, status=http_status.HTTP_400_BAD_REQUEST)
        verification = KycCommands.request_upgrade(
            verification, serializer.validated_data['requested_user_type'], request.user,
        )

        from security.models import SecurityEvent
        from security.services.commands import SecurityCommands
        SecurityCommands.log_event(
            SecurityEvent.AI_ACTION_EXECUTED,
            request=request,
            metadata={'tool': 'RequestKycUpgradeTool',
                      'requested_user_type': verification.requested_user_type},
        )
        return Response({'verification': {
            'status': verification.status,
            'requested_user_type': verification.requested_user_type,
            'detail': 'Upgrade solicitado: sube los documentos requeridos en mi-cuenta/verificacion.',
        }})
