from django.utils import timezone
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from users.api.permissions import IsAdminUser
from security.api.serializers import SecurityEventSerializer
from security.services.selectors import SecuritySelector


class SecurityHealthView(APIView):
    """GET /api/v1/security/health/ -- ping de DB/Redis/Celery, solo admin."""
    permission_classes = [IsAdminUser]

    @extend_schema(summary="[Admin] Estado de salud de DB/Redis/Celery")
    def get(self, request):
        snapshot = SecuritySelector.get_health_snapshot()
        snapshot['timestamp'] = timezone.now()
        return Response(snapshot)


class SecurityEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    K-04 (auditoria enterprise): antes SecuritySelector.list_events() existia
    pero no estaba conectado a ninguna vista -- la unica forma de revisar
    SecurityEvent era el admin de Django (bien protegido, pero no
    programable/automatizable). Solo lectura, solo admin -- SecurityEvent es
    append-only, nunca se expone un endpoint de escritura fuera de
    SecurityCommands.log_event().

    GET /api/v1/security/events/?event_type=...&severity=...&user_uuid=...
    """
    permission_classes = [IsAdminUser]
    serializer_class = SecurityEventSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        return SecuritySelector.list_events(
            event_type=self.request.query_params.get('event_type'),
            severity=self.request.query_params.get('severity'),
            user_uuid=self.request.query_params.get('user_uuid'),
        )
