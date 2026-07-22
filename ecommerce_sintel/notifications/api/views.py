from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from users.api.permissions import IsAuthenticatedActiveUser
from notifications.models import (
    NotificationLog, UserNotificationPreference,
    CHANNEL_CHOICES,
)
from notifications.api.serializers import (
    NotificationLogSerializer,
    UserNotificationPreferenceSerializer,
)
from notifications.services.commands import NotificationPreferenceCommands


@extend_schema(tags=['notifications'])
class NotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Historial de notificaciones del usuario autenticado.
    GET /api/v1/notifications/logs/
    """
    serializer_class   = NotificationLogSerializer
    permission_classes = [IsAuthenticatedActiveUser]
    lookup_field       = 'uuid'

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return NotificationLog.objects.none()
        return (
            NotificationLog.objects
            .filter(user=self.request.user, is_deleted=False)
            .select_related('template')
            .order_by('-created_at')
        )


@extend_schema(tags=['notifications'])
class UserNotificationPreferenceViewSet(viewsets.ViewSet):
    """
    Preferencias de canal de notificación del usuario autenticado.

    GET  /api/v1/notifications/preferences/  → lista canales y estado actual
    POST /api/v1/notifications/preferences/set/  → { channel, is_enabled }
    """
    permission_classes = [IsAuthenticatedActiveUser]

    def list(self, request):
        prefs = UserNotificationPreference.objects.filter(user=request.user)
        # Completar con canales sin preferencia registrada (is_enabled=True por defecto)
        pref_map = {p.channel: p.is_enabled for p in prefs}
        result = []
        for code, label in CHANNEL_CHOICES:
            result.append({
                'channel':    code,
                'label':      label,
                'is_enabled': pref_map.get(code, True),
            })
        return Response(result)

    @action(detail=False, methods=['post'], url_path='set')
    def set_preference(self, request):
        channel    = request.data.get('channel', '').upper()
        is_enabled = request.data.get('is_enabled')

        valid_channels = [c for c, _ in CHANNEL_CHOICES]
        if channel not in valid_channels:
            return Response(
                {'detail': f'Canal inválido. Opciones: {valid_channels}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if is_enabled is None:
            return Response(
                {'detail': 'Campo is_enabled requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pref = NotificationPreferenceCommands.set_preference(
            user=request.user, channel=channel, is_enabled=bool(is_enabled)
        )
        return Response(UserNotificationPreferenceSerializer(pref).data)
