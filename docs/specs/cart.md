---
app_name: cart
layer: api
doc_type: spec
critical_rules:
  - wishlist_soft_delete
  - cart_polymorphic_items
  - inventory_check_before_add
associated_models:
  - Cart
  - CartItem
  - WishlistItem
cross_app_dependencies:
  - shop
  - technical_services
  - inventory
permissions_required:
  - IsAuthenticated (cart)
  - IsAuthenticatedActiveUser (wishlist)
---

# App: cart

## Modelos

### Cart

```python
class Cart(SintelBaseModel):
    user     = models.ForeignKey(AUTH_USER_MODEL, null=True, blank=True, related_name='cart')
    guest_id = models.UUIDField(null=True, blank=True, db_index=True)
```

Un carrito por usuario. `get_or_create(user=user)` en cada request.

### CartItem — Polimorfismo blando

```python
class CartItem(SintelBaseModel):
    cart            = models.ForeignKey(Cart, related_name='items')
    variant         = models.ForeignKey(ProductVariant, null=True, blank=True)
    service_variant = models.ForeignKey(ServiceVariant, null=True, blank=True)
    quantity        = models.PositiveIntegerField(default=1)
```

Un CartItem referencia `variant` O `service_variant` — nunca ambos, nunca ninguno.

### WishlistItem — Solo productos

```python
class WishlistItem(SintelBaseModel):
    user    = models.ForeignKey(AUTH_USER_MODEL, related_name='wishlist')
    variant = models.ForeignKey(ProductVariant)

    class Meta:
        unique_together = ('user', 'variant')
```

## Endpoints del Carrito (`/api/v1/cart/`)

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| GET | `/api/v1/cart/` | Carrito actual del usuario |
| POST | `/api/v1/cart/add_item/` | Agregar item (variant_uuid o service_variant_uuid) |
| POST | `/api/v1/cart/clear/` | Vaciar carrito |
| POST | `/api/v1/cart/remove-item/{uuid}/` | Eliminar item especifico |

## Endpoints de Wishlist (`/api/v1/cart/wishlist/`)

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| GET | `/api/v1/cart/wishlist/` | Lista favoritos del usuario |
| POST | `/api/v1/cart/wishlist/` | Agregar producto a favoritos |
| DELETE | `/api/v1/cart/wishlist/{uuid}/` | Eliminar de favoritos (SOFT-DELETE) |

**Permiso:** `IsAuthenticatedActiveUser` (de `users.api.permissions`).

### WishlistViewSet — Patron de implementacion

```python
class WishlistViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedActiveUser]

    def list(self, request):
        items = WishlistItem.objects.filter(
            user=request.user, is_deleted=False
        ).select_related('variant__product')
        data = [{
            'uuid': str(item.uuid),
            'product_name': item.variant.product.name,
            'sku': item.variant.sku,
            'price': str(item.variant.price),
            'created_at': item.created_at,
        } for item in items]
        return Response(data)

    def create(self, request):
        variant_uuid = request.data.get('variant_uuid')
        variant = get_object_or_404(ProductVariant, uuid=variant_uuid)
        item, _ = WishlistItem.objects.get_or_create(
            user=request.user, variant=variant
        )
        return Response({'uuid': str(item.uuid)}, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None):
        item = get_object_or_404(WishlistItem, uuid=pk, user=request.user)
        # SOFT-DELETE — nunca .delete() fisico
        item.is_deleted = True
        item.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
```

## Regla Critica: Soft-Delete en Wishlist

```python
# CORRECTO
item.is_deleted = True
item.save()

# INCORRECTO — nunca eliminar fisicamente
item.delete()
WishlistItem.objects.filter(...).delete()
```

## Registro en urls.py

```python
from cart.api.views import CartViewSet, WishlistViewSet

router = DefaultRouter()
router.register(r'', CartViewSet, basename='cart')
router.register(r'wishlist', WishlistViewSet, basename='wishlist')
```

## Stock Check antes de agregar al carrito

Al agregar un item, verificar stock via `InventorySelector` (SSoT de inventory):

```python
from inventory.services.selectors import InventorySelector

stock = InventorySelector.get_stock_for_variant(variant)
if stock < quantity:
    raise ValidationError(f"Sin existencias suficientes para: {variant.sku}")
```

El stock se obtiene de `StockRecord` via GenericFK — NO de `ProductVariant.stock`.
