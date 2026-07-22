"""
users/api/admin_auth.py

Endpoint de autenticacion EXCLUSIVO para administradores del sistema.

REGLAS DE DISENO (NO MODIFICAR):
- Este archivo es completamente independiente de accounts.api.views y AccountCommands.
- Solo permite login a usuarios con is_staff=True AND is_superuser=True.
- Usa django.contrib.auth.authenticate() directamente — no pasa por ninguna logica
  de accounts ni por ContractorRecommendationSelector ni por ninguna otra abstraccion.
- NUNCA agregar checks de is_verified, user_type, TechnicianProfile.is_available,
  ContractorProfile, ni ningun otro campo de negocio aqui.
- Si se rompe este endpoint, el admin queda sin acceso. Tocar con extremo cuidado.
"""
from django.conf import settings
from django.contrib.auth import authenticate
from django.http import HttpResponseRedirect
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

def _get_frontend_login_url():
    """
    URL del login admin en el frontend Vue.

    [2026-07-12] `settings.FRONTEND_ADMIN_LOGIN_URL` nunca se definio en ningun
    .env de este proyecto (bug fantasma encontrado en la auditoria de
    MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md) -- en produccion este redirect
    siempre caia al hardcode de abajo. Ahora prefiere
    organization.EmailSettings.admin_login_url (editable a futuro desde el
    panel admin), conservando los mismos 2 fallbacks de antes sin cambiar el
    comportamiento actual (el campo esta vacio hasta que se configure).
    Evaluado por request, no a nivel de modulo, porque requiere el ORM.
    """
    from organization.services.selectors import OrganizationSelector
    email_settings = OrganizationSelector.get_email_settings()
    return (
        (email_settings.admin_login_url if email_settings else '')
        or getattr(settings, 'FRONTEND_ADMIN_LOGIN_URL', '')
        or 'http://localhost:5173/panel/login'
    )


class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        return value.lower().strip()


class AdminLoginView(APIView):
    """
    POST /api/v1/admin-auth/login/

    Login exclusivo para superusuarios (is_staff=True + is_superuser=True).
    Retorna tokens JWT y datos basicos del admin.

    AISLAMIENTO: No depende de accounts.api ni de AccountCommands.
    Cambios en el flujo de login de usuarios regulares NO afectan este endpoint.
    renderer_classes = [JSONRenderer] desactiva la UI navegable de DRF — solo JSON.
    """
    permission_classes     = [AllowAny]
    authentication_classes = []
    throttle_classes       = [ScopedRateThrottle]
    throttle_scope         = 'admin_login'
    renderer_classes       = [JSONRenderer]

    def get(self, request):
        return HttpResponseRedirect(_get_frontend_login_url())

    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email    = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = authenticate(request, email=email, password=password)

        if user is None:
            raise AuthenticationFailed("Credenciales invalidas.")

        if not user.is_active:
            raise AuthenticationFailed("Cuenta desactivada.")

        if not (user.is_staff and user.is_superuser):
            raise AuthenticationFailed("Acceso restringido a administradores del sistema.")

        refresh = RefreshToken.for_user(user)
        refresh['is_staff']     = user.is_staff
        refresh['is_superuser'] = user.is_superuser

        return Response({
            'user': {
                'id':           user.id,
                'uuid':         str(user.uuid),
                'email':        user.email,
                'is_staff':     user.is_staff,
                'is_superuser': user.is_superuser,
            },
            'tokens': {
                'refresh': str(refresh),
                'access':  str(refresh.access_token),
            },
        })
