---
app_name: orders
layer: service_layer
doc_type: spec
critical_rules:
  - decimal_money
  - transaction_atomic
  - stock_pre_check
  - on_commit_notify
  - soft_delete_double
associated_models:
  - Order
  - OrderItem
  - ShippingAddress
  - Coupon
cross_app_dependencies:
  - inventory
  - cart
  - wompi
  - notifications
  - technical_services
  - renting
permissions_required:
  - IsAuthenticatedActiveUser
  - IsAdminUser
---

# App: orders

## Estados de Orden (Order.status)

```
pending -> processing -> paid -> shipped -> delivered
                    \-> cancelled
```

- `pending`: creada, esperando pago (Wompi/Nequi)
- `processing`: COD aprobado o pago recibido
- `paid`: confirmado por webhook Wompi
- `shipped`: despachado
- `delivered`: entregado
- `cancelled`: cancelado

## Metodos de Pago

```python
PAYMENT_METHOD_CHOICES = [
    ('WOMPI', 'Wompi (online)'),
    ('COD',   'Pago contra entrega'),
    ('NEQUI', 'Nequi Push'),
]
```

El `initial_status` al crear la orden depende del `payment_method`:
- `COD` -> `status='processing'` inmediatamente
- `WOMPI` / `NEQUI` -> `status='pending'` hasta confirmar webhook

## Command: OrderCommands.create_from_cart

```python
@staticmethod
@transaction.atomic
def create_from_cart(user, shipping_address, coupon_code=None, payment_method='WOMPI') -> Order:
    cart = Cart.objects.prefetch_related('items__variant__product').filter(user=user).first()
    if not cart or not cart.items.exists():
        raise ValidationError("El carrito esta vacio.")

    items = list(cart.items.all())

    # Validar stock ANTES de crear la orden
    for item in items:
        _check_item_stock(item)

    # Calcular precios con Decimal — nunca float
    total_items_price = Decimal('0.00')
    for item in items:
        total_items_price += _item_unit_price(item) * item.quantity

    # Validar cupon: ventana temporal obligatoria, descuento nunca supera el total
    discount = Decimal('0.00')
    if coupon_code:
        now = timezone.now()
        coupon = Coupon.objects.filter(
            code=coupon_code,
            active=True,
            valid_from__lte=now,
            valid_to__gte=now,
        ).first()
        if not coupon:
            raise ValidationError("El cupon no es valido o ha expirado.")
        if coupon.is_percentage:
            discount = (total_items_price * coupon.discount_value) / 100
        else:
            discount = coupon.discount_value
        discount = min(discount, total_items_price)  # nunca negativo

    total = total_items_price - discount

    # Crear orden
    initial_status = 'processing' if payment_method == 'COD' else 'pending'
    order = Order.objects.create(
        user=user,
        shipping_address=shipping_address,
        status=initial_status,
        payment_method=payment_method,
        total_amount=total,
        discount_amount=discount,
    )

    # Notificar en on_commit
    _user = user
    _ctx  = {
        'order_uuid': str(order.uuid),
        'status': order.status,
        'total': str(order.total_amount),
        'user_name': _user.get_short_name(),
    }
    transaction.on_commit(
        lambda: NotificationCommands.dispatch_notification(
            user=_user, template_slug='order_created', context=_ctx,
            ws_group=f'user_{_user.uuid}',
        )
    )
    return order
```

### Reglas de Cupon (obligatorias)

- Filtrar siempre por `active=True`, `valid_from__lte=now`, `valid_to__gte=now`.
- Si `coupon_code` fue enviado pero no existe cupon valido → `ValidationError`.
- `discount = min(discount_calculado, total_items_price)` — el descuento nunca puede superar el total de items.
- Nunca generar `total < 0`.

## Validacion de Stock (_check_item_stock)

```python
def _check_item_stock(item):
    if item.variant:
        stock = InventorySelector.get_stock_for_variant(item.variant)
        if stock < item.quantity:
            raise ValidationError(f"Sin existencias suficientes para: {item.variant.sku}")
    elif item.service_variant:
        sv = item.service_variant
        if not sv.is_active or not sv.service.is_active:
            raise ValidationError(f"El servicio {sv.sku} ya no esta disponible.")
```

## Calculo de Precio (_item_unit_price) — Solo Decimal

```python
def _item_unit_price(item) -> Decimal:
    if item.variant:
        from shop.services.pricing_service import PricingService
        return PricingService.calculate_variant_price(item.variant, include_active_taxes=True)
    if item.service_variant:
        sv = item.service_variant
        if sv.fixed_price is not None:
            return Decimal(str(sv.fixed_price))
        from technical_services.services.selectors import ServiceSelector
        return Decimal(str(ServiceSelector.get_variant_quotation(sv)['total_price']))
    return Decimal('0.00')
```

## OrderItem: FK Polimorfico

`OrderItem` acepta tres tipos de variante (mutuamente excluyentes):

```python
class OrderItem(SintelBaseModel):
    order             = models.ForeignKey(Order, related_name='items')
    variant           = models.ForeignKey(ProductVariant, null=True, blank=True)   # producto fisico
    service_variant   = models.ForeignKey(ServiceVariant, null=True, blank=True)   # servicio tecnico
    equipment_variant = models.ForeignKey(EquipmentVariant, null=True, blank=True) # equipo en renta

    # Snapshots inmutables al momento de la orden
    item_name = models.CharField(max_length=255)
    sku       = models.CharField(max_length=100)
    quantity  = models.PositiveIntegerField()
    price     = models.DecimalField(max_digits=12, decimal_places=2)  # Decimal siempre
```

## Soft-Delete en Ordenes

Las ordenes nunca se eliminan fisicamente. Para cancelar:

```python
@transaction.atomic
def cancel_order(order: Order) -> Order:
    order.status = 'cancelled'
    order.save(update_fields=['status', 'updated_at'])
    # Devolver stock si aplica
    for item in order.items.filter(is_deleted=False):
        if item.variant:
            InventoryCommands.register_entry(...)
    return order
```
