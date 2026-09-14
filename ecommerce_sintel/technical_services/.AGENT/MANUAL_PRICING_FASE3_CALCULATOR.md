# FASE 3 -- ManualPricingCalculator

**Fecha:** 2026-08-13. Plan "Manual Pricing Engine". Ver FASE 1
(`MANUAL_PRICING_FASE1_CONTRACT.md`) y FASE 2 (`MANUAL_PRICING_FASE2_SNAPSHOT.md`).

## Cambio

`technical_services/services/manual_pricing.py` (archivo nuevo) --
`ManualPricingCalculator` con `calculate_project_price()`, `calculate_general_
price()`, `calculate_hourly_price()`, `calculate()` (dispatch por
`variant.pricing_source`). Deliberadamente separado de `LaborCostCalculator`
(instruccion explicita del usuario).

## Contrato de salida -- ampliado a proposito

El propio plan mostraba un shape reducido (`pricing_source, base_amount, hours,
unit_price, iva_rate, iva_amount, total_price`). Se amplio para devolver
**exactamente las mismas claves top-level que `ServiceSelector.
get_variant_quotation()`** (`labor_cost, material_cost, base_amount,
discount_pct, discount_amount, iva_rate, iva_amount, total_price,
breakdown{...}`, mas `pricing_source` como campo adicional). Motivo: FASE 12 del
propio plan exige "el endpoint debe devolver exactamente el mismo contrato
independientemente del modo" -- alinear el shape aqui, en FASE 3, evita tener
que traducir/adaptar en FASE 4 (`ServiceQuotationResolver`) o en el serializer
mas adelante. Confirmado en `SERVICE_MANUAL_PRICING_BASELINE.md` §5:
`CostCalculationPanel.vue` ya es agnostico al shape (lee claves de un dict, no
asume `HOURLY -> SMLV`), asi que este contrato compartido es lo que le permite
seguir funcionando sin cambios para variantes MANUAL_*.

## Decisiones explicitas (FASE 5 del plan, ya anticipadas)

1. **Materiales NO se suman** sobre un precio manual -- `material_cost` siempre
   `0.00`. El precio que define el administrador ya es el precio final base.
2. **`ServiceCostRule` NO se aplica** sobre precio manual -- `breakdown.
   cost_rules` siempre `[]`. Reservado para AUTOMATIC (regla explicita del plan).
3. **`labor_cost` reutilizado** como "precio manual base" -- mismo patron ya
   existente en el codebase para `FIXED` (`labor_cost = variant.fixed_price`,
   sin calculo SMLV), no una convencion nueva.
4. **`MANUAL_PROJECT`/`MANUAL_GENERAL` ignoran `duration`** por completo (regla
   explicita FASE 20 del plan) -- verificado con test (`duration=10` no cambia
   el resultado).
5. **`MANUAL_HOURLY` respeta `min_duration`/`max_duration`** -- mismo clamping
   que ya usa `LaborCostCalculator.calculate_variant_labor_cost()`.
6. **Descuento se aplica antes del IVA**, igual que la ruta AUTOMATIC.

## Fuera de esta fase

`ServiceSelector.get_variant_quotation()` sigue sin tocarse -- **ninguna
variante MANUAL_* se cotiza todavia con este calculador**, solo existe como
clase standalone, sin ningun caller real. El dispatch (FASE 4,
`ServiceQuotationResolver`) es la siguiente fase.

## Tests

`ManualPricingCalculatorTestCase` (nueva, 8 tests) -- incluye el caso exacto del
propio plan (tarifa $85.000/h x 6h = $510.000, IVA 19% = $96.900, total =
$606.900, FASE 25 del plan), clamping de duracion, descuento antes de IVA,
dispatch por `pricing_source`, y el caso de error (`ValueError` si se llama
`calculate()` sobre una variante AUTOMATIC o sin el precio requerido). Suite
completo de `technical_services`: **154/154 PASS** (146 preexistentes + 8
nuevos), 0 regresiones.
