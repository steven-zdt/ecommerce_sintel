"""
dashboard/api/views.py

Unified administrative gateway (BFF) for the admin SPA.
All ViewSets delegate to dashboard.services.admin_orchestrators.
Zero ORM access in this layer.
"""
from rest_framework import viewsets, mixins, status, permissions
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from django.db.models import Q
from django.db import IntegrityError
from django.core.exceptions import ValidationError as DjangoValidationError

from users.api.permissions import IsAdminUser

from dashboard.services.admin_orchestrators import (
    AdminMetricsOrchestrator,
    ShopAdminOrchestrator,
    ServiceAdminOrchestrator,
    ServiceAdminRequestOrchestrator,
    RentingAdminOrchestrator,
    QuotationAdminOrchestrator,
    QuoteTemplateAdminOrchestrator,
    OrderAdminOrchestrator,
    MarketingAdminOrchestrator,
    SupportAdminOrchestrator,
    SecurityAdminOrchestrator,
    NotificationAdminOrchestrator,
    PaymentAdminOrchestrator,
)
from shop.services.pricing import ShopPricingCalculator, ProductCostRuleSelector, ProductCostRuleCommands
from renting.services.pricing import RentalPricingCalculator, RentalCostRuleSelector, RentalCostRuleCommands
from technical_services.services.pricing import ServicePricingCalculator, ServiceCostRuleSelector, ServiceCostRuleCommands
from renting.services import (
    EquipmentLogisticsConfigCommands, EquipmentMarketingCommands,
    EquipmentCommercialConfigCommands, EquipmentCommercialOptionCommands,
)
from dashboard.api.serializers import (
    # Shop
    ProductSerializer, ProductInputSerializer,
    CategorySerializer, CategoryInputSerializer,
    BrandSerializer, BrandInputSerializer,
    TaxSerializer, TaxInputSerializer,
    ProductVariantSerializer, ProductVariantInputSerializer,
    ProductCostRuleSerializer, ProductCostRuleInputSerializer, ProductCostAssignmentInputSerializer,
    # Orders
    OrderSerializer,
    # Renting
    EquipmentSerializer, EquipmentInputSerializer,
    EquipmentVariantSerializer, EquipmentVariantInputSerializer,
    RentingCategorySerializer, RentingCategoryInputSerializer,
    RentingBrandSerializer, RentingBrandInputSerializer,
    RentalLaborSerializer, RentalLaborInputSerializer,
    EquipmentLogisticsConfigSerializer, EquipmentLogisticsConfigInputSerializer,
    EquipmentMarketingSerializer, EquipmentMarketingInputSerializer,
    EquipmentCommercialConfigSerializer, EquipmentCommercialConfigInputSerializer,
    EquipmentCommercialOptionSerializer, EquipmentCommercialOptionInputSerializer,
    RentalCostRuleSerializer, RentalCostRuleInputSerializer, RentalCostAssignmentInputSerializer,
    # Quotes
    QuotationSerializer, QuotationListSerializer, QuotationCreateInputSerializer,
    QuotationStatusChangeInputSerializer, QuotationAddItemInputSerializer, QuotationAddServiceInputSerializer,
    QuoteTemplateCategorySerializer, QuoteTemplateCategoryInputSerializer,
    QuoteTemplateSubcategorySerializer, QuoteTemplateSubcategoryInputSerializer,
    QuoteTemplateListSerializer, QuoteTemplateSerializer, QuoteTemplateInputSerializer,
    QuoteTemplateAttributeSerializer, QuoteTemplateAttributeInputSerializer,
    QuoteEquipmentTypeSerializer, QuoteEquipmentTypeInputSerializer,
    QuoteTemplateModuleSerializer, QuoteTemplateModuleInputSerializer, QuoteModuleReorderInputSerializer,
    QuoteQuestionSerializer, QuoteQuestionInputSerializer,
    QuoteQuestionOptionSerializer, QuoteQuestionOptionInputSerializer,
    QuoteQuestionDuplicateToModuleInputSerializer,
    # Technical Services
    TechnicalServiceSerializer, TechnicalServiceInputSerializer, TechnicalServiceAdminCreateSerializer,
    ServiceCategorySerializer, ServiceCategoryInputSerializer,
    ServiceLevelSerializer, ServiceLevelInputSerializer,
    ServiceVariantSerializer, ServiceVariantInputSerializer,
    ServiceMaterialSerializer, ServiceMaterialInputSerializer,
    ServicePriceHistorySerializer, SetVariantPricingInputSerializer,
    ServiceCostRuleSerializer, ServiceCostRuleInputSerializer, ServiceCostAssignmentInputSerializer,
    ServiceAdminRequestSummarySerializer,
    # Support
    ChatRoomListSerializer, ChatRoomSerializer, SupportTicketSerializer,
)
from technical_services.api.serializers import (
    ServiceImageSerializer, ServiceImageUpdateInputSerializer, ServiceImageReorderInputSerializer,
    ServiceFAQSerializer, ServiceFAQInputSerializer,
    ServiceMarketingSerializer, ServiceMarketingInputSerializer,
)
from technical_services.services import ServiceFAQSelector, ServiceFAQCommands, ServiceMarketingCommands
from technical_services.api.operation_serializers import (
    ServiceOperationPlanSerializer, ServiceOperationAssignSerializer,
    ServiceOperationRescheduleSerializer, ServiceOperationCancelSerializer,
)
from shop.models import ProductImage
from shop.services.commands import ProductImageCommands
from security.api.serializers import SecurityEventSerializer
from notifications.api.serializers import NotificationTemplateSerializer, NotificationLogSerializer
from payment.models import Transaction
from payment.online.api.serializers import TransactionSerializer, TransactionEventSerializer
from payment.nequi.api.serializers import NequiTransactionSerializer
from payment.cod.api.serializers import CodTransactionSerializer
from shop.api.serializers import ProductImageSerializer

ADMIN_PERMISSIONS = [permissions.IsAuthenticated, IsAdminUser]


class DashboardResultsSetPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


# ---------------------------------------------------------------------------
# METRICS
# ---------------------------------------------------------------------------


class AdminMetricsView(APIView):
    """
    GET /api/v1/dashboard/metrics/
    Retorna metricas principales del panel administrativo.
    """
    permission_classes = ADMIN_PERMISSIONS

    @extend_schema(
        summary="Metricas del dashboard administrativo",
        responses={200: {
            'type': 'object',
            'properties': {
                'total_sales':     {'type': 'number'},
                'orders_count':    {'type': 'integer'},
                'customers_count': {'type': 'integer'},
                'products_count':  {'type': 'integer'},
                'recent_orders':   {'type': 'array'},
            }
        }}
    )
    def get(self, request):
        return Response(AdminMetricsOrchestrator.get_metrics())


class AdminWhatsAppConnectionStatusView(APIView):
    """
    GET /api/v1/dashboard/whatsapp/connection-status/

    Mision "Refactorizacion Arquitectonica del Modulo WhatsApp" (2026-09-16)
    dejo el backend listo (whatsapp/factory.py, whatsapp/adapters/) pero
    nunca conecto un endpoint admin real -- gap encontrado por el usuario
    el mismo dia. Solo lectura: expone el adapter ACTIVO segun
    settings.WHATSAPP_CONNECTION_TYPE (capabilities/status/health real) y,
    a modo informativo, el estado del OTRO mecanismo -- para que el panel
    sea honesto sobre que QR existe estructuralmente pero esta
    NOT_IMPLEMENTED (sin gateway real integrado), en vez de ocultarlo.
    """
    permission_classes = ADMIN_PERMISSIONS

    @extend_schema(summary="[Admin] Estado real del mecanismo de conexion de WhatsApp (REST/QR)")
    def get(self, request):
        from django.conf import settings
        from whatsapp.factory import WhatsAppConnectionFactory, CONNECTION_TYPE_QR, CONNECTION_TYPE_REST

        def _describe(connection_type):
            adapter = WhatsAppConnectionFactory.create(connection_type)
            caps = adapter.capabilities
            return {
                'connection_type': connection_type,
                'status': adapter.get_status().value,
                'healthy': adapter.health_check(),
                'capabilities': {
                    'send_text': caps.send_text,
                    'receive_text': caps.receive_text,
                    'send_media': caps.send_media,
                    'receive_media': caps.receive_media,
                    'webhook': caps.webhook,
                    'polling': caps.polling,
                    'qr_pairing': caps.qr_pairing,
                    'session_persistence': caps.session_persistence,
                    'delivery_status': caps.delivery_status,
                },
            }

        active_type = (settings.WHATSAPP_CONNECTION_TYPE or '').strip().upper()
        return Response({
            'active_connection_type': active_type,
            'active': _describe(active_type),
            'rest': _describe(CONNECTION_TYPE_REST),
            'qr': _describe(CONNECTION_TYPE_QR),
        })


# ---------------------------------------------------------------------------
# Nota: la administracion de usuarios vive exclusivamente en users.api.views.UserViewSet
# (/api/v1/users/) -- un AdminUserViewSet duplicado que existio aca fue eliminado (2026-07-05):
# el frontend nunca lo llamaba y ya habia divergido (su update_user ignoraba is_active/is_verified).

# ---------------------------------------------------------------------------
# SHOP — Products, Categories, Brands, Taxes, Variants
# ---------------------------------------------------------------------------

@extend_schema_view(
    list=extend_schema(summary="[Admin] Lista productos"),
    create=extend_schema(summary="[Admin] Crea producto", request=ProductInputSerializer),
    retrieve=extend_schema(summary="[Admin] Detalle producto"),
    partial_update=extend_schema(summary="[Admin] Actualiza producto", request=ProductInputSerializer),
    destroy=extend_schema(summary="[Admin] Elimina producto"),
)
class AdminProductViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/products/
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        qs = ShopAdminOrchestrator.list_products()
        search = request.query_params.get('search')
        is_active = request.query_params.get('is_active')
        is_featured = request.query_params.get('is_featured')
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(slug__icontains=search)
                | Q(short_description__icontains=search)
                | Q(description__icontains=search)
                | Q(variants__sku__icontains=search)
            ).distinct()
        if is_active in ('true', 'false'):
            qs = qs.filter(is_active=is_active == 'true')
        if is_featured in ('true', 'false'):
            qs = qs.filter(is_featured=is_featured == 'true')
        paginator = DashboardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(ProductSerializer(page, many=True).data)
        return Response(ProductSerializer(qs, many=True).data)

    def create(self, request):
        ser = ProductInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        product = ShopAdminOrchestrator.create_product(request.user, ser.validated_data)
        product = ShopAdminOrchestrator.get_product(product.uuid)
        return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        product = ShopAdminOrchestrator.get_product(uuid)
        return Response(ProductSerializer(product).data)

    def partial_update(self, request, uuid=None):
        product = ShopAdminOrchestrator.get_product(uuid)
        ser = ProductInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = ShopAdminOrchestrator.update_product(product, ser.validated_data)
        updated = ShopAdminOrchestrator.get_product(updated.uuid)
        return Response(ProductSerializer(updated).data)

    def destroy(self, request, uuid=None):
        product = ShopAdminOrchestrator.get_product(uuid)
        ShopAdminOrchestrator.delete_product(product)
        _log_admin_delete(request, 'Product', uuid)  # D-02
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Lista variantes del producto")
    @action(detail=True, methods=['get'], url_path='variants')
    def variants(self, request, uuid=None):
        qs = ShopAdminOrchestrator.list_variants(uuid)
        return Response(ProductVariantSerializer(qs, many=True).data)

    @extend_schema(summary="[Admin] Crea variante de producto", request=ProductVariantInputSerializer)
    @action(detail=True, methods=['post'], url_path='variants/create')
    def create_variant(self, request, uuid=None):
        product = ShopAdminOrchestrator.get_product(uuid)
        ser = ProductVariantInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        variant = ShopAdminOrchestrator.create_variant(product, ser.validated_data)
        variant = ShopAdminOrchestrator.get_variant(variant.uuid)
        return Response(ProductVariantSerializer(variant).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Actualiza variante de producto", request=ProductVariantInputSerializer)
    @action(detail=True, methods=['patch'], url_path='variants/(?P<variant_uuid>[^/.]+)')
    def update_variant(self, request, uuid=None, variant_uuid=None):
        variant = ShopAdminOrchestrator.get_variant(variant_uuid)
        ser = ProductVariantInputSerializer(instance=variant, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = ShopAdminOrchestrator.update_variant(variant, ser.validated_data)
        updated = ShopAdminOrchestrator.get_variant(updated.uuid)
        return Response(ProductVariantSerializer(updated).data)

    @extend_schema(summary="[Admin] Elimina variante de producto (soft-delete)")
    @action(detail=True, methods=['delete'], url_path='variants/(?P<variant_uuid>[^/.]+)/delete')
    def delete_variant(self, request, uuid=None, variant_uuid=None):
        variant = ShopAdminOrchestrator.get_variant(variant_uuid)
        ShopAdminOrchestrator.delete_variant(variant)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Sube imagen al producto")
    @action(detail=True, methods=['post'], url_path='add_image',
            parser_classes=[MultiPartParser, FormParser])
    def add_image(self, request, uuid=None):
        product = ShopAdminOrchestrator.get_product(uuid)
        image_file = request.FILES.get('image')
        if not image_file:
            return Response({'detail': 'Se requiere el archivo image.'}, status=status.HTTP_400_BAD_REQUEST)
        alt_text = request.data.get('alt_text', '')
        is_primary = request.data.get('is_primary', 'false').lower() == 'true'
        img = ProductImageCommands.add_image(product, image_file, alt_text=alt_text, is_primary=is_primary)
        return Response(ProductImageSerializer(img).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Elimina imagen de producto")
    @action(detail=True, methods=['delete'], url_path='delete_image/(?P<image_uuid>[^/.]+)')
    def delete_image(self, request, uuid=None, image_uuid=None):
        product = ShopAdminOrchestrator.get_product(uuid)
        try:
            ProductImageCommands.delete_image(product, image_uuid)
        except ProductImage.DoesNotExist:
            return Response({'detail': 'Imagen no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Establece imagen principal del producto")
    @action(detail=True, methods=['post'], url_path='set_primary/(?P<image_uuid>[^/.]+)')
    def set_primary_image(self, request, uuid=None, image_uuid=None):
        product = ShopAdminOrchestrator.get_product(uuid)
        try:
            img = ProductImageCommands.set_primary_image(product, image_uuid)
        except ProductImage.DoesNotExist:
            return Response({'detail': 'Imagen no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ProductImageSerializer(img).data)



class AdminCategoryViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/categories/
    """
    permission_classes = ADMIN_PERMISSIONS
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = 'uuid'

    def list(self, request):
        qs = ShopAdminOrchestrator.list_categories()
        return Response(CategorySerializer(qs, many=True).data)

    def create(self, request):
        ser = CategoryInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        category = ShopAdminOrchestrator.create_category(ser.validated_data)
        return Response(CategorySerializer(category).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        category = ShopAdminOrchestrator.get_category(uuid)
        return Response(CategorySerializer(category).data)

    def partial_update(self, request, uuid=None):
        category = ShopAdminOrchestrator.get_category(uuid)
        ser = CategoryInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = ShopAdminOrchestrator.update_category(category, ser.validated_data)
        return Response(CategorySerializer(updated).data)

    def destroy(self, request, uuid=None):
        category = ShopAdminOrchestrator.get_category(uuid)
        ShopAdminOrchestrator.delete_category(category)
        return Response(status=status.HTTP_204_NO_CONTENT)



class AdminBrandViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/brands/
    """
    permission_classes = ADMIN_PERMISSIONS
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = 'uuid'

    def list(self, request):
        qs = ShopAdminOrchestrator.list_brands()
        return Response(BrandSerializer(qs, many=True).data)

    def create(self, request):
        ser = BrandInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        brand = ShopAdminOrchestrator.create_brand(ser.validated_data)
        return Response(BrandSerializer(brand).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        brand = ShopAdminOrchestrator.get_brand(uuid)
        return Response(BrandSerializer(brand).data)

    def partial_update(self, request, uuid=None):
        brand = ShopAdminOrchestrator.get_brand(uuid)
        ser = BrandInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = ShopAdminOrchestrator.update_brand(brand, ser.validated_data)
        return Response(BrandSerializer(updated).data)

    def destroy(self, request, uuid=None):
        brand = ShopAdminOrchestrator.get_brand(uuid)
        ShopAdminOrchestrator.delete_brand(brand)
        return Response(status=status.HTTP_204_NO_CONTENT)



class AdminTaxViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/taxes/
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        qs = ShopAdminOrchestrator.list_taxes()
        return Response(TaxSerializer(qs, many=True).data)

    def create(self, request):
        ser = TaxInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        tax = ShopAdminOrchestrator.create_tax(ser.validated_data)
        return Response(TaxSerializer(tax).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        tax = ShopAdminOrchestrator.get_tax(uuid)
        return Response(TaxSerializer(tax).data)

    def partial_update(self, request, uuid=None):
        tax = ShopAdminOrchestrator.get_tax(uuid)
        ser = TaxInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = ShopAdminOrchestrator.update_tax(tax, ser.validated_data)
        return Response(TaxSerializer(updated).data)

    def destroy(self, request, uuid=None):
        tax = ShopAdminOrchestrator.get_tax(uuid)
        ShopAdminOrchestrator.delete_tax(tax)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# ORDERS (Admin: read-only + status transitions)
# ---------------------------------------------------------------------------

class AdminOrderViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/orders/
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        qs = OrderAdminOrchestrator.list_orders()
        return Response(OrderSerializer(qs, many=True).data)

    def retrieve(self, request, uuid=None):
        order = OrderAdminOrchestrator.get_order(uuid)
        return Response(OrderSerializer(order).data)


# ---------------------------------------------------------------------------
# RENTING — Equipment, Variants, Categories, Brands, Labor
# ---------------------------------------------------------------------------

class AdminEquipmentViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/equipment/
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        search = request.query_params.get('search', '')
        category_slug = request.query_params.get('category__slug', '')
        brand_slug = request.query_params.get('brand__slug', '')
        qs = RentingAdminOrchestrator.list_equipment(
            search=search, category_slug=category_slug, brand_slug=brand_slug
        )
        return Response(EquipmentSerializer(qs, many=True).data)

    def create(self, request):
        ser = EquipmentInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        equipment = RentingAdminOrchestrator.create_equipment(request.user, ser.validated_data)
        return Response(EquipmentSerializer(equipment).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        equipment = RentingAdminOrchestrator.get_equipment(uuid)
        return Response(EquipmentSerializer(equipment).data)

    def partial_update(self, request, uuid=None):
        equipment = RentingAdminOrchestrator.get_equipment(uuid)
        ser = EquipmentInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = RentingAdminOrchestrator.update_equipment(equipment, ser.validated_data)
        return Response(EquipmentSerializer(updated).data)

    def destroy(self, request, uuid=None):
        equipment = RentingAdminOrchestrator.get_equipment(uuid)
        RentingAdminOrchestrator.delete_equipment(equipment)
        _log_admin_delete(request, 'Equipment', uuid)  # D-02
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Lista variantes del equipo")
    @action(detail=True, methods=['get'], url_path='variants')
    def variants(self, request, uuid=None):
        qs = RentingAdminOrchestrator.list_variants(uuid)
        return Response(EquipmentVariantSerializer(qs, many=True).data)

    @extend_schema(summary="[Admin] Crea variante de equipo", request=EquipmentVariantInputSerializer)
    @action(detail=True, methods=['post'], url_path='variants/create')
    def create_variant(self, request, uuid=None):
        equipment = RentingAdminOrchestrator.get_equipment(uuid)
        ser = EquipmentVariantInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        variant = RentingAdminOrchestrator.create_variant(ser.validated_data | {'equipment': equipment})
        return Response(EquipmentVariantSerializer(variant).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Actualiza variante de equipo", request=EquipmentVariantInputSerializer)
    @action(detail=True, methods=['patch'], url_path=r'variants/(?P<variant_pk>[^/.]+)')
    def update_variant(self, request, uuid=None, variant_pk=None):
        variant = RentingAdminOrchestrator.get_variant(variant_pk)
        ser = EquipmentVariantInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = RentingAdminOrchestrator.update_variant(variant, ser.validated_data)
        return Response(EquipmentVariantSerializer(updated).data)

    @extend_schema(summary="[Admin] Elimina variante de equipo")
    @action(detail=True, methods=['delete'], url_path=r'variants/(?P<variant_pk>[^/.]+)/delete')
    def delete_variant(self, request, uuid=None, variant_pk=None):
        variant = RentingAdminOrchestrator.get_variant(variant_pk)
        RentingAdminOrchestrator.delete_variant(variant)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Obtiene, crea/actualiza o elimina config de logistica del equipo")
    @action(detail=True, methods=['get', 'put', 'delete'], url_path='logistics')
    def logistics(self, request, uuid=None):
        equipment = RentingAdminOrchestrator.get_equipment(uuid)
        if request.method == 'GET':
            config = getattr(equipment, 'logistics_config', None)
            if not config:
                return Response(None)
            return Response(EquipmentLogisticsConfigSerializer(config).data)
        if request.method == 'PUT':
            ser = EquipmentLogisticsConfigInputSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            config = EquipmentLogisticsConfigCommands.upsert(equipment, **ser.validated_data)
            return Response(EquipmentLogisticsConfigSerializer(config).data)
        if request.method == 'DELETE':
            EquipmentLogisticsConfigCommands.delete(equipment)
            return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Obtiene, crea/actualiza o elimina la configuracion de marketing del equipo")
    @action(detail=True, methods=['get', 'put', 'delete'], url_path='marketing')
    def marketing(self, request, uuid=None):
        equipment = RentingAdminOrchestrator.get_equipment(uuid)
        if request.method == 'GET':
            config = getattr(equipment, 'marketing', None)
            if not config:
                return Response(None)
            return Response(EquipmentMarketingSerializer(config).data)
        if request.method == 'PUT':
            ser = EquipmentMarketingInputSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            config = EquipmentMarketingCommands.upsert(equipment, **ser.validated_data)
            return Response(EquipmentMarketingSerializer(config).data)
        if request.method == 'DELETE':
            EquipmentMarketingCommands.delete(equipment)
            return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Obtiene, crea/actualiza o elimina la configuracion comercial (Renting/Comodato) del equipo")
    @action(detail=True, methods=['get', 'put', 'delete'], url_path='commercial-config')
    def commercial_config(self, request, uuid=None):
        equipment = RentingAdminOrchestrator.get_equipment(uuid)
        if request.method == 'GET':
            config = getattr(equipment, 'commercial_config', None)
            if not config:
                return Response(None)
            return Response(EquipmentCommercialConfigSerializer(config).data)
        if request.method == 'PUT':
            ser = EquipmentCommercialConfigInputSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            config = EquipmentCommercialConfigCommands.upsert(equipment, **ser.validated_data)
            return Response(EquipmentCommercialConfigSerializer(config).data)
        if request.method == 'DELETE':
            EquipmentCommercialConfigCommands.delete(equipment)
            return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Lista o crea/actualiza opciones de plazo comercial (Comodato) del equipo")
    @action(detail=True, methods=['get', 'post'], url_path='commercial-options')
    def commercial_options(self, request, uuid=None):
        equipment = RentingAdminOrchestrator.get_equipment(uuid)
        if request.method == 'GET':
            qs = RentingAdminOrchestrator.list_commercial_options(uuid)
            return Response(EquipmentCommercialOptionSerializer(qs, many=True).data)
        ser = EquipmentCommercialOptionInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        option = RentingAdminOrchestrator.upsert_commercial_option(equipment, ser.validated_data)
        return Response(EquipmentCommercialOptionSerializer(option).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Elimina una opcion de plazo comercial")
    @action(detail=True, methods=['delete'], url_path=r'commercial-options/(?P<option_uuid>[^/.]+)/delete')
    def delete_commercial_option(self, request, uuid=None, option_uuid=None):
        RentingAdminOrchestrator.delete_commercial_option(option_uuid)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminRentingCategoryViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/renting-categories/
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        qs = RentingAdminOrchestrator.list_categories()
        return Response(RentingCategorySerializer(qs, many=True).data)

    def create(self, request):
        ser = RentingCategoryInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        category = RentingAdminOrchestrator.create_category(ser.validated_data)
        return Response(RentingCategorySerializer(category).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        category = RentingAdminOrchestrator.get_category(uuid)
        return Response(RentingCategorySerializer(category).data)

    def partial_update(self, request, uuid=None):
        category = RentingAdminOrchestrator.get_category(uuid)
        ser = RentingCategoryInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = RentingAdminOrchestrator.update_category(category, ser.validated_data)
        return Response(RentingCategorySerializer(updated).data)

    def destroy(self, request, uuid=None):
        category = RentingAdminOrchestrator.get_category(uuid)
        RentingAdminOrchestrator.delete_category(category)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminRentingBrandViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/renting-brands/
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        qs = RentingAdminOrchestrator.list_brands()
        return Response(RentingBrandSerializer(qs, many=True).data)

    def create(self, request):
        ser = RentingBrandInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        brand = RentingAdminOrchestrator.create_brand(ser.validated_data['name'])
        return Response(RentingBrandSerializer(brand).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        brand = RentingAdminOrchestrator.get_brand(uuid)
        return Response(RentingBrandSerializer(brand).data)

    def partial_update(self, request, uuid=None):
        brand = RentingAdminOrchestrator.get_brand(uuid)
        ser = RentingBrandInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = RentingAdminOrchestrator.update_brand(brand, ser.validated_data.get('name', ''))
        return Response(RentingBrandSerializer(updated).data)

    def destroy(self, request, uuid=None):
        brand = RentingAdminOrchestrator.get_brand(uuid)
        RentingAdminOrchestrator.delete_brand(brand)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminRentalLaborViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/rental-labor/
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        qs = RentingAdminOrchestrator.list_labor()
        return Response(RentalLaborSerializer(qs, many=True).data)

    def create(self, request):
        ser = RentalLaborInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        labor = RentingAdminOrchestrator.create_labor(ser.validated_data)
        return Response(RentalLaborSerializer(labor).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        labor = RentingAdminOrchestrator.get_labor(uuid)
        return Response(RentalLaborSerializer(labor).data)

    def partial_update(self, request, uuid=None):
        labor = RentingAdminOrchestrator.get_labor(uuid)
        ser = RentalLaborInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = RentingAdminOrchestrator.update_labor(labor, ser.validated_data)
        return Response(RentalLaborSerializer(updated).data)

    def destroy(self, request, uuid=None):
        labor = RentingAdminOrchestrator.get_labor(uuid)
        RentingAdminOrchestrator.delete_labor(labor)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# QUOTATIONS
# ---------------------------------------------------------------------------

class AdminQuotationViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/quotations/
    Cotizaciones catalogo/personalizado Y Solicitudes de Cotizacion
    (Quotation generada desde un cuestionario tecnico, revisada aqui por
    el asesor comercial).
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        qs = QuotationAdminOrchestrator.list_quotations()
        return Response(QuotationListSerializer(qs, many=True).data)

    def create(self, request):
        ser = QuotationCreateInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        quotation = QuotationAdminOrchestrator.create_quotation(ser.validated_data, request.user)
        return Response(QuotationSerializer(quotation).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        quotation = QuotationAdminOrchestrator.get_quotation(uuid)
        return Response(QuotationSerializer(quotation).data)

    def partial_update(self, request, uuid=None):
        quotation = QuotationAdminOrchestrator.get_quotation(uuid)
        quotation = QuotationAdminOrchestrator.partial_update(quotation, request.data)
        return Response(QuotationSerializer(quotation).data)

    @action(detail=True, methods=['post'], url_path='change-status')
    def change_status(self, request, uuid=None):
        quotation = QuotationAdminOrchestrator.get_quotation(uuid)
        ser = QuotationStatusChangeInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        updated = QuotationAdminOrchestrator.change_status(
            quotation, ser.validated_data['status'], ser.validated_data.get('notes', ''), request.user,
        )
        return Response(QuotationSerializer(updated).data)

    @action(detail=True, methods=['post'], url_path='add-item')
    def add_item(self, request, uuid=None):
        quotation = QuotationAdminOrchestrator.get_quotation(uuid)
        ser = QuotationAddItemInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        QuotationAdminOrchestrator.add_item(quotation, ser.validated_data)
        return Response(QuotationSerializer(QuotationAdminOrchestrator.get_quotation(uuid)).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='add-service')
    def add_service(self, request, uuid=None):
        quotation = QuotationAdminOrchestrator.get_quotation(uuid)
        ser = QuotationAddServiceInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        QuotationAdminOrchestrator.add_service(quotation, dict(ser.validated_data))
        return Response(QuotationSerializer(QuotationAdminOrchestrator.get_quotation(uuid)).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# CONSTRUCTOR DE CUESTIONARIOS TECNICOS — DOMINIO DE DEFINICION DE PLANTILLAS
# ---------------------------------------------------------------------------

class AdminQuoteTemplateCategoryViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/quote-template-categories/
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        qs = QuoteTemplateAdminOrchestrator.list_categories()
        return Response(QuoteTemplateCategorySerializer(qs, many=True).data)

    def create(self, request):
        ser = QuoteTemplateCategoryInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            category = QuoteTemplateAdminOrchestrator.create_category(ser.validated_data)
        except IntegrityError:
            return Response({"detail": "Ya existe una categoria con ese nombre."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(QuoteTemplateCategorySerializer(category).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        category = QuoteTemplateAdminOrchestrator.get_category(uuid)
        return Response(QuoteTemplateCategorySerializer(category).data)

    def partial_update(self, request, uuid=None):
        category = QuoteTemplateAdminOrchestrator.get_category(uuid)
        ser = QuoteTemplateCategoryInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        try:
            updated = QuoteTemplateAdminOrchestrator.update_category(category, ser.validated_data)
        except IntegrityError:
            return Response({"detail": "Ya existe una categoria con ese nombre."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(QuoteTemplateCategorySerializer(updated).data)

    def destroy(self, request, uuid=None):
        category = QuoteTemplateAdminOrchestrator.get_category(uuid)
        QuoteTemplateAdminOrchestrator.delete_category(category)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminQuoteTemplateViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/quote-templates/
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        qs = QuoteTemplateAdminOrchestrator.list_templates()
        return Response(QuoteTemplateListSerializer(qs, many=True).data)

    def create(self, request):
        ser = QuoteTemplateInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            template = QuoteTemplateAdminOrchestrator.create_template(ser.validated_data)
        except IntegrityError:
            return Response({"detail": "Ya existe una plantilla con ese nombre o codigo."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(QuoteTemplateSerializer(template).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        template = QuoteTemplateAdminOrchestrator.get_template(uuid)
        return Response(QuoteTemplateSerializer(template).data)

    def partial_update(self, request, uuid=None):
        template = QuoteTemplateAdminOrchestrator.get_template(uuid)
        ser = QuoteTemplateInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        try:
            updated = QuoteTemplateAdminOrchestrator.update_template(template, ser.validated_data)
        except IntegrityError:
            return Response({"detail": "Ya existe una plantilla con ese nombre o codigo."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(QuoteTemplateSerializer(updated).data)

    def destroy(self, request, uuid=None):
        template = QuoteTemplateAdminOrchestrator.get_template(uuid)
        QuoteTemplateAdminOrchestrator.delete_template(template)
        _log_admin_delete(request, 'QuoteTemplate', uuid)  # D-02
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def clone(self, request, uuid=None):
        template = QuoteTemplateAdminOrchestrator.get_template(uuid)
        clone = QuoteTemplateAdminOrchestrator.clone_template(template)
        return Response(QuoteTemplateSerializer(clone).data, status=status.HTTP_201_CREATED)


class AdminQuoteTemplateAttributeViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/quote-template-attributes/?kind=SERVICE_TYPE
    Catalogo generico para Tipo de Servicio / Tipo de Instalacion / Tipo de
    Sistema (mismo modelo, distinguidos por 'kind').
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        kind = request.query_params.get('kind')
        subcategory = request.query_params.get('subcategory')
        qs = QuoteTemplateAdminOrchestrator.list_attributes(kind, subcategory)
        return Response(QuoteTemplateAttributeSerializer(qs, many=True).data)

    def create(self, request):
        ser = QuoteTemplateAttributeInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            attribute = QuoteTemplateAdminOrchestrator.create_attribute(ser.validated_data)
        except IntegrityError:
            return Response({"detail": "Ya existe un atributo de ese tipo con ese nombre."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(QuoteTemplateAttributeSerializer(attribute).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        attribute = QuoteTemplateAdminOrchestrator.get_attribute(uuid)
        return Response(QuoteTemplateAttributeSerializer(attribute).data)

    def partial_update(self, request, uuid=None):
        attribute = QuoteTemplateAdminOrchestrator.get_attribute(uuid)
        ser = QuoteTemplateAttributeInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        try:
            updated = QuoteTemplateAdminOrchestrator.update_attribute(attribute, ser.validated_data)
        except IntegrityError:
            return Response({"detail": "Ya existe un atributo de ese tipo con ese nombre."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(QuoteTemplateAttributeSerializer(updated).data)

    def destroy(self, request, uuid=None):
        attribute = QuoteTemplateAdminOrchestrator.get_attribute(uuid)
        QuoteTemplateAdminOrchestrator.delete_attribute(attribute)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminQuoteEquipmentTypeViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/quote-equipment-types/
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        qs = QuoteTemplateAdminOrchestrator.list_equipment_types()
        return Response(QuoteEquipmentTypeSerializer(qs, many=True).data)

    def create(self, request):
        ser = QuoteEquipmentTypeInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            equipment_type = QuoteTemplateAdminOrchestrator.create_equipment_type(ser.validated_data)
        except IntegrityError:
            return Response({"detail": "Ya existe un tipo de equipo con ese nombre."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(QuoteEquipmentTypeSerializer(equipment_type).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        equipment_type = QuoteTemplateAdminOrchestrator.get_equipment_type(uuid)
        return Response(QuoteEquipmentTypeSerializer(equipment_type).data)

    def partial_update(self, request, uuid=None):
        equipment_type = QuoteTemplateAdminOrchestrator.get_equipment_type(uuid)
        ser = QuoteEquipmentTypeInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        try:
            updated = QuoteTemplateAdminOrchestrator.update_equipment_type(equipment_type, ser.validated_data)
        except IntegrityError:
            return Response({"detail": "Ya existe un tipo de equipo con ese nombre."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(QuoteEquipmentTypeSerializer(updated).data)

    def destroy(self, request, uuid=None):
        equipment_type = QuoteTemplateAdminOrchestrator.get_equipment_type(uuid)
        QuoteTemplateAdminOrchestrator.delete_equipment_type(equipment_type)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminQuoteTemplateSubcategoryViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/quote-template-subcategories/?category=<uuid>
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        category_uuid = request.query_params.get('category')
        qs = QuoteTemplateAdminOrchestrator.list_subcategories(category_uuid)
        return Response(QuoteTemplateSubcategorySerializer(qs, many=True).data)

    def create(self, request):
        ser = QuoteTemplateSubcategoryInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            subcategory = QuoteTemplateAdminOrchestrator.create_subcategory(ser.validated_data)
        except IntegrityError:
            return Response({"detail": "Ya existe una subcategoria con ese nombre en esta categoria."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(QuoteTemplateSubcategorySerializer(subcategory).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        subcategory = QuoteTemplateAdminOrchestrator.get_subcategory(uuid)
        return Response(QuoteTemplateSubcategorySerializer(subcategory).data)

    def partial_update(self, request, uuid=None):
        subcategory = QuoteTemplateAdminOrchestrator.get_subcategory(uuid)
        ser = QuoteTemplateSubcategoryInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        try:
            updated = QuoteTemplateAdminOrchestrator.update_subcategory(subcategory, ser.validated_data)
        except IntegrityError:
            return Response({"detail": "Ya existe una subcategoria con ese nombre en esta categoria."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(QuoteTemplateSubcategorySerializer(updated).data)

    def destroy(self, request, uuid=None):
        subcategory = QuoteTemplateAdminOrchestrator.get_subcategory(uuid)
        QuoteTemplateAdminOrchestrator.delete_subcategory(subcategory)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminQuoteTemplateModuleViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/quote-template-modules/?template=<uuid>&module_type=EQUIPMENT
    Modulo generico (Equipos/Materiales/Mano de Obra son el mismo modelo,
    distinguidos por module_type).
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        template_uuid = request.query_params.get('template')
        if not template_uuid:
            return Response({'detail': 'Parametro template (uuid) es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        module_type = request.query_params.get('module_type')
        qs = QuoteTemplateAdminOrchestrator.list_modules(template_uuid, module_type)
        return Response(QuoteTemplateModuleSerializer(qs, many=True).data)

    def create(self, request):
        template_uuid = request.data.get('template')
        if not template_uuid:
            return Response({'detail': 'Campo template (uuid) es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        template = QuoteTemplateAdminOrchestrator.get_template(template_uuid)
        data = {k: v for k, v in request.data.items() if k != 'template'}
        ser = QuoteTemplateModuleInputSerializer(data=data)
        ser.is_valid(raise_exception=True)
        module = QuoteTemplateAdminOrchestrator.create_module(template, ser.validated_data)
        return Response(QuoteTemplateModuleSerializer(module).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        module = QuoteTemplateAdminOrchestrator.get_module(uuid)
        return Response(QuoteTemplateModuleSerializer(module).data)

    def partial_update(self, request, uuid=None):
        module = QuoteTemplateAdminOrchestrator.get_module(uuid)
        ser = QuoteTemplateModuleInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = QuoteTemplateAdminOrchestrator.update_module(module, ser.validated_data)
        return Response(QuoteTemplateModuleSerializer(updated).data)

    def destroy(self, request, uuid=None):
        module = QuoteTemplateAdminOrchestrator.get_module(uuid)
        QuoteTemplateAdminOrchestrator.delete_module(module)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, uuid=None):
        module = QuoteTemplateAdminOrchestrator.get_module(uuid)
        clone = QuoteTemplateAdminOrchestrator.duplicate_module(module)
        return Response(QuoteTemplateModuleSerializer(clone).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def reorder(self, request, uuid=None):
        module = QuoteTemplateAdminOrchestrator.get_module(uuid)
        ser = QuoteModuleReorderInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        QuoteTemplateAdminOrchestrator.reorder_module(module, ser.validated_data['direction'])
        return Response(QuoteTemplateModuleSerializer(QuoteTemplateAdminOrchestrator.get_module(uuid)).data)


class AdminQuoteQuestionViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/quote-questions/?module=<uuid>
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        module_uuid = request.query_params.get('module')
        if not module_uuid:
            return Response({'detail': 'Parametro module (uuid) es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        qs = QuoteTemplateAdminOrchestrator.list_questions(module_uuid)
        return Response(QuoteQuestionSerializer(qs, many=True).data)

    def create(self, request):
        module_uuid = request.data.get('module')
        if not module_uuid:
            return Response({'detail': 'Campo module (uuid) es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        module = QuoteTemplateAdminOrchestrator.get_module(module_uuid)
        data = {k: v for k, v in request.data.items() if k != 'module'}
        ser = QuoteQuestionInputSerializer(data=data, context={'module': module})
        ser.is_valid(raise_exception=True)
        try:
            question = QuoteTemplateAdminOrchestrator.create_question(module, ser.validated_data)
        except IntegrityError:
            return Response({"detail": "Ya existe una pregunta con esa clave (key) en este modulo."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(QuoteQuestionSerializer(question).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        question = QuoteTemplateAdminOrchestrator.get_question(uuid)
        return Response(QuoteQuestionSerializer(question).data)

    def partial_update(self, request, uuid=None):
        question = QuoteTemplateAdminOrchestrator.get_question(uuid)
        ser = QuoteQuestionInputSerializer(
            data=request.data, partial=True,
            context={'module': question.module, 'exclude_question_uuid': str(question.uuid)},
        )
        ser.is_valid(raise_exception=True)
        try:
            updated = QuoteTemplateAdminOrchestrator.update_question(question, ser.validated_data)
        except IntegrityError:
            return Response({"detail": "Ya existe una pregunta con esa clave (key) en este modulo."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(QuoteQuestionSerializer(updated).data)

    def destroy(self, request, uuid=None):
        question = QuoteTemplateAdminOrchestrator.get_question(uuid)
        QuoteTemplateAdminOrchestrator.delete_question(question)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='duplicate-to-module')
    def duplicate_to_module(self, request, uuid=None):
        question = QuoteTemplateAdminOrchestrator.get_question(uuid)
        ser = QuoteQuestionDuplicateToModuleInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        clone = QuoteTemplateAdminOrchestrator.duplicate_question_to_module(
            question, ser.validated_data['target_module']
        )
        return Response(QuoteQuestionSerializer(clone).data, status=status.HTTP_201_CREATED)


class AdminQuoteQuestionOptionViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/quote-question-options/?question=<uuid>
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        question_uuid = request.query_params.get('question')
        if not question_uuid:
            return Response({'detail': 'Parametro question (uuid) es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        qs = QuoteTemplateAdminOrchestrator.list_options(question_uuid)
        return Response(QuoteQuestionOptionSerializer(qs, many=True).data)

    def create(self, request):
        question_uuid = request.data.get('question')
        if not question_uuid:
            return Response({'detail': 'Campo question (uuid) es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        question = QuoteTemplateAdminOrchestrator.get_question(question_uuid)
        data = {k: v for k, v in request.data.items() if k != 'question'}
        ser = QuoteQuestionOptionInputSerializer(data=data)
        ser.is_valid(raise_exception=True)
        option = QuoteTemplateAdminOrchestrator.create_option(question, ser.validated_data)
        return Response(QuoteQuestionOptionSerializer(option).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        option = QuoteTemplateAdminOrchestrator.get_option(uuid)
        return Response(QuoteQuestionOptionSerializer(option).data)

    def partial_update(self, request, uuid=None):
        option = QuoteTemplateAdminOrchestrator.get_option(uuid)
        ser = QuoteQuestionOptionInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = QuoteTemplateAdminOrchestrator.update_option(option, ser.validated_data)
        return Response(QuoteQuestionOptionSerializer(updated).data)

    def destroy(self, request, uuid=None):
        option = QuoteTemplateAdminOrchestrator.get_option(uuid)
        QuoteTemplateAdminOrchestrator.delete_option(option)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# TECHNICAL SERVICES
# ---------------------------------------------------------------------------

class AdminTechnicalServiceViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/services/
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        qs = ServiceAdminOrchestrator.list_services()
        return Response(TechnicalServiceSerializer(qs, many=True).data)

    def create(self, request):
        ser = TechnicalServiceAdminCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        service_data = dict(ser.validated_data)
        initial_variant = service_data.pop('initial_variant', None)
        service = ServiceAdminOrchestrator.create_service_with_default_variant(
            request.user,
            service_data,
            initial_variant,
        )
        return Response(TechnicalServiceSerializer(service).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        service = ServiceAdminOrchestrator.get_service(uuid)
        return Response(TechnicalServiceSerializer(service).data)

    def partial_update(self, request, uuid=None):
        service = ServiceAdminOrchestrator.get_service(uuid)
        ser = TechnicalServiceInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = ServiceAdminOrchestrator.update_service(service, ser.validated_data)
        return Response(TechnicalServiceSerializer(updated).data)

    def destroy(self, request, uuid=None):
        service = ServiceAdminOrchestrator.get_service(uuid)
        ServiceAdminOrchestrator.delete_service(service)
        _log_admin_delete(request, 'TechnicalService', uuid)  # D-02
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Subir imagen de servicio")
    @action(detail=True, methods=['post'], url_path='add_image',
            parser_classes=[MultiPartParser, FormParser])
    def add_image(self, request, uuid=None):
        service = ServiceAdminOrchestrator.get_service(uuid)
        image_file = request.FILES.get('image')
        if not image_file:
            return Response({'detail': 'Se requiere el campo image.'}, status=status.HTTP_400_BAD_REQUEST)
        alt_text   = request.data.get('alt_text', '')
        is_primary = request.data.get('is_primary', 'false').lower() == 'true'
        caption     = request.data.get('caption', '')
        description = request.data.get('description', '')
        img = ServiceAdminOrchestrator.add_image(
            service, image_file, alt_text=alt_text, is_primary=is_primary,
            caption=caption, description=description,
        )
        return Response(ServiceImageSerializer(img).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Eliminar imagen de servicio")
    @action(detail=True, methods=['delete'], url_path='delete_image/(?P<image_uuid>[^/.]+)')
    def delete_image(self, request, uuid=None, image_uuid=None):
        ServiceAdminOrchestrator.get_service(uuid)
        img = ServiceAdminOrchestrator.get_image(image_uuid)
        ServiceAdminOrchestrator.delete_image(img)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Establecer imagen principal de servicio")
    @action(detail=True, methods=['post'], url_path='set_primary/(?P<image_uuid>[^/.]+)')
    def set_primary_image(self, request, uuid=None, image_uuid=None):
        ServiceAdminOrchestrator.get_service(uuid)
        img = ServiceAdminOrchestrator.get_image(image_uuid)
        updated = ServiceAdminOrchestrator.set_primary_image(img)
        return Response(ServiceImageSerializer(updated).data)

    # Plan "Rediseno ServiceForm + Content/Media" FASE 4/5 (2026-08-14) --
    # galeria descriptiva: metadatos editables sin re-subir, reemplazo del
    # archivo, reordenamiento manual. Mismo patron BFF que el resto (Vue ->
    # store -> este ViewSet -> ServiceAdminOrchestrator -> Commands).
    @extend_schema(summary="[Admin] Actualizar metadatos de imagen de servicio (sin archivo)")
    @action(detail=True, methods=['patch'], url_path='update_image/(?P<image_uuid>[^/.]+)')
    def update_image(self, request, uuid=None, image_uuid=None):
        ServiceAdminOrchestrator.get_service(uuid)
        img = ServiceAdminOrchestrator.get_image(image_uuid)
        ser = ServiceImageUpdateInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = ServiceAdminOrchestrator.update_image_metadata(img, **ser.validated_data)
        return Response(ServiceImageSerializer(updated).data)

    @extend_schema(summary="[Admin] Reemplazar el archivo de una imagen de servicio")
    @action(detail=True, methods=['post'], url_path='replace_image/(?P<image_uuid>[^/.]+)',
            parser_classes=[MultiPartParser, FormParser])
    def replace_image(self, request, uuid=None, image_uuid=None):
        ServiceAdminOrchestrator.get_service(uuid)
        img = ServiceAdminOrchestrator.get_image(image_uuid)
        image_file = request.FILES.get('image')
        if not image_file:
            return Response({'detail': 'Se requiere el campo image.'}, status=status.HTTP_400_BAD_REQUEST)
        updated = ServiceAdminOrchestrator.replace_image_file(img, image_file)
        return Response(ServiceImageSerializer(updated).data)

    @extend_schema(summary="[Admin] Reordenar la galeria de imagenes de un servicio")
    @action(detail=True, methods=['post'], url_path='reorder_images')
    def reorder_images(self, request, uuid=None):
        service = ServiceAdminOrchestrator.get_service(uuid)
        ser = ServiceImageReorderInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ServiceAdminOrchestrator.reorder_images(service, ser.validated_data['ordered_uuids'])
        # ServiceSelector.get_by_uuid() (usado por get_service() arriba) hace
        # prefetch_related('images', ...) -- `service.images.all()` aqui
        # reusaria ese cache ya poblado ANTES del reorder recien aplicado (Django
        # no invalida un prefetch_related cache por escrituras posteriores).
        # Se consulta ServiceImage.objects directo para forzar una query fresca.
        from technical_services.models import ServiceImage
        images = ServiceImage.objects.filter(service=service)
        return Response(ServiceImageSerializer(images, many=True).data)

    @extend_schema(summary="[Admin] Duplicar servicio")
    @action(detail=True, methods=['post'])
    def duplicate(self, request, uuid=None):
        service = ServiceAdminOrchestrator.get_service(uuid)
        variants = service.variants.filter(is_deleted=False)
        default_variant = next((v for v in variants if v.is_default), None) or variants.first()
        service_data = {
            'name': f'{service.name} (copia)',
            'description': service.description,
            'category': service.category,
            'level': service.level,
            'is_active': False,
            'is_featured': False,
            'is_purchasable': service.is_purchasable,
        }
        variant_data = None
        if default_variant:
            variant_data = {
                'pricing_strategy': default_variant.pricing_strategy,
                'estimated_hours': default_variant.estimated_hours,
                'complexity_factor': default_variant.complexity_factor,
                'fixed_price': default_variant.fixed_price,
                'min_duration': default_variant.min_duration,
                'max_duration': default_variant.max_duration,
                'simultaneous_capacity': default_variant.simultaneous_capacity,
            }
        new_service = ServiceAdminOrchestrator.create_service_with_default_variant(
            request.user, service_data, variant_data,
        )
        return Response(TechnicalServiceSerializer(new_service).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Obtiene, crea/actualiza o elimina la configuracion de marketing del servicio")
    @action(detail=True, methods=['get', 'put', 'delete'], url_path='marketing')
    def marketing(self, request, uuid=None):
        service = ServiceAdminOrchestrator.get_service(uuid)
        if request.method == 'GET':
            config = getattr(service, 'marketing', None)
            if not config:
                return Response(None)
            return Response(ServiceMarketingSerializer(config).data)
        if request.method == 'PUT':
            ser = ServiceMarketingInputSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            config = ServiceMarketingCommands.upsert(service, **ser.validated_data)
            return Response(ServiceMarketingSerializer(config).data)
        if request.method == 'DELETE':
            ServiceMarketingCommands.delete(service)
            return Response(status=status.HTTP_204_NO_CONTENT)


def _facade_err(exc):
    if isinstance(exc, DjangoValidationError):
        return '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc)
    return str(exc)


class AdminServiceRequestViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/technical-services/requests/ -- Fachada Administrativa
    Unificada (Plan 2026-08-14). Listado/detalle combinan Order +
    OrderServiceDetail + ServiceOperation (ver
    ServiceAdminRequestSelector); las acciones delegan siempre a
    ServiceOperationCommands via ServiceAdminRequestOrchestrator -- este
    ViewSet nunca escribe un modelo directo. Ver
    technical_services/.AGENT/SERVICES_ADMIN_FACADE_MATRIX_2026-08-14.md.

    No existe accion `approve`: no hay estado de aprobacion en el backend
    de servicios (a diferencia de Renting) -- ver hallazgo H2 del baseline.
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        params = request.query_params
        qs = ServiceAdminRequestOrchestrator.list_requests(
            status=params.get('status') or None,
            priority=params.get('priority') or None,
            technician_id=params.get('technician_id') or None,
            has_technician=params.get('has_technician') or None,
            search=params.get('search', ''),
        )
        paginator = DashboardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(ServiceAdminRequestSummarySerializer(page, many=True).data)
        return Response(ServiceAdminRequestSummarySerializer(qs, many=True).data)

    def retrieve(self, request, uuid=None):
        order = ServiceAdminRequestOrchestrator.get_request(uuid)
        return Response(ServiceAdminRequestSummarySerializer(order).data)

    @extend_schema(summary="[Admin] Planificar solicitud de servicio (fecha/hora/duracion)")
    @action(detail=True, methods=['post'], url_path='plan')
    def plan(self, request, uuid=None):
        order = ServiceAdminRequestOrchestrator.get_request(uuid)
        serializer = ServiceOperationPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            ServiceAdminRequestOrchestrator.plan_request(order, actor=request.user, **serializer.validated_data)
        except (ValueError, DjangoValidationError) as exc:
            return Response({'detail': _facade_err(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ServiceAdminRequestSummarySerializer(ServiceAdminRequestOrchestrator.get_request(uuid)).data)

    @extend_schema(summary="[Admin] Asignar tecnico a la solicitud (ServiceOperation, fuente de verdad)")
    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, uuid=None):
        order = ServiceAdminRequestOrchestrator.get_request(uuid)
        serializer = ServiceOperationAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            ServiceAdminRequestOrchestrator.assign_technician(
                order, technician=serializer.validated_data['technician_uuid'], actor=request.user,
            )
        except (ValueError, DjangoValidationError) as exc:
            return Response({'detail': _facade_err(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ServiceAdminRequestSummarySerializer(ServiceAdminRequestOrchestrator.get_request(uuid)).data)

    @extend_schema(summary="[Admin] Reprogramar la solicitud (delega a ServiceOperationCommands.reschedule)")
    @action(detail=True, methods=['post'], url_path='schedule')
    def schedule(self, request, uuid=None):
        order = ServiceAdminRequestOrchestrator.get_request(uuid)
        serializer = ServiceOperationRescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            ServiceAdminRequestOrchestrator.schedule_request(order, actor=request.user, **serializer.validated_data)
        except (ValueError, DjangoValidationError) as exc:
            return Response({'detail': _facade_err(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ServiceAdminRequestSummarySerializer(ServiceAdminRequestOrchestrator.get_request(uuid)).data)

    @extend_schema(summary="[Admin] Notificar al cliente (ServiceOperationCommands.notify_client)")
    @action(detail=True, methods=['post'], url_path='notify')
    def notify(self, request, uuid=None):
        order = ServiceAdminRequestOrchestrator.get_request(uuid)
        try:
            ServiceAdminRequestOrchestrator.notify_customer(order, actor=request.user)
        except (ValueError, DjangoValidationError) as exc:
            return Response({'detail': _facade_err(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ServiceAdminRequestSummarySerializer(ServiceAdminRequestOrchestrator.get_request(uuid)).data)

    @extend_schema(summary="[Admin] Cancelar la solicitud (ServiceOperationCommands.cancel)")
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, uuid=None):
        order = ServiceAdminRequestOrchestrator.get_request(uuid)
        serializer = ServiceOperationCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            ServiceAdminRequestOrchestrator.cancel_request(order, actor=request.user, **serializer.validated_data)
        except (ValueError, DjangoValidationError) as exc:
            return Response({'detail': _facade_err(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ServiceAdminRequestSummarySerializer(ServiceAdminRequestOrchestrator.get_request(uuid)).data)


class AdminServiceFAQViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/service-faqs/

    Mismo patron (list/create/partial_update/destroy/toggle-active/reorder)
    que AdminRentalFAQViewSet (renting) -- ver plan de unificacion con Renting.
    No se generalizo via un orchestrator compartido en esta fase (esa
    abstraccion vive acoplada a Renting/Equipment hoy, ver Fase 1 del plan).
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        service_uuid = request.query_params.get('service')
        if not service_uuid:
            return Response({'detail': 'Parametro service (uuid) es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        qs = ServiceFAQSelector.list_for_service(service_uuid)
        return Response(ServiceFAQSerializer(qs, many=True).data)

    def create(self, request):
        service_uuid = request.data.get('service')
        if not service_uuid:
            return Response({'detail': 'service es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        service = ServiceAdminOrchestrator.get_service(service_uuid)
        ser = ServiceFAQInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        instance = ServiceFAQCommands.create(service, **ser.validated_data)
        return Response(ServiceFAQSerializer(instance).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, uuid=None):
        instance = ServiceFAQSelector.get_by_uuid(uuid)
        ser = ServiceFAQInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = ServiceFAQCommands.update(instance, **ser.validated_data)
        return Response(ServiceFAQSerializer(updated).data)

    def destroy(self, request, uuid=None):
        instance = ServiceFAQSelector.get_by_uuid(uuid)
        ServiceFAQCommands.delete(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='toggle-active')
    def toggle_active(self, request, uuid=None):
        instance = ServiceFAQSelector.get_by_uuid(uuid)
        updated = ServiceFAQCommands.toggle_active(instance)
        return Response(ServiceFAQSerializer(updated).data)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        service_uuid = request.data.get('service')
        ordered_uuids = request.data.get('ordered_uuids')
        if not service_uuid or not ordered_uuids:
            return Response({'detail': 'service y ordered_uuids son requeridos.'}, status=status.HTTP_400_BAD_REQUEST)
        service = ServiceAdminOrchestrator.get_service(service_uuid)
        ServiceFAQCommands.reorder(service.id, ordered_uuids)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminServiceCategoryViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/service-categories/
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        qs = ServiceAdminOrchestrator.list_categories()
        return Response(ServiceCategorySerializer(qs, many=True).data)

    def create(self, request):
        ser = ServiceCategoryInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        category = ServiceAdminOrchestrator.create_category(ser.validated_data)
        return Response(ServiceCategorySerializer(category).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        category = ServiceAdminOrchestrator.get_category(uuid)
        return Response(ServiceCategorySerializer(category).data)

    def partial_update(self, request, uuid=None):
        category = ServiceAdminOrchestrator.get_category(uuid)
        ser = ServiceCategoryInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = ServiceAdminOrchestrator.update_category(category, ser.validated_data)
        return Response(ServiceCategorySerializer(updated).data)

    def destroy(self, request, uuid=None):
        category = ServiceAdminOrchestrator.get_category(uuid)
        ServiceAdminOrchestrator.delete_category(category)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminServiceLevelViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/service-levels/
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        qs = ServiceAdminOrchestrator.list_levels()
        return Response(ServiceLevelSerializer(qs, many=True).data)

    def create(self, request):
        ser = ServiceLevelInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        level = ServiceAdminOrchestrator.create_level(ser.validated_data)
        return Response(ServiceLevelSerializer(level).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        level = ServiceAdminOrchestrator.get_level(uuid)
        return Response(ServiceLevelSerializer(level).data)

    def partial_update(self, request, uuid=None):
        level = ServiceAdminOrchestrator.get_level(uuid)
        ser = ServiceLevelInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = ServiceAdminOrchestrator.update_level(level, ser.validated_data)
        return Response(ServiceLevelSerializer(updated).data)

    def destroy(self, request, uuid=None):
        level = ServiceAdminOrchestrator.get_level(uuid)
        ServiceAdminOrchestrator.delete_level(level)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(summary="[Admin] Lista variantes de servicio"),
    create=extend_schema(summary="[Admin] Crea variante de servicio", request=ServiceVariantInputSerializer),
    retrieve=extend_schema(summary="[Admin] Detalle variante de servicio"),
    partial_update=extend_schema(summary="[Admin] Actualiza variante de servicio", request=ServiceVariantInputSerializer),
    destroy=extend_schema(summary="[Admin] Elimina variante de servicio"),
)
class AdminServiceVariantViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/service-variants/
    CRUD administrativo de variantes de servicio.
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        service_uuid = request.query_params.get('service')
        if not service_uuid:
            return Response({'detail': 'Parametro service (uuid) es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        qs = ServiceAdminOrchestrator.list_variants(service_uuid)
        return Response(ServiceVariantSerializer(qs, many=True).data)

    def create(self, request):
        service_uuid = request.data.get('service')
        if not service_uuid:
            return Response({'detail': 'Campo service (uuid) es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        service = ServiceAdminOrchestrator.get_service(service_uuid)
        data = {k: v for k, v in request.data.items() if k != 'service'}
        ser = ServiceVariantInputSerializer(data=data)
        ser.is_valid(raise_exception=True)
        variant = ServiceAdminOrchestrator.create_variant(service, ser.validated_data)
        return Response(ServiceVariantSerializer(variant).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, uuid=None):
        variant = ServiceAdminOrchestrator.get_variant(uuid)
        return Response(ServiceVariantSerializer(variant).data)

    def partial_update(self, request, uuid=None):
        variant = ServiceAdminOrchestrator.get_variant(uuid)
        ser = ServiceVariantInputSerializer(variant, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = ServiceAdminOrchestrator.update_variant(variant, ser.validated_data, updated_by=request.user)
        return Response(ServiceVariantSerializer(updated).data)

    def destroy(self, request, uuid=None):
        variant = ServiceAdminOrchestrator.get_variant(uuid)
        ServiceAdminOrchestrator.delete_variant(variant)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Historial de precios de variante de servicio")
    @action(detail=True, methods=['get'], url_path='price_history')
    def price_history(self, request, uuid=None):
        variant = ServiceAdminOrchestrator.get_variant(uuid)
        history = ServiceAdminOrchestrator.get_variant_price_history(variant)
        return Response(ServicePriceHistorySerializer(history, many=True).data)

    @extend_schema(
        summary="[Admin] Cambia la fuente de precio de una variante (AUTOMATIC/MANUAL_*)",
        request=SetVariantPricingInputSerializer,
    )
    @action(detail=True, methods=['post'], url_path='set-pricing')
    def set_pricing(self, request, uuid=None):
        """Plan 'Manual Pricing Engine' FASE 8/9 -- unica via para cambiar
        pricing_source (ver SetVariantPricingInputSerializer/
        ServicePricingCommands.set_manual_pricing). Nunca via el PATCH
        generico de esta variante."""
        variant = ServiceAdminOrchestrator.get_variant(uuid)
        ser = SetVariantPricingInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            updated = ServiceAdminOrchestrator.set_variant_pricing(
                variant,
                pricing_source=ser.validated_data['pricing_source'],
                unit_price=ser.validated_data.get('unit_price'),
                project_price=ser.validated_data.get('project_price'),
                changed_by=request.user,
                reason=ser.validated_data.get('reason', ''),
            )
        except DjangoValidationError as exc:
            return Response({'detail': '; '.join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ServiceVariantSerializer(updated).data)


# ---------------------------------------------------------------------------
# SHOP COST RULES (Motor de Precios autonomo de shop)
# ---------------------------------------------------------------------------


class AdminShopCostRuleViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    /api/v1/dashboard/shop-cost-rules/
    CRUD de reglas de costo para variantes de productos (shop).
    Contextos: TAX, DISCOUNT.
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'
    serializer_class = ProductCostRuleSerializer

    def get_queryset(self):
        return ProductCostRuleSelector.list_all_for_admin()

    @extend_schema(summary="[Admin] Listar reglas de costo de shop")
    def list(self, request, *args, **kwargs):
        return Response(ProductCostRuleSerializer(self.get_queryset(), many=True).data)

    @extend_schema(summary="[Admin] Detalle de regla de costo de shop")
    def retrieve(self, request, uuid=None):
        rule = ProductCostRuleSelector.get_by_uuid(uuid)
        return Response(ProductCostRuleSerializer(rule).data)

    @extend_schema(summary="[Admin] Crear regla de costo de shop")
    def create(self, request, *args, **kwargs):
        ser = ProductCostRuleInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        rule = ProductCostRuleCommands.create_rule(**ser.validated_data)
        return Response(ProductCostRuleSerializer(rule).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Editar regla de costo de shop")
    @action(detail=True, methods=['patch'], url_path='update')
    def partial_update_rule(self, request, uuid=None):
        rule = ProductCostRuleSelector.get_by_uuid(uuid)
        ser = ProductCostRuleInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        rule = ProductCostRuleCommands.update_rule(rule, ser.validated_data)
        return Response(ProductCostRuleSerializer(rule).data)

    @extend_schema(summary="[Admin] Desactivar regla de costo de shop")
    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, uuid=None):
        rule = ProductCostRuleSelector.get_by_uuid(uuid)
        ProductCostRuleCommands.deactivate_rule(rule)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Eliminar regla de costo de shop")
    def destroy(self, request, uuid=None):
        rule = ProductCostRuleSelector.get_by_uuid(uuid)
        ProductCostRuleCommands.delete_rule(rule)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Asignar regla a variante de producto")
    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, uuid=None):
        rule = ProductCostRuleSelector.get_by_uuid(uuid)
        ser = ProductCostAssignmentInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            from shop.models import ProductVariant
            variant = ProductVariant.objects.get(
                uuid=ser.validated_data['variant_uuid'], is_deleted=False
            )
        except Exception:
            return Response({'detail': 'Variante no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        assignment = ProductCostRuleCommands.assign_to_variant(rule, variant)
        return Response({'assignment_uuid': str(assignment.uuid)}, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# RENTAL COST RULES (Motor de Precios autonomo de renting)
# ---------------------------------------------------------------------------


class AdminRentalCostRuleViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    /api/v1/dashboard/rental-cost-rules/
    CRUD de reglas de costo para variantes de equipos (renting).
    Contextos: TAX, DISCOUNT, DEPOSIT, INSURANCE, SURCHARGE.

    NO existen reglas globales/heredadas: cada regla pertenece exclusivamente
    al Equipment donde se creo (ver RentalCostRule.__doc__). list()/create()
    exigen `equipment` -- nunca se expone ni se crea una regla fuera del
    contexto de un equipo especifico.
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'
    serializer_class = RentalCostRuleSerializer

    @extend_schema(summary="[Admin] Listar reglas de costo de un equipo")
    def list(self, request, *args, **kwargs):
        equipment_uuid = request.query_params.get('equipment')
        if not equipment_uuid:
            return Response({'detail': 'Parametro equipment (uuid) es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        equipment = RentingAdminOrchestrator.get_equipment(equipment_uuid)
        rules = RentalCostRuleSelector.list_for_equipment(equipment)
        return Response(RentalCostRuleSerializer(rules, many=True).data)

    @extend_schema(summary="[Admin] Detalle de regla de costo de alquiler")
    def retrieve(self, request, uuid=None):
        rule = RentalCostRuleSelector.get_by_uuid(uuid)
        return Response(RentalCostRuleSerializer(rule).data)

    @extend_schema(summary="[Admin] Crear regla de costo para un equipo")
    def create(self, request, *args, **kwargs):
        equipment_uuid = request.data.get('equipment')
        if not equipment_uuid:
            return Response({'detail': 'equipment es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        equipment = RentingAdminOrchestrator.get_equipment(equipment_uuid)
        ser = RentalCostRuleInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        rule = RentalCostRuleCommands.create_rule_for_equipment(equipment=equipment, **ser.validated_data)
        return Response(RentalCostRuleSerializer(rule).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Editar regla de costo de alquiler")
    @action(detail=True, methods=['patch'], url_path='update')
    def partial_update_rule(self, request, uuid=None):
        rule = RentalCostRuleSelector.get_by_uuid(uuid)
        ser = RentalCostRuleInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        rule = RentalCostRuleCommands.update_rule(rule, ser.validated_data)
        return Response(RentalCostRuleSerializer(rule).data)

    @extend_schema(summary="[Admin] Desactivar regla de costo de alquiler")
    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, uuid=None):
        rule = RentalCostRuleSelector.get_by_uuid(uuid)
        RentalCostRuleCommands.deactivate_rule(rule)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Eliminar regla de costo de alquiler")
    def destroy(self, request, uuid=None):
        rule = RentalCostRuleSelector.get_by_uuid(uuid)
        RentalCostRuleCommands.delete_rule(rule)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Asignar regla a variante de equipo")
    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, uuid=None):
        rule = RentalCostRuleSelector.get_by_uuid(uuid)
        ser = RentalCostAssignmentInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            from renting.models import EquipmentVariant
            variant = EquipmentVariant.objects.get(
                uuid=ser.validated_data['variant_uuid'], is_deleted=False
            )
        except Exception:
            return Response({'detail': 'Variante de equipo no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        assignment = RentalCostRuleCommands.assign_to_variant(rule, variant)
        return Response({'assignment_uuid': str(assignment.uuid)}, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# SERVICE COST RULES (Motor de Precios autonomo de technical_services)
# ---------------------------------------------------------------------------


class AdminServiceCostRuleViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    /api/v1/dashboard/service-cost-rules/
    CRUD de reglas de costo para variantes de servicios (technical_services).
    Contextos: TAX, DISCOUNT, SETUP, OPERATIONAL.
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'
    serializer_class = ServiceCostRuleSerializer

    def get_queryset(self):
        return ServiceCostRuleSelector.list_all_for_admin()

    @extend_schema(summary="[Admin] Listar reglas de costo de servicios")
    def list(self, request, *args, **kwargs):
        return Response(ServiceCostRuleSerializer(self.get_queryset(), many=True).data)

    @extend_schema(summary="[Admin] Detalle de regla de costo de servicio")
    def retrieve(self, request, uuid=None):
        rule = ServiceCostRuleSelector.get_by_uuid(uuid)
        return Response(ServiceCostRuleSerializer(rule).data)

    @extend_schema(summary="[Admin] Crear regla de costo de servicio")
    def create(self, request, *args, **kwargs):
        ser = ServiceCostRuleInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        rule = ServiceCostRuleCommands.create_rule(**ser.validated_data)
        return Response(ServiceCostRuleSerializer(rule).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Editar regla de costo de servicio")
    @action(detail=True, methods=['patch'], url_path='update')
    def partial_update_rule(self, request, uuid=None):
        rule = ServiceCostRuleSelector.get_by_uuid(uuid)
        ser = ServiceCostRuleInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        rule = ServiceCostRuleCommands.update_rule(rule, ser.validated_data)
        return Response(ServiceCostRuleSerializer(rule).data)

    @extend_schema(summary="[Admin] Desactivar regla de costo de servicio")
    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, uuid=None):
        rule = ServiceCostRuleSelector.get_by_uuid(uuid)
        ServiceCostRuleCommands.deactivate_rule(rule)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Asignar regla a variante de servicio")
    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, uuid=None):
        rule = ServiceCostRuleSelector.get_by_uuid(uuid)
        ser = ServiceCostAssignmentInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            from technical_services.models import ServiceVariant
            variant = ServiceVariant.objects.get(
                uuid=ser.validated_data['variant_uuid'], is_deleted=False
            )
        except Exception:
            return Response({'detail': 'Variante de servicio no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        assignment = ServiceCostRuleCommands.assign_to_variant(rule, variant)
        return Response({'assignment_uuid': str(assignment.uuid)}, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# MARKETING (read-only metrics)
# ---------------------------------------------------------------------------

class AdminMarketingViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/marketing/
    """
    permission_classes = ADMIN_PERMISSIONS

    @extend_schema(summary="[Admin] Resumen consolidado de marketing")
    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        data = MarketingAdminOrchestrator.get_consolidated_dashboard()
        return Response(data)

    @extend_schema(summary="[Admin] Lista campanas de marketing")
    @action(detail=False, methods=['get'], url_path='campaigns')
    def campaigns(self, request):
        qs = MarketingAdminOrchestrator.list_campaigns()
        return Response({'results': list(qs.values())})

    @extend_schema(summary="[Admin] Lista flash offers")
    @action(detail=False, methods=['get'], url_path='flash-offers')
    def flash_offers(self, request):
        qs = MarketingAdminOrchestrator.list_flash_offers()
        return Response({'results': list(qs.values())})


# ---------------------------------------------------------------------------
# HOME CONFIG (core)
# ---------------------------------------------------------------------------

def _invalidate_home_feed_cache():
    from django.core.cache import cache
    from core.api.views import HOME_FEED_CACHE_KEY
    cache.delete(HOME_FEED_CACHE_KEY)


def _invalidate_footer_cache():
    from django.core.cache import cache
    from core.api.views import FOOTER_CACHE_KEY
    cache.delete(FOOTER_CACHE_KEY)


def _invalidate_site_config_cache():
    from django.core.cache import cache
    from core.api.views import SITE_CONFIG_CACHE_KEY
    cache.delete(SITE_CONFIG_CACHE_KEY)


def _invalidate_about_us_cache():
    from django.core.cache import cache
    from core.api.views import ABOUT_US_CACHE_KEY
    cache.delete(ABOUT_US_CACHE_KEY)


class AdminHomeConfigViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/home-config/
    Gestiona banners y visibilidad de modulos de la Home publica.
    """
    permission_classes = ADMIN_PERMISSIONS
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    # ── Banners ──────────────────────────────────────────────────────────────

    @extend_schema(summary="[Admin] Lista banners de la Home")
    @action(detail=False, methods=['get'], url_path='banners')
    def list_banners(self, request):
        from core.services.selectors import HomeConfigSelector
        from core.api.serializers import HomeBannerSerializer
        qs = HomeConfigSelector.list_banners_for_admin()
        return Response(HomeBannerSerializer(qs, many=True, context={'request': request}).data)

    @extend_schema(summary="[Admin] Crea banner", request=None)
    @action(detail=False, methods=['post'], url_path='banners/create')
    def create_banner(self, request):
        from core.services.commands import HomeConfigCommands
        from core.api.serializers import HomeBannerInputSerializer, HomeBannerSerializer
        s = HomeBannerInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        banner = HomeConfigCommands.create_banner(
            title=d['title'],
            subtitle=d.get('subtitle', ''),
            link_url=d.get('link_url', ''),
            link_label=d.get('link_label', ''),
            display_order=d.get('display_order', 0),
            image=d.get('image'),
            video=d.get('video'),
        )
        _invalidate_home_feed_cache()
        return Response(HomeBannerSerializer(banner, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Actualiza banner")
    @action(detail=False, methods=['patch'], url_path='banners/(?P<uuid>[^/.]+)')
    def update_banner(self, request, uuid=None):
        from core.services.selectors import HomeConfigSelector
        from core.services.commands import HomeConfigCommands
        from core.api.serializers import HomeBannerInputSerializer, HomeBannerSerializer
        banner = HomeConfigSelector.get_banner_by_uuid(uuid)
        s = HomeBannerInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        banner = HomeConfigCommands.update_banner(banner, s.validated_data)
        _invalidate_home_feed_cache()
        return Response(HomeBannerSerializer(banner, context={'request': request}).data)

    @extend_schema(summary="[Admin] Elimina (soft) banner")
    @action(detail=False, methods=['delete'], url_path='banners/(?P<uuid>[^/.]+)/delete')
    def delete_banner(self, request, uuid=None):
        from core.services.selectors import HomeConfigSelector
        from core.services.commands import HomeConfigCommands
        banner = HomeConfigSelector.get_banner_by_uuid(uuid)
        HomeConfigCommands.deactivate_banner(banner)
        _invalidate_home_feed_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── Modules ───────────────────────────────────────────────────────────────

    @extend_schema(summary="[Admin] Lista configuracion de modulos de Home")
    @action(detail=False, methods=['get'], url_path='modules')
    def list_modules(self, request):
        from core.services.selectors import HomeConfigSelector
        from core.api.serializers import HomeModuleConfigSerializer
        qs = HomeConfigSelector.get_or_create_default_modules()
        return Response(HomeModuleConfigSerializer(qs, many=True, context={'request': request}).data)

    @extend_schema(summary="[Admin] Actualiza visibilidad/orden de modulo")
    @action(detail=False, methods=['patch'], url_path='modules/(?P<uuid>[^/.]+)')
    def update_module(self, request, uuid=None):
        from core.services.selectors import HomeConfigSelector
        from core.services.commands import HomeConfigCommands
        from core.api.serializers import HomeModuleConfigInputSerializer, HomeModuleConfigSerializer
        cfg = HomeConfigSelector.get_module_config_by_uuid(uuid)
        s = HomeModuleConfigInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        cfg = HomeConfigCommands.update_module_config(cfg, s.validated_data)
        _invalidate_home_feed_cache()
        return Response(HomeModuleConfigSerializer(cfg, context={'request': request}).data)

    @extend_schema(summary="[Admin] Crea modulo personalizado en Home")
    @action(detail=False, methods=['post'], url_path='modules/create')
    def create_module(self, request):
        from core.models import HomeModuleConfig
        from core.services.commands import HomeConfigCommands
        from core.api.serializers import HomeModuleCreateSerializer, HomeModuleConfigSerializer
        s = HomeModuleCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        if HomeModuleConfig.objects.filter(module_key=d['module_key'], is_deleted=False).exists():
            return Response(
                {'detail': f'Ya existe un modulo con la clave "{d["module_key"]}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        config = HomeConfigCommands.create_module(**d)
        _invalidate_home_feed_cache()
        return Response(HomeModuleConfigSerializer(config, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Elimina modulo personalizado de Home")
    @action(detail=False, methods=['delete'], url_path='modules/(?P<uuid>[^/.]+)/delete')
    def delete_module(self, request, uuid=None):
        from core.models import HomeModuleConfig
        from core.services.selectors import HomeConfigSelector
        from core.services.commands import HomeConfigCommands
        CORE_KEYS = {
            HomeModuleConfig.MODULE_SHOP, HomeModuleConfig.MODULE_RENTING,
            HomeModuleConfig.MODULE_SERVICES, HomeModuleConfig.MODULE_QUOTES,
        }
        cfg = HomeConfigSelector.get_module_config_by_uuid(uuid)
        if cfg.module_key in CORE_KEYS:
            return Response(
                {'detail': 'No se pueden eliminar los modulos principales del sistema.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        HomeConfigCommands.delete_module(cfg)
        _invalidate_home_feed_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminHomeCardViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/home-cards/
    CRUD de tarjetas informativas flat-design para la Home publica.
    """
    permission_classes = ADMIN_PERMISSIONS
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(summary="[Admin] Lista tarjetas de la Home")
    def list(self, request):
        from core.services.commands import HomeCardSelector
        from core.api.serializers import HomeCardSerializer
        qs = HomeCardSelector.list_for_admin()
        return Response(HomeCardSerializer(qs, many=True, context={'request': request}).data)

    @extend_schema(summary="[Admin] Crea tarjeta de la Home")
    @action(detail=False, methods=['post'], url_path='create')
    def create_card(self, request):
        from core.services.commands import HomeCardCommands
        from core.api.serializers import HomeCardInputSerializer, HomeCardSerializer
        s = HomeCardInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = dict(s.validated_data)
        d.pop('remove_image', None)
        d.pop('remove_video', None)
        card = HomeCardCommands.create_card(**d)
        _invalidate_home_feed_cache()
        return Response(HomeCardSerializer(card, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Actualiza tarjeta de la Home")
    @action(detail=False, methods=['patch'], url_path='(?P<uuid>[^/.]+)')
    def update_card(self, request, uuid=None):
        from core.services.commands import HomeCardSelector
        from core.services.commands import HomeCardCommands
        from core.api.serializers import HomeCardInputSerializer, HomeCardSerializer
        card = HomeCardSelector.get_by_uuid(uuid)
        s = HomeCardInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        card = HomeCardCommands.update_card(card, s.validated_data)
        _invalidate_home_feed_cache()
        return Response(HomeCardSerializer(card, context={'request': request}).data)

    @extend_schema(summary="[Admin] Elimina (soft) tarjeta de la Home")
    @action(detail=False, methods=['delete'], url_path='(?P<uuid>[^/.]+)/delete')
    def delete_card(self, request, uuid=None):
        from core.services.commands import HomeCardSelector
        from core.services.commands import HomeCardCommands
        card = HomeCardSelector.get_by_uuid(uuid)
        HomeCardCommands.delete_card(card)
        _invalidate_home_feed_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# HOME CARD GROUPS (core)
# ---------------------------------------------------------------------------

class AdminHomeCardGroupViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/home-card-groups/
    Titulos editables de los grupos de tarjetas de la Home.
    """
    permission_classes = ADMIN_PERMISSIONS

    @extend_schema(summary="[Admin] Lista grupos de tarjetas")
    def list(self, request):
        from core.services.commands import HomeCardGroupSelector
        from core.api.serializers import HomeCardGroupSerializer
        qs = HomeCardGroupSelector.list_all()
        return Response(HomeCardGroupSerializer(qs, many=True).data)

    @extend_schema(summary="[Admin] Crea o actualiza titulo de grupo (upsert por nombre)")
    @action(detail=False, methods=['post'], url_path='upsert')
    def upsert(self, request):
        from core.services.commands import HomeCardGroupCommands
        from core.api.serializers import HomeCardGroupInputSerializer, HomeCardGroupSerializer
        s = HomeCardGroupInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        extra = {k: d[k] for k in (
            'subtitle', 'description', 'bg_color', 'bg_image', 'remove_bg_image',
            'layout_type', 'padding', 'divider', 'columns', 'glass', 'hover',
            'columns_tablet', 'columns_mobile', 'gap',
            'carousel_autoplay', 'carousel_loop', 'carousel_speed',
            'show_arrows', 'show_indicators',
        ) if k in d}
        group = HomeCardGroupCommands.upsert(
            name=d['name'],
            title=d['title'],
            display_order=d.get('display_order', 0),
            is_visible=d.get('is_visible', True),
            **extra,
        )
        _invalidate_home_feed_cache()
        return Response(HomeCardGroupSerializer(group).data, status=status.HTTP_200_OK)

    @extend_schema(summary="[Admin] Actualiza titulo de grupo")
    @action(detail=False, methods=['patch'], url_path=r'(?P<uuid>[0-9a-f-]{36})')
    def update_group(self, request, uuid=None):
        from core.services.commands import HomeCardGroupSelector
        from core.services.commands import HomeCardGroupCommands
        from core.api.serializers import HomeCardGroupSerializer
        group = HomeCardGroupSelector.get_by_uuid(uuid)
        d = {}
        for field in (
            'title', 'display_order', 'is_visible',
            'subtitle', 'description', 'bg_color', 'bg_image',
            'layout_type', 'padding', 'divider', 'columns', 'glass', 'hover',
            'columns_tablet', 'columns_mobile', 'gap',
            'carousel_autoplay', 'carousel_loop', 'carousel_speed',
            'show_arrows', 'show_indicators',
        ):
            if field in request.data:
                d[field] = request.data[field]
        group = HomeCardGroupCommands.update(group, d)
        _invalidate_home_feed_cache()
        return Response(HomeCardGroupSerializer(group).data)

    @extend_schema(summary="[Admin] Elimina (soft) grupo de tarjetas")
    @action(detail=False, methods=['delete'], url_path=r'(?P<uuid>[0-9a-f-]{36})/delete')
    def delete_group(self, request, uuid=None):
        from core.services.commands import HomeCardGroupSelector
        from core.services.commands import HomeCardGroupCommands
        group = HomeCardGroupSelector.get_by_uuid(uuid)
        HomeCardGroupCommands.delete(group)
        _invalidate_home_feed_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# FEATURE BANNER (core) -- seccion promocional generica del Home Builder,
# 2026-08-06. Mismo patron exacto que HomeCard/HomeCardGroup arriba.
# ---------------------------------------------------------------------------

class AdminFeatureBannerSectionViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/feature-banner-sections/
    CRUD de secciones "Feature Banner" (contenedor de bloques imagen+texto+botones).
    """
    permission_classes = ADMIN_PERMISSIONS
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(summary="[Admin] Lista secciones de Feature Banner (con sus bloques)")
    def list(self, request):
        from core.services.commands import FeatureBannerSectionSelector
        from core.api.serializers import FeatureBannerSectionSerializer
        qs = FeatureBannerSectionSelector.list_all()
        return Response(FeatureBannerSectionSerializer(qs, many=True, context={'request': request}).data)

    @extend_schema(summary="[Admin] Crea seccion de Feature Banner")
    @action(detail=False, methods=['post'], url_path='create')
    def create_section(self, request):
        from core.services.commands import FeatureBannerSectionCommands
        from core.api.serializers import FeatureBannerSectionInputSerializer, FeatureBannerSectionSerializer
        s = FeatureBannerSectionInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = dict(s.validated_data)
        d.pop('remove_background_image', None)
        section = FeatureBannerSectionCommands.create(**d)
        _invalidate_home_feed_cache()
        return Response(FeatureBannerSectionSerializer(section, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Actualiza seccion de Feature Banner")
    @action(detail=False, methods=['patch'], url_path='(?P<uuid>[^/.]+)')
    def update_section(self, request, uuid=None):
        from core.services.commands import FeatureBannerSectionSelector, FeatureBannerSectionCommands
        from core.api.serializers import FeatureBannerSectionInputSerializer, FeatureBannerSectionSerializer
        section = FeatureBannerSectionSelector.get_by_uuid(uuid)
        s = FeatureBannerSectionInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        section = FeatureBannerSectionCommands.update(section, dict(s.validated_data))
        _invalidate_home_feed_cache()
        return Response(FeatureBannerSectionSerializer(section, context={'request': request}).data)

    @extend_schema(summary="[Admin] Elimina (soft) seccion de Feature Banner")
    @action(detail=False, methods=['delete'], url_path='(?P<uuid>[^/.]+)/delete')
    def delete_section(self, request, uuid=None):
        from core.services.commands import FeatureBannerSectionSelector, FeatureBannerSectionCommands
        section = FeatureBannerSectionSelector.get_by_uuid(uuid)
        FeatureBannerSectionCommands.delete(section)
        _invalidate_home_feed_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminFeatureBannerBlockViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/feature-banner-blocks/?section=<uuid>
    CRUD de bloques (imagen+texto+botones) dentro de una FeatureBannerSection.
    """
    permission_classes = ADMIN_PERMISSIONS
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(summary="[Admin] Lista bloques de una seccion de Feature Banner")
    def list(self, request):
        from core.services.commands import FeatureBannerBlockSelector
        from core.api.serializers import FeatureBannerBlockSerializer
        section_uuid = request.query_params.get('section')
        if not section_uuid:
            return Response({'detail': 'section (uuid) es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        qs = FeatureBannerBlockSelector.list_for_section(section_uuid)
        return Response(FeatureBannerBlockSerializer(qs, many=True, context={'request': request}).data)

    @extend_schema(summary="[Admin] Crea bloque de Feature Banner")
    @action(detail=False, methods=['post'], url_path='create')
    def create_block(self, request):
        from core.services.commands import FeatureBannerSectionSelector, FeatureBannerBlockCommands
        from core.api.serializers import FeatureBannerBlockInputSerializer, FeatureBannerBlockSerializer
        section_uuid = request.data.get('section')
        if not section_uuid:
            return Response({'detail': 'section (uuid) es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        section = FeatureBannerSectionSelector.get_by_uuid(section_uuid)
        s = FeatureBannerBlockInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = dict(s.validated_data)
        d.pop('remove_image', None)
        block = FeatureBannerBlockCommands.create(section, **d)
        _invalidate_home_feed_cache()
        return Response(FeatureBannerBlockSerializer(block, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Actualiza bloque de Feature Banner")
    @action(detail=False, methods=['patch'], url_path='(?P<uuid>[^/.]+)')
    def update_block(self, request, uuid=None):
        from core.services.commands import FeatureBannerBlockSelector, FeatureBannerBlockCommands
        from core.api.serializers import FeatureBannerBlockInputSerializer, FeatureBannerBlockSerializer
        block = FeatureBannerBlockSelector.get_by_uuid(uuid)
        s = FeatureBannerBlockInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        block = FeatureBannerBlockCommands.update(block, dict(s.validated_data))
        _invalidate_home_feed_cache()
        return Response(FeatureBannerBlockSerializer(block, context={'request': request}).data)

    @extend_schema(summary="[Admin] Elimina (soft) bloque de Feature Banner")
    @action(detail=False, methods=['delete'], url_path='(?P<uuid>[^/.]+)/delete')
    def delete_block(self, request, uuid=None):
        from core.services.commands import FeatureBannerBlockSelector, FeatureBannerBlockCommands
        block = FeatureBannerBlockSelector.get_by_uuid(uuid)
        FeatureBannerBlockCommands.delete(block)
        _invalidate_home_feed_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Reordena bloques de una seccion (drag & drop)")
    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        from core.services.commands import FeatureBannerSectionSelector, FeatureBannerBlockCommands
        section_uuid = request.data.get('section')
        ordered_uuids = request.data.get('ordered_uuids', [])
        if not section_uuid or not ordered_uuids:
            return Response({'detail': 'section y ordered_uuids son requeridos.'}, status=status.HTTP_400_BAD_REQUEST)
        section = FeatureBannerSectionSelector.get_by_uuid(section_uuid)
        FeatureBannerBlockCommands.reorder(section.id, ordered_uuids)
        _invalidate_home_feed_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# FOOTER (core)
# ---------------------------------------------------------------------------

class AdminFooterViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/footer/
    Gestiona enlaces del footer y datos de contacto institucional.

    [2026-07-12] Contacto y redes sociales viven ahora en `organization`
    (Company/Branding/ContactInfo/SocialLink migrados desde `core`, ver
    Documentacion/Arquitectura_general/MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md).
    Este ViewSet sigue exponiendo los MISMOS endpoints/contrato JSON que antes
    (el frontend -- HomeConfigView.vue -- todavia filtra 'links' por
    category='nav'|'social' en un solo array) para no romper el panel admin
    antes de la Fase 6 ("Frontend SPA", el ultimo consumidor en migrar). Por
    eso `create_link`/`update_link`/`delete_link` despachan entre
    core.FooterLink (nav) y organization.SocialLink (social) segun category,
    en vez de dejar que el frontend cambie de endpoint.
    """
    permission_classes = ADMIN_PERMISSIONS

    @extend_schema(summary="[Admin] Estado completo del footer (contacto + enlaces)")
    def list(self, request):
        from core.services.commands import FooterSelector
        from core.api.serializers import FooterLinkSerializer, social_link_to_footer_link_shape
        from organization.services.selectors import OrganizationSelector
        from organization.api.serializers import ContactInfoSerializer

        contact = OrganizationSelector.get_contact_info()
        nav_links = FooterSelector.list_all_links()
        social_links = OrganizationSelector.list_social_links(active_only=False)

        links = list(FooterLinkSerializer(nav_links, many=True).data) + [
            social_link_to_footer_link_shape(l) for l in social_links
        ]
        return Response({
            'contact': ContactInfoSerializer(contact).data if contact else None,
            'links':   links,
        })

    @extend_schema(summary="[Admin] Guarda (upsert) datos de contacto")
    @action(detail=False, methods=['post'], url_path='contact')
    def save_contact(self, request):
        from organization.services.commands import OrganizationCommands
        from organization.api.serializers import ContactInfoInputSerializer, ContactInfoSerializer
        s = ContactInfoInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        contact = OrganizationCommands.upsert_contact_info(s.validated_data)
        _invalidate_footer_cache()
        return Response(ContactInfoSerializer(contact).data)

    @extend_schema(summary="[Admin] Crea enlace de footer (nav o social)")
    @action(detail=False, methods=['post'], url_path='links/create')
    def create_link(self, request):
        from core.api.serializers import FooterLinkInputSerializer, FooterLinkSerializer, social_link_to_footer_link_shape
        if request.data.get('category') == 'social':
            from organization.services.commands import OrganizationCommands
            link = OrganizationCommands.create_social_link(
                platform=request.data.get('title', ''),
                url=request.data.get('url', ''),
                icon_class=request.data.get('icon_class', ''),
                display_order=request.data.get('display_order', 0) or 0,
            )
            _invalidate_footer_cache()
            return Response(social_link_to_footer_link_shape(link), status=status.HTTP_201_CREATED)

        from core.services.commands import FooterGroupSelector
        from core.services.commands import FooterCommands
        s = FooterLinkInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        group = FooterGroupSelector.get_by_uuid(d['group'])
        link = FooterCommands.create_link(
            title=d['title'], url=d['url'], category='nav',
            group=group, icon_class=d.get('icon_class', ''),
            open_new_tab=d.get('open_new_tab', False),
            display_order=d.get('display_order', 0),
        )
        _invalidate_footer_cache()
        return Response(FooterLinkSerializer(link).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Actualiza enlace de footer (nav o social)")
    @action(detail=False, methods=['patch'], url_path='links/(?P<uuid>[^/.]+)')
    def update_link(self, request, uuid=None):
        from core.api.serializers import FooterLinkInputSerializer, FooterLinkSerializer, social_link_to_footer_link_shape
        from organization.services.selectors import OrganizationSelector
        from organization.services.commands import OrganizationCommands

        social_link = OrganizationSelector.find_social_link_by_uuid(uuid)
        if social_link:
            data = dict(request.data)
            mapped = {}
            if 'title' in data:
                mapped['platform'] = data['title']
            for field in ('url', 'icon_class', 'display_order', 'is_active'):
                if field in data:
                    mapped[field] = data[field]
            link = OrganizationCommands.update_social_link(social_link, mapped)
            _invalidate_footer_cache()
            return Response(social_link_to_footer_link_shape(link))

        from core.services.commands import FooterSelector, FooterGroupSelector
        from core.services.commands import FooterCommands
        link = FooterSelector.get_link_by_uuid(uuid)
        s = FooterLinkInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        if 'group' in data:
            data['group'] = FooterGroupSelector.get_by_uuid(data['group'])
        link = FooterCommands.update_link(link, data)
        _invalidate_footer_cache()
        return Response(FooterLinkSerializer(link).data)

    @extend_schema(summary="[Admin] Elimina (soft) enlace de footer (nav o social)")
    @action(detail=False, methods=['delete'], url_path='links/(?P<uuid>[^/.]+)/delete')
    def delete_link(self, request, uuid=None):
        from organization.services.selectors import OrganizationSelector
        from organization.services.commands import OrganizationCommands

        social_link = OrganizationSelector.find_social_link_by_uuid(uuid)
        if social_link:
            OrganizationCommands.delete_social_link(social_link)
            _invalidate_footer_cache()
            return Response(status=status.HTTP_204_NO_CONTENT)

        from core.services.commands import FooterSelector
        from core.services.commands import FooterCommands
        link = FooterSelector.get_link_by_uuid(uuid)
        FooterCommands.delete_link(link)
        _invalidate_footer_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Reordena enlaces de navegacion dentro de un grupo (drag & drop)")
    @action(detail=False, methods=['post'], url_path='links/reorder')
    def reorder_links(self, request):
        from core.services.commands import FooterCommands
        from core.api.serializers import FooterLinkReorderSerializer
        s = FooterLinkReorderSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        FooterCommands.reorder_links(s.validated_data['items'])
        _invalidate_footer_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# FOOTER GROUPS (core)
# ---------------------------------------------------------------------------

class AdminFooterGroupViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/footer-groups/
    Gestiona las columnas (grupos) de navegacion del footer publico.
    """
    permission_classes = ADMIN_PERMISSIONS

    @extend_schema(summary="[Admin] Lista grupos del footer")
    def list(self, request):
        from core.services.commands import FooterGroupSelector
        from core.api.serializers import FooterGroupSerializer
        qs = FooterGroupSelector.list_all()
        return Response(FooterGroupSerializer(qs, many=True).data)

    @extend_schema(summary="[Admin] Crea grupo del footer", request=None)
    @action(detail=False, methods=['post'], url_path='create')
    def create_group(self, request):
        from core.services.commands import FooterGroupCommands
        from core.api.serializers import FooterGroupInputSerializer, FooterGroupSerializer
        s = FooterGroupInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        group = FooterGroupCommands.create(**s.validated_data)
        _invalidate_footer_cache()
        return Response(FooterGroupSerializer(group).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Actualiza grupo del footer")
    @action(detail=False, methods=['patch'], url_path='(?P<uuid>[^/.]+)')
    def update_group(self, request, uuid=None):
        from core.services.commands import FooterGroupSelector
        from core.services.commands import FooterGroupCommands
        from core.api.serializers import FooterGroupInputSerializer, FooterGroupSerializer
        group = FooterGroupSelector.get_by_uuid(uuid)
        s = FooterGroupInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        group = FooterGroupCommands.update(group, s.validated_data)
        _invalidate_footer_cache()
        return Response(FooterGroupSerializer(group).data)

    @extend_schema(summary="[Admin] Elimina (soft) grupo del footer")
    @action(detail=False, methods=['delete'], url_path='(?P<uuid>[^/.]+)/delete')
    def delete_group(self, request, uuid=None):
        from core.services.commands import FooterGroupSelector
        from core.services.commands import FooterGroupCommands
        group = FooterGroupSelector.get_by_uuid(uuid)
        FooterGroupCommands.delete(group)
        _invalidate_footer_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Reordena grupos del footer (drag & drop)")
    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        from core.services.commands import FooterGroupCommands
        from core.api.serializers import FooterGroupReorderSerializer
        s = FooterGroupReorderSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        FooterGroupCommands.reorder_groups(s.validated_data['items'])
        _invalidate_footer_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# SITE BRAND & NAVBAR (core)
# ---------------------------------------------------------------------------

class AdminSiteBrandViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/site-brand/
    Gestiona nombre, logo y tagline de la empresa.

    [2026-07-12] Migrado a organization.Company + organization.Branding (2
    modelos separados, decision confirmada en la migracion). Mantiene el mismo
    contrato JSON plano {uuid, site_name, logo, tagline, updated_at} que el
    frontend ya consume, combinando ambos modelos en la respuesta.
    """
    permission_classes = ADMIN_PERMISSIONS
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @staticmethod
    def _brand_response(request):
        from organization.services.selectors import OrganizationSelector
        company  = OrganizationSelector.get_company()
        branding = OrganizationSelector.get_branding()
        logo_url = None
        if branding and branding.logo:
            logo_url = request.build_absolute_uri(branding.logo.url)
        return {
            'uuid': str(company.uuid) if company else None,
            'site_name': OrganizationSelector.get_display_name(),
            'logo': logo_url,
            'tagline': branding.tagline if branding else '',
            'updated_at': company.updated_at if company else None,
        }

    @extend_schema(summary="[Admin] Obtiene configuracion de marca")
    def list(self, request):
        return Response(self._brand_response(request))

    @extend_schema(summary="[Admin] Actualiza (upsert) configuracion de marca")
    @action(detail=False, methods=['post', 'patch'], url_path='update')
    def update_brand(self, request):
        from organization.services.commands import OrganizationCommands
        data = request.data
        if 'site_name' in data:
            OrganizationCommands.upsert_company({'trade_name': data['site_name']})
        branding_data = {}
        for field in ('tagline', 'logo', 'remove_logo'):
            if field in data:
                branding_data[field] = data[field]
        if branding_data:
            OrganizationCommands.upsert_branding(branding_data)
        _invalidate_site_config_cache()
        return Response(self._brand_response(request))


class AdminNavbarViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/navbar/
    CRUD de enlaces del navbar publico.
    """
    permission_classes = ADMIN_PERMISSIONS

    @extend_schema(summary="[Admin] Lista todos los enlaces del navbar")
    def list(self, request):
        from core.services.commands import NavbarLinkSelector
        from core.api.serializers import NavbarLinkSerializer
        links = NavbarLinkSelector.list_all()
        return Response(NavbarLinkSerializer(links, many=True).data)

    @extend_schema(summary="[Admin] Crea enlace del navbar")
    @action(detail=False, methods=['post'], url_path='create')
    def create_link(self, request):
        from core.services.commands import NavbarLinkCommands
        from core.api.serializers import NavbarLinkInputSerializer, NavbarLinkSerializer
        s = NavbarLinkInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        link = NavbarLinkCommands.create(
            label=d['label'], url=d['url'],
            icon_class=d.get('icon_class', ''),
            display_order=d.get('display_order', 0),
            is_visible=d.get('is_visible', True),
            open_in_new_tab=d.get('open_in_new_tab', False),
        )
        _invalidate_site_config_cache()
        return Response(NavbarLinkSerializer(link).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Actualiza enlace del navbar")
    @action(detail=False, methods=['patch'], url_path='(?P<uuid>[^/.]+)')
    def update_link(self, request, uuid=None):
        from core.services.commands import NavbarLinkSelector
        from core.services.commands import NavbarLinkCommands
        from core.api.serializers import NavbarLinkInputSerializer, NavbarLinkSerializer
        link = NavbarLinkSelector.get_by_uuid(uuid)
        s = NavbarLinkInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        link = NavbarLinkCommands.update(link, s.validated_data)
        _invalidate_site_config_cache()
        return Response(NavbarLinkSerializer(link).data)

    @extend_schema(summary="[Admin] Elimina enlace del navbar")
    @action(detail=False, methods=['delete'], url_path='(?P<uuid>[^/.]+)/delete')
    def delete_link(self, request, uuid=None):
        from core.services.commands import NavbarLinkSelector
        from core.services.commands import NavbarLinkCommands
        link = NavbarLinkSelector.get_by_uuid(uuid)
        NavbarLinkCommands.delete(link)
        _invalidate_site_config_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# FOOTER CTA CONFIG (core)
# ---------------------------------------------------------------------------


class AdminFooterCTAViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/footer-cta/
    Singleton: texto y botones del bloque CTA final de la Home publica.
    """
    permission_classes = ADMIN_PERMISSIONS

    @extend_schema(summary="[Admin] Obtiene configuracion del CTA final")
    def list(self, request):
        from core.services.commands import FooterCTASelector
        from core.api.serializers import FooterCTAConfigSerializer
        cfg = FooterCTASelector.get_active()
        if not cfg:
            return Response({
                'uuid': None, 'eyebrow': 'Empieza hoy',
                'title_prefix': 'Impulsa tu empresa con',
                'title_highlighted': 'Sintel Technology',
                'subtitle': 'Soluciones tecnologicas, equipos y servicios profesionales en un solo lugar.',
                'btn_primary_label': 'Solicitar cotizacion', 'btn_primary_url': '/cotizar',
                'btn_ghost_label': 'Explorar catalogo', 'btn_ghost_url': '/tienda',
                'is_active': True, 'updated_at': None,
            })
        return Response(FooterCTAConfigSerializer(cfg).data)

    @extend_schema(summary="[Admin] Actualiza (upsert) configuracion del CTA final")
    @action(detail=False, methods=['post', 'patch'], url_path='update')
    def update_cta(self, request):
        from core.services.commands import FooterCTACommands
        from core.api.serializers import FooterCTAConfigInputSerializer, FooterCTAConfigSerializer
        s = FooterCTAConfigInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        cfg = FooterCTACommands.upsert(s.validated_data)
        _invalidate_home_feed_cache()
        return Response(FooterCTAConfigSerializer(cfg).data)


# ---------------------------------------------------------------------------
# BRAND SLIDER (core)
# ---------------------------------------------------------------------------

class AdminBrandSliderViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/brand-slider/
    Gestiona los logos y la configuracion del slider de marcas/clientes de la Home publica.
    """
    permission_classes = ADMIN_PERMISSIONS
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(summary="[Admin] Lista logos del slider de marcas")
    def list(self, request):
        from core.services.commands import BrandSliderSelector
        from core.api.serializers import BrandSliderItemSerializer
        qs = BrandSliderSelector.list_items_for_admin()
        return Response(BrandSliderItemSerializer(qs, many=True, context={'request': request}).data)

    @extend_schema(summary="[Admin] Crea logo del slider de marcas", request=None)
    @action(detail=False, methods=['post'], url_path='create')
    def create_item(self, request):
        from core.services.commands import BrandSliderCommands
        from core.api.serializers import BrandSliderItemInputSerializer, BrandSliderItemSerializer
        s = BrandSliderItemInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        item = BrandSliderCommands.create_item(
            name=d['name'],
            logo=d.get('logo'),
            website=d.get('website', ''),
            display_order=d.get('display_order', 0),
            is_active=d.get('is_active', True),
            open_new_tab=d.get('open_new_tab', True),
        )
        _invalidate_home_feed_cache()
        return Response(BrandSliderItemSerializer(item, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Actualiza logo del slider de marcas")
    @action(detail=False, methods=['patch'], url_path='(?P<uuid>[^/.]+)')
    def update_item(self, request, uuid=None):
        from core.services.commands import BrandSliderSelector
        from core.services.commands import BrandSliderCommands
        from core.api.serializers import BrandSliderItemInputSerializer, BrandSliderItemSerializer
        item = BrandSliderSelector.get_item_by_uuid(uuid)
        s = BrandSliderItemInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        item = BrandSliderCommands.update_item(item, s.validated_data)
        _invalidate_home_feed_cache()
        return Response(BrandSliderItemSerializer(item, context={'request': request}).data)

    @extend_schema(summary="[Admin] Elimina (soft) logo del slider de marcas")
    @action(detail=False, methods=['delete'], url_path='(?P<uuid>[^/.]+)/delete')
    def delete_item(self, request, uuid=None):
        from core.services.commands import BrandSliderSelector
        from core.services.commands import BrandSliderCommands
        item = BrandSliderSelector.get_item_by_uuid(uuid)
        BrandSliderCommands.delete_item(item)
        _invalidate_home_feed_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Reordena logos del slider de marcas (drag & drop)")
    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        from core.services.commands import BrandSliderCommands
        from core.api.serializers import BrandSliderReorderSerializer
        s = BrandSliderReorderSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        BrandSliderCommands.reorder_items(s.validated_data['items'])
        _invalidate_home_feed_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Obtiene configuracion del slider de marcas")
    @action(detail=False, methods=['get'], url_path='config')
    def get_config(self, request):
        from core.services.commands import BrandSliderSelector
        from core.api.serializers import BrandSliderConfigSerializer
        cfg = BrandSliderSelector.get_or_create_config()
        return Response(BrandSliderConfigSerializer(cfg).data)

    @extend_schema(summary="[Admin] Actualiza (upsert) configuracion del slider de marcas")
    @action(detail=False, methods=['post', 'patch'], url_path='config/update')
    def update_config(self, request):
        from core.services.commands import BrandSliderCommands
        from core.api.serializers import BrandSliderConfigInputSerializer, BrandSliderConfigSerializer
        s = BrandSliderConfigInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        cfg = BrandSliderCommands.upsert_config(s.validated_data)
        _invalidate_home_feed_cache()
        return Response(BrandSliderConfigSerializer(cfg).data)


class AdminAboutUsViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/about-us/
    Gestiona el contenido de la pagina publica 'Sobre Nosotros' (historia,
    mision, vision) y los valores institucionales.
    """
    permission_classes = ADMIN_PERMISSIONS
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    # ── Valores institucionales ────────────────────────────────────────────────

    @extend_schema(summary="[Admin] Lista valores institucionales")
    def list(self, request):
        from core.services.commands import AboutUsSelector
        from core.api.serializers import AboutUsValueSerializer
        qs = AboutUsSelector.list_values_for_admin()
        return Response(AboutUsValueSerializer(qs, many=True, context={'request': request}).data)

    @extend_schema(summary="[Admin] Crea valor institucional", request=None)
    @action(detail=False, methods=['post'], url_path='create')
    def create_value(self, request):
        from core.services.commands import AboutUsCommands
        from core.api.serializers import AboutUsValueInputSerializer, AboutUsValueSerializer
        s = AboutUsValueInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        value = AboutUsCommands.create_value(
            title=d['title'],
            description=d.get('description', ''),
            icon_class=d.get('icon_class', 'bi-gem'),
            display_order=d.get('display_order', 0),
            is_active=d.get('is_active', True),
        )
        _invalidate_about_us_cache()
        return Response(AboutUsValueSerializer(value, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Actualiza valor institucional")
    @action(detail=False, methods=['patch'], url_path='(?P<uuid>[^/.]+)')
    def update_value(self, request, uuid=None):
        from core.services.commands import AboutUsSelector, AboutUsCommands
        from core.api.serializers import AboutUsValueInputSerializer, AboutUsValueSerializer
        value = AboutUsSelector.get_value_by_uuid(uuid)
        s = AboutUsValueInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        value = AboutUsCommands.update_value(value, s.validated_data)
        _invalidate_about_us_cache()
        return Response(AboutUsValueSerializer(value, context={'request': request}).data)

    @extend_schema(summary="[Admin] Elimina (soft) valor institucional")
    @action(detail=False, methods=['delete'], url_path='(?P<uuid>[^/.]+)/delete')
    def delete_value(self, request, uuid=None):
        from core.services.commands import AboutUsSelector, AboutUsCommands
        value = AboutUsSelector.get_value_by_uuid(uuid)
        AboutUsCommands.delete_value(value)
        _invalidate_about_us_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Reordena valores institucionales (drag & drop)")
    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        from core.services.commands import AboutUsCommands
        from core.api.serializers import AboutUsValueReorderSerializer
        s = AboutUsValueReorderSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        AboutUsCommands.reorder_values(s.validated_data['items'])
        _invalidate_about_us_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── Configuracion (singleton) ───────────────────────────────────────────────

    @extend_schema(summary="[Admin] Obtiene configuracion de Sobre Nosotros")
    @action(detail=False, methods=['get'], url_path='config')
    def get_config(self, request):
        from core.services.commands import AboutUsSelector
        from core.api.serializers import AboutUsConfigSerializer
        cfg = AboutUsSelector.get_or_create_config()
        return Response(AboutUsConfigSerializer(cfg, context={'request': request}).data)

    @extend_schema(summary="[Admin] Actualiza (upsert) configuracion de Sobre Nosotros")
    @action(detail=False, methods=['post', 'patch'], url_path='config/update')
    def update_config(self, request):
        from core.services.commands import AboutUsCommands
        from core.api.serializers import AboutUsConfigInputSerializer, AboutUsConfigSerializer
        s = AboutUsConfigInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        cfg = AboutUsCommands.upsert_config(s.validated_data)
        _invalidate_about_us_cache()
        return Response(AboutUsConfigSerializer(cfg, context={'request': request}).data)


# ---------------------------------------------------------------------------
# SEO / METAETIQUETAS
# ---------------------------------------------------------------------------


class AdminSeoMetaTagViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/seo/meta-tags/
    Sistema empresarial de administracion de metaetiquetas del <head> del
    sitio publico (verificacion de dominio, analytics, pixels, SEO...).
    Renderizado real y unico en templates/spa_shell.html via
    seo.templatetags.seo_tags.render_meta_tags -- este ViewSet solo
    administra los datos, nunca construye HTML de produccion directamente.
    Toda la logica de negocio vive en seo.services (Selector/Commands).
    """
    permission_classes = ADMIN_PERMISSIONS
    pagination_class = DashboardResultsSetPagination
    lookup_field = 'uuid'

    @extend_schema(summary="[Admin] Lista metaetiquetas (filtros: provider, tag_type, environment, is_active, search)")
    def list(self, request):
        from seo.services.selectors import MetaTagSelector
        from seo.api.serializers import SiteMetaTagSerializer

        is_active_param = request.query_params.get('is_active')
        is_active = is_active_param.lower() in ('1', 'true') if is_active_param in ('true', 'false', '1', '0') else None

        qs = MetaTagSelector.list_for_admin({
            'provider': request.query_params.get('provider'),
            'tag_type': request.query_params.get('tag_type'),
            'environment': request.query_params.get('environment'),
            'is_active': is_active,
            'search': request.query_params.get('search'),
        })
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(SiteMetaTagSerializer(page, many=True).data)

    @extend_schema(summary="[Admin] Detalle de una metaetiqueta")
    def retrieve(self, request, uuid=None):
        from seo.services.selectors import MetaTagSelector
        from seo.api.serializers import SiteMetaTagSerializer
        tag = MetaTagSelector.get_by_uuid(uuid)
        return Response(SiteMetaTagSerializer(tag).data)

    @extend_schema(summary="[Admin] Crea una metaetiqueta", request=None)
    def create(self, request):
        from seo.services.commands import MetaTagCommands
        from seo.api.serializers import SiteMetaTagInputSerializer, SiteMetaTagSerializer
        s = SiteMetaTagInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        tag = MetaTagCommands.create(s.validated_data, request=request)
        return Response(SiteMetaTagSerializer(tag).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Actualiza una metaetiqueta")
    def partial_update(self, request, uuid=None):
        from seo.services.selectors import MetaTagSelector
        from seo.services.commands import MetaTagCommands
        from seo.api.serializers import SiteMetaTagInputSerializer, SiteMetaTagSerializer
        tag = MetaTagSelector.get_by_uuid(uuid)
        s = SiteMetaTagInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        tag = MetaTagCommands.update(tag, s.validated_data, request=request)
        return Response(SiteMetaTagSerializer(tag).data)

    @extend_schema(summary="[Admin] Elimina (soft) una metaetiqueta")
    def destroy(self, request, uuid=None):
        from seo.services.selectors import MetaTagSelector
        from seo.services.commands import MetaTagCommands
        tag = MetaTagSelector.get_by_uuid(uuid)
        MetaTagCommands.delete(tag, request=request)
        _log_admin_delete(request, 'SiteMetaTag', uuid)  # D-02
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Duplica una metaetiqueta (la copia nace inactiva)")
    @action(detail=True, methods=['post'])
    def duplicate(self, request, uuid=None):
        from seo.services.selectors import MetaTagSelector
        from seo.services.commands import MetaTagCommands
        from seo.api.serializers import SiteMetaTagSerializer
        tag = MetaTagSelector.get_by_uuid(uuid)
        copy = MetaTagCommands.duplicate(tag, request=request)
        return Response(SiteMetaTagSerializer(copy).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Activa/desactiva una metaetiqueta")
    @action(detail=True, methods=['post'])
    def toggle(self, request, uuid=None):
        from seo.services.selectors import MetaTagSelector
        from seo.services.commands import MetaTagCommands
        from seo.api.serializers import SiteMetaTagSerializer
        tag = MetaTagSelector.get_by_uuid(uuid)
        tag = MetaTagCommands.toggle_active(tag, request=request)
        return Response(SiteMetaTagSerializer(tag).data)

    @extend_schema(summary="[Admin] Reordena metaetiquetas por prioridad (drag & drop)")
    @action(detail=False, methods=['post'])
    def reorder(self, request):
        from seo.services.commands import MetaTagCommands
        from seo.api.serializers import SiteMetaTagReorderSerializer
        s = SiteMetaTagReorderSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        MetaTagCommands.reorder(s.validated_data['items'], request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Vista previa del HTML real que se renderiza en el <head>")
    @action(detail=True, methods=['get'])
    def preview(self, request, uuid=None):
        from seo.services.selectors import MetaTagSelector
        tag = MetaTagSelector.get_by_uuid(uuid)
        return Response({'html': tag.to_html()})

    @extend_schema(summary="[Admin] Exporta todas las metaetiquetas en JSON")
    @action(detail=False, methods=['get'])
    def export(self, request):
        from seo.services.commands import MetaTagCommands
        data = MetaTagCommands.export(request=request)
        return Response({'items': data})

    @extend_schema(summary="[Admin] Importa metaetiquetas desde JSON (cada item se valida/sanitiza igual que create)")
    @action(detail=False, methods=['post'], url_path='import')
    def import_tags(self, request):
        from seo.services.commands import MetaTagCommands
        from seo.api.serializers import SiteMetaTagImportSerializer, SiteMetaTagSerializer
        s = SiteMetaTagImportSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        created = [
            MetaTagCommands.create(item, request=request)
            for item in s.validated_data['items']
        ]
        MetaTagCommands.log_import(len(created), request=request)
        return Response(SiteMetaTagSerializer(created, many=True).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Historial de auditoria de una metaetiqueta")
    @action(detail=True, methods=['get'])
    def history(self, request, uuid=None):
        from seo.services.selectors import MetaTagSelector
        from seo.api.serializers import SeoMetaTagAuditLogSerializer
        tag = MetaTagSelector.get_by_uuid(uuid)
        entries = MetaTagSelector.list_history(tag)
        return Response(SeoMetaTagAuditLogSerializer(entries, many=True).data)


class AdminSiteVerificationFileViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/seo/verification-files/
    Archivos estaticos de verificacion servidos en la RAIZ del dominio
    (metodo "Subir archivo HTML", alternativo a la metaetiqueta) --
    servidos realmente por seo.views.serve_verification_file, registrado en
    ecommerce/urls.py ANTES del catch-all de la SPA.
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    @extend_schema(summary="[Admin] Lista archivos de verificacion")
    def list(self, request):
        from seo.services.selectors import VerificationFileSelector
        from seo.api.serializers import SiteVerificationFileSerializer
        qs = VerificationFileSelector.list_for_admin()
        return Response(SiteVerificationFileSerializer(qs, many=True).data)

    @extend_schema(summary="[Admin] Crea un archivo de verificacion", request=None)
    def create(self, request):
        from seo.services.commands import VerificationFileCommands
        from seo.api.serializers import SiteVerificationFileInputSerializer, SiteVerificationFileSerializer
        s = SiteVerificationFileInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        record = VerificationFileCommands.create(s.validated_data, request=request)
        return Response(SiteVerificationFileSerializer(record).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="[Admin] Actualiza un archivo de verificacion")
    def partial_update(self, request, uuid=None):
        from seo.services.selectors import VerificationFileSelector
        from seo.services.commands import VerificationFileCommands
        from seo.api.serializers import SiteVerificationFileInputSerializer, SiteVerificationFileSerializer
        record = VerificationFileSelector.get_by_uuid(uuid)
        s = SiteVerificationFileInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        record = VerificationFileCommands.update(record, s.validated_data, request=request)
        return Response(SiteVerificationFileSerializer(record).data)

    @extend_schema(summary="[Admin] Elimina (soft) un archivo de verificacion")
    def destroy(self, request, uuid=None):
        from seo.services.selectors import VerificationFileSelector
        from seo.services.commands import VerificationFileCommands
        record = VerificationFileSelector.get_by_uuid(uuid)
        VerificationFileCommands.delete(record, request=request)
        _log_admin_delete(request, 'SiteVerificationFile', uuid)  # D-02
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="[Admin] Activa/desactiva un archivo de verificacion")
    @action(detail=True, methods=['post'])
    def toggle(self, request, uuid=None):
        from seo.services.selectors import VerificationFileSelector
        from seo.services.commands import VerificationFileCommands
        from seo.api.serializers import SiteVerificationFileSerializer
        record = VerificationFileSelector.get_by_uuid(uuid)
        record = VerificationFileCommands.toggle_active(record, request=request)
        return Response(SiteVerificationFileSerializer(record).data)


# ---------------------------------------------------------------------------
# SUPPORT CHAT
# ---------------------------------------------------------------------------


class AdminSupportChatViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/support/chats/
    Panel de gestion de chats de soporte al cliente en tiempo real.
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    @extend_schema(summary="[Admin] Lista salas de chat activas")
    def list(self, request):
        rooms = SupportAdminOrchestrator.list_active_rooms()
        return Response(ChatRoomListSerializer(rooms, many=True).data)

    @extend_schema(summary="[Admin] Detalle de sala con historial completo")
    def retrieve(self, request, uuid=None):
        room = SupportAdminOrchestrator.get_room(uuid)
        SupportAdminOrchestrator.mark_read(room, request.user)
        return Response(ChatRoomSerializer(room).data)

    @extend_schema(summary="[Admin] Cierra sala de chat")
    @action(detail=True, methods=['post'], url_path='close')
    def close_room(self, request, uuid=None):
        room = SupportAdminOrchestrator.get_room(uuid)
        room = SupportAdminOrchestrator.close_room(room)
        return Response(ChatRoomSerializer(room).data)

    @extend_schema(summary="[Admin] Asigna esta sala (y su ticket, si existe) al admin que la solicita")
    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, uuid=None):
        room = SupportAdminOrchestrator.get_room(uuid)
        SupportAdminOrchestrator.assign_admin(room, request.user)
        # Re-fetch: el `ticket` de `room` viene de un select_related() cacheado ANTES
        # de la asignacion -- SupportTicketCommands.assign_ticket() escribe sobre una
        # instancia de ticket distinta (via SupportTicketSelector.get_by_chat_room),
        # asi que el cache en memoria de room.ticket queda stale si no se re-consulta.
        room = SupportAdminOrchestrator.get_room(uuid)
        return Response(ChatRoomSerializer(room).data)

    @extend_schema(summary="[Admin] Cambia el estado del SupportTicket de esta sala")
    @action(detail=True, methods=['post'], url_path='ticket-status')
    def set_ticket_status(self, request, uuid=None):
        room = SupportAdminOrchestrator.get_room(uuid)
        new_status = str(request.data.get('status', '')).strip()
        try:
            ticket = SupportAdminOrchestrator.set_ticket_status(room, new_status)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if ticket is None:
            return Response({'detail': 'Esta sala no tiene un ticket asociado.'}, status=status.HTTP_404_NOT_FOUND)
        room = SupportAdminOrchestrator.get_room(uuid)
        return Response(ChatRoomSerializer(room).data)

    @extend_schema(summary="[Admin] Cambia la prioridad del SupportTicket de esta sala")
    @action(detail=True, methods=['post'], url_path='ticket-priority')
    def set_ticket_priority(self, request, uuid=None):
        room = SupportAdminOrchestrator.get_room(uuid)
        new_priority = str(request.data.get('priority', '')).strip()
        try:
            ticket = SupportAdminOrchestrator.set_ticket_priority(room, new_priority)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if ticket is None:
            return Response({'detail': 'Esta sala no tiene un ticket asociado.'}, status=status.HTTP_404_NOT_FOUND)
        room = SupportAdminOrchestrator.get_room(uuid)
        return Response(ChatRoomSerializer(room).data)

    @extend_schema(summary="[Admin] Vincula esta sala a un pedido o alquiler (Customer Experience Hub)")
    @action(detail=True, methods=['post'], url_path='attach-context')
    def attach_context(self, request, uuid=None):
        context_type = str(request.data.get('context_type', '')).upper()
        order_uuid = request.data.get('order_uuid')
        rental_uuid = request.data.get('rental_uuid')
        if context_type not in ('ORDER', 'RENTAL'):
            return Response({'detail': 'context_type debe ser ORDER o RENTAL.'}, status=status.HTTP_400_BAD_REQUEST)
        room = SupportAdminOrchestrator.get_room(uuid)
        ctx = SupportAdminOrchestrator.attach_context(
            room, context_type, order_uuid=order_uuid, rental_uuid=rental_uuid, added_by=request.user,
        )
        if ctx is None:
            return Response({'detail': 'No se encontro el pedido/alquiler indicado.'}, status=status.HTTP_404_NOT_FOUND)
        room = SupportAdminOrchestrator.get_room(uuid)
        return Response(ChatRoomSerializer(room).data)

    @extend_schema(summary="[Admin] Vista Customer 360 de un cliente (perfil, KYC, pedidos, alquileres, timeline)")
    @action(detail=False, methods=['get'], url_path=r'customer360/(?P<user_uuid>[^/.]+)')
    def customer_360(self, request, user_uuid=None):
        data = SupportAdminOrchestrator.customer_360(user_uuid)
        return Response(data)

    @extend_schema(
        summary="[Admin] Analytics de conversaciones (Fase 9 AI Core -- Aprendizaje)",
        parameters=[OpenApiParameter('days', int, description='Ventana en dias (default 30, tope 365)')],
    )
    @action(detail=False, methods=['get'], url_path='analytics')
    def analytics(self, request):
        try:
            days = int(request.query_params.get('days', 30))
        except (TypeError, ValueError):
            days = 30
        days = max(1, min(days, 365))
        return Response(SupportAdminOrchestrator.get_analytics_summary(days=days))

    @extend_schema(
        summary="[Admin] Lista dedicada de tickets (filtros: status, priority, assigned_to_me)",
        parameters=[
            OpenApiParameter('status', str, required=False),
            OpenApiParameter('priority', str, required=False),
            OpenApiParameter('assigned_to_me', bool, required=False),
        ],
    )
    @action(detail=False, methods=['get'], url_path='tickets')
    def tickets(self, request):
        assigned_to_me = str(request.query_params.get('assigned_to_me', '')).lower() in ('1', 'true')
        tickets = SupportAdminOrchestrator.list_tickets(
            status=request.query_params.get('status') or None,
            priority=request.query_params.get('priority') or None,
            assigned_to_me=assigned_to_me,
            request_user=request.user,
        )
        return Response(SupportTicketSerializer(tickets, many=True).data)


class AdminSecurityViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/security-events/
    Centro de Seguridad -- tabla de eventos (login fallido, rate-limit, KYC
    bloqueado/rechazado, archivos rechazados) + health-check de DB/Redis/Celery.
    """
    permission_classes = ADMIN_PERMISSIONS
    pagination_class = DashboardResultsSetPagination

    @extend_schema(summary="[Admin] Lista eventos de seguridad (filtros: event_type, severity, user_uuid)")
    def list(self, request):
        events = SecurityAdminOrchestrator.list_events(
            event_type=request.query_params.get('event_type'),
            severity=request.query_params.get('severity'),
            user_uuid=request.query_params.get('user_uuid'),
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(events, request)
        return paginator.get_paginated_response(SecurityEventSerializer(page, many=True).data)

    @extend_schema(summary="[Admin] Estado de salud de DB/Redis/Celery")
    @action(detail=False, methods=['get'])
    def health(self, request):
        return Response(SecurityAdminOrchestrator.get_health())


class AdminNotificationTemplateViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/notification-templates/
    Edicion de plantillas de notificacion (subject/body/whatsapp/ws_event_type/is_active).
    El slug es de solo lectura -- es el contrato fijo con dispatch_notification().
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    @extend_schema(summary="[Admin] Lista todas las plantillas de notificacion")
    def list(self, request):
        templates = NotificationAdminOrchestrator.list_templates()
        return Response(NotificationTemplateSerializer(templates, many=True).data)

    @extend_schema(summary="[Admin] Edita una plantilla de notificacion")
    def partial_update(self, request, uuid=None):
        template = NotificationAdminOrchestrator.update_template(uuid, request.data)
        if template is None:
            return Response({'detail': 'Plantilla no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(NotificationTemplateSerializer(template).data)


class AdminNotificationLogViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/notification-logs/
    Auditoria de envios de notificacion, todos los usuarios (filtros: status, channel, template_slug, user_uuid).
    """
    permission_classes = ADMIN_PERMISSIONS
    pagination_class = DashboardResultsSetPagination

    @extend_schema(summary="[Admin] Lista logs de notificacion (filtros: status, channel, template_slug, user_uuid)")
    def list(self, request):
        logs = NotificationAdminOrchestrator.list_logs(
            status=request.query_params.get('status'),
            channel=request.query_params.get('channel'),
            template_slug=request.query_params.get('template_slug'),
            user_uuid=request.query_params.get('user_uuid'),
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(logs, request)
        return paginator.get_paginated_response(NotificationLogSerializer(page, many=True).data)


def _log_admin_delete(request, resource_type: str, resource_uuid) -> None:
    """D-02 (auditoria enterprise): extiende el audit trail administrativo
    mas alla de los 3 puntos que ya existian (feature flags, operations,
    ticket de IA). Generico para no duplicar un log_event() casi identico
    en cada destroy() -- se va adoptando incrementalmente en los ViewSets de
    mayor valor primero (Product, Equipment, TechnicalService, QuoteTemplate);
    el resto de los destroy() del BFF admin sigue el mismo patron de soft-
    delete + esta llamada cuando se extienda."""
    from security.models import SecurityEvent
    from security.services.commands import SecurityCommands
    SecurityCommands.log_event(
        SecurityEvent.ADMIN_RESOURCE_DELETED, request=request, user=request.user,
        severity=SecurityEvent.SEVERITY_WARNING,
        metadata={'resource_type': resource_type, 'resource_uuid': str(resource_uuid)},
    )


def _log_feature_flag_change(request, flag_name: str, previous_value: bool, new_value: bool):
    """ADR-001 Fase 8 (alertas operativas): togglear un kill-switch de pagos es
    una accion operativamente significativa -- queda auditada en
    /panel/seguridad, con quien/desde donde. Extraido a helper de modulo
    (plan hibrido Widget+API, auditoria 2026-07-22) porque ahora hay dos flags
    independientes que pueden cambiar en el mismo PATCH."""
    from security.models import SecurityEvent
    from security.services.commands import SecurityCommands
    SecurityCommands.log_event(
        SecurityEvent.PAYMENT_FEATURE_FLAG_CHANGED, request=request, user=request.user,
        severity=SecurityEvent.SEVERITY_WARNING,
        metadata={
            'flag': flag_name,
            'previous_value': previous_value,
            'new_value': new_value,
            'source': 'panel_admin',
        },
    )


class AdminPaymentViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/payment-transactions/
    Vista centralizada de transacciones de las 3 pasarelas (Wompi online,
    Nequi Push, COD) -- cada una con forma de datos distinta, por eso son
    3 listados separados en vez de un solo queryset unificado.
    """
    permission_classes = ADMIN_PERMISSIONS
    pagination_class = DashboardResultsSetPagination
    lookup_field = 'uuid'  # ADR-001 Fase 7: rutas detail (resync/events) por uuid, no pk

    @extend_schema(summary="[Admin] Lista transacciones Wompi (filtro: status)")
    def list(self, request):
        txs = PaymentAdminOrchestrator.list_wompi_transactions(status=request.query_params.get('status'))
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(txs, request)
        return paginator.get_paginated_response(TransactionSerializer(page, many=True).data)

    @extend_schema(summary="[Admin] Lista transacciones Nequi (filtro: status)")
    @action(detail=False, methods=['get'])
    def nequi(self, request):
        txs = PaymentAdminOrchestrator.list_nequi_transactions(status=request.query_params.get('status'))
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(txs, request)
        return paginator.get_paginated_response(NequiTransactionSerializer(page, many=True).data)

    @extend_schema(summary="[Admin] Lista transacciones COD (filtro: status)")
    @action(detail=False, methods=['get'])
    def cod(self, request):
        txs = PaymentAdminOrchestrator.list_cod_transactions(status=request.query_params.get('status'))
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(txs, request)
        return paginator.get_paginated_response(CodTransactionSerializer(page, many=True).data)

    @extend_schema(summary="[Admin] Reconsulta una transaccion Wompi PENDING contra la API real (ADR-001 Fase 7)")
    @action(detail=True, methods=['post'], url_path='resync')
    def resync(self, request, uuid=None):
        try:
            tx = PaymentAdminOrchestrator.resync_wompi_transaction(uuid)
        except Transaction.DoesNotExist:
            return Response({'detail': 'Transaccion no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        data = TransactionSerializer(tx).data
        if not tx.wompi_id:
            data['detail'] = (
                'Esta transaccion no tiene wompi_id todavia -- Wompi no ofrece '
                'busqueda por reference, no se puede reconciliar automaticamente.'
            )
            return Response(data, status=status.HTTP_409_CONFLICT)
        return Response(data)

    @extend_schema(summary="[Admin] Historial de eventos (webhook/sync/creacion) de una transaccion Wompi (ADR-001 Fase 7)")
    @action(detail=True, methods=['get'], url_path='events')
    def events(self, request, uuid=None):
        try:
            events = PaymentAdminOrchestrator.list_transaction_events(uuid)
        except Transaction.DoesNotExist:
            return Response({'detail': 'Transaccion no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(TransactionEventSerializer(events, many=True).data)

    @extend_schema(summary="[Admin] Consulta/actualiza los flags de pagos (ADR-001 Fase 5/7)")
    @action(detail=False, methods=['get', 'patch'], url_path='feature-flags')
    def feature_flags(self, request):
        def _parse_bool(raw):
            # bool('False') es True en Python -- si llega form-encoded (multipart,
            # el formato por defecto de APIClient/browsable API) el valor es un
            # string literal, no un bool real. Se interpreta explicitamente en
            # vez de confiar en bool(raw).
            if isinstance(raw, str):
                return raw.strip().lower() not in ('false', '0', 'no', '')
            return bool(raw)

        if request.method == 'PATCH':
            # Plan hibrido Widget+API (auditoria 2026-07-22): dos flags
            # independientes, cada PATCH puede traer uno u otro (o ambos).
            card_raw   = request.data.get('card_api_flow_enabled')
            widget_raw = request.data.get('widget_flow_enabled')
            if card_raw is None and widget_raw is None:
                return Response(
                    {'detail': 'card_api_flow_enabled o widget_flow_enabled es requerido.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            current = PaymentAdminOrchestrator.get_feature_flags()
            flags = current

            if card_raw is not None:
                enabled = _parse_bool(card_raw)
                previous_enabled = current.card_api_flow_enabled
                flags = PaymentAdminOrchestrator.set_card_api_flow_enabled(enabled)
                if enabled != previous_enabled:
                    _log_feature_flag_change(request, 'card_api_flow_enabled', previous_enabled, enabled)

            if widget_raw is not None:
                enabled = _parse_bool(widget_raw)
                previous_enabled = flags.widget_flow_enabled
                flags = PaymentAdminOrchestrator.set_widget_flow_enabled(enabled)
                if enabled != previous_enabled:
                    _log_feature_flag_change(request, 'widget_flow_enabled', previous_enabled, enabled)
        else:
            flags = PaymentAdminOrchestrator.get_feature_flags()
        return Response({
            'card_api_flow_enabled': flags.card_api_flow_enabled,
            'widget_flow_enabled': flags.widget_flow_enabled,
        })
