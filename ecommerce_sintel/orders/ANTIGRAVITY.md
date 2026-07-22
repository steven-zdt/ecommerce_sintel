# App: orders — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
ecommerce_sintel/orders/.AGENT/docs/ARQUITECTURA_COMPLETA_ORDERS.md
```

## Responsabilidad de esta app

Gestión de órdenes de compra. Creación desde carrito, estados de orden,
direcciones de envío y aplicación de cupones de descuento.

## Archivos clave

| Archivo | Propósito |
|---------|-----------|
| `models.py` | Order, OrderItem, ShippingAddress, Coupon |
| `api/views.py` | OrderViewSet: create_from_cart(); ShippingAddressViewSet |
| `api/serializers.py` | OrderSerializer, OrderItemSerializer, ShippingAddressSerializer |
| `services/commands.py` | OrderCommands: create_from_cart() |
| `services/selectors.py` | OrderSelector: list_for_user(), list_all_for_admin(), get_by_uuid() |

## Patrones obligatorios en esta app

- **Snapshot obligatorio:** `OrderItem` guarda `item_name`, `sku`, `price` al momento de la compra — NUNCA editar estos campos después
- **Flujo de estados:** `pending → paid → shipped → delivered → cancelled` — no saltar estados
- `create_from_cart()` usa `@transaction.atomic`: valida carrito, crea Order + OrderItems, vacía carrito
- Owner validation: `get_object_or_404(Order, uuid=uuid, user=request.user)`
- El pago lo confirma `wompi.PaymentCommands.confirm_payment()`, no esta app
- `OrderItem` puede apuntar a `variant` (ProductVariant), `equipment_variant`, o `service_variant`

## Flujo de creación de orden

```
POST /api/v1/orders/create-from-cart/
  → Validar carrito no vacío
  → Validar dirección de envío es del usuario
  → Calcular total + descuento de cupón
  → @transaction.atomic:
      Crear Order (status='pending')
      Crear OrderItems (snapshots de precio)
      Vaciar CartItems
  → Retornar Order completa
```

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
