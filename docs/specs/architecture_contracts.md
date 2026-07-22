---
app_name: architecture_contracts
layer: architecture
doc_type: spec
critical_rules:
  - service_layer_pure
  - bff_pattern
  - soft_delete_double
  - rbac_is_admin
---

# Contratos de Arquitectura — Sintel E-Commerce REST v5

## Estructura de Apps

```
ecommerce_sintel/
  accounts/          # Perfiles de usuario (UserProfile, TechnicianProfile)
  users/             # Auth pura (User model, JWT, permissions)
  shop/              # Catalogo publico (Product, ProductVariant, Category, Brand, Tax)
  inventory/         # Stock (StockRecord, InventoryTransaction, kardex)
  cart/              # Carrito de compras (Cart, CartItem)
  orders/            # Ordenes (Order, OrderItem, ShippingAddress, Coupon)
  wompi/             # Pagos online (Transaction, NequiTransaction, COD)
  technical_services/ # Servicios tecnicos (TechnicalService, ServiceVariant, OrderServiceDetail)
  renting/           # Alquiler de equipos (Equipment, EquipmentVariant, RentalRequest)
  quotes/            # Cotizaciones (Quote, CostRule)
  marketing/         # Marketing (campaigns, coupons avanzados)
  notifications/     # Notificaciones centralizadas (NotificationTemplate, NotificationLog)
  support/           # Chat de soporte (ChatRoom, ChatMessage)
  core/              # Home feed publico
  dashboard/         # BFF admin (Orchestrators para panel)
```

## Patron BFF (Backend For Frontend)

El panel admin NUNCA consume endpoints publicos directamente. Usa exclusivamente:

```
/api/v1/dashboard/<recurso>/
```

Los endpoints `/api/v1/shop/`, `/api/v1/renting/`, etc. son ReadOnly para el portal de cliente.

```python
# CORRECTO: endpoint de escritura en dashboard/
class DashboardProductViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]

    def create(self, request):
        s = ProductInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = ProductCommands.create_product(**s.validated_data)
        return Response(ProductSerializer(obj).data, status=201)

# INCORRECTO: endpoint de escritura en shop/ (debe ser ReadOnly)
class ShopProductViewSet(viewsets.ModelViewSet):  # ModelViewSet permite POST — PROHIBIDO en shop/
    pass
```

## Patron de Permisos por Contexto

| Endpoint prefix | Permission class |
|---|---|
| `/api/v1/dashboard/` | `IsAdminUser` |
| `/api/v1/shop/` (lectura) | `AllowAny` o `IsAdminOrReadOnly` |
| `/api/v1/orders/` | `IsAuthenticatedActiveUser` |
| `/api/v1/renting/` | `IsAuthenticatedActiveUser` |
| `/api/v1/technical_services/` | `IsAuthenticatedActiveUser` |
| `/api/v1/wompi/webhook/` | `AllowAny` (firma SHA256 verifica autenticidad) |

## Patron de URLs

```python
# Usar DefaultRouter para CRUDs estandar
router = DefaultRouter()
router.register('products', ProductViewSet, basename='product')

# lookup_field = 'uuid' en cada ViewSet que use UUID en URL
class ProductViewSet(viewsets.ViewSet):
    lookup_field = 'uuid'
```

## Patron de Respuestas

- Listas: paginadas con `{count, next, previous, results}`
- Creacion: `HTTP 201 Created`
- Actualizacion: `HTTP 200 OK`
- Soft-delete: `HTTP 204 No Content`
- Error de validacion: `HTTP 400 Bad Request` con `{field: [errors]}`
- Sin permisos: `HTTP 403 Forbidden`
- No encontrado: `HTTP 404 Not Found`

## Patron de Transacciones con Notificacion

```python
@staticmethod
@transaction.atomic
def create_resource(user, data) -> Model:
    obj = Model.objects.create(**data)

    # capturar variables en el closure ANTES del on_commit
    _user = user
    _ctx  = {'uuid': str(obj.uuid)}

    transaction.on_commit(
        lambda: NotificationCommands.dispatch_notification(
            user=_user,
            template_slug='resource_created',
            context=_ctx,
            ws_group=f'user_{_user.uuid}',
        )
    )
    return obj
```

## Manejo de Excepciones en ViewSets

```python
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError

def create(self, request):
    try:
        obj = SomeCommands.create_x(...)
    except DjangoValidationError as exc:
        raise ValidationError(exc.message_dict if hasattr(exc, 'message_dict') else str(exc))
    return Response(SomeSerializer(obj).data, status=201)
```
