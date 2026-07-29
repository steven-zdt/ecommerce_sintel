from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema

from users.api.permissions import IsAdminUser
from technical_services.models import (
    TechnicalService, ServiceCategory, ServiceLevel, ServiceConfiguration,
)
from technical_services.services import (
    ServiceSelector,
    ServiceCategorySelector, ServiceCategoryCommands,
    ServiceLevelSelector, ServiceLevelCommands,
    ServiceVariantSelector, ServiceVariantCommands,
    ServiceMaterialSelector, ServiceMaterialCommands,
    ServiceConfigurationSelector, ServiceConfigurationCommands,
    TechnicalServiceCommands,
    ServiceReviewSelector, ServiceReviewCommands,
    TechnicianSelector,
)
from technical_services.api.serializers import (
    TechnicalServiceSerializer, TechnicalServiceInputSerializer,
    ServiceCategorySerializer, ServiceCategoryInputSerializer,
    ServiceLevelSerializer, ServiceLevelInputSerializer,
    ServiceVariantSerializer, ServiceVariantInputSerializer,
    ServiceMaterialSerializer, ServiceMaterialInputSerializer,
    ServiceConfigurationSerializer, ServiceConfigurationInputSerializer,
    ServicePriceHistorySerializer,
    ServiceReviewSerializer, ServiceReviewInputSerializer,
    AvailableTechnicianSerializer,
)
from technical_services.api.package_serializers import (
    ServicePackageSerializer, AdditionalCostSelectionInputSerializer,
)
from technical_services.services.packages import ServicePackageSelector, PackagePriceCalculator


class StandardPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


# ─── TechnicalService ─────────────────────────────────────────────────────────

@extend_schema(tags=['technical_services'])
class TechnicalServiceViewSet(viewsets.ReadOnlyModelViewSet):
    """Lectura de servicios tecnicos."""
    lookup_field = 'uuid'
    serializer_class = TechnicalServiceSerializer
    pagination_class = StandardPagination
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description', 'slug']
    ordering_fields = ['name', 'created_at']
    filterset_fields = ['is_active', 'is_featured', 'is_purchasable']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return TechnicalService.objects.none()
        qs = ServiceSelector.list_all_for_admin() if (self.request.user and self.request.user.is_authenticated and self.request.user.is_staff) else ServiceSelector.list_active_services()
        cat_slug = self.request.query_params.get('category__slug')
        lvl_slug = self.request.query_params.get('level__slug')
        if cat_slug:
            qs = qs.filter(category__slug=cat_slug)
        if lvl_slug:
            qs = qs.filter(level__slug=lvl_slug)
        return qs

    def get_object(self):
        return ServiceSelector.get_by_uuid(self.kwargs[self.lookup_field])

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny], url_path='quotation')
    def quotation(self, request):
        """
        Cotizacion previa de una variante.
        Params: variant_uuid, duration (opcional)
        """
        variant_uuid = request.query_params.get('variant_uuid')
        if not variant_uuid:
            return Response({'detail': 'variant_uuid es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from technical_services.models import ServiceVariant
            variant = ServiceVariant.objects.get(uuid=variant_uuid, is_deleted=False)
        except ServiceVariant.DoesNotExist:
            return Response({'detail': 'Variante no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        duration = request.query_params.get('duration')
        discount_pct = request.query_params.get('discount_pct')

        try:
            quotation = ServiceSelector.get_variant_quotation(
                variant,
                duration=duration,
                discount_pct=discount_pct,
            )
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(quotation)

    @extend_schema(description="Lista los paquetes comerciales de un servicio, con incluye y costos adicionales.")
    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny], url_path='packages')
    def packages(self, request, uuid=None):
        """GET /services/services/{uuid}/packages/"""
        active_only = not (request.user and request.user.is_authenticated and request.user.is_staff)
        packages = ServicePackageSelector.list_for_service(uuid, active_only=active_only)
        return Response(ServicePackageSerializer(packages, many=True, context={'request': request}).data)

    @extend_schema(description="Cotiza en vivo un paquete + costos adicionales seleccionados (sin crear la orden).")
    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny], url_path='quote-package')
    def quote_package(self, request, uuid=None):
        """
        POST /services/services/{uuid}/quote-package/
        Body: { "package_uuid": "...", "variant_uuid": "...", "duration": 2.5 (opcional),
                "additional_costs": [{"additional_cost_uuid": "...", "quantity": 1}],
                "discount_pct": 0 (opcional) }
        """
        from technical_services.models import ServiceVariant

        package_uuid = request.data.get('package_uuid')
        if not package_uuid:
            return Response({'detail': 'package_uuid es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        package = ServicePackageSelector.get_by_uuid(package_uuid)
        if str(package.service.uuid) != str(uuid):
            return Response({'detail': 'El paquete no pertenece a este servicio.'}, status=status.HTTP_400_BAD_REQUEST)

        extra_base = 0
        variant_uuid = request.data.get('variant_uuid')
        if variant_uuid:
            try:
                variant = ServiceVariant.objects.get(uuid=variant_uuid, is_deleted=False)
            except ServiceVariant.DoesNotExist:
                return Response({'detail': 'Variante no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
            variant_quotation = ServiceSelector.get_variant_quotation(variant, duration=request.data.get('duration'))
            extra_base = variant_quotation['base_amount']

        selections_serializer = AdditionalCostSelectionInputSerializer(data=request.data.get('additional_costs') or [], many=True)
        selections_serializer.is_valid(raise_exception=True)
        additional_cost_selections = [
            {'additional_cost': item['additional_cost_uuid'], 'quantity': item['quantity']}
            for item in selections_serializer.validated_data
        ]

        breakdown = PackagePriceCalculator.calculate(
            package,
            additional_cost_selections=additional_cost_selections,
            extra_base=extra_base,
            discount_pct=request.data.get('discount_pct'),
        )
        return Response({
            'package_price': breakdown['package_price'],
            'service_base': breakdown['service_base'],
            'additional_costs_total': breakdown['additional_costs_total'],
            'subtotal': breakdown['subtotal'],
            'discount_pct': breakdown['discount_pct'],
            'discount_amount': breakdown['discount_amount'],
            'iva_rate': breakdown['iva_rate'],
            'iva_amount': breakdown['iva_amount'],
            'total': breakdown['total'],
        })

    @extend_schema(description="Lista las reseñas publicadas de un servicio.", responses={200: ServiceReviewSerializer(many=True)})
    @action(detail=True, methods=['get'], url_path='reviews', permission_classes=[permissions.AllowAny])
    def reviews(self, request, uuid=None):
        """GET /services/services/{uuid}/reviews/"""
        qs = ServiceReviewSelector.list_for_service(uuid)
        return Response(ServiceReviewSerializer(qs, many=True).data)

    @extend_schema(
        description=(
            "Crea una reseña del servicio. Solo permitido a usuarios con al menos "
            "una atencion de este servicio ya cerrada; una reseña por usuario/servicio."
        ),
        request=ServiceReviewInputSerializer,
        responses={201: ServiceReviewSerializer},
    )
    @action(detail=True, methods=['post'], url_path='review', permission_classes=[permissions.IsAuthenticated])
    def review(self, request, uuid=None):
        """POST /services/services/{uuid}/review/"""
        service = self.get_object()
        serializer = ServiceReviewInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            review = ServiceReviewCommands.create_review(
                user=request.user, service=service, **serializer.validated_data,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ServiceReviewSerializer(review).data, status=status.HTTP_201_CREATED)

    @extend_schema(description="Lista tecnicos disponibles/calificados para la categoria del servicio.", responses={200: AvailableTechnicianSerializer(many=True)})
    @action(detail=True, methods=['get'], url_path='technicians', permission_classes=[permissions.AllowAny])
    def technicians(self, request, uuid=None):
        """GET /services/services/{uuid}/technicians/"""
        service = self.get_object()
        if not service.category:
            return Response([])
        technicians = TechnicianSelector.get_available_for_category(service.category)[:12]
        return Response(AvailableTechnicianSerializer(technicians, many=True, context={'request': request}).data)

    @action(detail=True, methods=['get'], permission_classes=(permissions.AllowAny,), url_path='detail')
    def full_detail(self, request, uuid=None):
        """GET /services/services/{uuid}/detail/

        Retorna servicio técnico completo con toda la información pública.
        No rompe API existente (endpoint nuevo, aditivo).
        """
        service = self.get_object()
        serializer = TechnicalServiceSerializer(service, context={'request': request})
        return Response(serializer.data)


# ─── ServiceCategory ──────────────────────────────────────────────────────────

@extend_schema(tags=['technical_services'])
class ServiceCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Lectura de categorias de servicios."""
    lookup_field = 'uuid'
    serializer_class = ServiceCategorySerializer
    pagination_class = StandardPagination
    permission_classes = [permissions.AllowAny]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ServiceCategory.objects.none()
        return ServiceCategorySelector.list_all_for_admin() if (self.request.user and self.request.user.is_authenticated and self.request.user.is_staff) else ServiceCategorySelector.list_all()

    def get_object(self):
        return ServiceCategorySelector.get_by_uuid(self.kwargs[self.lookup_field])


# ─── ServiceLevel ─────────────────────────────────────────────────────────────

@extend_schema(tags=['technical_services'])
class ServiceLevelViewSet(viewsets.ReadOnlyModelViewSet):
    """Lectura de niveles de servicio."""
    lookup_field = 'uuid'
    serializer_class = ServiceLevelSerializer
    pagination_class = StandardPagination
    permission_classes = [permissions.AllowAny]
    filter_backends = [SearchFilter]
    search_fields = ['name']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ServiceLevel.objects.none()
        return ServiceLevelSelector.list_all()

    def get_object(self):
        return ServiceLevelSelector.get_by_uuid(self.kwargs[self.lookup_field])



# ─── ServiceVariant ───────────────────────────────────────────────────────────

@extend_schema(tags=['technical_services'])
class ServiceVariantViewSet(viewsets.ViewSet):
    """Lectura de variantes de servicio. Parámetro: ?service=<uuid>"""
    permission_classes = [permissions.AllowAny]
    lookup_field = 'uuid'

    def list(self, request):
        service_uuid = request.query_params.get('service')
        if not service_uuid:
            return Response({'detail': 'Parametro service (uuid) es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        variants = ServiceVariantSelector.list_for_service(service_uuid)
        return Response(ServiceVariantSerializer(variants, many=True).data)

    @action(detail=True, methods=['get'], permission_classes=[IsAdminUser])
    def price_history(self, request, uuid=None):
        variant = ServiceVariantSelector.get_by_uuid(uuid)
        history = ServiceVariantSelector.get_price_history(variant)
        return Response(ServicePriceHistorySerializer(history, many=True).data)



# ─── ServiceMaterial ──────────────────────────────────────────────────────────

@extend_schema(tags=['technical_services'])
class ServiceMaterialViewSet(viewsets.ViewSet):
    """Lectura de insumos de una variante de servicio. Parámetro: ?variant=<uuid>"""
    permission_classes = [permissions.AllowAny]
    lookup_field = 'uuid'

    def list(self, request):
        variant_uuid = request.query_params.get('variant')
        if not variant_uuid:
            return Response({'detail': 'Parametro variant (uuid) es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        materials = ServiceMaterialSelector.list_for_variant(variant_uuid)
        return Response(ServiceMaterialSerializer(materials, many=True).data)


# ─── ServiceConfiguration ─────────────────────────────────────────────────────

@extend_schema(tags=['technical_services'])
class ServiceConfigurationViewSet(viewsets.ReadOnlyModelViewSet):
    """Lectura de configuracion SMLV."""
    lookup_field = 'uuid'
    serializer_class = ServiceConfigurationSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ServiceConfiguration.objects.none()
        return ServiceConfigurationSelector.list_all()

    def get_object(self):
        return ServiceConfigurationSelector.get_by_uuid(self.kwargs[self.lookup_field])


