# SERVICES_OPTIMIZATION_BASELINE

Plan: `PLAN_IMPLEMENTACION_OPTIMIZACION_CRUD_SERVICIOS.md` (2026-09-30). Fase 0 (baseline) y primer paso de la Fase 2.
Entorno de medicion: desarrollo (`ecommerce_sintel_django`), 16 servicios, 17 variantes (10 activas no borradas).
Metodo: `CaptureQueriesContext` + `perf_counter` en `manage.py shell`, serializando igual que las vistas. Solo lectura.

## Baseline (antes)

| Caso | Queries | Total ms | SQL ms | Payload bytes |
|---|---|---|---|---|
| Listado admin (`ServiceSelector.list_all_for_admin` + `TechnicalServiceSerializer`, many) | 88 | 264 | 37 | 16054 |
| Listado admin, segunda pasada | 87 | 103 | 5 | 16054 |
| Detalle liviano (`TechnicalServiceSerializer`) | 28 | 60 | 25 | 2278 |
| Detalle completo (`TechnicalServiceDetailSerializer`) | 33 | 60 | 16 | 3832 |

`ServiceSelector.get_variant_quotation` se invocaba 20 veces para 10 variantes en el listado (2 por variante).

## Cambios aplicados (Fase 2, seguros)

1. `technical_services/api/serializers.py` -- `ServiceVariantSerializer._get_quotation()`: la cotizacion se calcula una sola vez por variante y por instancia de serializer; `get_calculated_price` y `get_price_info` la reutilizan. Semantica de error igual (`None`).
2. `technical_services/services/selectors.py` -- `_get_automatic_quotation`: si `materials` ya viene prefetcheado se usa `variant.materials.all()`; sin prefetch se conserva el `select_related` (no se introduce N+1 en commands/packages). Antes el `select_related` explicito ignoraba el prefetch y lanzaba una query por cotizacion.

Ninguna regla de precio se toco (SETUP/OPERATIONAL/TAX/DISCOUNT, IVA, descuentos, duracion).

## Despues

| Caso | Queries | Total ms | SQL ms | Payload bytes |
|---|---|---|---|---|
| Listado admin | 37 (-58%) | 189 | 17 | 16054 (identico) |
| Listado admin, segunda pasada | 37 (-57%) | 54 | 1 | 16054 (identico) |
| Detalle liviano | 18 (-36%) | 30 | 10 | 2278 (identico) |
| Detalle completo | 23 (-30%) | 35 | 7 | 3832 (identico) |

`get_variant_quotation` en el listado: 20 -> 10 llamadas.

## Codigo eliminado (imports muertos, verificados sin referencias ni parches en tests)

| Archivo | Elemento | Motivo |
|---|---|---|
| `technical_services/api/views.py` | `ServiceCategoryCommands`, `ServiceLevelCommands`, `ServiceVariantCommands`, `ServiceMaterialCommands`, `ServiceConfigurationCommands`, `TechnicalServiceCommands` | importados y nunca usados (el CRUD admin vive en `dashboard/api/`; estos ViewSets son ReadOnly). `api/urls.py` solo importa los ViewSets |
| `technical_services/api/views.py` | `TechnicalServiceInputSerializer`, `ServiceCategoryInputSerializer`, `ServiceLevelInputSerializer`, `ServiceVariantInputSerializer`, `ServiceMaterialInputSerializer`, `ServiceConfigurationInputSerializer` | idem: sin uso en el archivo |
| `technical_services/admin.py` | `Count`, `Q` | sin uso |
| `technical_services/services/commands.py` | `timezone` | sin uso |

Auditoria de frontend (modulos `technical_services`, `components/services`, `components/customer/services`): ningun componente `.vue` sin referencias.

## Tests ejecutados (autorizados 2026-09-30, contenedor de desarrollo, runner de Django)

| Suite | Resultado |
|---|---|
| `technical_services` (antes de tocar imports) | 203 tests OK |
| Nuevos: `tests_free_service_and_pricing_cache` (orden de $0 confirmada; orden con precio en PENDING_PAYMENT; cotizacion una vez por variante) | 3 tests OK |
| `payment` + `orders` (regresion de pago) | 88 tests OK |
| `technical_services` tras eliminar imports muertos | 206 tests OK |

## Pendiente / candidatos (no aplicados)

- Listado admin aun ejecuta 20 queries de `ServiceCostRule` (2 por variante: asignaciones globales y por variante) y 10 de `ServiceConfiguration` activa (1 por cotizacion). Estan dentro del motor de precios (`services/pricing.py`, `ServiceConfigurationSelector.get_active`); optimizarlas implica cache por request o prefetch de reglas, y se deja para decision explicita porque toca el calculo.
- El listado admin usa el serializer completo (variantes con precio, imagenes, FAQs); el plan pide un `ServiceListSerializer` reducido. Requiere revisar que consume `ServiceList.vue` antes de recortar el contrato.
- Fase 1 parcial: solo imports muertos (backend) y componentes sin referencias (frontend). Falta inventario de endpoints legacy, funciones sin referencias, serializers duplicados y stores duplicados.
- Fase 3 (consolidacion frontend del CRUD: `ServiceList`/`ServiceForm`/stores `technicalServicesAdmin`) y Fase 4 (`OrderServiceDetail.technician`, `TechnicianAssignmentBoard.vue`): sin ejecutar.
- Fase 5 parcial: suites de `technical_services`, `payment` y `orders` verificadas. Falta `dashboard` (CRUD admin de servicios) y tests de frontend.
