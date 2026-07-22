---
app_name: global_rules
layer: architecture
doc_type: spec
critical_rules:
  - decimal_money
  - no_physical_delete
  - no_emojis_python
  - service_layer_pure
  - on_commit_notify
  - soft_delete_double
  - uuid_in_urls
  - rbac_is_admin
  - no_role_field
  - wompi_signature
---

# Reglas Globales de Arquitectura — Sintel E-Commerce REST v5

## 1. Dinero: Solo Decimal, Nunca Float

Todos los campos monetarios usan `decimal.Decimal`. Nunca `float`.

```python
from decimal import Decimal

# CORRECTO
price = Decimal('19900.00')
total = Decimal('0.00')

# INCORRECTO — genera errores de precision en pagos
price = 19900.00
total = 0.0
```

Los campos de modelo correspondientes usan `DecimalField(max_digits=12, decimal_places=2)`.

## 2. Soft-Delete: Nunca Borrado Fisico

Ningun objeto de negocio se elimina de la BD. El patron obligatorio es:

```python
# CORRECTO
obj.is_active = False
obj.is_deleted = True
obj.save(update_fields=['is_active', 'is_deleted', 'updated_at'])

# INCORRECTO — nunca hacer esto
obj.delete()
QuerySet.filter(...).delete()
```

Los selectores de admin siempre filtran `is_deleted=False`. Los selectores publicos filtran `is_active=True, is_deleted=False`.

## 3. Sin Emojis en Archivos Python

Ningun emoji ni caracter Unicode fuera del BMP en archivos `.py`. Causa `SyntaxError` y respuesta 500 en produccion.

```python
# INCORRECTO — no incluir en comentarios, docstrings ni strings
# Funcion principal CORRECTO
def crear_orden():  # CORRECTO
    pass
```

## 4. Service Layer Pura

```
ViewSet / Consumer  -->  Command / Selector  -->  Model
   (orquesta)            (logica negocio)         (datos)
```

- **ViewSets**: Solo HTTP. Llaman Serializers para validar entrada, luego Commands para mutar.
- **Commands** (`services/commands.py`): Metodos estaticos `@transaction.atomic`. Toda escritura en BD.
- **Selectors** (`services/selectors.py`): Metodos estaticos de solo lectura. Sin efectos secundarios.

```python
# CORRECTO: ViewSet orquesta
class ProductViewSet(viewsets.ViewSet):
    def create(self, request):
        s = ProductInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = ProductCommands.create_product(**s.validated_data)
        return Response(ProductSerializer(obj).data, status=201)

# INCORRECTO: ViewSet escribe directamente en BD
class ProductViewSet(viewsets.ViewSet):
    def create(self, request):
        Product.objects.create(**request.data)  # PROHIBIDO
```

## 5. Notificaciones: Siempre en transaction.on_commit

```python
# CORRECTO
from django.db import transaction
from notifications.services.commands import NotificationCommands

@transaction.atomic
def create_order(user, ...):
    order = Order.objects.create(...)
    _user, _ctx = user, {'order_uuid': str(order.uuid)}
    transaction.on_commit(
        lambda: NotificationCommands.dispatch_notification(
            user=_user,
            template_slug='order_created',
            context=_ctx,
            ws_group=f'user_{_user.uuid}',
        )
    )
    return order

# INCORRECTO — puede notificar antes de que la transaccion comite
def create_order(user, ...):
    order = Order.objects.create(...)
    NotificationCommands.dispatch_notification(...)  # PROHIBIDO fuera de on_commit
```

## 6. UUID en URLs, Nunca PK Entero

```python
# CORRECTO
/api/v1/shop/products/a3f8c2d1-.../
router.register('products', ProductViewSet, basename='product')
# lookup_field = 'uuid' en el ViewSet

# INCORRECTO
/api/v1/shop/products/42/
```

## 7. RBAC: IsAdminUser Correcto

```python
# CORRECTO — siempre importar de users.api.permissions
from users.api.permissions import IsAdminUser

class MyAdminViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]

# INCORRECTO — el de DRF solo verifica is_staff
from rest_framework.permissions import IsAdminUser  # PROHIBIDO para admin
```

`IsAdminUser` de `users.api.permissions` verifica: `is_authenticated AND is_active AND is_staff AND is_superuser`.

## 8. SintelBaseModel: Campos Heredados por Todos los Modelos

```python
class SintelBaseModel(models.Model):
    uuid       = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    class Meta:
        abstract = True
```

Nota: `is_active` se define en cada modelo segun necesidad. `is_deleted` es universal.

## 9. No Existe Campo role en User

```python
# INCORRECTO
user.role == 'ADMIN'
request.user.role

# CORRECTO — el perfil esta en accounts.UserProfile
profile = request.user.profile  # OneToOne a UserProfile
profile.user_type  # 'TECHNICIAN' | 'PROFESSIONAL' | 'SPECIALIST' | 'CUSTOMER'

# Para verificar admin
request.user.is_staff and request.user.is_superuser
```

### Valores de UserProfile.user_type

| Valor | Descripcion |
|---|---|
| `CUSTOMER` | Comprador registrado (portal del cliente) |
| `TECHNICIAN` | Tecnico de servicio (TechnicianProfile asociado) |
| `PROFESSIONAL` | Profesional externo |
| `SPECIALIST` | Especialista avanzado |

Los administradores NO tienen UserProfile — se identifican por `is_staff=True AND is_superuser=True`.
`IsCustomerUser` es alias de `IsAuthenticatedActiveUser` (cualquier usuario activo, sin importar user_type).

## 10. Selectores: Siempre Filtrar is_deleted=False

```python
# CORRECTO
class ProductSelector:
    @staticmethod
    def get_active_products():
        return Product.objects.filter(is_active=True, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid):
        return Product.objects.filter(uuid=uuid, is_deleted=False).get()

# INCORRECTO
Product.objects.filter(uuid=uuid)  # puede retornar objetos borrados
```
