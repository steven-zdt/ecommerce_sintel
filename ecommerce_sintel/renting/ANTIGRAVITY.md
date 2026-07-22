# App: renting — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
ecommerce_sintel/renting/.AGENT/docs/ARQUITECTURA_COMPLETA_RENTIG.md
```

## Responsabilidad de esta app

Catálogo de equipos en alquiler. Pricing flexible por día u hora.
Integra con Inventory para disponibilidad y con Orders para crear contratos de renta.

## Archivos clave

| Archivo | Propósito |
|---------|-----------|
| `models.py` | RentingCategory, RentingBrand, Equipment, EquipmentVariant, EquipmentImage, EquipmentReview, RentalLabor |
| `api/views.py` | EquipmentViewSet (ReadOnly), RentingCategoryViewSet, RentingBrandViewSet, RentalLaborViewSet |
| `api/serializers.py` | EquipmentSerializer, EquipmentVariantSerializer, RentalLaborSerializer |
| `services/commands.py` | RentingCommands: process_rental_order() |
| `services/selectors.py` | RentingSelector: get_by_uuid(), list_available_equipment() |
| `services/summary.py` | RentingSummaryProvider: get_summary() → stats para marketing |

## Patrones obligatorios en esta app

- `EquipmentVariant` tiene pricing dual: `rental_price_per_day` Y/O `rental_price_per_hour` — validar que al menos uno esté presente
- `process_rental_order()` usa `@transaction.atomic`: valida stock → calcula precio → crea Order+OrderItem → WebSocket on_commit
- Validar modo de renta: días requiere `rental_price_per_day`, horas requiere `rental_price_per_hour`
- Stock gestionado por Inventory (StockRecord con GFK a EquipmentVariant)
- `RentalLabor` son servicios adicionales (operador, instalación) con `price_per_hour`
- `RentingSummaryProvider.get_summary()` es consumido por marketing — mantener la firma del dict

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
