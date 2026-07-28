"""
Endpoints internos para el AI Engine (Fase 4 AI Core).

Lectura: QuoteTemplateSelector.list_active() (paso 1 del wizard).
Escritura: QuotationCommands.create_from_template() reusando
QuotationFromTemplateInputSerializer (misma validacion que /cotizar).
Auditado en security.SecurityEvent (AI_ACTION_EXECUTED).
"""
from django.db import IntegrityError
from rest_framework import status as http_status
from rest_framework.views import APIView
from rest_framework.response import Response

from quotes.models import Quotation
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
        # Q-05 (auditoria enterprise): mismo mecanismo de idempotencia que el
        # endpoint publico /cotizar (from_template en quotes/api/views.py) --
        # antes este camino del motor de IA llamaba directo a
        # QuotationBuilder.create_from_template() sin ninguna proteccion,
        # asi que un reintento del Action Graph podia crear una segunda
        # Quotation para la misma solicitud.
        idempotency_key = request.data.get('idempotency_key') or None
        if idempotency_key:
            existing = Quotation.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                return Response({'quotation': {
                    'uuid': str(existing.uuid),
                    'status': existing.status,
                    'status_label': existing.get_status_display(),
                    'template': existing.template.name if existing.template_id else None,
                }}, status=http_status.HTTP_200_OK)

        serializer = QuotationFromTemplateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        template = data.pop('template')
        answers = data.pop('answers', {}) or {}
        applicant_data = {**data, 'user': request.user}
        if idempotency_key:
            applicant_data['idempotency_key'] = idempotency_key
        try:
            quotation = QuotationBuilder.create_from_template(applicant_data, template, answers)
        except IntegrityError:
            if idempotency_key:
                existing = Quotation.objects.filter(idempotency_key=idempotency_key).first()
                if existing:
                    return Response({'quotation': {
                        'uuid': str(existing.uuid),
                        'status': existing.status,
                        'status_label': existing.get_status_display(),
                        'template': existing.template.name if existing.template_id else None,
                    }}, status=http_status.HTTP_200_OK)
            return Response({'error': 'No se pudo procesar la solicitud.'}, status=http_status.HTTP_400_BAD_REQUEST)
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
