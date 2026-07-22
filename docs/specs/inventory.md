---
app_name: inventory
layer: service_layer
doc_type: spec
critical_rules:
  - select_for_update_mandatory
  - decimal_money
  - transaction_atomic
  - no_physical_delete
associated_models:
  - StockRecord
  - InventoryTransaction
cross_app_dependencies:
  - shop
  - orders
permissions_required:
  - IsAdminUser
---

# App: inventory

## Modelo StockRecord

Un `StockRecord` por `ProductVariant`. Controla el stock disponible.

```python
class StockRecord(SintelBaseModel):
    variant = models.OneToOneField(ProductVariant, related_name='stock_record')
    stock   = models.PositiveIntegerField(default=0)
    # sku es un shortcut desnormalizado para logging/reporting
```

## Command: InventoryCommands.register_entry (Entrada de Stock)

```python
@staticmethod
@transaction.atomic
def register_entry(dto: StockAdjustmentDTO) -> InventoryTransactionResultDTO:
    # OBLIGATORIO: bloqueo pesimista para evitar race conditions
    stock_record = StockRecord.objects.select_for_update().get(uuid=dto.stock_record_uuid)

    current     = InventorySelector.get_current_stock(stock_record.pk)
    new_balance = InventoryKardex.calculate_new_balance(current, 'ENTRY', dto.quantity)

    stock_record.stock = new_balance
    stock_record.save(update_fields=['stock', 'updated_at'])

    InventoryTransaction.objects.create(
        stock_record=stock_record,
        movement_type='ENTRY',
        quantity=dto.quantity,
        balance_after=new_balance,
    )

    # Actualizar cache en on_commit (no antes)
    cache_key = f"stock_record_balance_{stock_record.id}"
    transaction.on_commit(lambda ck=cache_key, nb=new_balance: cache.set(ck, nb, timeout=300))
```

## Command: InventoryCommands.register_exit (Salida de Stock)

```python
@staticmethod
@transaction.atomic
def register_exit(dto: StockAdjustmentDTO) -> InventoryTransactionResultDTO:
    stock_record = StockRecord.objects.select_for_update().get(uuid=dto.stock_record_uuid)

    current = InventorySelector.get_current_stock(stock_record.pk)
    # Valida que haya stock suficiente ANTES de decrementar
    InventoryKardex.validate_stock_availability(current, dto.quantity)
    new_balance = InventoryKardex.calculate_new_balance(current, 'EXIT', dto.quantity)

    stock_record.stock = new_balance
    stock_record.save(update_fields=['stock', 'updated_at'])
```

## Selector: InventorySelector

```python
class InventorySelector:
    @staticmethod
    def get_current_stock(stock_record_pk: int) -> int:
        # Lee desde cache primero; fallback a BD
        cache_key = f"stock_record_balance_{stock_record_pk}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        record = StockRecord.objects.only('stock').get(pk=stock_record_pk)
        cache.set(cache_key, record.stock, timeout=300)
        return record.stock

    @staticmethod
    def get_stock_for_variant(variant) -> int:
        try:
            return variant.stock_record.stock
        except StockRecord.DoesNotExist:
            return 0
```

## Regla Critica: select_for_update Obligatorio en Commands

Cualquier Command que lea-y-modifique stock DEBE usar `select_for_update()`:

```python
# CORRECTO
stock_record = StockRecord.objects.select_for_update().get(uuid=uuid)

# INCORRECTO — race condition bajo carga concurrente
stock_record = StockRecord.objects.get(uuid=uuid)
stock_record.stock -= qty
stock_record.save()
```

## InventoryTransaction: Kardex Inmutable

Cada movimiento crea un registro de `InventoryTransaction`. Nunca se editan ni eliminan. Sirven como auditoria inmutable (Kardex).

```python
MOVEMENT_TYPES = [
    ('ENTRY', 'Entry (Purchase/Restock)'),
    ('EXIT',  'Exit (Sale/Adjustment)'),
    ('ADJUSTMENT', 'Manual Adjustment'),
]
```
