---
app_name: payment
layer: integration
doc_type: spec
critical_rules:
  - confirm_order_payment_ssot
  - idempotent_confirm
  - on_commit_notify
  - decimal_money
  - inventory_deduct_physical_only
associated_models:
  - Transaction
  - CodTransaction
  - NequiTransaction
cross_app_dependencies:
  - orders
  - inventory
  - notifications
  - technical_services
permissions_required:
  - IsAuthenticatedActiveUser (initialize, cards)
  - AllowAny (webhook)
---

# App: payment

## Estructura de Paquetes

```
payment/
  online/
    api/views.py          # WompiPaymentViewSet: initialize(), webhook(), transaction_status()
    services/commands.py  # WompiCommands, PaymentCommands
  cod/
    services/commands.py  # CodCommands: confirm_order(), mark_delivered(), cancel()
  nequi/
    services/commands.py  # NequiCommands
  shared/
    commands.py           # confirm_order_payment() — SSoT post-aprobacion
  models.py               # Transaction, CodTransaction, NequiTransaction, TokenizedCard
```

## SSoT de Confirmacion: confirm_order_payment

`payment/shared/commands.py` es la funcion de verdad unica para toda logica post-aprobacion.
**No duplicar esta logica en Wompi, Nequi ni COD.**

```python
@transaction.atomic
def confirm_order_payment(order: Order, reference: str) -> None:
    from technical_services.services.commands import ServiceCommands
    from notifications.services.commands import NotificationCommands

    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status == 'paid':
        logger.info("Pago ya confirmado, no se descuenta inventario de nuevo | order=%s", order.uuid)
        return

    order.status = 'paid'
    order.save(update_fields=['status', 'updated_at'])

    ServiceCommands.confirm_slot_on_payment(order)
    _deduct_inventory_for_order(order, reference=f"Order {order.uuid} - {reference}")

    _user  = order.user
    _uuid  = str(order.uuid)
    _total = str(order.total_amount)
    transaction.on_commit(
        lambda: NotificationCommands.dispatch_notification(
            user=_user,
            template_slug='order_paid',
            context={'order_uuid': _uuid, 'status': 'paid', 'total': _total,
                     'user_name': _user.get_short_name()},
            ws_group=f'user_{_user.uuid}',
        )
    )
```

### Reglas obligatorias de confirm_order_payment

1. **Idempotente**: si `order.status == 'paid'` ya, retornar sin mutar nada.
2. **select_for_update**: re-obtener la orden con lock antes de mutar.
3. **Solo inventario fisico**: `_deduct_inventory_for_order` omite `service_variant` (sin StockRecord fisico).
4. **Notificacion en on_commit**: slug `order_paid`, nunca antes del commit.

## Deduccion de Inventario (_deduct_inventory_for_order)

```python
def _deduct_inventory_for_order(order: Order, reference: str) -> None:
    for item in order.items.select_for_update().all():
        variant = item.variant or item.equipment_variant
        if variant is None:
            continue   # service_variant: sin StockRecord, omitir
        record = _get_stock_record(variant)
        if record:
            InventoryCommands.register_exit(
                StockAdjustmentDTO(
                    stock_record_uuid=record.uuid,
                    quantity=item.quantity,
                    reference=reference,
                )
            )
```

## Flujo COD (CodCommands)

```python
@transaction.atomic
def confirm_order(order: Order) -> CodTransaction:
    _deduct_inventory_for_order(order, reference=f"COD Order {order.uuid}")
    cod_tx = CodTransaction.objects.create(order=order)

    transaction.on_commit(
        lambda: NotificationCommands.dispatch_notification(
            user=_user,
            template_slug='order_cod_confirmed',
            context={'order_uuid': _uuid, 'total': _total, 'user_name': _user.get_short_name()},
            ws_group='admin',
        )
    )
    return cod_tx
```

COD usa `_deduct_inventory_for_order` de `payment/shared/commands.py` directamente.
**No llama a `confirm_order_payment`** porque COD no pasa por webhook externo.

## Idempotencia del Webhook Wompi

```python
# En WompiCommands.process_webhook_notification
previous_status = wompi_tx.status
if previous_status == "APPROVED" and new_status == "APPROVED":
    logger.info("Wompi webhook duplicado ignorado | reference=%s", reference)
    return  # idempotente — no re-ejecutar confirm_order_payment

wompi_tx.status   = new_status
wompi_tx.wompi_id = wompi_id
wompi_tx.save(update_fields=["status", "wompi_id", "updated_at"])

if new_status == "APPROVED":
    PaymentCommands.confirm_payment(wompi_tx)
```

**Doble capa de idempotencia:**
1. El webhook ignora `APPROVED` repetido a nivel de `Transaction`.
2. `confirm_order_payment` ignora si `order.status == 'paid'`.

## Validacion de Stock en Wompi (PaymentCommands.confirm_payment)

```python
@transaction.atomic
def confirm_payment(wompi_transaction: Transaction) -> None:
    if wompi_transaction.status != "APPROVED":
        return

    order = wompi_transaction.order
    for item in order.items.select_for_update().all():
        variant = item.variant or item.equipment_variant   # omitir service_variant
        if variant and not _has_sufficient_stock(variant, item.quantity):
            wompi_transaction.status = "ERROR"
            wompi_transaction.save(update_fields=["status", "updated_at"])
            raise ValueError(f"Stock insuficiente para {item.item_name}")

    confirm_order_payment(order=order, reference=f"Wompi {wompi_transaction.wompi_id}")
```

## Flujo de Estados

```
Transaction: PENDING -> APPROVED | DECLINED | VOIDED | ERROR
Order:       pending  -> paid (Wompi/Nequi APPROVED)
             pending  -> processing (COD inmediato)
```
