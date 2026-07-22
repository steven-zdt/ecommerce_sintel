from django.core.exceptions import ObjectDoesNotExist
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework import status


def api_exception_handler(exc, context):
    """
    Extiende el exception handler por defecto de DRF: convierte un
    Model.DoesNotExist no capturado (ej. un uuid valido pero ya
    soft-deleted, o inexistente, pasado a un viewsets.ViewSet plano sin
    get_object_or_404) en un 404 limpio en vez de un 500 sin manejar.
    """
    if isinstance(exc, ObjectDoesNotExist):
        return Response({'detail': 'No encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    if isinstance(exc, Throttled):
        from security.models import SecurityEvent
        from security.services.commands import SecurityCommands
        SecurityCommands.log_event(
            SecurityEvent.RATE_LIMIT_HIT, request=context.get('request'),
            severity=SecurityEvent.SEVERITY_WARNING,
            metadata={'wait': exc.wait},
        )

    return drf_exception_handler(exc, context)
