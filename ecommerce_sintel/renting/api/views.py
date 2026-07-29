import django_filters
from rest_framework import viewsets, permissions, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404
from users.api.permissions import IsAdminUser, IsBuyerOrAdmin

from renting.models import Equipment, EquipmentVariant, RentingCategory, RentingBrand, RentalLabor, RentalRequest, EquipmentBlock
from renting.services import (
    RentingSelector, EquipmentVariantSelector, RentalRequestSelector,
    EquipmentCommands, EquipmentVariantCommands,
    RentingCategoryCommands, RentingBrandCommands, RentalLaborCommands,
    RentalRequestCommands, AvailabilityEngine,
    EquipmentBlockSelector, EquipmentBlockCommands,
    EquipmentReturnInspectionCommands,
    EquipmentReviewSelector, EquipmentReviewCommands,
)
from renting.services.presenters import EquipmentPublicDetailPresenter
from datetime import date as date_type, timedelta
from renting.api.serializers import (
    EquipmentSerializer, EquipmentDetailSerializer, EquipmentVariantSerializer,
    RentingCategorySerializer, RentingBrandSerializer, RentalLaborSerializer,
    EquipmentInputSerializer, EquipmentVariantInputSerializer,
    RentingCategoryInputSerializer, RentingBrandInputSerializer, RentalLaborInputSerializer,
    RentalRequestSerializer, RentalRequestInputSerializer, RentalProjectAttachmentSerializer,
    EquipmentAvailabilityResponseSerializer, EquipmentCalendarResponseSerializer,
    EquipmentTimelineResponseSerializer,
    EquipmentBlockSerializer, EquipmentBlockInputSerializer, EquipmentBlockReleaseInputSerializer,
    RentalRequestExtendInputSerializer,
    EquipmentReturnInspectionSerializer, EquipmentReturnInspectionInputSerializer,
    EquipmentReviewSerializer, EquipmentReviewInputSerializer,
    EquipmentPublicDetailDTOSerializer,
)

AVAILABILITY_LOOKAHEAD_DAYS = 60


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


@extend_schema(tags=['renting'])
class EquipmentViewSet(viewsets.ReadOnlyModelViewSet):
    """Lectura del catalogo de equipos en alquiler. Lectura publica."""
    serializer_class = EquipmentSerializer
    lookup_field = 'uuid'
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description', 'slug']
    ordering_fields = ['created_at', 'name']
    filterset_fields = ['is_active', 'is_featured', 'category__slug', 'brand__slug']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EquipmentDetailSerializer
        return EquipmentSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Equipment.objects.none()
        if self.request.user.is_staff:
            return RentingSelector.list_all_for_admin()
        return RentingSelector.list_available_equipment()

    def get_object(self):
        return RentingSelector.get_by_uuid(self.kwargs[self.lookup_field])

    def _parse_availability_request(self, request, equipment_uuid):
        """
        Parsea y valida los query params comunes a check-availability/availability.
        Retorna (variant, start_date, end_date, quantity, rental_mode) o
        (None, None, None, None, Response) si hubo un error -- el llamador debe
        retornar ese Response tal cual.
        """
        variant_uuid   = request.query_params.get('variant')
        start_date_str = request.query_params.get('start_date')
        end_date_str   = request.query_params.get('end_date')
        quantity_str   = request.query_params.get('quantity', '1')
        rental_mode    = request.query_params.get('rental_mode', RentalRequest.RENTAL_MODE_DAYS)

        if not all([variant_uuid, start_date_str, end_date_str]):
            return None, None, None, None, None, Response(
                {'detail': 'Parametros requeridos: variant, start_date, end_date.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start_date = date_type.fromisoformat(start_date_str)
            end_date   = date_type.fromisoformat(end_date_str)
            quantity   = max(1, int(quantity_str))
        except (ValueError, TypeError):
            return None, None, None, None, None, Response(
                {'detail': 'Formato invalido. Use YYYY-MM-DD para fechas y entero para quantity.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if end_date <= start_date:
            return None, None, None, None, None, Response(
                {'detail': 'end_date debe ser posterior a start_date.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        variant = get_object_or_404(
            EquipmentVariant, uuid=variant_uuid, equipment__uuid=equipment_uuid, is_deleted=False,
        )
        return variant, start_date, end_date, quantity, rental_mode, None

    def _build_availability_payload(self, variant, start_date, end_date, quantity, rental_mode):
        available = AvailabilityEngine.is_available(
            variant.id, start_date, end_date, quantity, rental_mode,
        )
        next_slot = None
        if not available:
            next_slot = AvailabilityEngine.find_next_available_slot(
                variant.id, start_date, quantity, rental_mode,
                duration_days=max((end_date - start_date).days, 1),
                search_horizon_days=AVAILABILITY_LOOKAHEAD_DAYS,
            )
        occupied_slots = AvailabilityEngine.generate_schedule(
            variant.id, start_date, start_date + timedelta(days=AVAILABILITY_LOOKAHEAD_DAYS),
        )
        return {
            'available': available,
            'variant_uuid': str(variant.uuid),
            'start_date': start_date,
            'end_date': end_date,
            'quantity': quantity,
            'rental_mode': rental_mode,
            'next_available_date': next_slot['date'] if next_slot else None,
            'next_available_time': next_slot['time'] if next_slot else None,
            'occupied_slots': occupied_slots,
        }

    @extend_schema(
        description="Verifica disponibilidad de una variante para un rango de fechas.",
        responses={200: dict},
    )
    @action(
        detail=True,
        methods=['get'],
        url_path='check-availability',
        permission_classes=[permissions.AllowAny],
    )
    def check_availability(self, request, uuid=None):
        """
        GET /renting/equipment/{uuid}/check-availability/
        Query params: variant=<uuid>&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&quantity=1

        Respuesta compatible con el wizard actual (available/variant_uuid/start_date/
        end_date/quantity como strings) mas los campos nuevos aditivos
        (next_available_date/next_available_time/occupied_slots) que consume el
        endpoint sucesor `availability/`.
        """
        variant, start_date, end_date, quantity, rental_mode, error = self._parse_availability_request(request, uuid)
        if error is not None:
            return error

        payload = self._build_availability_payload(variant, start_date, end_date, quantity, rental_mode)
        payload['start_date'] = request.query_params['start_date']
        payload['end_date'] = request.query_params['end_date']
        return Response(payload)

    @extend_schema(
        description=(
            "Disponibilidad de una variante para un rango de fechas, con proxima fecha "
            "disponible y huecos ocupados. Endpoint sucesor de check-availability."
        ),
        responses={200: EquipmentAvailabilityResponseSerializer},
    )
    @action(
        detail=True,
        methods=['get'],
        url_path='availability',
        permission_classes=[permissions.AllowAny],
    )
    def availability(self, request, uuid=None):
        """GET /renting/equipment/{uuid}/availability/"""
        variant, start_date, end_date, quantity, rental_mode, error = self._parse_availability_request(request, uuid)
        if error is not None:
            return error

        payload = self._build_availability_payload(variant, start_date, end_date, quantity, rental_mode)
        return Response(EquipmentAvailabilityResponseSerializer(payload).data)

    @extend_schema(
        description="Calendario dia a dia de una variante (unidades libres por dia).",
        responses={200: EquipmentCalendarResponseSerializer},
    )
    @action(
        detail=True,
        methods=['get'],
        url_path='calendar',
        permission_classes=[permissions.AllowAny],
    )
    def calendar(self, request, uuid=None):
        """
        GET /renting/equipment/{uuid}/calendar/
        Query params: variant=<uuid>&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
        """
        variant_uuid   = request.query_params.get('variant')
        start_date_str = request.query_params.get('start_date')
        end_date_str   = request.query_params.get('end_date')
        if not all([variant_uuid, start_date_str, end_date_str]):
            return Response(
                {'detail': 'Parametros requeridos: variant, start_date, end_date.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            range_start = date_type.fromisoformat(start_date_str)
            range_end   = date_type.fromisoformat(end_date_str)
        except (ValueError, TypeError):
            return Response(
                {'detail': 'Formato invalido. Use YYYY-MM-DD para fechas.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        variant = get_object_or_404(
            EquipmentVariant, uuid=variant_uuid, equipment__uuid=uuid, is_deleted=False,
        )

        periods = AvailabilityEngine.generate_schedule(variant.id, range_start, range_end)

        days = []
        current = range_start
        while current <= range_end:
            day_periods_days = [
                p for p in periods
                if p['rental_mode'] == RentalRequest.RENTAL_MODE_DAYS
                and p['start_date'] <= current < p['end_date']
            ]
            day_hour_bookings = [
                p for p in periods
                if p['rental_mode'] == RentalRequest.RENTAL_MODE_HOURS
                and p['start_date'] <= current <= p['end_date']
            ]
            occupied_units = sum(p['quantity'] for p in day_periods_days)
            available_units = variant.stock - occupied_units
            if available_units <= 0:
                day_status = 'full'
            elif day_periods_days or day_hour_bookings:
                day_status = 'booked'
            else:
                day_status = 'available'
            days.append({
                'date': current,
                'available_units': max(available_units, 0),
                'status': day_status,
                'hour_bookings': day_hour_bookings,
            })
            current += timedelta(days=1)

        payload = {
            'variant_uuid': str(variant.uuid),
            'range_start': range_start,
            'range_end': range_end,
            'stock': variant.stock,
            'days': days,
        }
        return Response(EquipmentCalendarResponseSerializer(payload).data)

    @extend_schema(
        description="Historial completo de periodos (los 4 estados) para timeline/heatmap.",
        responses={200: EquipmentTimelineResponseSerializer},
    )
    @action(
        detail=True,
        methods=['get'],
        url_path='timeline',
        permission_classes=[permissions.AllowAny],
    )
    def timeline(self, request, uuid=None):
        """
        GET /renting/equipment/{uuid}/timeline/
        Query params: variant=<uuid>&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
        Sin PII: no incluye datos del cliente, solo fecha/hora/modo/estado/cantidad.
        """
        from renting.models import RentalPeriod as RentalPeriodModel

        variant_uuid   = request.query_params.get('variant')
        start_date_str = request.query_params.get('start_date')
        end_date_str   = request.query_params.get('end_date')
        if not all([variant_uuid, start_date_str, end_date_str]):
            return Response(
                {'detail': 'Parametros requeridos: variant, start_date, end_date.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            range_start = date_type.fromisoformat(start_date_str)
            range_end   = date_type.fromisoformat(end_date_str)
        except (ValueError, TypeError):
            return Response(
                {'detail': 'Formato invalido. Use YYYY-MM-DD para fechas.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        variant = get_object_or_404(
            EquipmentVariant, uuid=variant_uuid, equipment__uuid=uuid, is_deleted=False,
        )

        all_statuses = [choice[0] for choice in RentalPeriodModel.STATUS_CHOICES]
        periods = AvailabilityEngine.generate_schedule(variant.id, range_start, range_end, statuses=all_statuses)

        payload = {
            'variant_uuid': str(variant.uuid),
            'range_start': range_start,
            'range_end': range_end,
            'periods': periods,
        }
        return Response(EquipmentTimelineResponseSerializer(payload).data)

    @extend_schema(
        description="Registra una descarga y devuelve la URL absoluta del archivo. Solo documentos publicos/activos.",
        responses={200: dict},
    )
    @action(
        detail=True,
        methods=['post'],
        url_path=r'documents/(?P<document_uuid>[^/.]+)/register-download',
        permission_classes=[permissions.AllowAny],
    )
    def register_document_download(self, request, uuid=None, document_uuid=None):
        """POST /renting/equipment/{uuid}/documents/{document_uuid}/register-download/"""
        from renting.services import RentalDocumentSelector, RentalDocumentCommands

        document = get_object_or_404(
            RentalDocumentSelector.list_for_equipment(uuid, public_only=True),
            uuid=document_uuid,
        )
        RentalDocumentCommands.register_download(document)
        return Response({
            'file': request.build_absolute_uri(document.file.url) if document.file else None,
            'downloads': document.downloads,
        })

    @extend_schema(description="Lista las reseñas publicadas de un equipo.", responses={200: EquipmentReviewSerializer(many=True)})
    @action(detail=True, methods=['get'], url_path='reviews', permission_classes=[permissions.AllowAny])
    def reviews(self, request, uuid=None):
        """GET /renting/equipment/{uuid}/reviews/"""
        qs = EquipmentReviewSelector.list_for_equipment(uuid)
        return Response(EquipmentReviewSerializer(qs, many=True).data)

    @extend_schema(
        description=(
            "Crea una reseña del equipo. Solo permitido a usuarios con al menos "
            "una renta de este equipo ya finalizada; una reseña por usuario/equipo."
        ),
        request=EquipmentReviewInputSerializer,
        responses={201: EquipmentReviewSerializer},
    )
    @action(detail=True, methods=['post'], url_path='review', permission_classes=[permissions.IsAuthenticated])
    def review(self, request, uuid=None):
        """POST /renting/equipment/{uuid}/review/"""
        equipment = self.get_object()
        serializer = EquipmentReviewInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            review = EquipmentReviewCommands.create_review(
                user=request.user, equipment=equipment, **serializer.validated_data,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EquipmentReviewSerializer(review).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='detail', permission_classes=[permissions.AllowAny])
    @extend_schema(
        description="Retorna EquipmentPublicDetailDTO completo sin breaking changes a endpoint existente.",
        responses={200: EquipmentPublicDetailDTOSerializer},
    )
    def detail(self, request, uuid=None):
        """GET /renting/equipment/{uuid}/detail/

        Retorna EquipmentPublicDetailDTO con toda la información pública:
        hero, pricing, marketing, technical, services, media, faqs,
        reviews, availability, commercial_options, logistics, related,
        y seo. Backend garantiza que cada DTO está 100% completo y listo.
        """
        equipment = self.get_object()
        presenter = EquipmentPublicDetailPresenter(equipment, user=request.user)
        dto = presenter.present()
        serializer = EquipmentPublicDetailDTOSerializer(dto)
        return Response(serializer.data)


@extend_schema(tags=['renting'])
class EquipmentVariantViewSet(viewsets.ViewSet):
    """Lectura de variantes (SKU/precio) de un equipo. Parametro: ?equipment=<uuid>"""
    permission_classes = [permissions.AllowAny]
    lookup_field = 'uuid'

    def list(self, request):
        equipment_uuid = request.query_params.get('equipment')
        if not equipment_uuid:
            return Response({'detail': 'Parametro equipment (uuid) es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        variants = EquipmentVariantSelector.list_for_equipment(equipment_uuid)
        return Response(EquipmentVariantSerializer(variants, many=True).data)


from rest_framework.views import APIView


@extend_schema(tags=['renting'])
class RentingCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Categorias de renta. Lectura publica."""
    serializer_class = RentingCategorySerializer
    lookup_field = 'uuid'
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name']
    filterset_fields = ['is_active']

    def get_queryset(self):
        return RentingSelector.list_categories()

    def get_object(self):
        return get_object_or_404(RentingCategory, uuid=self.kwargs[self.lookup_field], is_active=True, is_deleted=False)


@extend_schema(tags=['renting'])
class RentingBrandViewSet(viewsets.ReadOnlyModelViewSet):
    """Marcas de renta. Lectura publica."""
    serializer_class = RentingBrandSerializer
    lookup_field = 'uuid'
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']

    def get_queryset(self):
        return RentingSelector.list_brands()

    def get_object(self):
        return get_object_or_404(RentingBrand, uuid=self.kwargs[self.lookup_field], is_deleted=False)


@extend_schema(tags=['renting'])
class RentalLaborViewSet(viewsets.ReadOnlyModelViewSet):
    """Mano de obra de renta. Lectura publica."""
    serializer_class = RentalLaborSerializer
    lookup_field = 'uuid'
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name']
    filterset_fields = ['is_active']

    def get_queryset(self):
        return RentingSelector.list_rental_labor()

    def get_object(self):
        return get_object_or_404(RentalLabor, uuid=self.kwargs[self.lookup_field], is_active=True, is_deleted=False)


class RentalRequestFilterSet(django_filters.FilterSet):
    """
    payment_method dejo de ser columna de RentalRequest (auditoria DB-H1):
    vive en RentalRequestPaymentInfo ('payment_info', OneToOne). filterset_fields
    solo acepta campos reales del modelo, asi que se declara este FilterSet
    explicito para mantener el mismo query param publico (?payment_method=WOMPI)
    apuntando a la relacion.
    """
    payment_method = django_filters.CharFilter(field_name='payment_info__payment_method')

    class Meta:
        model = RentalRequest
        fields = ['status', 'payment_method', 'refund_required']


@extend_schema(tags=['renting'])
class RentalRequestViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Solicitudes de alquiler del usuario autenticado."""
    serializer_class = RentalRequestSerializer
    lookup_field = 'uuid'
    permission_classes = [IsBuyerOrAdmin]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RentalRequestFilterSet

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return RentalRequest.objects.none()
        if self.request.user.is_staff:
            return RentalRequestSelector.list_all_for_admin()
        return RentalRequestSelector.list_for_user(self.request.user)

    def get_object(self):
        uuid = self.kwargs[self.lookup_field]
        if self.request.user.is_staff:
            return RentalRequestSelector.get_by_uuid_for_admin(uuid)
        return RentalRequestSelector.get_by_uuid_for_user(uuid, self.request.user)

    @action(detail=True, methods=['post'], url_path='attachments')
    def attachments(self, request, uuid=None):
        """Adjunta hasta 10 fotografías o documentos de reconocimiento."""
        from rest_framework.exceptions import ValidationError as DRFValidationError

        rental_request = self.get_object()
        files = request.FILES.getlist('files')
        if not files:
            return Response({'detail': 'Selecciona al menos un archivo.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            created = RentalRequestCommands.add_project_attachments(rental_request, files, uploaded_by=request.user)
        except (ValueError, DRFValidationError) as e:
            detail = e.detail[0] if isinstance(getattr(e, 'detail', None), list) else str(e)
            return Response({'detail': str(detail)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RentalProjectAttachmentSerializer(created, many=True, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='process-payment')
    def process_payment(self, request, uuid=None):
        """
        POST /renting/rental-requests/{uuid}/process-payment/
        Body: { "payment_method": "WOMPI"|"NEQUI"|"COD", "phone_number": "300...", "card_token": "..." }

        Delega a RentalRequestCommands.process_payment_selection y retorna:
          - WOMPI (tarjeta, card_token presente): transaccion creada sincrona en Wompi, sin widget
          - WOMPI (PSE/Otros, sin card_token): datos del widget Wompi
          - NEQUI: { nequi_tx_uuid }
          - COD:   { status, rental_uuid }
        """
        rental_request = self.get_object()
        payment_method = request.data.get('payment_method', '').upper()
        valid_methods = [RentalRequest.PAYMENT_WOMPI, RentalRequest.PAYMENT_NEQUI, RentalRequest.PAYMENT_COD]

        if payment_method not in valid_methods:
            return Response(
                {'detail': f'Metodo de pago invalido. Opciones: {", ".join(valid_methods)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        card_token = request.data.get('card_token')
        if payment_method == RentalRequest.PAYMENT_WOMPI:
            # Mismo kill-switch real que Tienda/Servicios Tecnicos (ADR-001 Fase 5
            # + plan hibrido Widget+API): rechazar en el backend, no solo ocultar
            # el boton en el frontend -- simetrico en ambos sentidos.
            from payment.models import PaymentFeatureFlags
            flags = PaymentFeatureFlags.get_active()
            if card_token and not flags.card_api_flow_enabled:
                return Response(
                    {'detail': 'El pago con tarjeta via API esta deshabilitado temporalmente. Usa PSE/Otros.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if not card_token and not flags.widget_flow_enabled:
                return Response(
                    {'detail': 'El pago via Widget esta deshabilitado temporalmente. Usa Tarjeta.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        try:
            result = RentalRequestCommands.process_payment_selection(
                rental_request=rental_request,
                payment_method=payment_method,
                extra_data={'phone_number': request.data.get('phone_number', ''), 'card_token': card_token},
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(result, status=status.HTTP_200_OK)

    # initialize-payment (recalculaba la firma de integridad Wompi con su
    # propia copia de hashlib.sha256) se elimino en la auditoria SSoT de
    # Payment 2026-07-23 (hallazgo H-01): sin consumidores en frontend ni
    # backend, y duplicaba _compute_integrity_signature() de
    # payment/online/services/commands.py. El camino vigente es
    # process-payment/ -> process_payment_selection() -> WompiCommands.

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, uuid=None):
        rental_request = self.get_object()
        if rental_request.status in (
            RentalRequest.STATUS_PAID, RentalRequest.STATUS_CONFIRMED, RentalRequest.STATUS_IN_OPERATION,
        ):
            return Response(
                {'detail': 'No se puede cancelar una solicitud pagada, aprobada o en operacion.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        rental_request = RentalRequestCommands.cancel_request(rental_request)
        return Response(
            RentalRequestSerializer(rental_request, context={'request': request}).data
        )

    def _admin_action_response(self, request, command, **kwargs):
        rental_request = self.get_object()
        try:
            rental_request = command(rental_request, **kwargs) or rental_request
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            RentalRequestSerializer(rental_request, context={'request': request}).data
        )

    @action(detail=True, methods=['post'], url_path='approve', permission_classes=[IsAdminUser])
    def approve(self, request, uuid=None):
        """POST /renting/rental-requests/{uuid}/approve/ -- aprueba una solicitud COD pending_validation."""
        return self._admin_action_response(
            request, RentalRequestCommands.approve_manual_validation, admin_user=request.user,
        )

    @action(detail=True, methods=['post'], url_path='reject', permission_classes=[IsAdminUser])
    def reject(self, request, uuid=None):
        """POST /renting/rental-requests/{uuid}/reject/ -- rechaza una solicitud COD pending_validation."""
        return self._admin_action_response(
            request, RentalRequestCommands.reject_request,
            admin_user=request.user, reason=request.data.get('reason', ''),
        )

    @action(detail=True, methods=['post'], url_path='mark-delivered', permission_classes=[IsAdminUser])
    def mark_delivered(self, request, uuid=None):
        """POST /renting/rental-requests/{uuid}/mark-delivered/ -- paid/confirmed -> in_operation."""
        return self._admin_action_response(request, RentalRequestCommands.activate_period)

    @action(detail=True, methods=['post'], url_path='mark-returned', permission_classes=[IsAdminUser])
    def mark_returned(self, request, uuid=None):
        """POST /renting/rental-requests/{uuid}/mark-returned/ -- in_operation -> finished."""
        return self._admin_action_response(request, RentalRequestCommands.complete_period)

    @action(detail=True, methods=['post'], url_path='release-period', permission_classes=[IsAdminUser])
    def release_period(self, request, uuid=None):
        """POST /renting/rental-requests/{uuid}/release-period/ -- libera la agenda sin cancelar la solicitud."""
        return self._admin_action_response(
            request, RentalRequestCommands.release_period,
            admin_user=request.user, reason=request.data.get('reason', ''),
        )

    @extend_schema(request=RentalRequestExtendInputSerializer, responses={200: RentalRequestSerializer})
    @action(detail=True, methods=['post'], url_path='extend', permission_classes=[IsAdminUser])
    def extend(self, request, uuid=None):
        """POST /renting/rental-requests/{uuid}/extend/ -- extiende end_date si hay disponibilidad."""
        serializer = RentalRequestExtendInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._admin_action_response(
            request, RentalRequestCommands.extend_period,
            admin_user=request.user,
            new_end_date=serializer.validated_data['new_end_date'],
            reason=serializer.validated_data['reason'],
        )

    @extend_schema(request=EquipmentReturnInspectionInputSerializer, responses={201: EquipmentReturnInspectionSerializer})
    @action(detail=True, methods=['post'], url_path='return-inspection', permission_classes=[IsAdminUser])
    def return_inspection(self, request, uuid=None):
        """
        POST /renting/rental-requests/{uuid}/return-inspection/
        Registro opcional/aparte -- no gatea mark-returned/complete_period, solo
        exige que la solicitud ya este finished (equipo devuelto).
        """
        rental_request = self.get_object()
        serializer = EquipmentReturnInspectionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            inspection = EquipmentReturnInspectionCommands.create_inspection(
                rental_request, admin_user=request.user, **serializer.validated_data,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EquipmentReturnInspectionSerializer(inspection).data, status=status.HTTP_201_CREATED)


class RentalRequestListCreateAPIView(APIView):
    """Listado y creacion de solicitudes de alquiler para el usuario autenticado."""
    permission_classes = [IsBuyerOrAdmin]

    @extend_schema(
        responses={200: RentalRequestSerializer(many=True)},
        tags=['renting']
    )
    def get(self, request, *args, **kwargs):
        view = RentalRequestViewSet.as_view({'get': 'list'})
        return view(request._request, *args, **kwargs)

    @extend_schema(
        request=RentalRequestInputSerializer,
        responses={201: RentalRequestSerializer},
        tags=['renting']
    )
    def post(self, request, *args, **kwargs):
        serializer = RentalRequestInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rental_request = RentalRequestCommands.create_request(
            user=request.user,
            validated_data=serializer.validated_data,
        )
        return Response(
            RentalRequestSerializer(
                RentalRequestSelector.get_by_uuid_for_user(rental_request.uuid, request.user),
                context={'request': request},
            ).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=['renting'])
class EquipmentBlockViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Bloqueo manual de EquipmentVariant por mantenimiento/daño/inventario.
    Admin-only (a diferencia del resto de renting/, no tiene lectura publica --
    es informacion operativa interna, no debe filtrarse el motivo del bloqueo).

    Sigue la misma excepcion documentada que RentalRequestViewSet: pega directo a
    renting/ (no a dashboard/) porque el permiso es por-accion, no por namespace.
    """
    serializer_class = EquipmentBlockSerializer
    lookup_field = 'uuid'
    permission_classes = [IsAdminUser]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return EquipmentBlock.objects.none()

        variant_uuid = self.request.query_params.get('variant')
        equipment_uuid = self.request.query_params.get('equipment')
        if variant_uuid:
            qs = EquipmentBlockSelector.list_for_variant(variant_uuid)
        elif equipment_uuid:
            qs = EquipmentBlockSelector.list_for_equipment(equipment_uuid)
        else:
            qs = (
                EquipmentBlock.objects.filter(is_deleted=False)
                .select_related('equipment_variant__equipment', 'created_by', 'released_by')
                .order_by('-created_at')
            )

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        block_type_param = self.request.query_params.get('block_type')
        if block_type_param:
            qs = qs.filter(block_type=block_type_param)
        return qs

    def get_object(self):
        return EquipmentBlockSelector.get_by_uuid(self.kwargs[self.lookup_field])

    @extend_schema(request=EquipmentBlockInputSerializer, responses={201: EquipmentBlockSerializer})
    def create(self, request, *args, **kwargs):
        serializer = EquipmentBlockInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            block = EquipmentBlockCommands.create_block(
                equipment_variant=data['equipment_variant'],
                block_type=data['block_type'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                reason=data['reason'],
                quantity=data['quantity'],
                admin_user=request.user,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EquipmentBlockSerializer(block).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=EquipmentBlockReleaseInputSerializer, responses={200: EquipmentBlockSerializer})
    @action(detail=True, methods=['post'], url_path='release')
    def release(self, request, uuid=None):
        """POST /renting/equipment-blocks/{uuid}/release/ -- libera el bloqueo."""
        block = self.get_object()
        serializer = EquipmentBlockReleaseInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        block = EquipmentBlockCommands.release_block(
            block, admin_user=request.user, reason=serializer.validated_data['reason'],
        )
        return Response(EquipmentBlockSerializer(block).data)
