"""
users/api/admin_password_reset.py

Recuperacion de contrasena self-service EXCLUSIVA para administradores del sistema.

REGLAS DE DISENO (mismo aislamiento que users/api/admin_auth.py):
- Completamente independiente de accounts.api.views y AccountCommands.
- Solo opera sobre usuarios con is_staff=True AND is_superuser=True
  (ver AdminPasswordResetCommands en users/services/commands.py).
- No depende de accounts.api.serializers -- serializers propios, pequenos,
  duplicados a proposito para no crear una dependencia cruzada.
- Archivo nuevo (no se edita admin_auth.py) para no arriesgar el login admin.
"""
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from users.services.commands import AdminPasswordResetCommands


class AdminForgotPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower().strip()


class AdminVerifyResetCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)

    def validate_email(self, value):
        return value.lower().strip()

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("El codigo debe contener solo digitos.")
        return value


class AdminResetPasswordSerializer(AdminVerifyResetCodeSerializer):
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, data):
        data = super().validate(data)
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "Las contrasenas no coinciden."})
        return data


class _BaseAdminPasswordResetView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    renderer_classes = [JSONRenderer]


class AdminForgotPasswordRequestView(_BaseAdminPasswordResetView):
    """
    POST /api/v1/admin-auth/forgot-password-request/

    Paso 1. Siempre responde el mismo 200 generico exista o no el correo
    (y exista o no como admin), para no revelar cuentas.
    """
    throttle_scope = 'admin_password_reset_request'

    def post(self, request):
        serializer = AdminForgotPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AdminPasswordResetCommands.request_reset(serializer.validated_data['email'])
        return Response(
            {'detail': 'Si el correo existe, se ha enviado un codigo de recuperacion.'},
            status=status.HTTP_200_OK,
        )


class AdminForgotPasswordVerifyView(_BaseAdminPasswordResetView):
    """POST /api/v1/admin-auth/forgot-password-verify/ -- valida el codigo sin consumirlo."""
    throttle_scope = 'admin_password_reset_verify'

    def post(self, request):
        serializer = AdminVerifyResetCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AdminPasswordResetCommands.verify_reset_code(
            serializer.validated_data['email'], serializer.validated_data['code']
        )
        return Response({'detail': 'Codigo valido.'}, status=status.HTTP_200_OK)


class AdminResetPasswordView(_BaseAdminPasswordResetView):
    """
    POST /api/v1/admin-auth/reset-password/

    Paso 3: consume el codigo, establece la nueva contrasena, y emite tokens
    JWT (mismo shape que AdminLoginView) para iniciar sesion automaticamente.
    """
    throttle_scope = 'admin_password_reset_request'

    def post(self, request):
        serializer = AdminResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AdminPasswordResetCommands.confirm_reset(
            serializer.validated_data['email'],
            serializer.validated_data['code'],
            serializer.validated_data['new_password'],
        )

        refresh = RefreshToken.for_user(user)
        refresh['is_staff'] = user.is_staff
        refresh['is_superuser'] = user.is_superuser

        return Response({
            'user': {
                'id': user.id,
                'uuid': str(user.uuid),
                'email': user.email,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
        })
