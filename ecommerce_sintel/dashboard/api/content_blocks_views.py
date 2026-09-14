"""
dashboard/api/content_blocks_views.py

ViewSets administrativos para las pestanas "Contenido del Producto"/"Contenido
del Servicio" de ProductForm.vue/ServiceForm.vue. Construido en la Fase 3 de
la reingenieria PDP de Shop (DISENO_FASE2_SHOP_CONTENIDO_PDP_2026-08-05.md
SS4) y extendido en la reingenieria SDP de Technical Services (2026-08-05,
ver technical_services/.AGENT/docs/UI_MODULO_SERVICES.md) para un segundo
content_type -- ContentBlockConfig/CatalogRelation (shared/models.py,
shared/services/content_blocks.py) son genericos por diseno, la traduccion a
ContentType pasa en esta capa, no en el modelo/servicio, para que cada modulo
mantenga su propio contrato REST (`product=<uuid>` vs `service=<uuid>`).

Contrato Shop:
  GET  product-content-blocks/?product=<uuid>              lista los 15 bloques resueltos
  POST product-content-blocks/reorder/                     body: product, ordered_block_types
  POST product-content-blocks/set-visibility/               body: product, block_type, is_visible

  GET    product-relations/?product=<uuid>&relation_type=X  lista relaciones resueltas
  POST   product-relations/                                  body: product, relation_type, related_product
  DELETE product-relations/<uuid>/                           borrado logico
  POST   product-relations/reorder/                          body: product, relation_type, ordered_uuids

Contrato Technical Services (mismo shape, `service` en vez de `product`; las
relaciones aceptan un target de otro TechnicalService O de un shop.Product --
`related_entity_type` decide cual, ver AdminServiceRelationViewSet):
  GET  service-content-blocks/?service=<uuid>
  POST service-content-blocks/reorder/                      body: service, ordered_block_types
  POST service-content-blocks/set-visibility/                body: service, block_type, is_visible

  GET    service-relations/?service=<uuid>&relation_type=X
  POST   service-relations/                                   body: service, relation_type, related_entity_type ('service'|'product'), related_uuid
  DELETE service-relations/<uuid>/
  POST   service-relations/reorder/                           body: service, relation_type, ordered_uuids
"""
from django.contrib.contenttypes.models import ContentType
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from users.api.permissions import IsAdminUser
from dashboard.services.admin_orchestrators import ShopAdminOrchestrator, ServiceAdminOrchestrator
from shop.models import Product
from shop.api.serializers import ProductSerializer
from technical_services.models import TechnicalService
from technical_services.api.serializers import TechnicalServiceSerializer
from shared.models import ContentBlockConfig, CatalogRelation
from shared.services.content_blocks import (
    ContentBlockConfigSelector, ContentBlockConfigCommands,
    CatalogRelationSelector, CatalogRelationCommands,
)
from shared.serializers.content_blocks import (
    ContentBlockSerializer, ContentBlockOrderInputSerializer, ContentBlockVisibilityInputSerializer,
    CatalogRelationInputSerializer, CatalogRelationReorderInputSerializer,
)

ADMIN_PERMISSIONS = [IsAdminUser]


def _product_content_type():
    return ContentType.objects.get_for_model(Product)


def _service_content_type():
    return ContentType.objects.get_for_model(TechnicalService)


class AdminProductContentBlockViewSet(viewsets.ViewSet):
    """/api/v1/dashboard/product-content-blocks/"""
    permission_classes = ADMIN_PERMISSIONS

    def list(self, request):
        product_uuid = request.query_params.get('product')
        if not product_uuid:
            return Response({'detail': 'Parametro product (uuid) es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        product = ShopAdminOrchestrator.get_product(product_uuid)
        blocks = ContentBlockConfigSelector.resolve_for(_product_content_type(), product.uuid)
        return Response(ContentBlockSerializer(blocks, many=True).data)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        product_uuid = request.data.get('product')
        if not product_uuid:
            return Response({'detail': 'product es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        product = ShopAdminOrchestrator.get_product(product_uuid)
        ser = ContentBlockOrderInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ContentBlockConfigCommands.set_order(
            _product_content_type(), product.uuid, ser.validated_data['ordered_block_types'],
        )
        blocks = ContentBlockConfigSelector.resolve_for(_product_content_type(), product.uuid)
        return Response(ContentBlockSerializer(blocks, many=True).data)

    @action(detail=False, methods=['post'], url_path='set-visibility')
    def set_visibility(self, request):
        product_uuid = request.data.get('product')
        if not product_uuid:
            return Response({'detail': 'product es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        product = ShopAdminOrchestrator.get_product(product_uuid)
        ser = ContentBlockVisibilityInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ContentBlockConfigCommands.set_visibility(
            _product_content_type(), product.uuid,
            ser.validated_data['block_type'], ser.validated_data['is_visible'],
        )
        blocks = ContentBlockConfigSelector.resolve_for(_product_content_type(), product.uuid)
        return Response(ContentBlockSerializer(blocks, many=True).data)


class AdminProductRelationViewSet(viewsets.ViewSet):
    """/api/v1/dashboard/product-relations/"""
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def _serialize_relation(self, relation):
        model_class = relation.related_content_type.model_class()
        related_obj = model_class.objects.filter(uuid=relation.related_object_uuid, is_deleted=False).first()
        return {
            'uuid': str(relation.uuid),
            'relation_type': relation.relation_type,
            'display_order': relation.display_order,
            'product': ProductSerializer(related_obj, context={'request': self.request}).data if related_obj else None,
        }

    def list(self, request):
        product_uuid = request.query_params.get('product')
        if not product_uuid:
            return Response({'detail': 'Parametro product (uuid) es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        product = ShopAdminOrchestrator.get_product(product_uuid)
        relation_type = request.query_params.get('relation_type')
        relations = CatalogRelationSelector.list_for(_product_content_type(), product.uuid, relation_type)
        return Response([self._serialize_relation(rel) for rel in relations])

    def create(self, request):
        product_uuid = request.data.get('product')
        if not product_uuid:
            return Response({'detail': 'product es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        product = ShopAdminOrchestrator.get_product(product_uuid)
        ser = CatalogRelationInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        related_product = ser.validated_data['related_product']
        if related_product.id == product.id:
            return Response({'detail': 'Un producto no puede relacionarse consigo mismo.'}, status=status.HTTP_400_BAD_REQUEST)
        content_type = _product_content_type()
        relation = CatalogRelationCommands.add(
            content_type=content_type, object_uuid=product.uuid,
            related_content_type=content_type, related_object_uuid=related_product.uuid,
            relation_type=ser.validated_data['relation_type'],
        )
        return Response(self._serialize_relation(relation), status=status.HTTP_201_CREATED)

    def destroy(self, request, uuid=None):
        relation = CatalogRelationSelector.get_by_uuid(uuid)
        CatalogRelationCommands.remove(relation)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        product_uuid = request.data.get('product')
        if not product_uuid:
            return Response({'detail': 'product es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        product = ShopAdminOrchestrator.get_product(product_uuid)
        ser = CatalogRelationReorderInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        CatalogRelationCommands.reorder(
            _product_content_type(), product.uuid,
            ser.validated_data['relation_type'], ser.validated_data['ordered_uuids'],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminServiceContentBlockViewSet(viewsets.ViewSet):
    """/api/v1/dashboard/service-content-blocks/ -- mismo contrato que
    AdminProductContentBlockViewSet, content_type=TechnicalService y orden
    por defecto propio (ContentBlockConfig.SERVICE_DEFAULT_ORDER, 18 bloques
    en vez de los 15 de Shop)."""
    permission_classes = ADMIN_PERMISSIONS

    def list(self, request):
        service_uuid = request.query_params.get('service')
        if not service_uuid:
            return Response({'detail': 'Parametro service (uuid) es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        service = ServiceAdminOrchestrator.get_service(service_uuid)
        blocks = ContentBlockConfigSelector.resolve_for(_service_content_type(), service.uuid, ContentBlockConfig.SERVICE_DEFAULT_ORDER)
        return Response(ContentBlockSerializer(blocks, many=True).data)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        service_uuid = request.data.get('service')
        if not service_uuid:
            return Response({'detail': 'service es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        service = ServiceAdminOrchestrator.get_service(service_uuid)
        ser = ContentBlockOrderInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ContentBlockConfigCommands.set_order(
            _service_content_type(), service.uuid, ser.validated_data['ordered_block_types'],
        )
        blocks = ContentBlockConfigSelector.resolve_for(_service_content_type(), service.uuid, ContentBlockConfig.SERVICE_DEFAULT_ORDER)
        return Response(ContentBlockSerializer(blocks, many=True).data)

    @action(detail=False, methods=['post'], url_path='set-visibility')
    def set_visibility(self, request):
        service_uuid = request.data.get('service')
        if not service_uuid:
            return Response({'detail': 'service es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        service = ServiceAdminOrchestrator.get_service(service_uuid)
        ser = ContentBlockVisibilityInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ContentBlockConfigCommands.set_visibility(
            _service_content_type(), service.uuid,
            ser.validated_data['block_type'], ser.validated_data['is_visible'],
            ContentBlockConfig.SERVICE_DEFAULT_ORDER,
        )
        blocks = ContentBlockConfigSelector.resolve_for(_service_content_type(), service.uuid, ContentBlockConfig.SERVICE_DEFAULT_ORDER)
        return Response(ContentBlockSerializer(blocks, many=True).data)


class AdminServiceRelationViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/service-relations/ -- mismo contrato que
    AdminProductRelationViewSet, pero el target de la relacion puede ser OTRO
    TechnicalService (bloques "compatible"/"related") o un shop.Product
    (bloque "recommended_products", Fase 21 del brief SDP: "consumir Shop sin
    romper el desacoplamiento" -- este endpoint es la unica pieza que sabe de
    ambos modulos a la vez, ni el modelo ni el service layer lo saben).
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def _serialize_relation(self, relation):
        model_class = relation.related_content_type.model_class()
        related_obj = model_class.objects.filter(uuid=relation.related_object_uuid, is_deleted=False).first()
        is_product = relation.related_content_type_id == ContentType.objects.get_for_model(Product).id
        serializer_class = ProductSerializer if is_product else TechnicalServiceSerializer
        return {
            'uuid': str(relation.uuid),
            'relation_type': relation.relation_type,
            'display_order': relation.display_order,
            'related_entity_type': 'product' if is_product else 'service',
            'entity': serializer_class(related_obj, context={'request': self.request}).data if related_obj else None,
        }

    def list(self, request):
        service_uuid = request.query_params.get('service')
        if not service_uuid:
            return Response({'detail': 'Parametro service (uuid) es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        service = ServiceAdminOrchestrator.get_service(service_uuid)
        relation_type = request.query_params.get('relation_type')
        relations = CatalogRelationSelector.list_for(_service_content_type(), service.uuid, relation_type)
        return Response([self._serialize_relation(rel) for rel in relations])

    def create(self, request):
        service_uuid = request.data.get('service')
        related_entity_type = request.data.get('related_entity_type')
        related_uuid = request.data.get('related_uuid')
        relation_type = request.data.get('relation_type')
        if not service_uuid:
            return Response({'detail': 'service es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        if related_entity_type not in ('service', 'product'):
            return Response({'detail': "related_entity_type debe ser 'service' o 'product'."}, status=status.HTTP_400_BAD_REQUEST)
        if not related_uuid or not relation_type:
            return Response({'detail': 'related_uuid y relation_type son requeridos.'}, status=status.HTTP_400_BAD_REQUEST)
        if relation_type not in dict(CatalogRelation.RELATION_TYPE_CHOICES):
            return Response({'detail': 'relation_type invalido.'}, status=status.HTTP_400_BAD_REQUEST)

        service = ServiceAdminOrchestrator.get_service(service_uuid)

        if related_entity_type == 'service':
            related_obj = TechnicalService.objects.filter(uuid=related_uuid, is_deleted=False).first()
            related_content_type = _service_content_type()
            if related_obj and related_obj.id == service.id:
                return Response({'detail': 'Un servicio no puede relacionarse consigo mismo.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            related_obj = Product.objects.filter(uuid=related_uuid, is_deleted=False).first()
            related_content_type = _product_content_type()

        if not related_obj:
            return Response({'detail': 'No se encontro la entidad relacionada.'}, status=status.HTTP_404_NOT_FOUND)

        relation = CatalogRelationCommands.add(
            content_type=_service_content_type(), object_uuid=service.uuid,
            related_content_type=related_content_type, related_object_uuid=related_obj.uuid,
            relation_type=relation_type,
        )
        return Response(self._serialize_relation(relation), status=status.HTTP_201_CREATED)

    def destroy(self, request, uuid=None):
        relation = CatalogRelationSelector.get_by_uuid(uuid)
        CatalogRelationCommands.remove(relation)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        service_uuid = request.data.get('service')
        if not service_uuid:
            return Response({'detail': 'service es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        service = ServiceAdminOrchestrator.get_service(service_uuid)
        ser = CatalogRelationReorderInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        CatalogRelationCommands.reorder(
            _service_content_type(), service.uuid,
            ser.validated_data['relation_type'], ser.validated_data['ordered_uuids'],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
