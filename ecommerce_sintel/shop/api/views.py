from django.db import IntegrityError
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema

from shop.models import Product, ProductReview, Category, Brand, Tax, ProductVariant
from shop.services import (
    ProductSelector,
    ProductVariantSelector,
    CategorySelector,
    BrandSelector,
    TaxSelector,
    ProductReviewCommands,
)
from shop.api.serializers import (
    ProductSerializer,
    ProductVariantSerializer,
    CategorySerializer,
    BrandSerializer,
    TaxSerializer,
    ProductReviewSerializer,
)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


# ---------------------------------------------------------------------------
# Product  (READ-ONLY public + reviews para autenticados)
# ---------------------------------------------------------------------------

@extend_schema(tags=['shop'])
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Catalogo publico de productos.
    - list / retrieve: acceso libre (AllowAny).
    - review: solo usuarios autenticados.
    Las operaciones de escritura (create, update, destroy) se realizan
    exclusivamente a traves del BFF /api/v1/dashboard/.
    """
    lookup_field = 'uuid'
    serializer_class = ProductSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'slug', 'short_description', 'description']
    ordering_fields = ['created_at', 'name']
    filterset_fields = ['is_featured', 'category']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Product.objects.none()
        return ProductSelector.list_active()

    def get_object(self):
        return ProductSelector.get_by_uuid(self.kwargs[self.lookup_field])

    @extend_schema(summary='Listar resenas de un producto')
    @action(
        detail=True,
        methods=['get'],
        permission_classes=[permissions.AllowAny],
        url_path='reviews',
    )
    def reviews(self, request, uuid=None):
        product = self.get_object()
        qs = (
            ProductReview.objects
            .filter(product=product, is_deleted=False)
            .select_related('user')
            .order_by('-created_at')
        )
        return Response(ProductReviewSerializer(qs, many=True).data)

    @extend_schema(summary='Crear resena de producto')
    @action(
        detail=True,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated],
        url_path='review'
    )
    def review(self, request, uuid=None):
        product = self.get_object()
        serializer = ProductReviewSerializer(
            data=request.data,
            context={'request': request, 'product': product}
        )
        serializer.is_valid(raise_exception=True)
        try:
            ProductReviewCommands.create_review(
                user=request.user,
                product=product,
                rating=serializer.validated_data['rating'],
                comment=serializer.validated_data['comment']
            )
        except IntegrityError:
            # Condicion de carrera: dos envios simultaneos pasaron la validacion del
            # serializer antes de que cualquiera confirmara. La constraint unique_together
            # (user, product) en BD es quien realmente lo bloquea (agregada 2026-07-03).
            return Response(
                {"detail": "Ya has calificado este producto."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], permission_classes=(permissions.AllowAny,), url_path='detail')
    def full_detail(self, request, uuid=None):
        """GET /shop/products/{uuid}/detail/

        Retorna producto completo con toda la información pública.
        No rompe API existente (endpoint nuevo, aditivo).
        """
        product = self.get_object()
        serializer = ProductSerializer(product, context={'request': request})
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# ProductVariant  (READ-ONLY public — escritura via dashboard)
# ---------------------------------------------------------------------------

@extend_schema(tags=['shop'])
class ProductVariantViewSet(viewsets.ViewSet):
    """
    Listado publico de variantes de un producto.
    Requiere ?product=<uuid>.
    Escritura exclusiva via /api/v1/dashboard/equipment/ o dashboard/products/.
    """
    permission_classes = [permissions.AllowAny]
    lookup_field = 'uuid'

    def list(self, request):
        product_uuid = request.query_params.get('product')
        if not product_uuid:
            return Response(
                {'detail': 'Parametro product (uuid) es requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        variants = ProductVariantSelector.list_for_product(product_uuid)
        return Response(ProductVariantSerializer(variants, many=True).data)

    def retrieve(self, request, uuid=None):
        try:
            variant = ProductVariant.objects.get(uuid=uuid, is_deleted=False)
        except ProductVariant.DoesNotExist:
            return Response({'detail': 'No encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ProductVariantSerializer(variant).data)

    @extend_schema(summary='Desglose de precio con costos adicionales para una variante')
    @action(
        detail=True,
        methods=['get'],
        url_path='price-breakdown',
        permission_classes=[permissions.AllowAny],
    )
    def price_breakdown(self, request, uuid=None):
        """
        Retorna el desglose completo de precio aplicando el motor de costos adicionales.
        Query param: quantity (int, default 1).
        """
        try:
            variant = ProductVariant.objects.get(uuid=uuid, is_deleted=False)
        except ProductVariant.DoesNotExist:
            return Response({'detail': 'No encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            quantity = max(1, int(request.query_params.get('quantity', 1)))
        except (ValueError, TypeError):
            quantity = 1

        from shop.services.pricing import ShopPricingCalculator
        breakdown = ShopPricingCalculator.calculate_breakdown(variant, quantity)

        breakdown['base_price']       = str(breakdown['base_price'])
        breakdown['base_subtotal']    = str(breakdown['base_subtotal'])
        breakdown['total_additions']  = str(breakdown['total_additions'])
        breakdown['total_discounts']  = str(breakdown['total_discounts'])
        breakdown['final_price']      = str(breakdown['final_price'])
        for line in breakdown['costs']:
            line['value']  = str(line['value'])
            line['amount'] = str(line['amount'])

        return Response(breakdown)


# ---------------------------------------------------------------------------
# Category  (READ-ONLY public — escritura via dashboard)
# ---------------------------------------------------------------------------

@extend_schema(tags=['shop'])
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Listado publico de categorias.
    Escritura exclusiva via /api/v1/dashboard/shop-categories/.
    """
    serializer_class = CategorySerializer
    lookup_field = 'uuid'
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name']
    filterset_fields = ['is_active', 'parent']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Category.objects.none()
        return CategorySelector.list_all()

    def get_object(self):
        return CategorySelector.get_by_uuid(self.kwargs[self.lookup_field])


# ---------------------------------------------------------------------------
# Brand  (READ-ONLY public — escritura via dashboard)
# ---------------------------------------------------------------------------

@extend_schema(tags=['shop'])
class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Listado publico de marcas activas.
    Escritura exclusiva via /api/v1/dashboard/shop-brands/.
    """
    serializer_class = BrandSerializer
    lookup_field = 'uuid'
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.AllowAny]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Brand.objects.none()
        return BrandSelector.list_all()

    def get_object(self):
        return BrandSelector.get_by_uuid(self.kwargs[self.lookup_field])


# ---------------------------------------------------------------------------
# Tax  (READ-ONLY public — escritura via dashboard)
# ---------------------------------------------------------------------------

@extend_schema(tags=['shop'])
class TaxViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Listado publico de impuestos activos.
    Escritura exclusiva via /api/v1/dashboard/shop-taxes/.
    """
    serializer_class = TaxSerializer
    lookup_field = 'uuid'
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']
    filterset_fields = ['is_active', 'tax_type']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Tax.objects.none()
        return TaxSelector.list_active()

    def get_object(self):
        return TaxSelector.get_by_uuid(self.kwargs[self.lookup_field])
