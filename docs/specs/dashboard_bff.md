---
app_name: dashboard
layer: api
doc_type: spec
critical_rules:
  - BFF_only_admin_writes
  - IsAdminUser_mandatory
  - orchestrator_pattern
cross_app_dependencies:
  - shop
  - inventory
  - orders
  - technical_services
  - renting
  - notifications
  - users
  - accounts
permissions_required:
  - IsAdminUser
---

# App: dashboard (BFF)

## Principio BFF

El panel de administracion (`/panel/*`) consume EXCLUSIVAMENTE:

```
/api/v1/dashboard/<recurso>/
```

Los endpoints publicos (`/api/v1/shop/`, `/api/v1/renting/`, etc.) son ReadOnly y no tienen acciones de escritura. Toda mutacion admin pasa por dashboard/.

## Patron de Orchestrator

Cada dominio tiene un Orchestrator en `dashboard/services/`:

```python
class ProductOrchestrator:
    @staticmethod
    def create_product_with_variant(admin_user, product_data, variant_data):
        product = ProductCommands.create_product(**product_data)
        variant = ProductVariantCommands.create_variant(product=product, **variant_data)
        InventoryCommands.create_stock_record(variant=variant)
        return product, variant
```

El Orchestrator coordina multiples Commands de diferentes apps en una sola operacion.

## Permisos: IsAdminUser en Todos los ViewSets del Dashboard

```python
from users.api.permissions import IsAdminUser

class DashboardProductViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]   # OBLIGATORIO en TODOS los ViewSets del dashboard
    # ...
```

## Rutas BFF por Dominio

| Dominio | Prefijo |
|---|---|
| Productos | `/api/v1/dashboard/products/` |
| Inventario | `/api/v1/dashboard/inventory/` |
| Ordenes | `/api/v1/dashboard/orders/` |
| Servicios tecnicos | `/api/v1/dashboard/services/` |
| Renting | `/api/v1/dashboard/renting/` |
| Usuarios | `/api/v1/dashboard/users/` |
| Notificaciones | `/api/v1/dashboard/notifications/` |
| Costos | `/api/v1/dashboard/cost-rules/` |

## Regla: No Exponer PKs Enteros en Dashboard

Incluso en el panel admin, usar UUID:

```python
class DashboardOrderViewSet(viewsets.ViewSet):
    lookup_field = 'uuid'

    def retrieve(self, request, uuid=None):
        order = OrderSelector.get_by_uuid(uuid)
        return Response(ServiceOrderSerializer(order).data)
```
