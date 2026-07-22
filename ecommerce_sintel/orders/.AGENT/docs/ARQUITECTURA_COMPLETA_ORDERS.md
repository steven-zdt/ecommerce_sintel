# ARQUITECTURA COMPLETA - MODULO ORDERS

## Descripcion General

El modulo **Orders** es el sistema central de gestion de ordenes de compra en la plataforma Sintel E-Commerce.

**Responsabilidades principales:**
- Gestion de ordenes de compra (creacion, lectura, seguimiento)
- Gestion de direcciones de envio por usuario
- Creacion de ordenes a partir del carrito (checkout)
- Soporte para aplicacion de cupones de descuento
- Captura de precios y datos como snapshots inmutables en el momento de la compra
- Soporte multiproducto: Productos fisicos, Servicios tecnicos, Equipos de renta
- Auditoria completa del ciclo de vida de ordenes (pending -> processing -> paid -> shipped -> delivered)
- Gestion de solicitudes de servicio tecnico (ServiceOrderViewSet)
- Metricas de dashboard administrativo (DashboardMetricsView)

**Conceptos clave:**
- **Snapshot pattern**: OrderItem almacena precio en el momento de la compra (inmutable)
- **OrderItemCostSnapshot**: Snapshot inmutable del desglose de costos adicionales por item
- **Service Layer**: Commands (crear orden), Selectors (consultar)
- **Transacciones atomicas**: Garantiza consistencia entre Order, OrderItems y Cart
- **Polymorphic items**: OrderItem puede apuntar a ProductVariant, ServiceVariant, o EquipmentVariant
- **Seguridad**: Validacion que usuario solo acceda a sus propias ordenes y direcciones
- **COD flow**: Estado inicial `processing` (no `pending`) para pago contra entrega

---

## Estructura de Directorios

```
orders/
|-- __init__.py
|-- apps.py                          # Configuracion de la app
|-- models.py                        # Order, OrderItem, ShippingAddress, Coupon, OrderItemCostSnapshot
|-- admin.py                         # Django admin configuration
|-- urls.py                          # Router raiz del modulo (include api/urls.py)
|
|-- api/
|   |-- __init__.py
|   |-- views.py                     # OrderViewSet, ShippingAddressViewSet
|   |-- serializers.py               # Serializadores de entrada/salida
|   |-- urls.py                      # Router REST con endpoints (orders, addresses, service-orders)
|   |-- service_orders.py            # ServiceOrderViewSet (solicitudes de servicio tecnico)
|   |-- dashboard.py                 # DashboardMetricsView (metricas admin)
|   `-- dashboard_urls.py            # Ruta metrics/ para dashboard
|
|-- services/
|   |-- __init__.py                  # Exports: OrderCommands, OrderSelector, ShippingAddressSelector, ShippingAddressCommands
|   |-- commands.py                  # OrderCommands.create_from_cart() + helpers; ShippingAddressCommands
|   `-- selectors.py                 # OrderSelector, ShippingAddressSelector
|
`-- migrations/
    |-- __init__.py
    |-- 0001_initial.py
    |-- 0002_initial.py
    |-- 0003_orderitem_equipment_variant.py
    |-- 0004_coupon_is_deleted_order_is_deleted_and_more.py   # is_deleted en SintelBaseModel
    |-- 0005_alter_order_shipping_address.py                  # shipping_address nullable
    |-- 0006_orderitemcostsnapshot.py                         # nuevo modelo
    |-- 0007_postal_code_optional.py                          # state/postal_code opcionales
    |-- 0008_order_payment_method.py                          # campo payment_method
    |-- 0009_alter_order_payment_method.py                    # ajuste choices/db_index
    |-- ...
    `-- 0015_shippingaddress_label.py                         # campo label ("Casa"/"Oficina", 2026-07-17)
```

---

## Diagramas de Arquitectura

### Flujo de Capas (Layered Architecture)

```
+-----------------------------------------------------+
|  CLIENTE (Frontend / Dashboard Admin)               |
+---------------------------+-------------------------+
                            |
            +---------------v--------------+
            |   REST API (DRF)             |
            |  ViewSets + Routers          |
            +---------------+--------------+
                            |
            +---------------v-----------------------------------------------+
            |   API Layer                                                    |
            |  - OrderViewSet (readonly + create_from_cart)                 |
            |  - ShippingAddressViewSet (CRUD)                              |
            |  - ServiceOrderViewSet (solicitudes de servicio tecnico)      |
            |  - DashboardMetricsView (metricas admin)                      |
            +---------------+-----------------------------------------------+
                            |
            +---------------v-----------------------------------------------+
            |  Serializers (api/serializers.py)                             |
            |  - OrderSerializer (output + payment_method)                  |
            |  - OrderItemSerializer (nested)                               |
            |  - ShippingAddressSerializer (CRUD + validaciones Colombia)   |
            |  - OrderCreateInputSerializer (input + payment_method)        |
            +---------------+-----------------------------------------------+
                            |
            +---------------v--------------------------------------------------+
            |   Business Logic Layer (services/)                               |
            |  +----------------------------------------------------------+    |
            |  | OrderCommands (Write Operations)                         |    |
            |  | - create_from_cart(user, address, coupon, payment_method)|    |
            |  |   [transactional, atomic]                                |    |
            |  | helpers: _check_item_stock(), _item_unit_price()         |    |
            |  +----------------------------------------------------------+    |
            |  +----------------------------------------------------------+    |
            |  | OrderSelector (Read-only Queries)                        |    |
            |  | - list_for_user()                                        |    |
            |  | - list_all_for_admin()                                   |    |
            |  | - get_by_uuid()                                          |    |
            |  +----------------------------------------------------------+    |
            |  +----------------------------------------------------------+    |
            |  | ShippingAddressSelector (Read-only)                      |    |
            |  | - list_for_user()                                        |    |
            |  | - get_by_uuid()                                          |    |
            |  +----------------------------------------------------------+    |
            +---------------+--------------------------------------------------+
                            |
            +---------------v------------------------------------------+
            |   ORM Layer (Django Models)                              |
            |  - Order (master record + payment_method)                |
            |  - OrderItem (line items)                                |
            |  - OrderItemCostSnapshot (desglose de costos inmutable)  |
            |  - ShippingAddress (delivery info)                       |
            |  - Coupon (discount codes)                               |
            +---------------+------------------------------------------+
                            |
            +---------------v------------------------------------------+
            |   External Dependencies                                  |
            |  - Cart (cart app)                                       |
            |  - ProductVariant (shop app)                             |
            |  - ServiceVariant (technical_services)                   |
            |  - EquipmentVariant (renting app)                        |
            |  - PricingService (shop.services.pricing_service)        |
            |  - NotificationCommands (notifications app)              |
            |  - CodCommands (payment.cod app)                         |
            |  - User (users app)                                      |
            |  - Database (PostgreSQL)                                 |
            +----------------------------------------------------------+
```

### Flujo de Creacion de Orden (Checkout)

```
+--------------------------------------------------------+
|  Usuario hace Checkout desde el Frontend               |
|  POST /api/v1/orders/orders/create_from_cart/         |
|  {                                                     |
|    "shipping_address_uuid": "...",                    |
|    "coupon_code": "SUMMER20" (opcional),              |
|    "payment_method": "WOMPI" | "COD" | "NEQUI"       |
|  }                                                     |
+----+---------------------------------------------------+
     |
     v
+--------------------------------------------------------+
|  OrderViewSet.create_from_cart()                       |
|  [permission: IsBuyerOrAdmin]                          |
|  1. Valida serializer (address_uuid, coupon_code,      |
|     payment_method)                                    |
|  2. Verifica que direccion pertenece al usuario        |
|  3. Delega a OrderCommands.create_from_cart()          |
+----+---------------------------------------------------+
     |
     v
+------------------------------------------------------------------+
|  OrderCommands.create_from_cart()                               |
|  @transaction.atomic                                            |
|                                                                 |
|  1. Cargar carrito con prefetch:                               |
|       Cart.objects.prefetch_related(                            |
|         'items__variant__product',                              |
|         'items__service_variant__service',                      |
|       )                                                         |
|                                                                 |
|  2. Validar carrito no vacio                                   |
|                                                                 |
|  3. Verificar stock/disponibilidad (_check_item_stock):        |
|       - ProductVariant: pasa (gestionado en inventory/)        |
|       - ServiceVariant: verifica sv.is_active y service.is_active |
|                                                                 |
|  4. Calcular precio unitario (_item_unit_price):               |
|       - ProductVariant -> PricingService.calculate_variant_price|
|         (con impuestos activos)                                 |
|       - ServiceVariant -> sv.fixed_price ?? ServiceSelector    |
|                                                                 |
|  5. Calcular total_items_price = sum(precio * qty)             |
|                                                                 |
|  6. Aplicar cupon (si existe):                                 |
|       - Filtrar por active=True + rango valid_from/valid_to    |
|       - Si no existe -> ValidationError                        |
|       - Calcular descuento (fijo o %)                          |
|       - Cap obligatorio: discount = min(discount, total)       |
|                                                                 |
|  7. Calcular total = total_items_price - discount              |
|                                                                 |
|  8. initial_status = Order.STATUS_PENDING_PAYMENT               |
|       (unico para todo payment_method, sin rama especial)      |
|                                                                 |
|  9. CREAR Order:                                               |
|       Order.objects.create(                                     |
|         user, shipping_address, total_amount, discount_amount, |
|         status=initial_status, payment_method=payment_method,  |
|       )                                                         |
|                                                                 |
| 10. CREAR OrderItems (Snapshots):                              |
|       Para ProductVariant: item_name=variant.product.name      |
|       Para ServiceVariant: item_name="name (sku)"             |
|       price = _item_unit_price(item)  <- SNAPSHOT              |
|                                                                 |
| 11. VACIAR carrito: cart.items.all().delete()                  |
|                                                                 |
| 12. on_commit: NotificationCommands.dispatch_notification(     |
|       template_slug='order_created',                           |
|       context={order_uuid, status, total, user_name},          |
|       ws_group=f'user_{user.uuid}',                            |
|     )                                                           |
|                                                                 |
| 13. Si payment_method == 'COD':                                |
|       CodCommands.confirm_order(order)  # descuenta stock +    |
|       crea CodTransaction + order.status = STATUS_PAID         |
|       (restaurado 2026-07-03, ver Historial de Cambios)        |
|                                                                 |
| RETURN: Order (created; status=PAID ya si fue COD)              |
+----+------------------------------------------------------------+
     |
     v
+--------------------------------------------------------+
|  Response: 201 Created                                 |
|  {                                                     |
|    "uuid": "order-uuid-...",                          |
|    "status": "PENDING_PAYMENT" | "paid",              |
|    "payment_method": "WOMPI",                         |
|    "total_amount": 1500.00,                           |
|    "discount_amount": 300.00,                         |
|    "shipping_address": { ... },                       |
|    "items": [                                         |
|      { "item_name": "Laptop", "price": 1200.00 },    |
|      { "item_name": "Instalacion", "price": 300.00 } |
|    ],                                                 |
|    "created_at": "2026-06-27T15:30:00Z"              |
|  }                                                     |
+--------------------------------------------------------+
```

### Flujo de Consulta de Ordenes (Lectura)

```
+----------------------------------------------------+
|  GET /api/v1/orders/orders/                        |
+----+-----------------------------------------------+
     |
     v
+----------------------------------------------------+
|  OrderViewSet.list()  [IsBuyerOrAdmin]             |
|  1. Si user.is_staff:                              |
|     OrderSelector.list_all_for_admin()             |
|  2. Si usuario normal:                             |
|     OrderSelector.list_for_user(user)              |
|  3. Paginar (PAGE_SIZE=20)                         |
+----+-----------------------------------------------+
     |
     v
+----------------------------------------------------+
|  OrderSelector.list_for_user(user)                 |
|  .filter(user=user, is_deleted=False)              |
|  .only(id, uuid, status, total_amount, created_at) |
|  .order_by('-created_at')                          |
+----------------------------------------------------+
```

### Gestion de Direcciones de Envio

```
GET    /api/v1/orders/addresses/          -> list_for_user()
POST   /api/v1/orders/addresses/          -> perform_create() asigna user=request.user
GET    /api/v1/orders/addresses/{uuid}/   -> retrieve()
PUT    /api/v1/orders/addresses/{uuid}/   -> update()
PATCH  /api/v1/orders/addresses/{uuid}/   -> partial_update()
DELETE /api/v1/orders/addresses/{uuid}/   -> destroy()
```

### Solicitudes de Servicio Tecnico

```
POST   /api/v1/orders/service-orders/                        -> crear (cliente)
GET    /api/v1/orders/service-orders/                        -> listar (cliente ve solo las suyas)
GET    /api/v1/orders/service-orders/{uuid}/                 -> detalle
POST   /api/v1/orders/service-orders/{uuid}/timeline/        -> agregar evento (admin)
POST   /api/v1/orders/service-orders/{uuid}/attachments/     -> subir adjunto
POST   /api/v1/orders/service-orders/{uuid}/assign-technician/ -> asignar tecnico (admin)
POST   /api/v1/orders/service-orders/{uuid}/auto-assign/     -> asignacion automatica (admin)
POST   /api/v1/orders/service-orders/{uuid}/confirm-cod/     -> confirmar pago en sitio (cliente)
```

### Dashboard Administrativo

```
GET /api/v1/dashboard/metrics/   [IsAuthenticated + IsAdminUser]
  -> total_sales (status in paid/delivered)
  -> orders_count
  -> customers_count (is_active=True, is_staff=False)
  -> products_count (is_active=True)
  -> recent_orders (ultimos 5)
```

---

## Descripcion Detallada de Archivos

### `models.py` - Modelos de Dominio

#### **ShippingAddress (Direccion de Envio)**

```python
class ShippingAddress(SintelBaseModel):
    user = ForeignKey(AUTH_USER_MODEL, related_name='shipping_addresses')
    label = CharField(max_length=50, blank=True, default='')      # "Casa"/"Oficina" (mig 0015)
    full_name = CharField(max_length=255)
    address_line_1 = CharField(max_length=255)
    address_line_2 = CharField(blank=True, null=True)
    city = CharField(max_length=100)
    state = CharField(max_length=100, blank=True, default='')    # opcional
    postal_code = CharField(max_length=20, blank=True, default='') # opcional (mig 0007)
    country = CharField(default='Colombia')
    phone_number = CharField(max_length=20)
    is_default = BooleanField(default=False)
```

**Cambios desde doc inicial:**
- `state` y `postal_code` ahora son opcionales (`blank=True, default=''`) — migration 0007
- `label` agregado (migration 0015, 2026-07-17) — nombre libre para la direccion ("Casa",
  "Oficina") mostrado como titulo de card en `CustomerAddressView.vue`; ver seccion de
  Historial de Cambios para el fix completo de sincronizacion con el registro.

**Responsabilidades:**
- Almacena direcciones de envio por usuario
- `is_default`: Marca direccion por defecto — la unicidad ("solo un default por usuario") la
  garantiza `ShippingAddressCommands` (ver mas abajo), no una constraint de BD
- Campo `is_deleted` (heredado de SintelBaseModel): Borrado logico
- Es la **fuente unica oficial** de direcciones de envio del cliente: se reutiliza tal cual
  en Checkout (`OrderCommands.create_from_cart` exige `shipping_address_uuid`), y desde
  2026-07-17 tambien es alimentada automaticamente por el registro (ver mas abajo) — no
  existe ni debe crearse ningun otro modelo de "direccion" paralelo para el cliente final.

#### **Coupon (Cupones de Descuento)**

```python
class Coupon(SintelBaseModel):
    code = CharField(max_length=20, unique=True)
    discount_value = DecimalField(max_digits=12, decimal_places=2)
    is_percentage = BooleanField(default=False)  # True: %, False: amount
    active = BooleanField(default=True)
    valid_from = DateTimeField()
    valid_to = DateTimeField()
```

**Responsabilidades:**
- Cupones reutilizables con codigo unico
- Soporte para descuentos fijos y porcentuales
- Validez temporal (valid_from / valid_to) — ahora validada activamente en commands

#### **Order (Orden de Compra)**

> **[DESACTUALIZADO Y CORREGIDO 2026-07-03]** El enum de abajo y la "logica de status inicial" que
> seguia eran de una version anterior del modelo (2 estados intermedios: `pending`/`processing`). El
> proyecto migro a un motor de fulfillment mas granular; ver el enum real inmediatamente despues.

```python
class Order(SintelBaseModel):
    STATUS_CREATED            = 'CREATED'
    STATUS_PENDING_PAYMENT    = 'PENDING_PAYMENT'   # <- estado inicial UNICO para todo payment_method
    STATUS_PAID               = 'paid'              # <- gate que desbloquea fulfillment (prepare/pack/...)
    STATUS_PREPARING          = 'PREPARING'
    STATUS_READY_FOR_DISPATCH = 'READY_FOR_DISPATCH'
    STATUS_ASSIGNED           = 'ASSIGNED'
    STATUS_PICKED_UP          = 'PICKED_UP'
    STATUS_IN_TRANSIT         = 'IN_TRANSIT'
    STATUS_OUT_FOR_DELIVERY   = 'OUT_FOR_DELIVERY'
    STATUS_DELIVERED          = 'delivered'
    STATUS_COMPLETED          = 'COMPLETED'
    STATUS_CANCELLED          = 'cancelled'
    STATUS_RETURN_REQUESTED   = 'RETURN_REQUESTED'
    STATUS_RETURNED           = 'RETURNED'
    STATUS_FAILED_DELIVERY    = 'FAILED_DELIVERY'
    STATUS_LOST               = 'LOST'
    # 'pending' y 'processing' siguen en STATUS_CHOICES marcados "(legacy)" por compatibilidad,
    # pero create_from_cart() ya NO los usa.

    PAYMENT_METHOD_CHOICES = [
        ('WOMPI', 'Wompi (online)'),
        ('COD',   'Pago contra entrega'),
        ('NEQUI', 'Nequi Push'),
    ]

    user = ForeignKey(AUTH_USER_MODEL, related_name='orders')
    shipping_address = ForeignKey(ShippingAddress, on_delete=PROTECT,
                                  null=True, blank=True)  # nullable (mig 0005)
    status = CharField(choices=STATUS_CHOICES, default='pending')
    payment_method = CharField(
        choices=PAYMENT_METHOD_CHOICES, default='WOMPI', db_index=True
    )  # campo agregado en mig 0008/0009
    total_amount = DecimalField(max_digits=12, decimal_places=2)
    discount_amount = DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tracking_number = CharField(blank=True, null=True)
```

**Cambios desde doc inicial:**
- Motor de fulfillment granular agregado (migration `0010_fulfillment_models`): `Shipment` +
  `STATUS_PREPARING`/`STATUS_READY_FOR_DISPATCH`/`STATUS_ASSIGNED`/`STATUS_PICKED_UP`/
  `STATUS_IN_TRANSIT`/`STATUS_OUT_FOR_DELIVERY`/`STATUS_COMPLETED`/`STATUS_RETURN_REQUESTED`/
  `STATUS_RETURNED`/`STATUS_FAILED_DELIVERY`/`STATUS_LOST` — ver `orders/services/fulfillment/`
  (`FulfillmentCommands.start_preparation()`, `.complete_packing()`, etc.) y los endpoints
  `prepare/`, `pack/`, `assign-dispatch-center/`, `assign-carrier/`, `assign-driver/`, `dispatch/`,
  `in-transit/`, `deliver/`, `timeline/`, `tracking/` en `OrderViewSet` (no documentados en la
  version anterior de este archivo).
- Campo `payment_method` agregado (WOMPI | COD | NEQUI), con `db_index=True`
- `shipping_address` ahora `null=True, blank=True` (migration 0005, 2026-06-19)

**Logica de status inicial (real, verificada contra el codigo 2026-07-03):**
- **Todos** los `payment_method` (WOMPI, NEQUI, COD) crean la orden en `STATUS_PENDING_PAYMENT` —
  no hay rama especial por metodo en `create_from_cart()`.
- La transicion a `STATUS_PAID` (que desbloquea el motor de fulfillment) la hace, segun el metodo:
  - WOMPI/NEQUI: `payment.shared.commands.confirm_order_payment()`, al aprobarse el pago via webhook
    o polling.
  - COD: `payment.cod.services.commands.CodCommands.confirm_order()`, llamado de forma sincrona
    **dentro** de `create_from_cart()` justo despues de crear la orden (ver bug corregido abajo).

#### **OrderItem (Linea de Orden)**

```python
class OrderItem(SintelBaseModel):
    order = ForeignKey(Order, related_name='items')
    variant = ForeignKey(ProductVariant, null=True, blank=True)
    service_variant = ForeignKey(ServiceVariant, null=True, blank=True)
    equipment_variant = ForeignKey(EquipmentVariant, null=True, blank=True)

    # Snapshots for immutability
    item_name = CharField(max_length=255)
    sku = CharField(max_length=100)
    quantity = PositiveIntegerField()
    price = DecimalField(max_digits=12, decimal_places=2)  # <- SNAPSHOT
```

**Responsabilidades:**
- Representa cada linea en la orden
- Polymorphic: puede referenciar ProductVariant, ServiceVariant, o EquipmentVariant
- **SNAPSHOT PATTERN**: `price` es inmutable, captura valor al momento de la compra
- El precio para productos fisicos es calculado por `PricingService.calculate_variant_price()`
  (incluye impuestos activos) — no `variant.discounted_price` directo

#### **OrderItemCostSnapshot (Desglose de Costos Inmutable)**

```python
class OrderItemCostSnapshot(SintelBaseModel):
    """
    Snapshot inmutable de un AdditionalCost aplicado a un OrderItem.
    Permite mostrar el desglose de precio en el historial de ordenes
    sin depender de los valores actuales de CostRule (que pueden cambiar).
    """
    order_item = ForeignKey(OrderItem, related_name='cost_snapshots')
    cost_name = CharField(max_length=150)
    context = CharField(max_length=20)      # e.g. 'tax', 'shipping', 'fee'
    cost_type = CharField(max_length=10)    # e.g. 'PCT', 'FIXED'
    value = DecimalField(max_digits=12, decimal_places=4)
    computed_amount = DecimalField(max_digits=12, decimal_places=2)
    is_discount = BooleanField(default=False)
```

**Responsabilidades:**
- Guarda el desglose detallado de costos adicionales por `OrderItem`
- Completamente inmutable despues de creado
- Separado de `CostRule` (que pertenece a cada app del motor de costos descentralizado)
- Permite auditoria historica exacta de impuestos, descuentos, cargos adicionales

**Nota:** Agregado en migration 0006 (2026-06-22). El poblado de este modelo se hace
desde el motor de costos descentralizado, no desde `commands.py` directamente.

---

### `api/views.py` - API REST Endpoints

#### **ShippingAddressViewSet**

> **[ACTUALIZADO 2026-07-17]** `perform_create`/`perform_update` ya no llaman
> `serializer.save()` directo — delegan a `ShippingAddressCommands` (Service Layer real,
> antes inexistente para este modelo) para garantizar la invariante "solo un default por
> usuario" sin importar por que puerta entre el dato. Ver Historial de Cambios.

```python
class ShippingAddressViewSet(viewsets.ModelViewSet):
    serializer_class = ShippingAddressSerializer
    lookup_field = 'uuid'
    permission_classes = [IsBuyerOrAdmin]

    def get_queryset(self):
        if self.request.user.is_staff:
            return ShippingAddress.objects.filter(is_deleted=False)
        return ShippingAddressSelector.list_for_user(self.request.user)

    def perform_create(self, serializer):
        ShippingAddressCommands.create(self.request.user, **serializer.validated_data)

    def perform_update(self, serializer):
        ShippingAddressCommands.update(serializer.instance, **serializer.validated_data)

    @action(detail=True, methods=['post'], url_path='set-default')
    def set_default(self, request, uuid=None):
        address = get_object_or_404(self.get_queryset(), uuid=uuid)
        ShippingAddressCommands.set_as_default(request.user, address)
        return Response(ShippingAddressSerializer(address).data)
```

**Tipo:** ModelViewSet (CRUD completo) + 1 action custom
**Permiso:** `IsBuyerOrAdmin` (from users.api.permissions)

**Acciones:**
1. **list()** - GET `/api/v1/orders/addresses/`
2. **create()** - POST `/api/v1/orders/addresses/`
3. **retrieve()** - GET `/api/v1/orders/addresses/{uuid}/`
4. **update()** - PUT `/api/v1/orders/addresses/{uuid}/`
5. **partial_update()** - PATCH `/api/v1/orders/addresses/{uuid}/`
6. **destroy()** - DELETE `/api/v1/orders/addresses/{uuid}/`
7. **set_default()** - POST `/api/v1/orders/addresses/{uuid}/set-default/` (2026-07-17) —
   mapea 1:1 al boton "Seleccionar como direccion de envio" del frontend sin necesitar un
   PATCH completo solo para cambiar el default.

#### **OrderViewSet**

```python
class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    lookup_field = 'uuid'
    permission_classes = [IsBuyerOrAdmin]

    def get_queryset(self):
        if self.request.user.is_staff:
            return OrderSelector.list_all_for_admin()
        return OrderSelector.list_for_user(self.request.user)

    @extend_schema(request=OrderCreateInputSerializer, responses={201: OrderSerializer})
    @action(detail=False, methods=['post'])
    def create_from_cart(self, request):
        input_serializer = OrderCreateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        data = input_serializer.validated_data
        address_uuid   = data['shipping_address_uuid']
        coupon_code    = data.get('coupon_code')
        payment_method = data.get('payment_method', 'WOMPI')

        address = get_object_or_404(ShippingAddress, uuid=address_uuid, is_deleted=False)

        if address.user != request.user and not request.user.is_staff:
            return Response({"detail": "..."}, status=HTTP_403_FORBIDDEN)

        order = OrderCommands.create_from_cart(
            user=request.user,
            shipping_address=address,
            coupon_code=coupon_code,
            payment_method=payment_method,
        )
        return Response(OrderSerializer(order).data, status=HTTP_201_CREATED)
```

**Tipo:** ReadOnlyModelViewSet (con custom action para crear)
**Permiso:** `IsBuyerOrAdmin`

**Acciones:**
1. **list()** - GET `/api/v1/orders/orders/`
2. **retrieve()** - GET `/api/v1/orders/orders/{uuid}/`
3. **create_from_cart()** - POST `/api/v1/orders/orders/create_from_cart/`

---

### `api/service_orders.py` - Solicitudes de Servicio Tecnico

```python
@extend_schema(tags=['orders'])
class ServiceOrderViewSet(viewsets.ModelViewSet):
    lookup_field = 'uuid'
    serializer_class = ServiceOrderSerializer
    pagination_class = ServiceOrderPagination  # page_size=25, max=100
    permission_classes = [IsAuthenticated]
```

**get_queryset:**
```python
qs = (
    Order.objects
    .filter(service_detail__isnull=False)   # solo ordenes de servicio
    .select_related('service_detail')
    .prefetch_related('items', 'timeline', 'attachments')
)
if self.request.user.is_staff:
    return qs
return qs.filter(user=self.request.user)
```

**Permisos granulares (get_permissions):**
- `update`, `partial_update`, `destroy`, `assign_technician`, `auto_assign_technician`: `IsAdminUser`
- resto de acciones: `IsAuthenticated`

**Acciones:**

| Accion | Metodo | URL | Permiso | Descripcion |
|--------|--------|-----|---------|-------------|
| `create` | POST | `/service-orders/` | Authenticated | Llama `ServiceCommands.request_service()` |
| `list` | GET | `/service-orders/` | Authenticated | Lista las propias (admin ve todas) |
| `retrieve` | GET | `/service-orders/{uuid}/` | Authenticated | Detalle |
| `add_timeline_event` | POST | `/{uuid}/timeline/` | is_staff | `ServiceTimelineCommands.add_timeline_event()` |
| `upload_attachment` | POST | `/{uuid}/attachments/` | Authenticated | `ServiceAttachmentCommands.add_attachment()` |
| `assign_technician` | POST | `/{uuid}/assign-technician/` | IsAdminUser | `ServiceAssignmentCommands.assign_technician()` |
| `auto_assign_technician` | POST | `/{uuid}/auto-assign/` | IsAdminUser | `ServiceAssignmentCommands.auto_assign_technician()` |
| `confirm_cod` | POST | `/{uuid}/confirm-cod/` | owner (user) | Confirma pago en sitio COD para servicio |

**Detalle de `confirm_cod`:**
```python
# Valida: order.user == request.user
# Valida: order.status == Order.STATUS_PENDING_PAYMENT  (bug corregido 2026-07-03: comparaba
#   contra el string legacy 'pending', rechazando siempre con 400 -- ver Historial de Cambios)
# Valida: no existe CodTransaction para esta orden
# with transaction.atomic():
#     ServiceCommands.confirm_slot_on_payment(order)
#     CodCommands.confirm_order(order)
```

**Dependencias externas:**
- `technical_services.api.serializers`: Serializers de servicio
- `technical_services.services`: ServiceCommands, ServiceTimelineCommands,
  ServiceAttachmentCommands, ServiceAssignmentCommands
- `payment.cod.services.commands`: CodCommands (solo en confirm_cod)

---

### `api/dashboard.py` - Metricas Administrativas

```python
class DashboardMetricsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
```

**Endpoint:** `GET /api/v1/dashboard/metrics/`

**Response:**
```json
{
    "total_sales": 15000.00,
    "orders_count": 42,
    "customers_count": 18,
    "products_count": 30,
    "recent_orders": [
        {
            "id": 1,
            "uuid": "...",
            "status": "paid",
            "total_amount": "1500.00",
            "created_at": "2026-06-27T..."
        }
    ]
}
```

- `total_sales`: suma de `total_amount` donde `status in ['paid', 'delivered']`
- `orders_count`: conteo total de ordenes (sin filtro de estado)
- `customers_count`: usuarios activos no staff
- `products_count`: productos activos
- `recent_orders`: ultimos 5 pedidos ordenados por `-created_at`

**Nota:** Migrado desde `coreui.api.views` (2026-05-14).

---

### `api/serializers.py` - Serializadores

#### **ShippingAddressSerializer**

```python
class ShippingAddressSerializer(serializers.ModelSerializer):
    # Campos opcionales con defaults
    postal_code  = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    address_line_2 = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    state = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    label = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')  # 2026-07-17

    class Meta:
        model = ShippingAddress
        fields = ['id', 'uuid', 'label', 'full_name', 'address_line_1', 'address_line_2',
                  'city', 'state', 'postal_code', 'country', 'phone_number', 'is_default']
        read_only_fields = ['id', 'uuid']

    def validate_phone_number(self, value):
        # Extrae solo digitos, valida 10 digitos iniciando en '3' (celular colombiano)
        phone = ''.join(ch for ch in str(value or '') if ch.isdigit())
        if len(phone) != 10 or not phone.startswith('3'):
            raise ValidationError('Ingresa un celular colombiano valido de 10 digitos, iniciando en 3.')
        return phone

    def validate_country(self, value):
        # Acepta 'CO', 'COL', 'Colombia' -> normaliza a 'Colombia'
        # Rechaza cualquier otro pais
        ...

    def validate(self, attrs):
        # Strip whitespace en todos los campos de texto
        # full_name/address_line_1/city son requeridos SOLO si vienen en attrs, o si
        # self.partial es False (creacion/PUT completo) -- ver bug corregido 2026-07-17
        ...
```

**Cambios desde doc inicial:**
- Campos `postal_code`, `address_line_2`, `state` declarados explicitamente como opcionales
- `label` agregado (2026-07-17), mismo patron opcional que los anteriores
- `validate_phone_number()`: valida celular colombiano (10 digitos, inicia en 3)
- `validate_country()`: normaliza CO/COL/Colombia, rechaza otros paises
- `validate()`: strip de espacios + requeridos minimos (full_name, address_line_1, city)

**Bug corregido 2026-07-17 — `validate()` no respetaba `self.partial`:** el chequeo de
requeridos (`full_name`/`address_line_1`/`city`) era incondicional, por lo que un `PATCH`
parcial que solo enviara `{"is_default": true}` (exactamente lo que hacia el boton
"Usar como predeterminada" antes de existir el action `set-default`) fallaba con 400
exigiendo los 3 campos aunque no vinieran en la request. Fix: el requerido solo aplica si
el campo SI vino en `attrs`, o si `self.partial` es `False` (creacion/PUT completo):
```python
for field in ('full_name', 'address_line_1', 'city'):
    if field in attrs:
        if not attrs[field]:
            raise serializers.ValidationError({field: 'Este campo es requerido.'})
    elif not self.partial:
        raise serializers.ValidationError({field: 'Este campo es requerido.'})
```
Encontrado por un test nuevo (`test_update_with_is_default_true_unsets_other_addresses`),
no reportado por el usuario — bug preexistente, no introducido por el fix de "Mis Direcciones".

#### **OrderItemSerializer**

```python
class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['uuid', 'item_name', 'sku', 'quantity', 'price']
        read_only_fields = fields  # Todo read-only (snapshots)
```

Sin cambios respecto a doc anterior.

#### **OrderSerializer**

```python
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_address = ShippingAddressSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'uuid', 'status', 'payment_method',   # <- payment_method nuevo
            'total_amount', 'discount_amount', 'tracking_number',
            'shipping_address', 'items', 'created_at',
        ]
        read_only_fields = fields
```

**Cambio:** `payment_method` agregado a `fields`.

#### **OrderCreateInputSerializer**

```python
class OrderCreateInputSerializer(serializers.Serializer):
    shipping_address_uuid = serializers.UUIDField()
    coupon_code = serializers.CharField(required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(
        choices=[code for code, _ in Order.PAYMENT_METHOD_CHOICES],
        default='WOMPI',
        required=False,
    )
```

**Cambio:** `payment_method` ChoiceField agregado (WOMPI | COD | NEQUI).

---

### `services/commands.py` - Operaciones de Escritura

#### **Helpers de modulo**

```python
def _check_item_stock(item):
    """Verifica disponibilidad antes de crear la orden."""
    if item.variant:
        stock = InventorySelector.get_stock_for_variant(item.variant)
        if stock < item.quantity:
            raise ValidationError(f"Sin existencias suficientes para: {item.variant.sku}")
    elif item.service_variant:
        sv = item.service_variant
        if not sv.is_active or not sv.service.is_active:
            raise ValidationError(f"El servicio {sv.sku} ya no esta disponible.")


def _item_unit_price(item) -> Decimal:
    """Calcula precio unitario segun tipo de item."""
    if item.variant:
        from shop.services.pricing_service import PricingService
        return PricingService.calculate_variant_price(
            item.variant, include_active_taxes=True
        )
    if item.service_variant:
        sv = item.service_variant
        if sv.fixed_price is not None:
            return Decimal(str(sv.fixed_price))
        from technical_services.services.selectors import ServiceSelector
        return Decimal(str(ServiceSelector.get_variant_quotation(sv)['total_price']))
    return Decimal('0.00')
```

**Patron:** Helpers de modulo privados (prefijo `_`) — no son metodos de clase.
Separacion de responsabilidades: stock-check y calculo de precio desacoplados del flujo principal.

#### **OrderCommands.create_from_cart()**

```python
@staticmethod
@transaction.atomic
def create_from_cart(
    user,
    shipping_address: ShippingAddress,
    coupon_code: str = None,
    payment_method: str = 'WOMPI',
) -> Order:
```

**Firma completa con pasos:**

1. Cargar carrito con `prefetch_related('items__variant__product', 'items__service_variant__service')`
2. Validar carrito no vacio
3. `for item in items: _check_item_stock(item)` — nueva validacion de disponibilidad
4. `total_items_price = sum(_item_unit_price(item) * item.quantity for item in items)`
5. Validacion de cupon con rango de fechas:
   ```python
   now = timezone.now()
   coupon = Coupon.objects.filter(
       code=coupon_code, active=True,
       valid_from__lte=now, valid_to__gte=now,
   ).first()
   if not coupon:
       raise ValidationError("El cupon no es valido o ha expirado.")
   discount = min(descuento_calculado, total_items_price)  # cap obligatorio
   ```
6. `initial_status = 'processing' if payment_method == 'COD' else 'pending'`
7. `Order.objects.create(..., status=initial_status, payment_method=payment_method)`
8. `OrderItem.objects.create(...)` para cada item con `price=_item_unit_price(item)` como SNAPSHOT
9. `cart.items.all().delete()`
10. `transaction.on_commit(lambda: NotificationCommands.dispatch_notification(...))`
    - context incluye: `order_uuid`, `status`, `total`, `user_name`
11. Si `payment_method == 'COD'`: `CodCommands.confirm_order(order)`
12. `return order`

**Diferencias clave respecto a version anterior:**

| Aspecto | Antes | Ahora |
|---------|-------|-------|
| Firma | `(user, address, coupon_code)` | `(user, address, coupon_code, payment_method)` |
| Precio producto | `variant.discounted_price` directo | `PricingService.calculate_variant_price()` |
| Stock check | Sin verificacion | `_check_item_stock()` antes de calcular precios |
| Cupon expirado | Aceptado si `active=True` | Rechazado si fuera de `valid_from`/`valid_to` |
| Cap descuento | Sin cap | `discount = min(discount, total_items_price)` |
| Status inicial | Siempre `pending` | Siempre `Order.STATUS_PENDING_PAYMENT` (COD incluido) |
| COD post-commit | No existia | `CodCommands.confirm_order(order)` — restaurado 2026-07-03 tras regresion |
| Notificacion context | `{order_uuid, total}` | `{order_uuid, status, total, user_name}` |

---

### `services/selectors.py` - Operaciones de Lectura

Sin cambios respecto a la version anterior.

#### **ShippingAddressSelector**

```python
class ShippingAddressSelector:
    LIST_FIELDS = ('id', 'uuid', 'label', 'full_name', 'address_line_1', 'address_line_2',
                   'city', 'state', 'postal_code', 'country', 'phone_number', 'is_default')

    @staticmethod
    def list_for_user(user) -> QuerySet:
        return ShippingAddress.objects.filter(
            user=user, is_deleted=False
        ).only(*ShippingAddressSelector.LIST_FIELDS)

    @staticmethod
    def get_by_uuid(uuid: str) -> ShippingAddress:
        return ShippingAddress.objects.get(uuid=uuid, is_deleted=False)
```

**Bug de N+1 corregido 2026-07-17:** `LIST_FIELDS` no cubria `address_line_1`,
`address_line_2`, `postal_code`, `country` — 4 columnas que `ShippingAddressSerializer` SI
serializa. Cada una disparaba una query de recarga de campo diferido (`.only()` incompleto)
por fila listada. Se completo el tuple al agregar `label`, cerrando el N+1 de paso.

#### **ShippingAddressCommands** (nuevo, 2026-07-17)

Antes de este fix, `ShippingAddressViewSet` llamaba `serializer.save()` directo — sin
ninguna clase Commands, nada garantizaba que solo una direccion por usuario tuviera
`is_default=True` a la vez si el usuario editaba dos por separado.

```python
class ShippingAddressCommands:
    @staticmethod
    @transaction.atomic
    def create(user, **data) -> ShippingAddress:
        is_first = not ShippingAddress.objects.filter(user=user, is_deleted=False).exists()
        requested_default = data.pop('is_default', False)
        address = ShippingAddress.objects.create(
            user=user, is_default=is_first or requested_default, **data
        )
        if address.is_default:
            ShippingAddress.objects.filter(
                user=user, is_deleted=False
            ).exclude(pk=address.pk).update(is_default=False)
        return address

    @staticmethod
    @transaction.atomic
    def update(address: ShippingAddress, **data) -> ShippingAddress:
        make_default = data.pop('is_default', None)
        for field, value in data.items():
            setattr(address, field, value)
        if make_default:
            ShippingAddress.objects.filter(
                user=address.user, is_deleted=False
            ).exclude(pk=address.pk).update(is_default=False)
            address.is_default = True
        address.save()
        return address

    @staticmethod
    @transaction.atomic
    def set_as_default(user, address: ShippingAddress) -> ShippingAddress:
        ShippingAddress.objects.filter(
            user=user, is_deleted=False
        ).exclude(pk=address.pk).update(is_default=False)
        address.is_default = True
        address.save(update_fields=['is_default'])
        return address
```

**Invariante garantizada:** la primera direccion de un usuario siempre es default; las
demas rutas (crear con `is_default=True`, editar marcandolo, o el action `set-default`)
siempre desmarcan cualquier otra direccion default del mismo usuario en la misma
transaccion. Verificado por `orders.tests.ShippingAddressBookTestCase` (4 tests).

#### **OrderSelector**

```python
class OrderSelector:
    LIST_FIELDS = ('id', 'uuid', 'status', 'total_amount', 'created_at')
    DETAIL_FIELDS = LIST_FIELDS + ('shipping_address_id', 'discount_amount', 'tracking_number')

    @staticmethod
    def list_all_for_admin() -> QuerySet:
        return Order.objects.filter(is_deleted=False).only(*OrderSelector.LIST_FIELDS).order_by('-created_at')

    @staticmethod
    def list_for_user(user) -> QuerySet:
        return Order.objects.filter(user=user, is_deleted=False).only(*OrderSelector.LIST_FIELDS).order_by('-created_at')

    @staticmethod
    def get_by_uuid(uuid: str) -> Order:
        return (
            Order.objects
            .filter(is_deleted=False)
            .prefetch_related('items')
            .get(uuid=uuid)
        )
```

---

## Mapa completo de Endpoints

| Metodo | URL | ViewSet / View | Permiso |
|--------|-----|---------------|---------|
| GET | `/api/v1/orders/orders/` | OrderViewSet.list | IsBuyerOrAdmin |
| GET | `/api/v1/orders/orders/{uuid}/` | OrderViewSet.retrieve | IsBuyerOrAdmin |
| POST | `/api/v1/orders/orders/create_from_cart/` | OrderViewSet.create_from_cart | IsBuyerOrAdmin |
| GET | `/api/v1/orders/addresses/` | ShippingAddressViewSet.list | IsBuyerOrAdmin |
| POST | `/api/v1/orders/addresses/` | ShippingAddressViewSet.create | IsBuyerOrAdmin |
| GET | `/api/v1/orders/addresses/{uuid}/` | ShippingAddressViewSet.retrieve | IsBuyerOrAdmin |
| PUT | `/api/v1/orders/addresses/{uuid}/` | ShippingAddressViewSet.update | IsBuyerOrAdmin |
| PATCH | `/api/v1/orders/addresses/{uuid}/` | ShippingAddressViewSet.partial_update | IsBuyerOrAdmin |
| DELETE | `/api/v1/orders/addresses/{uuid}/` | ShippingAddressViewSet.destroy | IsBuyerOrAdmin |
| POST | `/api/v1/orders/addresses/{uuid}/set-default/` | ShippingAddressViewSet.set_default | IsBuyerOrAdmin |
| POST | `/api/v1/orders/service-orders/` | ServiceOrderViewSet.create | IsAuthenticated |
| GET | `/api/v1/orders/service-orders/` | ServiceOrderViewSet.list | IsAuthenticated |
| GET | `/api/v1/orders/service-orders/{uuid}/` | ServiceOrderViewSet.retrieve | IsAuthenticated |
| POST | `/api/v1/orders/service-orders/{uuid}/timeline/` | ServiceOrderViewSet.add_timeline_event | is_staff |
| POST | `/api/v1/orders/service-orders/{uuid}/attachments/` | ServiceOrderViewSet.upload_attachment | IsAuthenticated |
| POST | `/api/v1/orders/service-orders/{uuid}/assign-technician/` | ServiceOrderViewSet.assign_technician | IsAdminUser |
| POST | `/api/v1/orders/service-orders/{uuid}/auto-assign/` | ServiceOrderViewSet.auto_assign_technician | IsAdminUser |
| POST | `/api/v1/orders/service-orders/{uuid}/confirm-cod/` | ServiceOrderViewSet.confirm_cod | owner |
| GET | `/api/v1/dashboard/metrics/` | DashboardMetricsView | IsAuthenticated + IsAdminUser |

---

## Patrones de Diseno Utilizados

### 1. Service Layer Pattern
- **Commands**: Operaciones de escritura (`create_from_cart`)
- **Selectors**: Operaciones de lectura (`list_for_user`, `get_by_uuid`)
- **Helpers de modulo**: `_check_item_stock()`, `_item_unit_price()` — logica extraida al nivel de modulo

### 2. Snapshot Pattern
```python
# OrderItem captura valores al momento de creacion
price = _item_unit_price(item)   # precio calculado con impuestos, INMUTABLE
OrderItem.objects.create(..., price=price)

# OrderItemCostSnapshot captura desglose de costos adicionales por item
OrderItemCostSnapshot.objects.create(
    order_item=item,
    cost_name='IVA 19%',
    computed_amount=228.00,
    ...
)
```

### 3. Transactional Consistency
```python
@transaction.atomic
def create_from_cart(...):
    # Si falla cualquier paso: rollback completo
    # on_commit para efectos secundarios (notificaciones)
```

### 4. Polymorphic Item References
```python
class OrderItem:
    variant = ForeignKey(ProductVariant, null=True)
    service_variant = ForeignKey(ServiceVariant, null=True)
    equipment_variant = ForeignKey(EquipmentVariant, null=True)
```

### 5. Queryset Optimization
```python
# Listado: .only() para reducir columnas
Order.objects.only('id', 'uuid', 'status', 'total_amount', 'created_at')

# Detalle: .prefetch_related() para evitar N+1
Order.objects.prefetch_related('items').get(uuid=uuid)

# ServiceOrderViewSet: select_related + prefetch combinados
Order.objects.filter(service_detail__isnull=False)
    .select_related('service_detail')
    .prefetch_related('items', 'timeline', 'attachments')
```

### 6. Soft Delete
```python
# SintelBaseModel provee: uuid, created_at, updated_at, is_deleted
ShippingAddress.objects.filter(user=user, is_deleted=False)
```

### 7. COD Status Branch
```python
initial_status = Order.STATUS_PENDING_PAYMENT  # igual para todos los payment_method
# COD confirma inmediatamente via CodCommands.confirm_order() -> order.status = STATUS_PAID
# WOMPI/NEQUI esperan webhook/polling -> confirm_order_payment() -> order.status = STATUS_PAID
```

---

## Consideraciones de Rendimiento

### 1. Prefetch en Retrieve
```python
Order.objects.prefetch_related('items').get(uuid=uuid)
# 2 queries totales en lugar de 1 + N (N+1 problem evitado)
```

### 2. Only Fields en Listado
```python
Order.objects.only('id', 'uuid', 'status', 'total_amount', 'created_at')
# Reduce columnas SELECT, menor I/O y deserializacion
```

### 3. Indices en Modelos
```python
# SintelBaseModel: Index en uuid, created_at
# Order.payment_method: db_index=True (filtros frecuentes por metodo de pago)
```

### 4. Calculo de precio extraido
```python
# _item_unit_price() calcula una vez, se reutiliza en calculo de total y en snapshot
unit_price = _item_unit_price(item)
total_items_price += unit_price * item.quantity
# ... mas tarde
OrderItem.objects.create(..., price=unit_price)  # no recalcula
```

---

## Validaciones y Seguridad

### 1. Validacion de Carrito
```python
if not cart or not cart.items.exists():
    raise ValidationError("El carrito esta vacio.")
```

### 2. Verificacion de Stock/Disponibilidad
```python
for item in items:
    _check_item_stock(item)
# ServiceVariant: falla si sv.is_active=False o sv.service.is_active=False
```

### 3. Ownership Check en Direccion
```python
if address.user != request.user and not request.user.is_staff:
    return Response({"detail": "..."}, status=HTTP_403_FORBIDDEN)
```

### 4. Queryset Filtering por Usuario
```python
def get_queryset(self):
    if self.request.user.is_staff:
        return OrderSelector.list_all_for_admin()
    return OrderSelector.list_for_user(self.request.user)
```

### 5. Validacion de Cupon Estricta
```python
coupon = Coupon.objects.filter(
    code=coupon_code,
    active=True,
    valid_from__lte=timezone.now(),
    valid_to__gte=timezone.now(),
).first()
if not coupon:
    raise ValidationError("El cupon no es valido o ha expirado.")
discount = min(discount, total_items_price)  # cap anti-negativo
```

### 6. Validacion de Telefono Colombiano
```python
# ShippingAddressSerializer.validate_phone_number()
# 10 digitos, inicia en '3' (celulares Colombia)
```

### 7. Restriccion de Pais
```python
# ShippingAddressSerializer.validate_country()
# Solo acepta Colombia / CO / COL — rechaza envios internacionales
```

### 8. On Delete Protection
```python
shipping_address = ForeignKey(ShippingAddress, on_delete=models.PROTECT)
# No se puede eliminar una direccion si tiene ordenes vinculadas
```

---

## Resumen de la Arquitectura

| Aspecto | Detalles |
|---------|----------|
| **Patron Principal** | Service Layer (Commands/Selectors) + Snapshot Pattern |
| **Modelos** | Order, OrderItem, OrderItemCostSnapshot, ShippingAddress, Coupon |
| **Operaciones** | Commands para crear, Selectors para consultar, helpers de modulo para precio/stock |
| **Transacciones** | @transaction.atomic en create_from_cart; on_commit para notificaciones |
| **Snapshots** | OrderItem.price inmutable (via PricingService); OrderItemCostSnapshot para desglose |
| **Polymorphism** | OrderItem referencia ProductVariant, ServiceVariant, o EquipmentVariant |
| **Optimizacion** | .prefetch_related() en detalle; .only() en listado; db_index en payment_method |
| **Seguridad** | IsBuyerOrAdmin, ownership checks, soft deletes, PROTECT FK, validaciones Colombia |
| **Metodos de pago** | WOMPI (pending), COD (processing inmediato), NEQUI (pending) |
| **Nuevas APIs** | ServiceOrderViewSet (8 acciones), DashboardMetricsView |
| **Permisos** | IsBuyerOrAdmin en orders/addresses; granular en service-orders |

---

## Historial de Cambios

### C1 — 2026-05-14 — 500 en GET /api/v1/orders/orders/ (FieldError: is_deleted)

**Sintoma:** HTTP 500. `FieldError: Cannot resolve keyword 'is_deleted'`

**Causa raiz:** `OrderSelector` y `ShippingAddressSelector` filtraban `is_deleted=False`
pero `SintelBaseModel` no tenia ese campo. Mismo bug latente en `QuotationViewSet`.

**Fix:** Agregar `is_deleted = BooleanField(default=False, db_index=True)` a `SintelBaseModel`
en `ecommerce/base_models.py`.

**Migraciones generadas (10 apps):** cart, inventory, marketing, orders, quotes, renting,
shop, technical_services, users, wompi — migration `0004_..._is_deleted_...` en orders.

**Regla derivada:** `SintelBaseModel` provee `uuid`, `created_at`, `updated_at`, `is_deleted`.

---

### 2026-06-19 — shipping_address nullable (migration 0005)

`Order.shipping_address` ahora es `null=True, blank=True`.

**Motivo:** Soportar ordenes de servicio tecnico que no requieren direccion de envio fisico.

---

### 2026-06-22 — OrderItemCostSnapshot (migration 0006)

Nuevo modelo `OrderItemCostSnapshot` para guardar desglose de costos adicionales por `OrderItem`.
Motor de costos descentralizado lo popula; no se toca desde `commands.py` directamente.

---

### 2026-06-25 — campo payment_method (migrations 0008/0009)

`Order.payment_method` agregado con `WOMPI | COD | NEQUI`, `db_index=True`, `default='WOMPI'`.
Migration 0009 ajusta los `choices` al formato final.

---

### 2026-06-27 — Validacion de cupones + payment_method + notificacion + COD

**Validacion de cupones con rango de fechas:**
- Antes: solo `active=True`. Un cupon vencido era aceptado si seguia activo.
- Ahora: filtro completo `valid_from__lte=now, valid_to__gte=now` + cap obligatorio
  `discount = min(discount, total_items_price)`.

**payment_method en create_from_cart:**
- `OrderCreateInputSerializer` incluye `payment_method` ChoiceField.
- `OrderViewSet.create_from_cart()` extrae y pasa el campo al Command.
- `OrderSerializer` expone `payment_method` en el output.
- `initial_status`: `'processing'` si COD, `'pending'` en otro caso.
- Si COD: `CodCommands.confirm_order(order)` ejecutado tras crear la orden.

**Helpers de modulo extraidos:**
- `_check_item_stock(item)`: verifica disponibilidad (ServiceVariant: is_active).
- `_item_unit_price(item)`: calcula precio via `PricingService` (productos) o
  `fixed_price / ServiceSelector` (servicios).

**Notificacion order_created en on_commit:**
- Context ampliado: `{order_uuid, status, total, user_name}`.
- `ws_group=f'user_{user.uuid}'`.

**Validaciones en ShippingAddressSerializer:**
- `validate_phone_number()`: celular colombiano 10 digitos, inicia en 3.
- `validate_country()`: normaliza CO/COL -> Colombia, rechaza paises extranjeros.
- `validate()`: strip de espacios + required check en full_name/address_line_1/city.
- `postal_code`, `state`, `address_line_2` declarados explicitamente como opcionales.

**Archivos afectados:** `orders/models.py`, `orders/services/commands.py`,
`orders/api/views.py`, `orders/api/serializers.py`.

---

### 2026-06-27 — ServiceOrderViewSet y DashboardMetricsView (nuevos archivos)

**`orders/api/service_orders.py`:**
- `ServiceOrderViewSet` con 8 acciones (ver seccion dedicada arriba).
- Delega logica a `technical_services.services` — no duplica Business Logic.
- Registrado en `api/urls.py` bajo `service-orders`.

**`orders/api/dashboard.py`:**
- `DashboardMetricsView` migrado desde `coreui.api.views`.
- `GET /api/v1/dashboard/metrics/` para panel administrativo.
- Registrado en `orders/api/dashboard_urls.py`.

---

### 2026-07-03 — Bug critico: checkout COD sin confirmar (regresion) + doc desincronizado

**Contexto:** al auditar `payment/` (ver `payment/.AGENT/docs/ARQUITECTURA_COMPLETA_PAYMENT.md`) se
encontro que este documento describia un modelo de estados (`pending`/`processing`/`paid`/...) y un
flujo de `create_from_cart()` que ya no correspondian al codigo real desde que se migro al motor de
fulfillment granular (migration `orders.0010_fulfillment_models`, `STATUS_PREPARING` etc.).

**Bug real encontrado (no solo de documentacion):** `OrderCommands.create_from_cart()` habia dejado
de llamar a `CodCommands.confirm_order()` — el bloque `if payment_method == 'COD': CodCommands
.confirm_order(order)` que este mismo documento describia como existente **no estaba en el codigo**.
Efecto: toda orden de tienda/servicio con `payment_method='COD'` se creaba y quedaba en
`STATUS_PENDING_PAYMENT` para siempre, sin `CodTransaction`, sin descuento de inventario. Ademas,
`_check_item_stock()` para `ProductVariant` era un no-op (`pass`) con un comentario que prometia
"gestionado via signals" — signal que no existe.

**Corregido:**
- `orders/services/commands.py`: restaurada la llamada a `CodCommands.confirm_order(order)` al final
  de `create_from_cart()`, y restaurado el chequeo real de stock en `_check_item_stock()` usando
  `InventorySelector.get_stock_for_variant()`.
- `payment/cod/services/commands.py`: `CodCommands.confirm_order()` ahora tambien transiciona
  `order.status = Order.STATUS_PAID` (antes no tocaba el status en absoluto) — mismo gate que usan
  Wompi/Nequi via `confirm_order_payment()` para desbloquear el motor de fulfillment.
- Eliminado `orders/services/commands.py.bak` (version anterior, ya superada por el fix).
- Tests nuevos: `orders.tests.CodCheckoutEndToEndTestCase` (2 tests — comando directo y endpoint HTTP
  real `/api/v1/orders/orders/create_from_cart/`), mas la actualizacion de
  `payment.tests.PaymentInventoryIntegrationTestCase.test_cod_confirm_order_deducts_stock_immediately`
  para verificar `order.status == STATUS_PAID`.
- Documentacion: este archivo (enum de status, flujo de checkout, tabla de diferencias, COD Status
  Branch) y `ARQUITECTURA_COMPLETA_PAYMENT.md` seccion 2.5, sincronizados con el codigo real.

**Bug adicional del mismo tipo, en el mismo archivo revisado:** `ServiceOrderViewSet.confirm_cod`
(`orders/api/service_orders.py`) tambien comparaba `order.status != 'pending'` (string legacy) en vez
de `Order.STATUS_PENDING_PAYMENT` — confirmar un pago COD en sitio para un servicio tecnico siempre
devolvia 400. Es la tercera instancia del mismo bug encontrada en esta sesion (las otras dos: Wompi y
Nequi `initialize()`, ver `ARQUITECTURA_COMPLETA_PAYMENT.md`). Corregido igual. Cubierto por
`orders.tests.ServiceOrderConfirmCodTestCase`.

**Regla derivada:** cuando un documento SSoT describe una llamada o comportamiento ("Llamado desde
X"), verificar que X realmente lo invoque en el codigo actual antes de asumirlo — los documentos de
este proyecto han quedado desincronizados mas de una vez tras refactors incompletos (mismo patron ya
visto en `payment/`, ver su documento). Ademas, el string legacy `'pending'` parece haber quedado
regado por multiples archivos como copy-paste de un modelo de estados antiguo — vale la pena un grep
global de `'pending'`/`"pending"` contra `order.status` en el resto del proyecto (frontend incluido)
si se quiere cerrar el patron por completo; no se hizo en esta sesion por estar fuera del archivo
que se estaba auditando.

### 2026-07-03 (Fase 6 — auditoria de base de datos) — N+1 real en OrderViewSet.list()/retrieve()

**Bug encontrado y medido empiricamente:** `OrderSelector.list_for_user()`/`list_all_for_admin()`
(usadas por `OrderViewSet.list()` **y** `.retrieve()`, ya que el ViewSet no sobreescribe
`get_object()`) hacian `.only('id', 'uuid', 'status', 'total_amount', 'created_at')` sin ningun
`select_related`/`prefetch_related`, pese a que `OrderSerializer` siempre serializa `items`
(reverse FK), `shipping_address` (FK), y `shipment` (OneToOne) + `shipment.dispatch_center`/
`carrier`/`driver` (3 FK mas). El `.only()` tampoco cubria `payment_method`, `discount_amount`,
`tracking_number` ni `shipping_address_id`, que el serializer si necesita — cada acceso a esos
campos disparaba una query de recarga de campo diferido.

**Medicion real** (test con `CaptureQueriesContext`, 2 ordenes con item+shipment+carrier
completos): **19 queries** antes del fix, escalando linealmente con la cantidad de ordenes en la
pagina.

**Corregido:** `OrderSelector` ahora usa `select_related('shipping_address', 'shipment',
'shipment__dispatch_center', 'shipment__carrier', 'shipment__driver')` +
`prefetch_related('items')`, sin `.only()` parcial. Resultado: **3 queries constantes**
(1 count de paginacion + 1 select principal con joins + 1 prefetch de items), sin importar cuantas
ordenes se listen. `OrderSelector.DETAIL_FIELDS` (constante nunca usada en ningun lado) se elimino
en el mismo cambio.

**Test de regresion:** `orders.tests.OrderFulfillmentAPITestCase.test_list_orders_has_no_n_plus_1`
usa `assertNumQueries(3)` — fallara de inmediato si alguien reintroduce el N+1.

**Ademas:** se agrego `db_index=True` a `Order.status` (no lo tenia, pese a filtrarse
constantemente en metricas de dashboard y en `ShopSummaryProvider`). Migracion
`orders/migrations/0012_alter_order_status.py`.

---

### 2026-07-17 — "Mis Direcciones" 404 + sincronizacion con la direccion del registro

**Sintoma reportado:** `Mi Cuenta > Mis Direcciones` (`CustomerAddressView.vue`) devolvia
404 en las 4 llamadas (list/create/set-default/delete). Ademas, la direccion capturada
durante `/register` (constructor colombiano tipo de via/numero/generadora/placa) nunca
aparecia ahi, obligando al usuario a re-escribirla.

**Causa raiz del 404 — simple mismatch de ruta, no un endpoint faltante:**
`orders/api/urls.py` registra `router.register(r'addresses', ShippingAddressViewSet,
basename='shipping-address')` -> la URL real es `/api/v1/orders/addresses/`. El
`basename` solo nombra el reverse-URL interno de DRF, no cambia el path. El frontend
llamaba `orders/shipping-addresses/` en sus 4 requests — ruta que nunca existio en
ningun lado del proyecto.

**Causa raiz de la desincronizacion con el registro:**
`AccountCommands.register_user()`/`.create_from_verified_payload()` (`accounts/services/
commands.py`) solo escribian `direccion`/`ciudad`/`pais` a `UserProfile.address`/`.city`/
`.country` — nunca creaban una fila en `orders.ShippingAddress`. `orders.ShippingAddress`
ya era el modelo oficial y completamente conectado (Checkout ya exige
`shipping_address_uuid` de este modelo) — no se creo ningun modelo nuevo, solo se cerro el
puente que faltaba entre el registro y el.

**Corregido (backend):**
- `orders/models.py::ShippingAddress` — campo nuevo `label` (migration 0015).
- `orders/services/commands.py` — nueva clase `ShippingAddressCommands` (Service Layer que
  antes no existia para este modelo) con `create()`/`update()`/`set_as_default()`,
  garantizando SIEMPRE "solo un default por usuario" sin importar la ruta de entrada.
- `orders/api/views.py::ShippingAddressViewSet` — `perform_create`/`perform_update` ahora
  delegan a los Commands; nuevo action `set-default`.
- `orders/api/serializers.py::ShippingAddressSerializer` — campo `label`; ademas se
  corrigio un bug preexistente en `validate()` que no respetaba `self.partial` (ver
  seccion de serializers arriba).
- `orders/services/selectors.py::ShippingAddressSelector.LIST_FIELDS` — completado (N+1
  preexistente, ver seccion de selectors arriba).
- `accounts/services/commands.py` — nuevo helper de modulo
  `_create_default_shipping_address_from_registration(user, kyc_data, phone_number)`,
  llamado desde **ambos** `register_user()` y `create_from_verified_payload()` justo
  despues de crear el `UserProfile`. Reutiliza los mismos datos ya capturados en el
  registro (`profile_extra['address']`/`['city']`/`['country']`) — nunca se piden de
  nuevo. Si el registro no incluyo una direccion estructurada (casos legacy/admin sin
  `KycRegistrationFieldsMixin`), no se crea nada — el usuario ve el estado vacio con su CTA.

**Corregido (frontend):** `CustomerAddressView.vue` — las 4 llamadas API corregidas a
`orders/addresses/`; campo `label` agregado al formulario y usado como titulo de card;
`confirm()` nativo del navegador reemplazado por confirmacion inline (`pendingDelete` +
bloque `.addr-confirm-delete`, mismo patron `bg-danger-subtle` que `UserList.vue` — el
proyecto prohibe dialogs nativos); "Usar como predeterminada" ahora llama al action
`set-default` en vez de un PATCH completo.

**Fuera de alcance (diferido explicitamente):** pre-rellenar la direccion principal en los
wizards independientes de Renting/Quotes/Technical Services — cada uno captura direccion
inline en su propio flujo ya aprobado en sesiones anteriores; tocarlos es un cambio de UX
en 3 flujos distintos, no un bug de esta sesion.

**Tests:** `orders.tests.ShippingAddressBookTestCase` (4 — path correcto, primera
direccion=default automatico, `set-default` desmarca la anterior, `PATCH` parcial con solo
`is_default` ya no rompe) y `orders.tests.RegistrationCreatesDefaultShippingAddressTestCase`
(1 — `create_from_verified_payload` crea la `ShippingAddress` default con los datos
correctos). Suite completa `orders`/`accounts`/`kyc` corrida sin regresiones nuevas.

**Verificacion end-to-end real (Playwright, contra el dev DB real):** registro completo de
un usuario nuevo con direccion estructurada -> la direccion aparece de inmediato en
`/mi-cuenta/direcciones` marcada "Direccion Principal", sin re-pedirla; creacion de una 2da
direccion + click en "Seleccionar como direccion de envio" -> la 1ra pierde el badge de
default (invariante confirmada en la UI real, no solo en tests); eliminacion de una
direccion via la confirmacion inline (nunca `confirm()` nativo). Datos de prueba
desechables eliminados al terminar.

**Regla derivada (nota tecnica de la sesion, no arquitectura del proyecto):** al verificar
con Playwright contra contenedores Docker en Windows, el patron previamente documentado
`--host-resolver-rules=MAP localhost:8000 ecommerce_sintel_django:8000` es innecesario
(y rompe la resolucion DNS) cuando Docker Desktop ya publica los puertos directamente en
`localhost` del host — usar `chromium.launch()` sin ese flag. Asimismo, un marker file
para el handoff de codigos OTP debe escribirse con un path Windows explicito (ej.
`C:/tmp/...`) en vez de `/tmp/...`: Node.js nativo en Windows resuelve `/tmp/...` como
`C:\tmp\...`, mientras que Git Bash/MSYS resuelve su propio `/tmp` como
`C:\Users\<usuario>\AppData\Local\Temp\...` — dos ubicaciones distintas que no coinciden.

---

**Ultima actualizacion:** 2026-07-17 (Fix "Mis Direcciones" 404 + auto-creacion de
direccion principal desde el registro; Fase 6 de 2026-07-03 sigue vigente sin cambios)
