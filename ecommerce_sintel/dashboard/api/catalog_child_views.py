"""
dashboard/api/catalog_child_views.py

Base generica compartida por los 4 ViewSets base de catalogo hijo (Shop/Renting/
Services/Packages) -- Sprint 4, 2026-08-05, auditoria transversal. Antes
`ProductCatalogChildViewSet`/`EquipmentCatalogChildViewSet`/`ServiceCatalogChildViewSet`/
`PackageChildViewSet` (uno por archivo: shop_catalog_views.py/renting_catalog_views.py/
services_catalog_views.py/package_views.py) repetian el mismo contrato REST
byte-identico salvo el orquestador y el nombre del query-param/campo del padre
(product/equipment/service/package). Se mantienen los 4 nombres de clase en sus
respectivos archivos (las subclases concretas de cada uno, ej. `AdminProductFeatureViewSet`,
no cambian) -- solo la definicion de la base se reduce a heredar de esta clase +
configurar `orchestrator_class`/`parent_field`/`get_parent`.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from users.api.permissions import IsAdminUser

ADMIN_PERMISSIONS = [IsAdminUser]


class GenericCatalogChildViewSet(viewsets.ViewSet):
    """
    Contrato comun (ver el docstring de cada modulo concreto para el detalle):
      GET    <recurso>/?<parent_field>=<uuid>       lista los hijos del padre
      POST   <recurso>/                             crea (body incluye parent_field)
      PATCH  <recurso>/<uuid>/                       actualiza
      DELETE <recurso>/<uuid>/                       borrado logico (is_deleted)
      POST   <recurso>/<uuid>/toggle-active/         activa/desactiva
      POST   <recurso>/<uuid>/duplicate/             duplica (si supports_duplicate)
      POST   <recurso>/reorder/                      reordena (body: parent_field, ordered_uuids)
    """
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'
    resource = None
    output_serializer_class = None
    input_serializer_class = None
    reorder_serializer_class = None
    supports_duplicate = True

    orchestrator_class = None  # Product/Renting/Service/ServicePackageChildOrchestrator
    parent_field = None        # 'product' | 'equipment' | 'service' | 'package'

    def get_parent(self, parent_uuid):
        """Resuelve la instancia del padre (Product/Equipment/TechnicalService/
        ServicePackage) -- cada base concreta lo implementa contra su propio
        AdminOrchestrator (Shop/Renting/Service), fuera del registro generico."""
        raise NotImplementedError

    def _serialize(self, instance, many=False):
        return self.output_serializer_class(instance, many=many, context={'request': self.request}).data

    def list(self, request):
        parent_uuid = request.query_params.get(self.parent_field)
        if not parent_uuid:
            return Response(
                {'detail': f'Parametro {self.parent_field} (uuid) es requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = self.orchestrator_class.list_for_parent(self.resource, parent_uuid)
        return Response(self._serialize(qs, many=True))

    def create(self, request):
        parent_uuid = request.data.get(self.parent_field)
        if not parent_uuid:
            return Response({'detail': f'{self.parent_field} es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        parent = self.get_parent(parent_uuid)
        ser = self.input_serializer_class(data=request.data)
        ser.is_valid(raise_exception=True)
        instance = self.orchestrator_class.create(self.resource, parent, ser.validated_data)
        return Response(self._serialize(instance), status=status.HTTP_201_CREATED)

    def partial_update(self, request, uuid=None):
        instance = self.orchestrator_class.get(self.resource, uuid)
        ser = self.input_serializer_class(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = self.orchestrator_class.update(self.resource, instance, ser.validated_data)
        return Response(self._serialize(updated))

    def destroy(self, request, uuid=None):
        instance = self.orchestrator_class.get(self.resource, uuid)
        self.orchestrator_class.delete(self.resource, instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='toggle-active')
    def toggle_active(self, request, uuid=None):
        instance = self.orchestrator_class.get(self.resource, uuid)
        updated = self.orchestrator_class.toggle_active(self.resource, instance)
        return Response(self._serialize(updated))

    @action(detail=True, methods=['post'], url_path='duplicate')
    def duplicate(self, request, uuid=None):
        if not self.supports_duplicate:
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        instance = self.orchestrator_class.get(self.resource, uuid)
        copy = self.orchestrator_class.duplicate(self.resource, instance)
        return Response(self._serialize(copy), status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        parent_uuid = request.data.get(self.parent_field)
        if not parent_uuid:
            return Response({'detail': f'{self.parent_field} es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        parent = self.get_parent(parent_uuid)
        ser = self.reorder_serializer_class(data=request.data)
        ser.is_valid(raise_exception=True)
        self.orchestrator_class.reorder(self.resource, parent.id, ser.validated_data['ordered_uuids'])
        return Response(status=status.HTTP_204_NO_CONTENT)
