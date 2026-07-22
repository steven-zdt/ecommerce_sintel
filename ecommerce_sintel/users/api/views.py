"""
UserViewSet — Gestión de usuarios para el panel administrativo.
Ahora usa permisos DRF centralizados (users.api.permissions) en lugar
de validaciones manuales por método.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.contrib.auth.models import Group
from django.shortcuts import get_object_or_404
from django.db import transaction as db_transaction
from drf_spectacular.utils import extend_schema, extend_schema_view
from users.models import User, UserAuditLog
from django.db.models.deletion import ProtectedError
from django.db import IntegrityError
from users.services import UserSelector, UserAuditLogSelector, UserAuditCommands, UserCommands
from users.api.permissions import IsAdminUser
from users.api.serializers import (
    UserDetailSerializer,
    UserProfileSerializer,
    UserAdminCreateSerializer,
    UserAdminUpdateSerializer,
    GroupSerializer,
    UserGroupsUpdateSerializer,
    UserAuditLogSerializer,
)
from accounts.services import AccountCommands, ProfileResolver


class UserAdminResultsPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


@extend_schema_view(
    list=extend_schema(summary="Lista usuarios, con filtros/busqueda/paginacion (solo admin)", responses={200: UserDetailSerializer(many=True)}),
    create=extend_schema(summary="Crea un usuario nuevo (solo admin)", request=UserAdminCreateSerializer, responses={201: UserDetailSerializer}),
    retrieve=extend_schema(summary="Detalle de un usuario (solo admin)", responses={200: UserDetailSerializer}),
    partial_update=extend_schema(summary="Actualiza parcialmente un usuario (solo admin)", request=UserAdminUpdateSerializer, responses={200: UserDetailSerializer}),
    destroy=extend_schema(summary="Desactiva un usuario (soft-delete, solo admin)"),
)
class UserViewSet(viewsets.ViewSet):
    """
    ViewSet para gestión de usuarios.
    - Admin CRUD: /api/v1/users/  (list, create, retrieve, partial_update, destroy)
    - Protegido por IsAdminUser — Solo staff con role=ADMIN.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    lookup_field = 'uuid'

    def list(self, request):
        """Lista usuarios con filtros/busqueda/ordering + paginacion del servidor."""
        qs = UserSelector.list_all(
            search=request.query_params.get('search', ''),
            user_type=request.query_params.get('user_type', ''),
            is_active=request.query_params.get('is_active', ''),
            is_verified=request.query_params.get('is_verified', ''),
            company=request.query_params.get('company', ''),
            city=request.query_params.get('city', ''),
            country=request.query_params.get('country', ''),
            ordering=request.query_params.get('ordering', '-date_joined'),
        )
        paginator = UserAdminResultsPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(UserDetailSerializer(page, many=True).data)
        return Response(UserDetailSerializer(qs, many=True).data)

    def create(self, request):
        """Crea un usuario nuevo."""
        serializer = UserAdminCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AccountCommands.register_user(serializer.validated_data)
        UserAuditCommands.log(
            request.user, user, UserAuditLog.ACTION_CREATED,
            metadata={'user_type': ProfileResolver.get_type(user)},
        )
        return Response(UserDetailSerializer(user).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        """Detalle de un usuario por ID."""
        user = get_object_or_404(User, uuid=uuid)
        return Response(UserDetailSerializer(user).data)

    def partial_update(self, request, uuid=None):
        """Actualiza parcialmente un usuario."""
        user = get_object_or_404(User, uuid=uuid)
        if user == request.user and request.data.get('is_active') is False:
            return Response(
                {'detail': 'No puedes desactivarte a ti mismo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = UserAdminUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        prev_is_active = user.is_active
        with db_transaction.atomic():
            updated = AccountCommands.admin_update_user(user, serializer.validated_data)
            if 'is_active' in serializer.validated_data and updated.is_active != prev_is_active:
                UserAuditCommands.log(
                    request.user, updated,
                    UserAuditLog.ACTION_ACTIVATED if updated.is_active else UserAuditLog.ACTION_DEACTIVATED,
                )
            UserAuditCommands.log(
                request.user, updated, UserAuditLog.ACTION_UPDATED,
                metadata=dict(serializer.validated_data),
            )
        return Response(UserDetailSerializer(updated).data)

    def destroy(self, request, uuid=None):
        """Desactiva (soft-delete) un usuario."""
        user = get_object_or_404(User, uuid=uuid)
        if user == request.user:
            return Response(
                {'detail': 'No puedes desactivarte a ti mismo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with db_transaction.atomic():
            user.is_active = False
            user.save(update_fields=['is_active'])
            UserAuditCommands.log(request.user, user, UserAuditLog.ACTION_DEACTIVATED, metadata={'source': 'destroy'})
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['delete'], url_path='erase')
    def erase(self, request, uuid=None):
        """
        Elimina permanentemente (de la UI) un usuario inactivo -- soft-delete
        real (is_deleted=True), nunca DELETE fisico. Ver UserCommands.erase_user
        para el porque: un hard-delete aqui podia chocar con on_delete=PROTECT
        dos saltos mas abajo en el grafo de borrado y lanzar un 500 sin control.
        """
        user = get_object_or_404(User, uuid=uuid)
        try:
            UserCommands.erase_user(request.user, user)
        except (ProtectedError, IntegrityError):
            # Defensa adicional: con el diseno actual (soft-delete) esto no
            # deberia poder ocurrir nunca -- se deja como red de seguridad.
            return Response(
                {'detail': 'No es posible eliminar este usuario porque posee informacion asociada.'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=None, responses={200: dict})
    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, uuid=None):
        """Genera una contrasena temporal, la aplica y la envia por correo al usuario."""
        user = get_object_or_404(User, uuid=uuid)
        AccountCommands.admin_reset_password(user)
        UserAuditCommands.log(request.user, user, UserAuditLog.ACTION_PASSWORD_RESET)
        return Response({'detail': 'Se generó una nueva contraseña temporal y se envió por correo al usuario.'})

    @extend_schema(request=None, responses={200: dict})
    @action(detail=True, methods=['post'], url_path='resend-verification')
    def resend_verification(self, request, uuid=None):
        """Reenvia un enlace de verificacion de correo a un usuario ya existente."""
        user = get_object_or_404(User, uuid=uuid)
        if user.is_verified:
            return Response(
                {'detail': 'Este usuario ya tiene el correo verificado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        AccountCommands.resend_verification_email(user)
        UserAuditCommands.log(request.user, user, UserAuditLog.ACTION_VERIFICATION_RESENT)
        return Response({'detail': 'Se envió un enlace de verificación al correo del usuario.'})

    @extend_schema(responses={200: GroupSerializer(many=True)})
    @action(detail=False, methods=['get'], url_path='groups-catalog')
    def groups_catalog(self, request):
        """Catalogo de Django Groups existentes, para el editor de asignacion."""
        return Response(GroupSerializer(Group.objects.all().order_by('name'), many=True).data)

    @extend_schema(request=UserGroupsUpdateSerializer, responses={200: UserDetailSerializer})
    @action(detail=True, methods=['put'], url_path='groups')
    def update_groups(self, request, uuid=None):
        """
        Asigna al usuario a un conjunto de Django Groups existentes.
        Nota: hoy esto NO tiene ningun efecto en la autorizacion real del sistema (todo se basa en
        is_staff/is_superuser + accounts.UserProfile.user_type via ProfileResolver) -- es solo una
        UI de asignacion, tal como se pidio explicitamente.
        """
        user = get_object_or_404(User, uuid=uuid)
        serializer = UserGroupsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with db_transaction.atomic():
            updated = AccountCommands.set_user_groups(user, serializer.validated_data['group_ids'])
            UserAuditCommands.log(
                request.user, updated, UserAuditLog.ACTION_GROUPS_CHANGED,
                metadata={'group_ids': serializer.validated_data['group_ids']},
            )
        return Response(UserDetailSerializer(updated).data)

    @extend_schema(responses={200: UserAuditLogSerializer(many=True)})
    @action(detail=True, methods=['get'], url_path='audit-log')
    def audit_log(self, request, uuid=None):
        """Historial de acciones administrativas sobre este usuario, paginado."""
        user = get_object_or_404(User, uuid=uuid)
        qs = UserAuditLogSelector.list_for_user(user)
        paginator = UserAdminResultsPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(UserAuditLogSerializer(page, many=True).data)
