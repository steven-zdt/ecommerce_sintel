"""
Endpoints internos consumidos exclusivamente por el AI Engine (sintel_ai).

Fase 1 del AI Core (ai_engine/.AGENT/PLAN_DE_ACCION_AI_CORE.md): el motor
valida el JWT de Django localmente (firma/expiracion) y luego llama a este
endpoint reenviando el MISMO token para resolverlo a un usuario/perfil real
via ProfileResolver -- nunca reimplementa esa logica fuera de Django.

Estas rutas viven bajo /api/v1/internal/ y solo son alcanzables dentro de la
red Docker (nginx no las proxea hacia afuera); aun asi exigen un JWT valido
de un usuario activo, igual que cualquier endpoint de negocio.
"""
from rest_framework.views import APIView
from rest_framework.response import Response

from accounts.services.profile_resolver import ProfileResolver
from users.api.permissions import IsAuthenticatedActiveUser


class AiContextView(APIView):
    """
    GET /api/v1/internal/ai-context/

    Devuelve el contexto minimo de identidad que el AI Engine necesita para
    saber "quien pregunta": tipo de usuario, nombre, flags de staff y estado
    KYC. No expone datos de negocio (pedidos/pagos) -- eso llega en fases
    posteriores via Tools dedicadas.
    """
    permission_classes = [IsAuthenticatedActiveUser]

    def get(self, request):
        user = request.user
        profile = ProfileResolver.get_profile(user)
        verification = ProfileResolver.get_verification(user)
        return Response({
            'user_id': user.id,
            'uuid': str(user.uuid),
            'email': user.email,
            'full_name': user.get_full_name(),
            'user_type': profile.user_type if profile else None,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'is_verified': user.is_verified,
            'kyc_status': verification.status if verification else None,
        })
