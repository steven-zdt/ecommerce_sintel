# Sintel DRF Patterns: Gold Standard Examples

Usa estos patrones como base para cualquier implementación de DRF en este proyecto.

## 1. Patrón ViewSet + Service (SSoT)

Este patrón garantiza que la vista solo se encargue del flujo HTTP.

```python
# module/api/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from .serializers import ItemSerializer
from ..services import ItemSelector, ItemCommands

class ItemViewSet(viewsets.ModelViewSet):
    serializer_class = ItemSerializer
    lookup_field = 'uuid' 

    def get_queryset(self):
        # 1. Manejo obligatorio de swagger_fake_view para OpenAPI
        if getattr(self, 'swagger_fake_view', False):
            return Item.objects.none()
            
        # 2. Consulta optimizada en Selector + N+1 prevention
        return ItemSelector.list_active(user=self.request.user)

    def get_serializer_class(self):
        # 3. Serializers específicos por acción
        if self.action == 'create':
            return ItemCreateSerializer
        if self.action == 'partial_update':
            return ItemUpdateSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        return ItemCommands.create_item(
            user=self.request.user,
            **serializer.validated_data
        )
```

## 2. Serializer con OpenAPI Doc y Enmascaramiento

```python
# module/api/serializers.py
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from ..models import Item

class ItemSerializer(serializers.ModelSerializer):
    extra_data = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = ('uuid', 'name', 'extra_data', 'api_key')

    @extend_schema_field({"type": "object", "properties": {"val": {"type": "string"}}})
    def get_extra_data(self, obj):
        return {"val": "some-value"}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Enmascaramiento de datos sensibles
        if 'api_key' in data and data['api_key']:
            data['api_key'] = '********'
        return data
```

## 3. Paginación por PK (Rendimiento Extremo)

Para querysets grandes con joins costosos.

```python
# module/api/pagination.py
class PaginateByPkMixin:
    def paginate_by_pk(self, request, base_queryset, manager):
        # 1. Obtener solo PKs (rápido)
        pk_list = base_queryset.values_list("id", flat=True)
        page = self.paginate_queryset(pk_list)
        # 2. Traer objetos completos solo para la página
        queryset = manager.filter(id__in=page).select_related('...').prefetch_related('...')
        # 3. Mantener el orden original de la DB
        queryset = sorted(queryset, key=lambda obj: list(page).index(obj.id))
        return self.get_paginated_response(self.get_serializer(queryset, many=True).data)
```

## 4. Permisos Personalizados

```python
# users/api/permissions.py — patron real del proyecto (verificado 2026-07-11).
# NUNCA usar request.user.role — el modelo User NO tiene campo 'role'.
# El admin real se identifica por is_staff=True AND is_superuser=True
# (creados exclusivamente por CLI createsuperuser, la API nunca los crea).
# Ver ai_skills/frontend/architecture/state_management.md (authStore.isAdmin)
# y memoria de proyecto [[project_users_accounts_refactor]].
from rest_framework.permissions import BasePermission

class IsOwner(BasePermission):
    """Garantiza que solo el dueño del objeto pueda interactuar."""
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user

class IsAdminUser(BasePermission):
    """Solo usuarios con is_staff=True y is_superuser=True pueden acceder."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
            and request.user.is_superuser
        )
```

## 5. Filtros y Paginación

```python
# module/api/views.py
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ('category_id', 'is_active')
    search_fields = ('name', 'description')
    ordering_fields = ('price', 'created_at')
```
