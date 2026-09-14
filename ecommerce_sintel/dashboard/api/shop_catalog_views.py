"""
dashboard/api/shop_catalog_views.py

ViewSets administrativos para el catalogo enriquecido de Product (2026-08-03),
espejo de dashboard/api/renting_catalog_views.py (renting.Equipment): galeria con
tipo, incluye/no incluye, caracteristicas, especificaciones, requisitos, servicios
(incluidos/opcionales), FAQ, videos y documentos. Un ViewSet por recurso
(registrado aparte en dashboard/api/urls.py), pero todos menos ProductSpecification/
ProductDocument comparten el mismo contrato REST via `ProductCatalogChildViewSet` --
ver `dashboard.services.admin_orchestrators.ProductCatalogChildOrchestrator` para el
detalle de la delegacion (Zero ORM access en esta capa).

Contrato comun:
  GET    <recurso>/?product=<uuid>             lista los hijos del producto
  POST   <recurso>/                            crea (body incluye 'product')
  PATCH  <recurso>/<uuid>/                     actualiza
  DELETE <recurso>/<uuid>/                     borrado logico (is_deleted)
  POST   <recurso>/<uuid>/toggle-active/       activa/desactiva
  POST   <recurso>/<uuid>/duplicate/           duplica (no aplica a imagenes/videos/documentos)
  POST   <recurso>/reorder/                    reordena (body: product, ordered_uuids)
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from dashboard.api.catalog_child_views import GenericCatalogChildViewSet
from dashboard.services.admin_orchestrators import ShopAdminOrchestrator, ProductCatalogChildOrchestrator
from shop.services.catalog import ProductImageCommands
from shop.api.serializers import (
    ProductCatalogReorderInputSerializer,
    ProductImageSerializer, ProductImageInputSerializer,
    ProductIncludedItemSerializer, ProductIncludedItemInputSerializer,
    ProductExcludedItemSerializer, ProductExcludedItemInputSerializer,
    ProductFeatureSerializer, ProductFeatureInputSerializer,
    ProductSpecificationGroupSerializer, ProductSpecificationGroupInputSerializer,
    ProductSpecificationSerializer, ProductSpecificationInputSerializer,
    ProductRequirementSerializer, ProductRequirementInputSerializer,
    ProductServiceIncludedSerializer, ProductServiceIncludedInputSerializer,
    ProductOptionalServiceSerializer, ProductOptionalServiceInputSerializer,
    ProductFAQSerializer, ProductFAQInputSerializer,
    ProductVideoSerializer, ProductVideoInputSerializer,
    ProductDocumentSerializer, ProductDocumentInputSerializer,
    ProductFunctioningStepSerializer, ProductFunctioningStepInputSerializer,
)

class ProductCatalogChildViewSet(GenericCatalogChildViewSet):
    """Base generica -- ver docstring del modulo."""
    orchestrator_class = ProductCatalogChildOrchestrator
    parent_field = 'product'
    reorder_serializer_class = ProductCatalogReorderInputSerializer

    def get_parent(self, parent_uuid):
        return ShopAdminOrchestrator.get_product(parent_uuid)


class AdminProductIncludedItemViewSet(ProductCatalogChildViewSet):
    """/api/v1/dashboard/product-included-items/"""
    resource = 'included-items'
    output_serializer_class = ProductIncludedItemSerializer
    input_serializer_class = ProductIncludedItemInputSerializer


class AdminProductExcludedItemViewSet(ProductCatalogChildViewSet):
    """/api/v1/dashboard/product-excluded-items/"""
    resource = 'excluded-items'
    output_serializer_class = ProductExcludedItemSerializer
    input_serializer_class = ProductExcludedItemInputSerializer


class AdminProductFeatureViewSet(ProductCatalogChildViewSet):
    """/api/v1/dashboard/product-features/"""
    resource = 'features'
    output_serializer_class = ProductFeatureSerializer
    input_serializer_class = ProductFeatureInputSerializer


class AdminProductSpecificationGroupViewSet(ProductCatalogChildViewSet):
    """/api/v1/dashboard/product-specification-groups/"""
    resource = 'specification-groups'
    output_serializer_class = ProductSpecificationGroupSerializer
    input_serializer_class = ProductSpecificationGroupInputSerializer
    supports_duplicate = False


class AdminProductRequirementViewSet(ProductCatalogChildViewSet):
    """/api/v1/dashboard/product-requirements/"""
    resource = 'requirements'
    output_serializer_class = ProductRequirementSerializer
    input_serializer_class = ProductRequirementInputSerializer


class AdminProductServiceIncludedViewSet(ProductCatalogChildViewSet):
    """/api/v1/dashboard/product-services-included/"""
    resource = 'services-included'
    output_serializer_class = ProductServiceIncludedSerializer
    input_serializer_class = ProductServiceIncludedInputSerializer


class AdminProductOptionalServiceViewSet(ProductCatalogChildViewSet):
    """/api/v1/dashboard/product-optional-services/"""
    resource = 'optional-services'
    output_serializer_class = ProductOptionalServiceSerializer
    input_serializer_class = ProductOptionalServiceInputSerializer


class AdminProductFAQViewSet(ProductCatalogChildViewSet):
    """/api/v1/dashboard/product-faqs/"""
    resource = 'faqs'
    output_serializer_class = ProductFAQSerializer
    input_serializer_class = ProductFAQInputSerializer


class AdminProductVideoViewSet(ProductCatalogChildViewSet):
    """/api/v1/dashboard/product-videos/ -- multipart (video_file/thumbnail)."""
    resource = 'videos'
    output_serializer_class = ProductVideoSerializer
    input_serializer_class = ProductVideoInputSerializer
    supports_duplicate = False
    parser_classes = [MultiPartParser, FormParser, JSONParser]


class AdminProductImageViewSet(ProductCatalogChildViewSet):
    """
    /api/v1/dashboard/product-catalog-images/ -- galeria con tipo. Multipart, y
    create() esta sobreescrito porque `image` llega por request.FILES (no por
    el input serializer, igual que el resto de uploads del proyecto).

    Distinto endpoint del `ProductImageViewSet` de escritura simple ya existente
    en dashboard (si aplica) -- este expone el contrato generico completo
    (toggle-active/reorder/set-primary) para la galeria tipada nueva.
    """
    resource = 'images'
    output_serializer_class = ProductImageSerializer
    input_serializer_class = ProductImageInputSerializer
    supports_duplicate = False
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def create(self, request):
        product_uuid = request.data.get('product')
        if not product_uuid:
            return Response({'detail': 'product es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        image_file = request.FILES.get('image')
        if not image_file:
            return Response({'detail': 'Se requiere el archivo image.'}, status=status.HTTP_400_BAD_REQUEST)
        product = ShopAdminOrchestrator.get_product(product_uuid)
        ser = self.input_serializer_class(data=request.data)
        ser.is_valid(raise_exception=True)
        instance = ProductImageCommands.create(product, image=image_file, **ser.validated_data)
        return Response(self._serialize(instance), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='set-primary')
    def set_primary(self, request, uuid=None):
        instance = ProductCatalogChildOrchestrator.get(self.resource, uuid)
        updated = ProductImageCommands.set_primary(instance)
        return Response(self._serialize(updated))


class AdminProductFunctioningStepViewSet(ProductCatalogChildViewSet):
    """/api/v1/dashboard/product-functioning-steps/ -- multipart (image), mirror de AdminServiceProcessStepViewSet."""
    resource = 'functioning-steps'
    output_serializer_class = ProductFunctioningStepSerializer
    input_serializer_class = ProductFunctioningStepInputSerializer
    supports_duplicate = False
    parser_classes = [MultiPartParser, FormParser, JSONParser]


class AdminProductSpecificationViewSet(ProductCatalogChildViewSet):
    """
    /api/v1/dashboard/product-specifications/ -- fila de ficha tecnica. Cuelga
    de un ProductSpecificationGroup ademas de product, asi que list/create/
    reorder estan sobreescritos (el registro generico no cubre el FK a group).
    """
    resource = None  # no usa el registro generico
    output_serializer_class = ProductSpecificationSerializer
    input_serializer_class = ProductSpecificationInputSerializer

    def list(self, request):
        group_uuid = request.query_params.get('group')
        product_uuid = request.query_params.get('product')
        if not group_uuid and not product_uuid:
            return Response(
                {'detail': 'Parametro group (uuid) o product (uuid) es requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = ShopAdminOrchestrator.list_specifications(product_uuid=product_uuid, group_uuid=group_uuid)
        return Response(self._serialize(qs, many=True))

    def create(self, request):
        product_uuid = request.data.get('product')
        if not product_uuid:
            return Response({'detail': 'product es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        product = ShopAdminOrchestrator.get_product(product_uuid)
        ser = self.input_serializer_class(data=request.data)
        ser.is_valid(raise_exception=True)
        instance = ShopAdminOrchestrator.create_specification(product, ser.validated_data)
        return Response(self._serialize(instance), status=status.HTTP_201_CREATED)

    def partial_update(self, request, uuid=None):
        instance = ShopAdminOrchestrator.get_specification(uuid)
        ser = self.input_serializer_class(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        data.pop('group', None)  # no se reasigna de grupo al editar
        updated = ShopAdminOrchestrator.update_specification(instance, data)
        return Response(self._serialize(updated))

    def destroy(self, request, uuid=None):
        instance = ShopAdminOrchestrator.get_specification(uuid)
        ShopAdminOrchestrator.delete_specification(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='toggle-active')
    def toggle_active(self, request, uuid=None):
        instance = ShopAdminOrchestrator.get_specification(uuid)
        updated = ShopAdminOrchestrator.toggle_specification(instance)
        return Response(self._serialize(updated))

    @action(detail=True, methods=['post'], url_path='duplicate')
    def duplicate(self, request, uuid=None):
        instance = ShopAdminOrchestrator.get_specification(uuid)
        copy = ShopAdminOrchestrator.duplicate_specification(instance)
        return Response(self._serialize(copy), status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        group_uuid = request.data.get('group')
        if not group_uuid:
            return Response({'detail': 'group es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        from shop.services.catalog import ProductSpecificationGroupSelector
        group = ProductSpecificationGroupSelector.get_by_uuid(group_uuid)
        ser = ProductCatalogReorderInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ShopAdminOrchestrator.reorder_specifications(group.id, ser.validated_data['ordered_uuids'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminProductDocumentViewSet(ProductCatalogChildViewSet):
    """
    /api/v1/dashboard/product-documents/ -- documento descargable. create()
    esta sobreescrito: exige `file` (multipart) y pasa por
    ProductDocumentCommands.create(), que valida extension/tamano/magic-bytes.
    """
    resource = 'documents'
    output_serializer_class = ProductDocumentSerializer
    input_serializer_class = ProductDocumentInputSerializer
    supports_duplicate = False
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def create(self, request):
        from rest_framework.exceptions import ValidationError as DRFValidationError

        product_uuid = request.data.get('product')
        if not product_uuid:
            return Response({'detail': 'product es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'detail': 'Se requiere el archivo file.'}, status=status.HTTP_400_BAD_REQUEST)
        product = ShopAdminOrchestrator.get_product(product_uuid)
        ser = self.input_serializer_class(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            instance = ShopAdminOrchestrator.create_document(product, {**ser.validated_data, 'file': file_obj})
        except (ValueError, DRFValidationError) as exc:
            detail = exc.detail[0] if isinstance(getattr(exc, 'detail', None), list) else str(exc)
            return Response({'detail': str(detail)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self._serialize(instance), status=status.HTTP_201_CREATED)
