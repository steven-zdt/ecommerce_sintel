"""
dashboard/api/package_views.py

ViewSets administrativos para el dominio de Paquetes de Servicio (2026-07-16):
ServicePackage (hijo de TechnicalService), PackageIncludedItem y
PackageAdditionalCost (hijos de ServicePackage). Mismo patron que
dashboard/api/renting_catalog_views.py -- una clase base generica (contrato
REST identico) + subclases finas por recurso.

Contrato comun:
  GET    <recurso>/?<scope>=<uuid>          lista los hijos del padre
  POST   <recurso>/                          crea (body incluye '<scope>')
  PATCH  <recurso>/<uuid>/                   actualiza
  DELETE <recurso>/<uuid>/                   borrado logico (is_deleted)
  POST   <recurso>/<uuid>/toggle-active/     activa/desactiva
  POST   <recurso>/<uuid>/duplicate/         duplica
  POST   <recurso>/reorder/                  reordena (body: <scope>, ordered_uuids)
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from users.api.permissions import IsAdminUser
from dashboard.api.catalog_child_views import GenericCatalogChildViewSet
from dashboard.services.admin_orchestrators import ServiceAdminOrchestrator, ServicePackageChildOrchestrator
from technical_services.api.package_serializers import (
    ReorderInputSerializer,
    ServicePackageSerializer, ServicePackageInputSerializer,
    PackageIncludedItemSerializer, PackageIncludedItemInputSerializer,
    PackageAdditionalCostSerializer, PackageAdditionalCostInputSerializer,
)

ADMIN_PERMISSIONS = [IsAdminUser]


class AdminServicePackageViewSet(viewsets.ViewSet):
    """
    /api/v1/dashboard/service-packages/ -- hijo de TechnicalService (?service=<uuid>).
    Multipart para el campo `image`.
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _serialize(self, instance, many=False):
        return ServicePackageSerializer(instance, many=many, context={'request': self.request}).data

    def list(self, request):
        service_uuid = request.query_params.get('service')
        if not service_uuid:
            return Response({'detail': 'Parametro service (uuid) es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        qs = ServiceAdminOrchestrator.list_packages(service_uuid)
        return Response(self._serialize(qs, many=True))

    def create(self, request):
        service_uuid = request.data.get('service')
        if not service_uuid:
            return Response({'detail': 'service es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        service = ServiceAdminOrchestrator.get_service(service_uuid)
        ser = ServicePackageInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        image = request.FILES.get('image')
        if image:
            data['image'] = image
        instance = ServiceAdminOrchestrator.create_package(service, data)
        return Response(self._serialize(instance), status=status.HTTP_201_CREATED)

    def partial_update(self, request, uuid=None):
        instance = ServiceAdminOrchestrator.get_package(uuid)
        ser = ServicePackageInputSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        image = request.FILES.get('image')
        if image:
            data['image'] = image
        updated = ServiceAdminOrchestrator.update_package(instance, data)
        return Response(self._serialize(updated))

    def destroy(self, request, uuid=None):
        instance = ServiceAdminOrchestrator.get_package(uuid)
        ServiceAdminOrchestrator.delete_package(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='toggle-active')
    def toggle_active(self, request, uuid=None):
        instance = ServiceAdminOrchestrator.get_package(uuid)
        updated = ServiceAdminOrchestrator.toggle_package(instance)
        return Response(self._serialize(updated))

    @action(detail=True, methods=['post'], url_path='duplicate')
    def duplicate(self, request, uuid=None):
        instance = ServiceAdminOrchestrator.get_package(uuid)
        copy = ServiceAdminOrchestrator.duplicate_package(instance)
        return Response(self._serialize(copy), status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        service_uuid = request.data.get('service')
        if not service_uuid:
            return Response({'detail': 'service es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        service = ServiceAdminOrchestrator.get_service(service_uuid)
        ser = ReorderInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ServiceAdminOrchestrator.reorder_packages(service.id, ser.validated_data['ordered_uuids'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class PackageChildViewSet(GenericCatalogChildViewSet):
    """Base generica para PackageIncludedItem/PackageAdditionalCost -- ver docstring del modulo."""
    orchestrator_class = ServicePackageChildOrchestrator
    parent_field = 'package'
    reorder_serializer_class = ReorderInputSerializer

    def get_parent(self, parent_uuid):
        return ServiceAdminOrchestrator.get_package(parent_uuid)


class AdminPackageIncludedItemViewSet(PackageChildViewSet):
    """/api/v1/dashboard/package-included-items/"""
    resource = 'included-items'
    output_serializer_class = PackageIncludedItemSerializer
    input_serializer_class = PackageIncludedItemInputSerializer


class AdminPackageAdditionalCostViewSet(PackageChildViewSet):
    """/api/v1/dashboard/package-additional-costs/"""
    resource = 'additional-costs'
    output_serializer_class = PackageAdditionalCostSerializer
    input_serializer_class = PackageAdditionalCostInputSerializer
