"""
dashboard/api/renting_catalog_views.py

ViewSets administrativos para el catalogo enriquecido de Equipment
(2026-07-16): galeria avanzada, incluye/no incluye, caracteristicas,
especificaciones, requisitos, servicios (incluidos/opcionales), FAQ, videos y
documentos. Un ViewSet por recurso (registrado aparte en dashboard/api/urls.py),
pero todos menos RentalSpecification/RentalDocument comparten el mismo
contrato REST via `EquipmentCatalogChildViewSet` -- ver
`dashboard.services.admin_orchestrators.RentingCatalogChildOrchestrator` para
el detalle de la delegacion (Zero ORM access en esta capa).

Contrato comun:
  GET    <recurso>/?equipment=<uuid>          lista los hijos del equipo
  POST   <recurso>/                            crea (body incluye 'equipment')
  PATCH  <recurso>/<uuid>/                     actualiza
  DELETE <recurso>/<uuid>/                     borrado logico (is_deleted)
  POST   <recurso>/<uuid>/toggle-active/       activa/desactiva
  POST   <recurso>/<uuid>/duplicate/           duplica (no aplica a imagenes/videos/documentos)
  POST   <recurso>/reorder/                    reordena (body: equipment, ordered_uuids)
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from dashboard.api.catalog_child_views import GenericCatalogChildViewSet
from dashboard.services.admin_orchestrators import RentingAdminOrchestrator, RentingCatalogChildOrchestrator
from renting.services import EquipmentImageCommands
from renting.api.serializers import (
    ReorderInputSerializer,
    EquipmentImageSerializer, EquipmentImageInputSerializer,
    RentalIncludedItemSerializer, RentalIncludedItemInputSerializer,
    RentalExcludedItemSerializer, RentalExcludedItemInputSerializer,
    RentalFeatureSerializer, RentalFeatureInputSerializer,
    RentalSpecificationGroupSerializer, RentalSpecificationGroupInputSerializer,
    RentalSpecificationSerializer, RentalSpecificationInputSerializer,
    RentalRequirementSerializer, RentalRequirementInputSerializer,
    RentalServiceIncludedSerializer, RentalServiceIncludedInputSerializer,
    RentalOptionalServiceSerializer, RentalOptionalServiceInputSerializer,
    RentalFAQSerializer, RentalFAQInputSerializer,
    RentalVideoSerializer, RentalVideoInputSerializer,
    RentalDocumentSerializer, RentalDocumentInputSerializer,
)

class EquipmentCatalogChildViewSet(GenericCatalogChildViewSet):
    """Base generica -- ver docstring del modulo."""
    orchestrator_class = RentingCatalogChildOrchestrator
    parent_field = 'equipment'
    reorder_serializer_class = ReorderInputSerializer

    def get_parent(self, parent_uuid):
        return RentingAdminOrchestrator.get_equipment(parent_uuid)


class AdminRentalIncludedItemViewSet(EquipmentCatalogChildViewSet):
    """/api/v1/dashboard/rental-included-items/"""
    resource = 'included-items'
    output_serializer_class = RentalIncludedItemSerializer
    input_serializer_class = RentalIncludedItemInputSerializer


class AdminRentalExcludedItemViewSet(EquipmentCatalogChildViewSet):
    """/api/v1/dashboard/rental-excluded-items/"""
    resource = 'excluded-items'
    output_serializer_class = RentalExcludedItemSerializer
    input_serializer_class = RentalExcludedItemInputSerializer


class AdminRentalFeatureViewSet(EquipmentCatalogChildViewSet):
    """/api/v1/dashboard/rental-features/"""
    resource = 'features'
    output_serializer_class = RentalFeatureSerializer
    input_serializer_class = RentalFeatureInputSerializer


class AdminRentalSpecificationGroupViewSet(EquipmentCatalogChildViewSet):
    """/api/v1/dashboard/rental-specification-groups/"""
    resource = 'specification-groups'
    output_serializer_class = RentalSpecificationGroupSerializer
    input_serializer_class = RentalSpecificationGroupInputSerializer
    supports_duplicate = False


class AdminRentalRequirementViewSet(EquipmentCatalogChildViewSet):
    """/api/v1/dashboard/rental-requirements/"""
    resource = 'requirements'
    output_serializer_class = RentalRequirementSerializer
    input_serializer_class = RentalRequirementInputSerializer


class AdminRentalServiceIncludedViewSet(EquipmentCatalogChildViewSet):
    """/api/v1/dashboard/rental-services-included/"""
    resource = 'services-included'
    output_serializer_class = RentalServiceIncludedSerializer
    input_serializer_class = RentalServiceIncludedInputSerializer


class AdminRentalOptionalServiceViewSet(EquipmentCatalogChildViewSet):
    """/api/v1/dashboard/rental-optional-services/"""
    resource = 'optional-services'
    output_serializer_class = RentalOptionalServiceSerializer
    input_serializer_class = RentalOptionalServiceInputSerializer


class AdminRentalFAQViewSet(EquipmentCatalogChildViewSet):
    """/api/v1/dashboard/rental-faqs/"""
    resource = 'faqs'
    output_serializer_class = RentalFAQSerializer
    input_serializer_class = RentalFAQInputSerializer


class AdminRentalVideoViewSet(EquipmentCatalogChildViewSet):
    """/api/v1/dashboard/rental-videos/ -- multipart (video_file/thumbnail)."""
    resource = 'videos'
    output_serializer_class = RentalVideoSerializer
    input_serializer_class = RentalVideoInputSerializer
    supports_duplicate = False
    parser_classes = [MultiPartParser, FormParser, JSONParser]


class AdminEquipmentImageViewSet(EquipmentCatalogChildViewSet):
    """
    /api/v1/dashboard/equipment-images/ -- galeria avanzada. Multipart, y
    create() esta sobreescrito porque `image` llega por request.FILES (no por
    el input serializer, igual que el resto de uploads del proyecto).
    """
    resource = 'images'
    output_serializer_class = EquipmentImageSerializer
    input_serializer_class = EquipmentImageInputSerializer
    supports_duplicate = False
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def create(self, request):
        equipment_uuid = request.data.get('equipment')
        if not equipment_uuid:
            return Response({'detail': 'equipment es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        image_file = request.FILES.get('image')
        if not image_file:
            return Response({'detail': 'Se requiere el archivo image.'}, status=status.HTTP_400_BAD_REQUEST)
        equipment = RentingAdminOrchestrator.get_equipment(equipment_uuid)
        ser = self.input_serializer_class(data=request.data)
        ser.is_valid(raise_exception=True)
        instance = EquipmentImageCommands.create(equipment, image=image_file, **ser.validated_data)
        return Response(self._serialize(instance), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='set-primary')
    def set_primary(self, request, uuid=None):
        instance = RentingCatalogChildOrchestrator.get(self.resource, uuid)
        updated = EquipmentImageCommands.set_primary(instance)
        return Response(self._serialize(updated))


class AdminRentalSpecificationViewSet(EquipmentCatalogChildViewSet):
    """
    /api/v1/dashboard/rental-specifications/ -- fila de ficha tecnica. Cuelga
    de un RentalSpecificationGroup ademas de equipment, asi que list/create/
    reorder estan sobreescritos (el registro generico no cubre el FK a group).
    """
    resource = None  # no usa el registro generico
    output_serializer_class = RentalSpecificationSerializer
    input_serializer_class = RentalSpecificationInputSerializer

    def list(self, request):
        group_uuid = request.query_params.get('group')
        equipment_uuid = request.query_params.get('equipment')
        if not group_uuid and not equipment_uuid:
            return Response(
                {'detail': 'Parametro group (uuid) o equipment (uuid) es requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = RentingAdminOrchestrator.list_specifications(equipment_uuid=equipment_uuid, group_uuid=group_uuid)
        return Response(self._serialize(qs, many=True))

    def create(self, request):
        equipment_uuid = request.data.get('equipment')
        if not equipment_uuid:
            return Response({'detail': 'equipment es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        equipment = RentingAdminOrchestrator.get_equipment(equipment_uuid)
        ser = self.input_serializer_class(data=request.data)
        ser.is_valid(raise_exception=True)
        instance = RentingAdminOrchestrator.create_specification(equipment, ser.validated_data)
        return Response(self._serialize(instance), status=status.HTTP_201_CREATED)

    def partial_update(self, request, uuid=None):
        instance = RentingAdminOrchestrator.get_specification(uuid)
        ser = self.input_serializer_class(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        data.pop('group', None)  # no se reasigna de grupo al editar
        updated = RentingAdminOrchestrator.update_specification(instance, data)
        return Response(self._serialize(updated))

    def destroy(self, request, uuid=None):
        instance = RentingAdminOrchestrator.get_specification(uuid)
        RentingAdminOrchestrator.delete_specification(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='toggle-active')
    def toggle_active(self, request, uuid=None):
        instance = RentingAdminOrchestrator.get_specification(uuid)
        updated = RentingAdminOrchestrator.toggle_specification(instance)
        return Response(self._serialize(updated))

    @action(detail=True, methods=['post'], url_path='duplicate')
    def duplicate(self, request, uuid=None):
        instance = RentingAdminOrchestrator.get_specification(uuid)
        copy = RentingAdminOrchestrator.duplicate_specification(instance)
        return Response(self._serialize(copy), status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        group_uuid = request.data.get('group')
        if not group_uuid:
            return Response({'detail': 'group es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        from renting.services import RentalSpecificationGroupSelector
        group = RentalSpecificationGroupSelector.get_by_uuid(group_uuid)
        ser = ReorderInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        RentingAdminOrchestrator.reorder_specifications(group.id, ser.validated_data['ordered_uuids'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminRentalDocumentViewSet(EquipmentCatalogChildViewSet):
    """
    /api/v1/dashboard/rental-documents/ -- documento descargable. create()
    esta sobreescrito: exige `file` (multipart) y pasa por
    RentalDocumentCommands.create(), que valida extension/tamano/magic-bytes.
    """
    resource = 'documents'
    output_serializer_class = RentalDocumentSerializer
    input_serializer_class = RentalDocumentInputSerializer
    supports_duplicate = False
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def create(self, request):
        from rest_framework.exceptions import ValidationError as DRFValidationError

        equipment_uuid = request.data.get('equipment')
        if not equipment_uuid:
            return Response({'detail': 'equipment es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'detail': 'Se requiere el archivo file.'}, status=status.HTTP_400_BAD_REQUEST)
        equipment = RentingAdminOrchestrator.get_equipment(equipment_uuid)
        ser = self.input_serializer_class(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            instance = RentingAdminOrchestrator.create_document(equipment, {**ser.validated_data, 'file': file_obj})
        except (ValueError, DRFValidationError) as exc:
            detail = exc.detail[0] if isinstance(getattr(exc, 'detail', None), list) else str(exc)
            return Response({'detail': str(detail)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self._serialize(instance), status=status.HTTP_201_CREATED)
