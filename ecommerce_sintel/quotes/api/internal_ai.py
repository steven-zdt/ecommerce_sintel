"""
Endpoints internos para el AI Engine (Fase 4 AI Core).

Lectura: QuoteTemplateSelector.list_active() (paso 1 del wizard).
Escritura: QuotationCommands.create_from_template() reusando
QuotationFromTemplateInputSerializer (misma validacion que /cotizar).
Auditado en security.SecurityEvent (AI_ACTION_EXECUTED).
"""
from rest_framework import status as http_status
from rest_framework.views import APIView
from rest_framework.response import Response

from quotes.api.serializers import QuotationFromTemplateInputSerializer
from quotes.services.commands import QuotationBuilder
from quotes.services.selectors import QuoteTemplateSelector
from users.api.permissions import IsAuthenticatedActiveUser


class AiQuoteTemplatesView(APIView):
    """GET /api/v1/internal/ai/quotes/templates/ -> plantillas activas del cuestionario."""
    permission_classes = [IsAuthenticatedActiveUser]

    def get(self, request):
        templates = QuoteTemplateSelector.list_active()[:20]
        return Response({'templates': [
            {
                'uuid': str(t.uuid),
                'name': t.name,
                'description': getattr(t, 'description', '') or '',
            }
            for t in templates
        ]})


class AiStartQuotationView(APIView):
    """
    POST /api/v1/internal/ai/quotes/create/ (Fase 4)

    Crea una Quotation-solicitud (STATUS_RECEIVED, sin precios -- un asesor
    cotiza despues). Misma validacion que el cuestionario publico.
    """
    permission_classes = [IsAuthenticatedActiveUser]

    def post(self, request):
        serializer = QuotationFromTemplateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        template = data.pop('template')
        answers = data.pop('answers', {}) or {}
        applicant_data = {**data, 'user': request.user}
        try:
            quotation = QuotationBuilder.create_from_template(applicant_data, template, answers)
        except Exception as exc:
            return Response({'error': str(exc)}, status=http_status.HTTP_400_BAD_REQUEST)

        from security.models import SecurityEvent
        from security.services.commands import SecurityCommands
        SecurityCommands.log_event(
            SecurityEvent.AI_ACTION_EXECUTED,
            request=request,
            metadata={'tool': 'StartQuotationTool', 'quotation_uuid': str(quotation.uuid)},
        )
        return Response({'quotation': {
            'uuid': str(quotation.uuid),
            'status': quotation.status,
            'status_label': quotation.get_status_display(),
            'template': template.name,
        }}, status=http_status.HTTP_201_CREATED)
