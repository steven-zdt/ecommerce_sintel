from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from users.api.permissions import IsAdminUser
from security.services.selectors import SecuritySelector


class SecurityHealthView(APIView):
    """GET /api/v1/security/health/ -- ping de DB/Redis/Celery, solo admin."""
    permission_classes = [IsAdminUser]

    @extend_schema(summary="[Admin] Estado de salud de DB/Redis/Celery")
    def get(self, request):
        snapshot = SecuritySelector.get_health_snapshot()
        snapshot['timestamp'] = timezone.now()
        return Response(snapshot)
