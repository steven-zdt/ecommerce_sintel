# Auditoria del flujo venta, pago y confirmacion

Fecha: 2026-06-27  
Alcance: checkout cliente, datos de envio, creacion de orden, pagos Wompi/Nequi/COD, confirmacion, inventario y notificaciones al usuario.

## Resumen ejecutivo

El flujo principal existe y esta bien separado por capas: `cart` calcula el preview, `orders` crea la orden desde carrito, `payment` confirma pagos y `notifications` despacha emails, WebSocket y WhatsApp. Sin embargo, habia riesgos criticos en confirmacion de pago: un webhook Wompi duplicado podia ejecutar el descuento de inventario mas de una vez, y las ordenes con servicios podian fallar al confirmar porque se validaban como inventario fisico. Tambien habia una desviacion entre slugs de notificacion usados por codigo y los documentados.

Se aplicaron mejoras seguras en backend para reducir esos riesgos sin cambiar contratos de API.

## Flujo actual auditado

1. El frontend `CheckoutView.vue` carga el carrito y solicita `POST /api/v1/cart/checkout/`.
2. `CartCommands.checkout_cart` valida stock, disponibilidad de servicios y calcula subtotal, impuestos y total con `Decimal`.
3. El usuario completa direccion colombiana y metodo de pago.
4. El frontend crea una direccion con `POST /api/v1/orders/addresses/`.
5. El frontend crea la orden con `POST /api/v1/orders/orders/create_from_cart/`.
6. `OrderCommands.create_from_cart` valida carrito, valida stock, crea `Order`, crea `OrderItem`, vacia carrito y deja snapshots de precio.
7. Si el metodo es COD, se confirma internamente, se descuenta inventario y se crea `CodTransaction`.
8. Si el metodo es Wompi, el frontend inicializa `Transaction`, abre widget y espera webhook o callback.
9. Si el metodo es Nequi, se crea `NequiTransaction` y la pantalla de espera consulta estado.
10. Cuando un pago online se aprueba, `confirm_order_payment` marca la orden como `paid`, confirma slots de servicio, descuenta inventario y dispara notificacion.

## Mejoras aplicadas

### Idempotencia de Wompi

Archivo: `ecommerce_sintel/payment/online/services/commands.py`

- Si llega un webhook `APPROVED` repetido para una transaccion ya `APPROVED`, se ignora.
- La confirmacion de pago ya no intenta validar stock sobre `service_variant`; solo valida producto fisico o equipo.
- Los updates de estado incluyen `updated_at`.

### Confirmacion de pago segura

Archivo: `ecommerce_sintel/payment/shared/commands.py`

- `confirm_order_payment` ahora retorna sin descontar inventario si la orden ya esta `paid`.
- El slug de notificacion de pago confirmado se alinea con la spec: `order_paid`.

### Notificacion de orden creada

Archivo: `ecommerce_sintel/orders/services/commands.py`

- Al crear una orden desde carrito se programa `order_created` con `transaction.on_commit`.
- El contexto incluye `order_uuid`, `status`, `total` y `user_name`.

### Precision de datos de envio

Archivo: `ecommerce_sintel/orders/api/serializers.py`

- `phone_number` se normaliza a digitos y exige celular colombiano de 10 digitos iniciado en `3`.
- `country` acepta `CO`, `COL` o `Colombia`, y normaliza a `Colombia`.
- Campos de texto se guardan recortados.
- `full_name`, `address_line_1` y `city` se validan como obligatorios en serializer.

## Hallazgos principales

### Critico: duplicidad de webhook podia duplicar descuento

Wompi puede reintentar eventos. Antes, un `APPROVED` repetido llamaba de nuevo a `confirm_order_payment`, con riesgo de doble salida de inventario. Quedo mitigado en webhook y en la funcion compartida.

### Alto: servicios tratados como inventario fisico

En confirmacion Wompi se tomaba `item.variant or item.equipment_variant or item.service_variant`. Para servicios no hay `StockRecord` fisico, por lo que la validacion podia fallar aunque la orden fuera valida. Quedo mitigado validando solo items con inventario real.

### Alto: slugs de notificacion no estaban alineados

La spec define `order_created`, `order_paid`, `order_shipped`; el codigo usaba `order_payment_confirmed` y `order_cod_confirmed`. Se corrigio pago online a `order_paid` y se agrego `order_created`. Queda pendiente decidir si `order_cod_confirmed` sera una plantilla oficial o si COD debe reutilizar `order_created`.

### Medio: direccion del formulario tiene mas datos que el modelo

El frontend captura email y barrio/localidad, pero el backend `ShippingAddress` no los persiste. En checkout actual, el email se toma del usuario autenticado y el barrio se pierde. Esto afecta precision logistica.

### Medio: cupones no validan ventana temporal ni limite de descuento

`OrderCommands.create_from_cart` filtra `code` y `active`, pero no usa `valid_from`/`valid_to` ni evita que el descuento supere el total. Puede generar totales inconsistentes.

### Medio: Wompi amount usa `ROUND_DOWN`

`initialize_transaction` convierte total a centavos con `ROUND_DOWN`. Para COP normalmente no deberia haber centavos reales; aun asi conviene estandarizar redondeo en toda la app y validar que `total_amount` ya este cuantizado a dos decimales.

### Medio: inventario usa cache en ruta de escritura

`InventoryCommands.register_exit` comenta que evita cache, pero llama a `InventorySelector.get_current_stock`, que puede leer cache. El `select_for_update` protege el registro, pero una cache stale puede calcular `balance_after` incorrecto.

## Plan de mejoras priorizado

### Fase 1: consistencia transaccional y datos criticos

- Agregar tests para webhook Wompi duplicado: un solo descuento de inventario y una sola transicion efectiva.
- Agregar tests para orden con `service_variant`: pago aprobado no debe fallar por falta de stock.
- Cambiar `InventoryCommands.register_entry/register_exit` para tomar el stock desde `stock_record.stock` bloqueado o desde la ultima transaccion dentro de la misma transaccion, sin cache.
- Validar cupones con `valid_from`, `valid_to`, `is_deleted` y `discount <= total_items_price`.
- Decidir y seedear plantillas oficiales: `order_created`, `order_paid`, `order_shipped` y, si aplica, `order_cod_confirmed`.

### Fase 2: precision de formularios y logistica

- Agregar campos a `ShippingAddress`: `email`, `neighborhood`, `delivery_instructions`.
- Persistir `email` y `neighborhood` enviados por `ColombianAddressForm`.
- Evitar crear direcciones duplicadas exactas en cada checkout; reutilizar o marcar `is_default`.
- Validar nomenclatura con limites razonables y normalizacion de mayusculas/minusculas.
- Exponer en `OrderSerializer` el desglose `subtotal`, `tax_total`, `shipping_total` o snapshots equivalentes.

### Fase 3: confirmacion, emails y UX post-pago

- En la pantalla `OrderConfirmedView`, mostrar estados diferenciados: `paid`, `pending`, `processing`, `declined`.
- Para Wompi, consultar backend despues del callback del widget en vez de asumir que `APPROVED` local ya equivale a orden pagada.
- Crear plantilla email HTML para `order_created` y `order_paid` con items, total, direccion y numero de orden.
- Registrar eventos de negocio de orden: `created`, `payment_initialized`, `paid`, `inventory_deducted`, `email_sent`.
- Agregar panel admin para reintentar notificaciones fallidas desde `NotificationLog`.

### Fase 4: endurecimiento operacional

- Guardar payload minimo del webhook y checksum para auditoria e idempotencia externa.
- Agregar constraint de integridad para `NequiTransaction`: exactamente una FK entre `order` y `rental_request`.
- Agregar constraint de integridad para `OrderItem`: exactamente una variante entre producto, servicio o equipo.
- Revisar que todos los endpoints de checkout usen `IsAuthenticatedActiveUser`.
- Crear pruebas E2E del flujo completo: carrito -> checkout -> orden -> pago simulado -> email/log.

## Checklist de QA recomendado

- Producto fisico Wompi aprobado descuenta inventario una sola vez.
- Webhook Wompi `APPROVED` repetido no cambia stock ni reenvia flujo critico.
- Servicio tecnico Wompi aprobado no exige `StockRecord`.
- COD crea orden `processing`, descuenta inventario y notifica.
- Nequi aprobado marca orden `paid` y descuenta inventario.
- Direccion con telefono invalido devuelve 400 antes de crear orden.
- Pais distinto de Colombia devuelve 400.
- Carrito con stock insuficiente no crea orden.
- Cupon vencido o mayor al total queda rechazado cuando se implemente Fase 1.
