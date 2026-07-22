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
| `api/service_orders.py` | ServiceOrderViewSet — solicitudes de servicio tecnico (movido desde technical_services) |
| `api/serializers.py` | OrderSerializer, OrderItemSerializer, ShippingAddressSerializer |
| `services/commands.py` | OrderCommands: create_from_cart() |
| `services/selectors.py` | OrderSelector: list_for_user(), list_all_for_admin(), get_by_uuid() |

## Patrones obligatorios en esta app

- **Snapshot obligatorio:** `OrderItem` guarda `item_name`, `sku`, `price` al momento de la compra — NUNCA editar estos campos después
- **Flujo de estados:** `pending → paid → shipped → delivered → cancelled` — no saltar estados
- `create_from_cart()` usa `@transaction.atomic`: valida carrito, crea Order + OrderItems, vacía carrito
- Owner validation: `get_object_or_404(Order, uuid=uuid, user=request.user)`
- El pago lo confirma `payment.online.services.commands.PaymentCommands.confirm_payment()`, no esta app
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

## Endpoints de ordenes de servicio tecnico

Todos los endpoints de solicitudes de servicio viven en esta app bajo `/api/v1/orders/service-orders/`.
La logica de negocio (calculos, asignacion de tecnicos, timeline) sigue en `technical_services/services/`.

```
POST   /api/v1/orders/service-orders/                         Crear solicitud (cliente autenticado)
GET    /api/v1/orders/service-orders/                         Listar mis solicitudes
GET    /api/v1/orders/service-orders/<uuid>/                  Detalle de solicitud
POST   /api/v1/orders/service-orders/<uuid>/timeline/         Agregar evento de estado (admin)
POST   /api/v1/orders/service-orders/<uuid>/attachments/      Subir adjunto evidencia
POST   /api/v1/orders/service-orders/<uuid>/assign-technician/ Asignar tecnico manualmente (admin)
POST   /api/v1/orders/service-orders/<uuid>/auto-assign/      Asignacion automatica (admin)
```

El ViewSet usa `ServiceCommands`, `ServiceTimelineCommands`, `ServiceAttachmentCommands` y
`ServiceAssignmentCommands` de `technical_services.services` — no duplicar esa logica aqui.

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
