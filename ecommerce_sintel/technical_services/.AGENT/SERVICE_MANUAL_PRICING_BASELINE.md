# SERVICE_MANUAL_PRICING_BASELINE.md

**Fecha:** 2026-08-13. Plan "Manual Pricing Engine" para `technical_services`, FASE 0
(auditoria read-only, sin cambios de codigo -- ver regla explicita del usuario "no
tocar todavia"). Ultima migracion aplicada: **0032**
(`0032_technicalservice_coverage_notes_and_more.py`).

Doc de referencia obligatorio ya existente y auditado (no reescrito aqui, solo
verificado contra codigo real donde importa para este plan):
`technical_services/.AGENT/docs/ARQUITECTURA_COMPLETA_SERVICES.md` (§2.5 ServiceVariant,
§5.2/§5.2bis pricing, §2.9 OrderServiceDetail, §2.10ter ServiceOperation).

## 1. Modelos verificados contra codigo real

- **`ServiceVariant`** (`models.py:120-169`): `service`, `sku`, `estimated_hours`,
  `complexity_factor`, `fixed_price`, `pricing_strategy` (HOURLY/DAILY/FIXED),
  `min_duration`, `max_duration`, `simultaneous_capacity`, `is_default`, `is_active`.
  Sin ningun campo de pricing manual hoy -- confirmado con grep, cero resultados para
  `pricing_source`/`manual_pricing`/`ManualPricing` en toda la app.
- **`ServiceConfiguration`** (`models.py:46`): `smlv`, `transport_subsidy`,
  `benefit_rate`, `indirect_costs_rate`, `iva_rate` (default 19.00). Cacheada 300s
  (`LaborCostCalculator.CACHE_KEY`), invalidada por signal `post_save`/`post_delete`.
- **`ServiceCostRule`/`ServiceCostAssignment`** (`models.py:658-689`, heredan de
  `AbstractCostRule`/`AbstractCostAssignment`): reglas TAX/DISCOUNT/SETUP/OPERATIONAL,
  fijo o porcentaje, globales o por-variante. `ServicePricingCalculator.
  calculate_breakdown(variant, base_price)` (`services/pricing.py:100`) las aplica
  SIEMPRE sobre `base_amount = labor_cost + material_cost`, antes de
  descuento/IVA -- paso obligatorio, no opcional, en `get_variant_quotation()`.
- **`ServicePriceHistory`** (`models.py:692`): SOLO `old_price`/`new_price` (ambos
  `DecimalField` simples) + `changed_by`. **No tiene `reason` ni ningun campo que
  distinga la fuente del precio** (FASE 6 del plan requiere ampliarlo).
  Poblado automaticamente por `ServiceVariantCommands.update_variant()` únicamente
  cuando `fixed_price` cambia (comparacion `old_price != new_price` sobre ese campo
  especifico, `services/commands.py:540-552`) -- un cambio de `pricing_source` sin
  tocar `fixed_price` HOY no generaria ninguna entrada de historial.
- **`OrderServiceDetail`** (`models.py:515-568`): tiene `applied_rate_type`
  (choices HOURLY/DAILY/PROJECT) y `applied_rate_amount` (Decimal) -- **el snapshot
  real es MAS LIMITADO de lo que el plan asume.** Verificado en
  `services/commands.py:156-157`:
  ```python
  applied_rate_type = quotation.get('pricing_strategy')
  applied_rate_amount = quotation.get('labor_cost')
  ```
  Solo se snapshotea `labor_cost` (mano de obra, antes de materiales/reglas de
  costo/descuento/IVA), **no** `base_amount`/`subtotal_after_rules`/`discount_amount`/
  `iva_amount`/`total_price`. El total real de la orden vive disperso en
  `Order.total_amount` (post-paquete si aplica) y `OrderItem.price` (=
  `quotation['base_amount'] / quantity`) -- no hay HOY un unico JSON estructurado de
  snapshot comercial completo como el que pide FASE 2. Esto es una **extension
  real**, no un simple "agregar 3 campos mas al lado de los que ya existen".

## 2. Motor de precios automatico (flujo verificado, `services/selectors.py:180-260`)

```
1. labor_cost = fixed_price (FIXED) | LaborCostCalculator.calculate_variant_labor_cost(variant, duration)
2. material_cost = sum(material.product_variant.discounted_price_or_price * qty)
3. base_amount = labor_cost + material_cost
4. pricing_breakdown = ServicePricingCalculator.calculate_breakdown(variant, base_amount)  -- SIEMPRE
   subtotal_after_rules = pricing_breakdown['final_price']
5. discount_amount = subtotal_after_rules * (discount_pct / 100)   -- discount_pct clamped 0..100
   taxable_base = subtotal_after_rules - discount_amount
6. iva_rate = ServiceConfiguration activa (default 19%)
   iva_amount = taxable_base * (iva_rate / 100)
   total_price = taxable_base + iva_amount
```

Retorna dict con: `variant_id, sku, service_name, pricing_strategy, labor_cost,
material_cost, base_amount, discount_pct, discount_amount, iva_rate, iva_amount,
total_price, breakdown{hours, base_hourly_rate, complexity, labor_calculation,
materials[], cost_rules[]...}`. **Este shape exacto es el contrato publico
consumido por el frontend** (ver §4) -- cualquier motor manual nuevo debe devolver
las mismas claves top-level para no romper `CostCalculationPanel.vue` ni
`ServicePriceBreakdown` (cliente).

`duration_val` se calcula SIEMPRE (incluso en FIXED, solo para mostrar en
`breakdown`) y se clampa contra `min_duration`/`max_duration` si estan definidos --
confirma la regla propuesta en FASE 14 del plan (duration no afecta precio en
FIXED/MANUAL_PROJECT/MANUAL_GENERAL, comportamiento ya existente para FIXED hoy).

## 3. Confirmado: `ServiceVariantSerializer` calcula la cotizacion DOS VECES

`technical_services/api/serializers.py:72-95` (`ServiceVariantSerializer`):

```python
def get_calculated_price(self, obj):
    return float(ServiceSelector.get_variant_quotation(obj)['total_price'])

def get_price_info(self, obj):
    q = ServiceSelector.get_variant_quotation(obj)
    return {...}
```

Ambos `SerializerMethodField` llaman `get_variant_quotation(obj)` de forma
independiente -- **cada variante serializada dispara el calculo completo dos
veces** (2 llamadas a `LaborCostCalculator`, `ServicePricingCalculator`, N+1 de
materiales). Confirmado que es una deuda YA CONOCIDA (mencionada explicitamente
por el usuario) -- **no se toca en este plan salvo que una fase posterior lo
requiera explicitamente**, para no mezclar una correccion de performance con la
funcionalidad de pricing manual. Nota para mas adelante: cuando se construya
`ServiceQuotationResolver` (FASE 4), sera trivial resolverla de paso (una sola
llamada, cacheada en el serializer) -- pero queda fuera del scope de FASE 0-3.

## 4. Flujo Dashboard BFF (verificado, coincide con el plan)

```
Vue (ServiceForm.vue -> CostosTab.vue -> CostCalculationPanel.vue)
  -> GET /api/v1/services/services/quotation/?variant_uuid=...&duration=...  (PUBLICO, AllowAny)
     [api/views.py TechnicalServiceViewSet.quotation]

Vue (ServiceForm.vue, guardar variante)
  -> POST/PATCH /api/v1/dashboard/service-variants/{uuid}/   [AdminServiceVariantViewSet, ADMIN_PERMISSIONS]
     -> ServiceVariantInputSerializer (valida)
     -> ServiceAdminOrchestrator.create_variant()/update_variant()
        -> ServiceVariantCommands.create_variant(service=service, **data)   [kwargs EXPLICITOS]
        -> ServiceVariantCommands.update_variant(variant, data, updated_by=...) [setattr generico, SIN allowlist]
```

**Hallazgo importante para FASE 1/7:** `create_variant()` recibe `**data` contra una
firma con kwargs nombrados explicitos (`sku, pricing_strategy, estimated_hours,
complexity_factor, fixed_price, min_duration, max_duration, simultaneous_capacity,
is_default, is_active`) -- agregar `pricing_source`/`manual_unit_price`/
`manual_project_price` exige extender esta firma o el create fallara con
`TypeError: unexpected keyword argument`. `update_variant()` en cambio hace
`for field, value in data.items(): setattr(variant, field, value)` sin ningun
allowlist -- cualquier campo que pase el serializer de input llega directo al
modelo, sin proteccion contra combinaciones invalidas (ej. `manual_project_price`
seteado junto con `pricing_source=AUTOMATIC`). Confirma la recomendacion del plan
(FASE 7) de un `ServicePricingCommands.set_manual_pricing()` dedicado con
validacion cruzada explicita, en vez de confiar en el `update_variant()` generico
para las reglas de consistencia.

`AdminServiceVariantViewSet` (nombre real, no `AdminTechnicalServiceViewSet` --
ese es el ViewSet del `TechnicalService` padre, distinto) vive en
`dashboard/api/views.py:1346`, ruta base `/api/v1/dashboard/service-variants/`.

## 5. Frontend verificado

- `frontend/src/modules/technical_services/ServiceForm.vue` -- 4 tabs consolidados
  hoy (**General, Imagen, Variantes, Costos** -- el doc de arquitectura menciona 7-8
  tabs de una fase distinta de catalogo enriquecido/marketing/FAQ que no aplica
  aqui; confirmar cual es el estado real al implementar FASE 9, puede haber mas
  tabs que los 4 "consolidados" nombrados en el import).
- **`CostosTab.vue`** (`service-form/CostosTab.vue`) -- selector de
  variante+duracion+descuento, delega el render a:
- **`CostCalculationPanel.vue`** (`modules/technical_services/`) -- consume
  `GET services/services/quotation/?variant_uuid=...` DIRECTO (no via store), pinta
  labor_cost/material_cost/base_amount/discount/reglas de costo/IVA/total. **Este
  componente es genérico sobre el shape de respuesta** -- no asume `HOURLY -> SMLV`
  en ningun punto del template, solo lee las claves del dict. Confirma que FASE
  12/13 del plan (mismo contrato para todos los modos, frontend no calcula reglas)
  es alcanzable sin reescribir este componente, siempre que
  `ServiceQuotationResolver`/`ManualPricingCalculator` devuelvan las mismas claves
  top-level (`labor_cost, material_cost, base_amount, discount_pct, discount_amount,
  iva_rate, iva_amount, total_price, breakdown{...}`).
- Store real: `@/store/technicalServicesAdmin/services` (modulo Pinia, no un unico
  archivo `technicalServicesAdmin.js` como nombra el plan -- es un directorio con
  varios stores, mismo patron que `rentingAdmin/*`/`quotesAdmin/*`).
- `ServiceOperationBoard.vue` existe en `modules/technical_services/` (tablero
  operativo de `/panel/servicios/operaciones`, dominio `ServiceOperation` -- FASE
  16/17 del plan).
- Cliente publico: `ServiceRequestWizard.vue` (`views/customer/services/`) --
  **no existe `ServiceDetailView.vue`** (eliminado en la reingenieria SDP
  2026-08-05, ver nota en `technical_services/CLAUDE.md`) -- el archivo real hoy es
  `frontend/src/views/customer/detail/ServiceDetailContent.vue`. El plan (FASE 13)
  menciona `ServiceDetailView.vue` -- referencia desactualizada, usar
  `ServiceDetailContent.vue`.

## 6. `ServiceOperation` vs. precio comercial (confirma FASE 15 del plan)

`ServiceOperation.estimated_duration_minutes` (`models.py:764`) se usa
EXCLUSIVAMENTE para planeacion/agenda (`services/operations.py`: `plan()`,
`reschedule()`) -- verificado que **no** hay ninguna referencia cruzada entre este
campo y el motor de precios (`pricing.py`/`selectors.py`/`calculator.py`). La
separacion de responsabilidades que pide FASE 15/28 (`OrderServiceDetail` =
snapshot comercial, `ServiceOperation` = duracion/agenda/tecnico) ya es el diseño
real actual, no hay que corregir nada, solo preservarlo al construir el pricing
manual.

## 7. Decisiones a tomar (mi recomendacion, no aplicada todavia)

1. **Contrato de campos (FASE 1):** adoptar la propuesta reducida del propio
   usuario -- `pricing_source` + `manual_unit_price` + `manual_project_price` (no 3
   campos redundantes por modo). `MANUAL_GENERAL` y `MANUAL_HOURLY` comparten
   `manual_unit_price` (la diferencia es si `duration` multiplica o no) -- correcto,
   evita un cuarto campo.
2. **No tocar el bug de doble-calculo de `ServiceVariantSerializer`** en este plan
   (ver §3) -- documentar como side-effect deseable de FASE 4
   (`ServiceQuotationResolver`) pero no como tarea explicita, para no mezclar
   scope segun la instruccion original del usuario.
3. **`ServicePricingCommands.set_manual_pricing()` como comando dedicado** (no
   sobrecargar `update_variant()`), justificado por el hallazgo real de §4 (sin
   allowlist ni validacion cruzada hoy).
4. **Extender `ServicePriceHistory`** (no crear modelo nuevo) con los campos que
   pide FASE 6 -- ya tiene `changed_by`, solo faltan `reason` +
   `pricing_source_old/new` + `unit_price_old/new` + `project_price_old/new`.
5. **El snapshot de FASE 2 es trabajo real, no trivial** (ver §1) -- extender
   `OrderServiceDetail` con los campos que pide el plan
   (`pricing_source_snapshot`, `unit_price_snapshot`, `project_price_snapshot`,
   `duration_snapshot`) y ademas corregir `request_service()` para que capture el
   `quotation` completo (hoy solo guarda `labor_cost`), no solo agregar columnas
   vacias.

## CHECKPOINT

FASE 0 completada -- solo lectura, cero cambios de codigo (confirmado: unico
archivo escrito en esta fase es este mismo documento). Hallazgos reales
documentados en §1, §3, §4 (snapshot incompleto, doble-calculo confirmado,
`create_variant` sin espacio para kwargs nuevos). Ningun hallazgo bloquea el plan
-- todos son extensiones necesarias ya anticipadas por el propio plan del usuario
(FASE 2, FASE 6, FASE 7).

**PASS -> Continuar a FASE 1 (contrato de pricing).**
