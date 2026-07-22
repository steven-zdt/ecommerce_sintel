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
| `api/views.py` | StockRecordViewSet: movements(), adjust_stock() |
| `services/commands.py` | InventoryCommands: register_entry(), register_exit() |
| `services/selectors.py` | InventorySelector: get_current_stock(), is_available(), get_stock_record_for_variant() |
| `services/kardex.py` | InventoryKardex: calculate_new_balance(), validate_stock_availability() |

## Patrones obligatorios en esta app

- **Fuente de verdad del stock:** `InventoryTransaction.balance_after` — no `ProductVariant.stock`
- `register_exit()` valida stock antes de proceder — lanza `ValidationError` si insuficiente
- `InventoryTransaction` es append-only: nunca editar ni borrar registros existentes
- Toda variante nueva (Product, Equipment, Service) necesita un `StockRecord` propio
- `StockRecord` usa `GenericForeignKey` → no hacer FK directas desde otras apps a esta tabla
- Usar siempre `InventorySelector.is_available()` antes de confirmar pedidos o pagos

## Integración con otras apps

```python
# En orders, wompi, renting, technical_services:
from inventory.services.selectors import InventorySelector
from inventory.services.commands import InventoryCommands

if not InventorySelector.is_available(variant, qty):
    raise ValueError("Stock insuficiente")

stock_record = InventorySelector.get_stock_record_for_variant(variant)
InventoryCommands.register_exit(stock_record, qty, reference="Order XYZ")
```

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
