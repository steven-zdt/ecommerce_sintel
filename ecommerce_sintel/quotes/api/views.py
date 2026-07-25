import json
from django.db import IntegrityError
from django.http import HttpResponse
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from quotes.models import Quotation, QuotationAttachment
from quotes.services import (
    QuotationSelector, QuotationCommands,
    QuoteTemplateCategorySelector, QuoteTemplateSubcategorySelector, QuoteTemplateSelector,
)
from quotes.services.pdf_service import PDFService
from quotes.api.serializers import (
    QuotationSerializer,
    QuotationListSerializer,
    QuotationCreateInputSerializer,
    QuotationFromTemplateInputSerializer,
    QuoteTemplateCategorySerializer,
    QuoteTemplateSubcategorySerializer,
    QuoteTemplateListSerializer,
    QuoteTemplateSerializer,
)


class QuotationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for hybrid quotations (Products + Services + Rentals + Custom)
    y para Solicitudes de Cotizacion generadas desde un cuestionario tecnico.
    """
    queryset = QuotationSelector.list_all_for_admin()
    serializer_class = QuotationSerializer
    lookup_field = 'uuid'
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        # Cotizacion de Catalogo (create) es publica/anonima, como antes de
        # que el flujo del cuestionario tecnico exigiera login. list/retrieve
        # ya estan protegidos via get_queryset (Quotation.objects.none() sin auth).
        if self.action == 'create':
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_queryset(self):
        if self.request.user.is_authenticated and self.request.user.is_staff:
            return QuotationSelector.list_all_for_admin()
        if self.request.user.is_authenticated:
            return Quotation.objects.filter(user=self.request.user, is_deleted=False)
        return Quotation.objects.none()

    def get_serializer_class(self):
        if self.action == 'list':
            return QuotationListSerializer
        return QuotationSerializer

    @extend_schema(
        request=QuotationCreateInputSerializer,
        responses={201: QuotationSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = QuotationCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        client_data = {
            'client_name': data['client_name'],
            'client_email': data['client_email'],
            'valid_until': data['valid_until'],
            'notes': data.get('notes', ''),
            'user': request.user if request.user.is_authenticated else None,
        }

        attachments = request.FILES.getlist('attachments')

        try:
            quotation = QuotationCommands.create_quotation(
                client_data=client_data,
                product_items=data.get('product_items') or None,
                service_items=data.get('service_items') or None,
                rental_items=[dict(r) for r in data.get('rental_items', [])] or None,
                is_custom=data.get('is_custom', False),
                custom_service_data=[dict(s) for s in data.get('custom_service_data', [])] or None,
                attachments=attachments or None,
            )
            output = QuotationSerializer(quotation)
            return Response(output.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        request=QuotationFromTemplateInputSerializer,
        responses={201: QuotationSerializer},
    )
    @action(detail=False, methods=['post'], url_path='from-template', permission_classes=[permissions.IsAuthenticated])
    def from_template(self, request):
        """
        Crea una Solicitud de Cotizacion a partir de un cuestionario tecnico
        respondido por el cliente en /cotizar. NO calcula ningun precio —
        solo captura el requerimiento (respuestas por modulo + adjuntos de
        preguntas tipo archivo) para que un asesor comercial lo revise y
        cotice manualmente. Requiere cliente autenticado y destinatario
        identificado (nombre/email/documento) — ninguna solicitud se crea
        sin destinatario, ni anonima ni sin documento.
        """
        # H1 (auditoria E2E 2026-07-23): X-Idempotency-Key es la defensa de
        # backend contra duplicados -- reintentos con la misma llave (doble
        # clic que se cuela antes del guard de frontend, F5, reconexion)
        # devuelven la Quotation ya creada en vez de crear una nueva. El
        # guard sincrono en QuoteSummaryStep.vue evita la mayoria de los
        # casos; esto cubre lo que ese guard no puede (perdida de estado
        # del componente).
        idempotency_key = request.headers.get('X-Idempotency-Key') or None
        if idempotency_key:
            existing = Quotation.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                return Response(QuotationSerializer(existing).data, status=status.HTTP_200_OK)

        payload = request.data
        if isinstance(payload.get('answers'), str):
            payload = payload.copy()
            payload['answers'] = json.loads(payload['answers'] or '{}')

        serializer = QuotationFromTemplateInputSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        template = data.pop('template')
        answers = data.pop('answers', {}) or {}

        # getlist (no .items()) porque una misma clave file__<key> puede
        # traer varios archivos (ver requirement_documents, multiples
        # documentos por pregunta).
        files = {
            key[len('file__'):]: request.FILES.getlist(key)
            for key in request.FILES
            if key.startswith('file__')
        }

        applicant_data = {**data, 'user': request.user}
        if idempotency_key:
            applicant_data['idempotency_key'] = idempotency_key

        try:
            quotation = QuotationCommands.create_from_template(applicant_data, template, answers, files=files or None)
            return Response(QuotationSerializer(quotation).data, status=status.HTTP_201_CREATED)
        except IntegrityError:
            # Carrera real: dos peticiones con la misma llave llegaron a
            # INSERT casi al mismo tiempo y la constraint unique la gano
            # la otra -- devolver esa, no es un error del cliente.
            if idempotency_key:
                existing = Quotation.objects.filter(idempotency_key=idempotency_key).first()
                if existing:
                    return Response(QuotationSerializer(existing).data, status=status.HTTP_200_OK)
            return Response({"detail": "No se pudo procesar la solicitud. Intenta de nuevo."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def send(self, request, uuid=None):
        """Mark the quotation as SENT and dispatch the PDF email asynchronously."""
        quotation = self.get_object()
        if quotation.status not in (Quotation.STATUS_DRAFT, Quotation.STATUS_QUOTED):
            return Response(
                {"detail": f"No se puede enviar una cotizacion con estado '{quotation.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        QuotationCommands.mark_as_sent(quotation, changed_by=request.user)
        from quotes.tasks import send_quotation_email_task
        send_quotation_email_task.delay(str(quotation.uuid))
        return Response({"detail": "Quotation marked as SENT. Email dispatched."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def add_attachment(self, request, uuid=None):
        """Upload one or more image attachments to an existing quotation."""
        quotation = self.get_object()
        files = request.FILES.getlist('files')
        if not files:
            return Response({"detail": "No files provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Validacion de archivo identica a los otros caminos de creacion
        # (create_from_template / create_quotation): tamano, extension y
        # magic-bytes. Sin esto, add_attachment aceptaba cualquier binario.
        from accounts.services.commands import validate_file

        created = []
        for f in files:
            validate_file(
                f, max_size_mb=10,
                allowed_extensions=['.pdf', '.jpg', '.jpeg', '.png'],
                magic_bytes_check=True,
            )
            att = QuotationAttachment.objects.create(quotation=quotation, file=f)
            created.append(str(att.uuid))

        return Response({"uploaded": created}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def download_pdf(self, request, uuid=None):
        """Generate and return the quotation PDF as an attachment.

        Scoped al dueno via self.get_object() -> get_queryset(): un usuario
        solo puede descargar el PDF de su propia cotizacion (staff ve todas).
        Antes usaba AllowAny + query directo por uuid, exponiendo PII de
        cualquier cotizacion a quien tuviera el enlace.
        """
        quotation = self.get_object()

        pdf_buffer = PDFService.generate_quotation_pdf(quotation)
        filename = f"cotizacion_{quotation.uuid}.pdf"

        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class QuoteTemplateCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    /api/v1/quotes/quote-template-categories/
    Publico, solo lectura. Escritura vive en dashboard/quote-template-categories/.
    """
    permission_classes = [permissions.AllowAny]
    queryset = QuoteTemplateCategorySelector.list_all()
    serializer_class = QuoteTemplateCategorySerializer
    lookup_field = 'uuid'


class QuoteTemplateSubcategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    /api/v1/quotes/quote-template-subcategories/?category=<uuid>
    Publico, solo lectura. Escritura vive en dashboard/quote-template-subcategories/.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = QuoteTemplateSubcategorySerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        category_uuid = self.request.query_params.get('category')
        if category_uuid:
            return QuoteTemplateSubcategorySelector.list_for_category(category_uuid)
        return QuoteTemplateSubcategorySelector.list_all()


class QuoteTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    /api/v1/quotes/quote-templates/
    Publico, solo lectura — usado por el wizard dinamico en /cotizar.
    Escritura vive en dashboard/quote-templates/.
    """
    permission_classes = [permissions.AllowAny]
    lookup_field = 'uuid'

    def get_queryset(self):
        return QuoteTemplateSelector.list_active()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return QuoteTemplateSerializer
        return QuoteTemplateListSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = QuoteTemplateSelector.get_by_uuid(kwargs['uuid'])
        return Response(QuoteTemplateSerializer(instance).data)
