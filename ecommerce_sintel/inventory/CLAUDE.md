# App: inventory — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
ecommerce_sintel/inventory/.AGENT/docs/ARQUITECTURA_COMPLETA_INVENTORY.md
```

## Responsabilidad de esta app

Sistema de control de stock (kardex). Gestiona disponibilidad de ProductVariant,
EquipmentVariant y ServiceVariant mediante un único modelo polimórfico (StockRecord).

## Archivos clave

| Archivo | Propósito |
|---------|-----------|
| `models.py` | StockRecord (GenericFK), InventoryTransaction (append-only kardex) |
| `api/views.py` | StockRecordViewSet: `transactions()`, `adjust-stock()` |
| `services/commands.py` | `InventoryCommands`: `register_entry(dto)`, `register_exit(dto)` |
| `services/selectors.py` | `StockRecordSelector`: `list_all_active()`, `list_all_for_admin()`, `get_by_uuid()`. `InventorySelector`: `get_current_stock()`, `get_stock_for_variant()`, `list_movements()` |
| `services/dtos.py` | `StockAdjustmentDTO(stock_record_uuid, quantity, reference)`, `InventoryTransactionResultDTO` |
| `services/kardex.py` | `InventoryKardex`: `calculate_new_balance()`, `validate_stock_availability()` |

> **[CORREGIDO 2026-07-03]** La version anterior de este archivo mencionaba
> `InventorySelector.is_available()` y `InventorySelector.get_stock_record_for_variant()` —
> **ninguno de los dos existe** en `inventory/services/selectors.py`. Verificado leyendo el
> archivo completo. Usar `get_current_stock()` / `get_stock_for_variant()` como se documenta
> abajo.

## Patrones obligatorios en esta app

- **Fuente de verdad del stock:** `InventoryTransaction.balance_after` (con cache de 5 min por
  `StockRecord`) — no `ProductVariant.stock` (ese campo es solo una copia cacheada/legacy).
- `register_exit()` valida stock antes de proceder — lanza `ValidationError` (via
  `InventoryKardex.validate_stock_availability`) si insuficiente.
- `InventoryTransaction` es append-only: nunca editar ni borrar registros existentes.
- Toda variante nueva (Product, Equipment, Service) necesita un `StockRecord` propio
  (`content_type` + `object_id` = `variant.uuid`).
- `StockRecord` usa `GenericForeignKey` → no hacer FK directas desde otras apps a esta tabla.
- El **unico** punto del sistema que debe llamar `InventoryCommands.register_exit()` por un pago
  es `payment.shared.commands._deduct_inventory_for_order()` — ninguna otra app debe descontar
  inventario post-pago directamente (ver `payment/.AGENT/docs/ARQUITECTURA_COMPLETA_PAYMENT.md`).

## Integración con otras apps (patron real, verificado)

```python
from inventory.services.selectors import InventorySelector
from inventory.services.commands import InventoryCommands
from inventory.services.dtos import StockAdjustmentDTO

# Consultar stock disponible (acepta un ID de StockRecord o directamente la instancia variant):
stock = InventorySelector.get_current_stock(variant)   # o get_stock_for_variant(variant)
if quantity_requested > stock:
    raise ValidationError("Stock insuficiente")

# Descontar stock (dentro de un @transaction.atomic, tipicamente en payment/shared/commands.py):
InventoryCommands.register_exit(
    StockAdjustmentDTO(
        stock_record_uuid=stock_record.uuid,
        quantity=quantity,
        reference="Order XYZ",
    )
)
```

`register_entry()`/`register_exit()` reciben un `StockAdjustmentDTO`, **no** argumentos
posicionales sueltos (`stock_record, qty, reference` como decia una version anterior de este
archivo — esa firma nunca existio en el codigo).

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
