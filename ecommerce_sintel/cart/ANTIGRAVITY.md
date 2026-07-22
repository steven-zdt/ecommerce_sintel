# App: cart — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
ecommerce_sintel/cart/.AGENT/docs/ARQUITECTURA_COMPLETA_CART.md
```

## Responsabilidad de esta app

Carrito de compras por usuario. Gestión de ítems (agregar, actualizar cantidad, eliminar).
El carrito se vacía automáticamente al crear una orden en `orders`.

## Archivos clave

| Archivo | Propósito |
|---------|-----------|
| `models.py` | Cart (OneToOne User), CartItem (FK Cart + GenericFK variant) |
| `api/views.py` | CartViewSet: get_or_create cart, add_item, update_item, remove_item, clear |
| `api/serializers.py` | CartSerializer, CartItemSerializer, CartItemInputSerializer |
| `services/commands.py` | CartCommands: add_item(), update_quantity(), remove_item(), clear() |
| `services/selectors.py` | CartSelector: get_or_create_cart(), get_cart_with_items() |

## Patrones obligatorios en esta app

- Un carrito por usuario (`get_or_create` en cada request)
- Ítems usan `GenericForeignKey` → apuntan a ProductVariant, EquipmentVariant o ServiceVariant
- Validar stock disponible antes de agregar (`InventorySelector.is_available()`)
- Owner validation: `cart.user == request.user`
- El carrito NO se elimina al hacer orden — solo se vacían los ítems (`CartItem.delete_all()`)

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
