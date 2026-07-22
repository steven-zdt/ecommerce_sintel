# App: renting — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
ecommerce_sintel/renting/.AGENT/docs/ARQUITECTURA_COMPLETA_RENTIG.md
```

## Responsabilidad de esta app

Catálogo de equipos en alquiler. Pricing flexible por día u hora.
Disponibilidad autocontenida via `RentalPeriod` + `AvailabilityEngine` (NO depende de
Inventory/StockRecord — ver ARQUITECTURA_COMPLETA_RENTIG.md, seccion "Desacoplamiento de
Inventory"). Integra con Orders en dos puntos: el flujo legacy `process_rental_order()`
(sin wizard, sin gate de pago — ver nota abajo) y `OrderCommands.create_from_rental()`,
llamado desde `confirm_payment()`/`approve_manual_validation()` (ver regla PaymentResult).

## Archivos clave

| Archivo | Propósito |
|---------|-----------|
| `models.py` | RentingCategory, RentingBrand, Equipment, EquipmentVariant, EquipmentImage, EquipmentReview, RentalLabor, RentalRequest, RentalPeriod, + catalogo enriquecido de Equipment (migracion 0022): RentalIncludedItem, RentalExcludedItem, RentalFeature, RentalSpecificationGroup/RentalSpecification, RentalRequirement, RentalServiceIncluded, RentalOptionalService, RentalFAQ, RentalVideo, RentalDocument, EquipmentLogisticsConfig, RentalCostRule/RentalCostAssignment |
| `api/views.py` | EquipmentViewSet (availability/calendar/timeline + check-availability), RentalRequestViewSet (approve/reject/mark-delivered/mark-returned/release-period), RentingCategoryViewSet, RentingBrandViewSet, RentalLaborViewSet |
| `api/serializers.py` | EquipmentSerializer, EquipmentVariantSerializer, RentalLaborSerializer, RentalRequestSerializer |
| `services/commands.py` | `RentingCommands.process_rental_order()` (legacy); `RentalRequestCommands` (create_request, confirm_payment, approve_manual_validation, reject_request, activate_period, complete_period, release_period, release_on_payment_failure) |
| `services/selectors.py` | RentingSelector: get_by_uuid(), list_available_equipment(), check_availability() (wrapper de AvailabilityEngine) |
| `services/availability.py` | `AvailabilityEngine`: is_available(), find_next_available_slot(), generate_schedule() — motor real de disponibilidad |
| `services/display.py` | Vocabulario de 7 estados visibles (display_status_for_request/period) |
| `services/summary.py` | RentingSummaryProvider: get_summary() → stats para marketing |
| `tasks.py` | `expire_abandoned_pending_payment_requests` (Celery beat, sembrada via migration 0020) |

## Patrones obligatorios en esta app

- `EquipmentVariant` tiene pricing dual: `rental_price_per_day` Y/O `rental_price_per_hour` — validar que al menos uno esté presente
- `process_rental_order()` (legacy, sin wizard) usa `@transaction.atomic`: valida stock → calcula precio → crea Order+OrderItem → WebSocket on_commit
- Validar modo de renta: días requiere `rental_price_per_day`, horas requiere `rental_price_per_hour`
- **Disponibilidad NO usa Inventory/StockRecord** — `AvailabilityEngine` calcula contra `RentalPeriod` (calendario propio) y `EquipmentVariant.stock` (pool fisico simple)
- `pending_payment` NUNCA bloquea agenda — el `RentalPeriod` solo se crea en `confirm_payment()` (pago online aprobado) o `approve_manual_validation()` (COD aprobado por admin), los dos unicos puntos con lock
- **Regla PaymentResult (unico punto de decision):** `create_request()`/`process_payment_selection()` NO envian correo/WhatsApp al cliente ni crean Order/Operation — solo existe la intencion de compra. Todo (RentalPeriod, `Order`+`OrderItem` via `OrderCommands.create_from_rental()`, `OperationTicket`, `RentalOperation`, email+WhatsApp) nace en `confirm_payment()`/`approve_manual_validation()` cuando el PaymentResult es APPROVED. Si es DECLINED/VOIDED/ERROR, `release_on_payment_failure()` marca `cancelled` y notifica el rechazo — nunca crea Order/Operation/RentalPeriod. Wompi no tiene estado `EXPIRED` (ver `payment/.AGENT/docs/ADR_001_MIGRACION_API_WOMPI.md`) — transacciones abandonadas se manejan via `reconcile_pending_wompi_transactions`, no como un status nuevo.
- `RentalLabor` son servicios adicionales (operador, instalación) con `price_per_hour`
- `RentingSummaryProvider.get_summary()` es consumido por marketing — mantener la firma del dict
- **`Equipment` es el aggregate root, `EquipmentVariant` es SOLO inventario/precio** (regla vigente desde migracion `0022_catalog_detail_models`, 2026-07-16): todo el contenido descriptivo (Galeria/`EquipmentImage`, Incluye/`RentalIncludedItem`, No incluye/`RentalExcludedItem`, Caracteristicas/`RentalFeature`, Especificaciones/`RentalSpecificationGroup`+`RentalSpecification`, Requisitos/`RentalRequirement`, Servicios incluidos/`RentalServiceIncluded`, Servicios opcionales/`RentalOptionalService`, Documentacion/`RentalDocument`, Videos/`RentalVideo`, FAQ/`RentalFAQ`, SEO/`meta_title` etc.) vive exclusivamente en `Equipment`. `EquipmentVariant` solo tiene `sku, rental_price_per_day, rental_price_per_hour, stock, is_active`. Ningun Equipment hereda de otro — no existen plantillas/config compartida entre equipos. Ver ARQUITECTURA_COMPLETA_RENTIG.md para el detalle completo.
- **"Costos" (`RentalCostRule`/`RentalCostAssignment`, FK a Variant) != "Logistica" (`EquipmentLogisticsConfig`, FK a Equipment)** — comparten nombre por accidente, no el mismo dato. Logistica son costos operativos fijos del equipo (delivery/pickup/install/etc). Costos son reglas de PRECIO (IVA/descuento/deposito/seguro/recargo) que legitimamente pueden variar por variante dentro del mismo Equipment — no es una violacion de la regla de arriba, ya que son extension de precio, no contenido.
- **NO existen reglas de costo globales/heredadas/compartidas** (correccion definitiva, 2026-07-17, migracion `0027_remove_applies_globally_from_rentalcostrule`): el campo `RentalCostRule.applies_globally` fue eliminado. Toda regla nace atada a un `Equipment` especifico via `RentalCostRuleCommands.create_rule_for_equipment()` (crea + asigna a la variante principal en el mismo paso) y `RentalCostRuleSelector.list_for_equipment()` es la unica forma valida de listarlas — SIEMPRE filtrado por equipo, nunca el catalogo completo. Un equipo nuevo arranca con 0 reglas. Ver tambien `frontend/src/store/rentingAdmin/pricing.js` y `frontend/src/modules/renting/panels/CostRulesPanel.vue` (segunda UI de Costos, en `/panel/renta/:uuid`, corregida igual que `RentingForm.vue`).

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
