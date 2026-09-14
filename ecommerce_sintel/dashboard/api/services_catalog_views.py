"""
dashboard/api/services_catalog_views.py

ViewSets administrativos para el catalogo enriquecido de TechnicalService
(2026-08-05), espejo de dashboard/api/shop_catalog_views.py (shop.Product):
incluye/no incluye, requisitos, especificaciones, documentos, videos y pasos
del proceso. Un ViewSet por recurso (registrado aparte en dashboard/api/
urls.py), pero todos menos ServiceSpecification/ServiceDocument comparten el
mismo contrato REST via `ServiceCatalogChildViewSet` -- ver
`dashboard.services.admin_orchestrators.ServiceCatalogChildOrchestrator` para
el detalle de la delegacion (Zero ORM access en esta capa).

Contrato comun:
  GET    <recurso>/?service=<uuid>             lista los hijos del servicio
  POST   <recurso>/                            crea (body incluye 'service')
  PATCH  <recurso>/<uuid>/                     actualiza
  DELETE <recurso>/<uuid>/                     borrado logico (is_deleted)
  POST   <recurso>/<uuid>/toggle-active/       activa/desactiva
  POST   <recurso>/<uuid>/duplicate/           duplica (no aplica a videos/documentos/proceso)
  POST   <recurso>/reorder/                    reordena (body: service, ordered_uuids)
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from dashboard.api.catalog_child_views import GenericCatalogChildViewSet
from dashboard.services.admin_orchestrators import ServiceAdminOrchestrator, ServiceCatalogChildOrchestrator
from technical_services.api.serializers import (
    ServiceCatalogReorderInputSerializer,
    ServiceIncludedItemSerializer, ServiceIncludedItemInputSerializer,
    ServiceExcludedItemSerializer, ServiceExcludedItemInputSerializer,
    ServiceRequirementSerializer, ServiceRequirementInputSerializer,
    ServiceSpecificationGroupSerializer, ServiceSpecificationGroupInputSerializer,
    ServiceSpecificationSerializer, ServiceSpecificationInputSerializer,
    ServiceDocumentSerializer, ServiceDocumentInputSerializer,
    ServiceVideoSerializer, ServiceVideoInputSerializer,
    ServiceProcessStepSerializer, ServiceProcessStepInputSerializer,
)

class ServiceCatalogChildViewSet(GenericCatalogChildViewSet):
    """Base generica -- ver docstring del modulo."""
    orchestrator_class = ServiceCatalogChildOrchestrator
    parent_field = 'service'
    reorder_serializer_class = ServiceCatalogReorderInputSerializer

    def get_parent(self, parent_uuid):
        return ServiceAdminOrchestrator.get_service(parent_uuid)


class AdminServiceIncludedItemViewSet(ServiceCatalogChildViewSet):
    """/api/v1/dashboard/service-included-items/"""
    resource = 'included-items'
    output_serializer_class = ServiceIncludedItemSerializer
    input_serializer_class = ServiceIncludedItemInputSerializer


class AdminServiceExcludedItemViewSet(ServiceCatalogChildViewSet):
    """/api/v1/dashboard/service-excluded-items/"""
    resource = 'excluded-items'
    output_serializer_class = ServiceExcludedItemSerializer
    input_serializer_class = ServiceExcludedItemInputSerializer


class AdminServiceRequirementViewSet(ServiceCatalogChildViewSet):
    """/api/v1/dashboard/service-requirements/"""
    resource = 'requirements'
    output_serializer_class = ServiceRequirementSerializer
    input_serializer_class = ServiceRequirementInputSerializer


class AdminServiceSpecificationGroupViewSet(ServiceCatalogChildViewSet):
    """/api/v1/dashboard/service-specification-groups/"""
    resource = 'specification-groups'
    output_serializer_class = ServiceSpecificationGroupSerializer
    input_serializer_class = ServiceSpecificationGroupInputSerializer
    supports_duplicate = False


class AdminServiceVideoViewSet(ServiceCatalogChildViewSet):
    """/api/v1/dashboard/service-videos/ -- multipart (video_file/thumbnail)."""
    resource = 'videos'
    output_serializer_class = ServiceVideoSerializer
    input_serializer_class = ServiceVideoInputSerializer
    supports_duplicate = False
    parser_classes = [MultiPartParser, FormParser, JSONParser]


class AdminServiceProcessStepViewSet(ServiceCatalogChildViewSet):
    """/api/v1/dashboard/service-process-steps/ -- multipart (image)."""
    resource = 'process-steps'
    output_serializer_class = ServiceProcessStepSerializer
    input_serializer_class = ServiceProcessStepInputSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]


class AdminServiceSpecificationViewSet(ServiceCatalogChildViewSet):
    """
    /api/v1/dashboard/service-specifications/ -- fila de ficha tecnica. Cuelga
    de un ServiceSpecificationGroup ademas de service, asi que list/create/
    reorder estan sobreescritos (el registro generico no cubre el FK a group).
    """
    resource = None  # no usa el registro generico
    output_serializer_class = ServiceSpecificationSerializer
    input_serializer_class = ServiceSpecificationInputSerializer

    def list(self, request):
        group_uuid = request.query_params.get('group')
        service_uuid = request.query_params.get('service')
        if not group_uuid and not service_uuid:
            return Response(
                {'detail': 'Parametro group (uuid) o service (uuid) es requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = ServiceAdminOrchestrator.list_specifications(service_uuid=service_uuid, group_uuid=group_uuid)
        return Response(self._serialize(qs, many=True))

    def create(self, request):
        service_uuid = request.data.get('service')
        if not service_uuid:
            return Response({'detail': 'service es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        service = ServiceAdminOrchestrator.get_service(service_uuid)
        ser = self.input_serializer_class(data=request.data)
        ser.is_valid(raise_exception=True)
        instance = ServiceAdminOrchestrator.create_specification(service, ser.validated_data)
        return Response(self._serialize(instance), status=status.HTTP_201_CREATED)

    def partial_update(self, request, uuid=None):
        instance = ServiceAdminOrchestrator.get_specification(uuid)
        ser = self.input_serializer_class(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        data.pop('group', None)  # no se reasigna de grupo al editar
        updated = ServiceAdminOrchestrator.update_specification(instance, data)
        return Response(self._serialize(updated))

    def destroy(self, request, uuid=None):
        instance = ServiceAdminOrchestrator.get_specification(uuid)
        ServiceAdminOrchestrator.delete_specification(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='toggle-active')
    def toggle_active(self, request, uuid=None):
        instance = ServiceAdminOrchestrator.get_specification(uuid)
        updated = ServiceAdminOrchestrator.toggle_specification(instance)
        return Response(self._serialize(updated))

    @action(detail=True, methods=['post'], url_path='duplicate')
    def duplicate(self, request, uuid=None):
        instance = ServiceAdminOrchestrator.get_specification(uuid)
        copy = ServiceAdminOrchestrator.duplicate_specification(instance)
        return Response(self._serialize(copy), status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        group_uuid = request.data.get('group')
        if not group_uuid:
            return Response({'detail': 'group es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        from technical_services.services.catalog import ServiceSpecificationGroupSelector
        group = ServiceSpecificationGroupSelector.get_by_uuid(group_uuid)
        ser = ServiceCatalogReorderInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ServiceAdminOrchestrator.reorder_specifications(group.id, ser.validated_data['ordered_uuids'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminServiceDocumentViewSet(ServiceCatalogChildViewSet):
    """
    /api/v1/dashboard/service-documents/ -- documento descargable. create()
    esta sobreescrito: exige `file` (multipart) y pasa por
    ServiceDocumentCommands.create(), que valida extension/tamano/magic-bytes.
    """
    resource = 'documents'
    output_serializer_class = ServiceDocumentSerializer
    input_serializer_class = ServiceDocumentInputSerializer
    supports_duplicate = False
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def create(self, request):
        from rest_framework.exceptions import ValidationError as DRFValidationError

        service_uuid = request.data.get('service')
        if not service_uuid:
            return Response({'detail': 'service es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'detail': 'Se requiere el archivo file.'}, status=status.HTTP_400_BAD_REQUEST)
        service = ServiceAdminOrchestrator.get_service(service_uuid)
        ser = self.input_serializer_class(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            instance = ServiceAdminOrchestrator.create_document(service, {**ser.validated_data, 'file': file_obj})
        except (ValueError, DRFValidationError) as exc:
            detail = exc.detail[0] if isinstance(getattr(exc, 'detail', None), list) else str(exc)
            return Response({'detail': str(detail)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self._serialize(instance), status=status.HTTP_201_CREATED)
