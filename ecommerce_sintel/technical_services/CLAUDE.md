# App: technical_services — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
ecommerce_sintel/technical_services/.AGENT/docs/ARQUITECTURA_COMPLETA_SERVICES.md
```

## Responsabilidad de esta app

Catálogo de servicios técnicos (instalación, mantenimiento, reparación).
Precios calculados dinámicamente según SMLV colombiano o precio fijo.
Los materiales referencian ProductVariant del módulo shop.

## Archivos clave

| Archivo | Propósito |
|---------|-----------|
| `models.py` | ServiceCategory, ServiceLevel, ServiceConfiguration, TechnicalService (+ campos SEO `meta_title`/`meta_description`/`meta_keywords`/`og_image`, mig. 0031; + `scope`/`warranty`/`coverage_notes`, mig. 0032, reingenieria SDP 2026-08-05), ServiceVariant, ServiceMaterial, ServiceImage, ServiceReview, ServiceFAQ, ServiceMarketing (mig. 0031, unificacion con Renting — ver `.AGENT/docs/PLAN_UNIFICACION_SERVICES_CON_RENTING.md`), ServicePriceHistory, ServiceBooking, ServiceCostRule/ServiceCostAssignment, OrderServiceDetail/OrderServiceTimeline/ServiceAttachment, ServiceOperation/ServiceOperationEvent, WorkingSchedule/WorkingException, ServicePackage/PackageIncludedItem/PackageAdditionalCost, ServiceRequestPackage/ServiceRequestAdditionalCost, + catalogo enriquecido (mig. 0032, reingenieria SDP 2026-08-05, espejo de shop.Product*/renting.Rental*): ServiceIncludedItem, ServiceExcludedItem, ServiceRequirement, ServiceSpecificationGroup/ServiceSpecification, ServiceDocument, ServiceVideo, ServiceProcessStep |
| `services/catalog.py` | Selector+Commands del catalogo enriquecido (7 pares), mismo patron factorizado que `shop/services/catalog.py` (reingenieria SDP 2026-08-05) |
| `api/views.py` | TechnicalServiceViewSet/ServiceCategoryViewSet/ServiceLevelViewSet/ServiceConfigurationViewSet — **todos ReadOnly**; el CRUD real de estos modelos vive en `dashboard/api/` (BFF admin), no aqui. `TechnicalServiceViewSet.full_detail()` (`GET .../detail/`) usa `TechnicalServiceDetailSerializer` desde 2026-08-05 (antes usaba el liviano) |
| `api/serializers.py` | TechnicalServiceSerializer, TechnicalServiceDetailSerializer (nuevo, 2026-08-05 — catalogo enriquecido + `content_blocks`/relaciones, mismo patron que `ProductDetailSerializer` de Shop), ServiceVariantSerializer (con `calculated_price`, `simultaneous_capacity`, `is_active`), ServiceMaterialSerializer |
| `api/availability_views.py` + `api/availability_serializers.py` | Motor de disponibilidad de tecnicos (§19 del doc): `TechnicianAvailabilityViewSet`, `WorkingScheduleViewSet`, `WorkingExceptionViewSet` — admin-only |
| `api/operation_views.py` + `api/operation_serializers.py` | `ServiceOperationViewSet` — FSM completo de Operaciones de Servicio (§18): plan/assign-technician/auto-assign/reschedule/cancel/notify-client/ready-to-visit/start/arrive/start-service/complete/close/report-incident/resolve-incident |
| `api/package_serializers.py` | Serializers de `ServicePackage`/`PackageIncludedItem`/`PackageAdditionalCost` y de los snapshots `ServiceRequestPackage`/`ServiceRequestAdditionalCost` (§20) |
| `api/internal_ai.py` | `AiServiceStatusView` — API interna solo para el AI Core (`/api/v1/internal/ai/services/`), no expuesta al cliente |
| `services/commands.py` | ServiceCommands: request_service() (dispara `service_request_created`), ServiceTimelineCommands.add_timeline_event() (dispara `service_status_updated`) |
| `services/selectors.py` | ServiceSelector: get_variant_quotation() — **desde 2026-06 pasa el subtotal por `ServicePricingCalculator.calculate_breakdown()` (ver `pricing.py`) antes de aplicar descuento/IVA**, no es solo `labor_cost + material_cost` |
| `services/calculator.py` | LaborCostCalculator: calculate_hourly_rate(), calculate_variant_labor_cost() |
| `services/pricing.py` | `ServiceCostRule`/`ServiceCostAssignment` (reglas globales o por-variante, fijo/porcentaje, tag TAX/DISCOUNT/SETUP/OPERATIONAL) + `ServicePricingCalculator.calculate_breakdown()` — motor de reglas de costo, paso obligatorio de toda cotizacion, cubierto por `ServiceCostRulePricingTestCase` en `tests.py` |
| `services/operations.py` | `ServiceOperationCommands`/`ServiceOperationSelector` — FSM de `ServiceOperation` (plan/assign/reschedule/cancel/notify/transition/close/incidentes) + `try_auto_assign_via_engine` (Fase 7, **YA LIVE**, no pendiente) |
| `services/calendar.py` | `build_calendar_feed()` — agregacion de agenda de tecnicos (`WorkingSchedule`+`WorkingException`+`ServiceOperation`) para `/technician-availability/calendar/` |
| `services/packages.py` | CRUD de `ServicePackage`/`PackageIncludedItem`/`PackageAdditionalCost` + `PackagePriceCalculator` + `ServiceRequestPackageCommands.create_snapshot()` (§20) |
| `services/summary.py` | ServicesSummaryProvider: get_summary() → stats para marketing (incluye `active_bookings`) |
| `services/technician_availability.py` | `TechnicianAvailabilityEngine` (2026-07-14) — motor calculado de disponibilidad de técnicos, ver ARQUITECTURA §19. Aditivo: no reemplaza `ServiceBooking` todavia (la asignacion real de una operacion via `try_auto_assign_via_engine` SI ya usa este motor) |
| `services/marketing.py` | `ServiceFAQSelector`/`ServiceFAQCommands` (list/create/update/delete/toggle_active/reorder, mismo patron que `renting.RentalFAQCommands`) + `ServiceMarketingCommands` (upsert/delete, mismo patron que `renting.EquipmentMarketingCommands`) + `ServiceReviewSelector`/`ServiceReviewCommands` (2026-07-18, mismo patron "ownership + estado terminal" que `renting.EquipmentReviewCommands` — exige `ServiceOperation.CLOSED` en vez de `RentalRequest.STATUS_FINISHED`) — unificacion con Renting |
| `signals.py` | `post_save`/`post_delete` en `ServiceConfiguration` → invalida el cache de 5 min de `LaborCostCalculator` |

## Patrones obligatorios en esta app

- **Precio dinámico vs. fijo:** Si `ServiceVariant.fixed_price` existe, usar ese precio. Si no, calcular con `LaborCostCalculator`
- **Fórmula SMLV:** `hourly_rate = (SMLV × (1 + prestaciones%) + subsidio_transporte) / 240 × (1 + overhead%)`
- **Reglas de costo (`ServiceCostRule`) se aplican SIEMPRE**, antes de descuento/IVA, en `get_variant_quotation()` — no calcular precio final como `labor_cost + material_cost` directo en ningun caller nuevo
- `ServiceMaterial` referencia `shop.ProductVariant` para precios de insumos — no duplicar datos
- `get_variant_quotation()` retorna dict con `labor_cost`, `material_cost`, `total_price`, `breakdown` (el `breakdown` ahora incluye el desglose de `ServiceCostRule` aplicadas)
- Notificar admin via WebSocket al crear solicitud de servicio: `group="admin_notifications"` (template `service_request_created`) y al cliente en cada cambio de estado (`service_status_updated`) — ambos templates se siembran via migration `0030_seed_service_request_status_templates.py` (2026-07-17; antes solo existian manualmente en dev, sin seed — ver Historial de Cambios del doc completo)
- `ServicesSummaryProvider.get_summary()` es consumido por marketing — mantener la firma del dict (incluye `active_bookings`)
- La disponibilidad de servicios NO depende de `inventory.StockRecord` — ese mecanismo es legacy/vestigial en este modulo; `_check_service_availability()` solo mira `is_active`, y la capacidad por horario usa `ServiceBooking`/`TechnicianAvailabilityEngine`
- **`ServiceMarketing`/`ServiceFAQ`/campos SEO (2026-07-17):** replican fielmente `renting.EquipmentMarketing`/`RentalFAQ`/campos SEO de `Equipment` — mismo principio "cada servicio es un universo independiente" (OneToOne, sin herencia/plantillas). NO tienen campos de campaña con fecha ni testimonios a proposito (ni siquiera Renting los tiene hoy) — ver `.AGENT/docs/PLAN_UNIFICACION_SERVICES_CON_RENTING.md` antes de agregarlos. Endpoints admin: `dashboard/services/{uuid}/marketing/` (GET/PUT/DELETE) y `dashboard/service-faqs/` (CRUD + toggle-active + reorder) — mismo shape REST que sus equivalentes de Renting, para facilitar una futura generalizacion del frontend admin (ver Fase 1 del plan: los 6 managers admin genericos de Renting NO son reutilizables tal cual hoy, hardcodean `equipment` como nombre de campo FK).
- **Admin UI de Marketing/FAQ (2026-07-18):** `frontend/src/modules/technical_services/ServiceForm.vue` tenia entonces 7 tabs (General/Imagen/Variantes/Costos/Paquetes/FAQ/Marketing) -- **[CORREGIDO 2026-08-14]: hoy tiene 15 tabs en total**, tras sumarse las 8 del catalogo enriquecido documentadas mas abajo (reingenieria SDP 2026-08-05: Incluye/No incluye/Requisitos/Ficha tecnica/Documentacion/Videos/Proceso/Contenido del Servicio). Ver auditoria completa en `technical_services/.AGENT/SERVICES_FRONTEND_AUDIT_2026-08-14.md`. El tab Marketing replica el de `RentingForm.vue` casi campo a campo. El tab FAQ usa `ServiceFAQManager.vue` (mismo directorio) — componente NUEVO Y DEDICADO (no una generalizacion de `CatalogListManager.vue` de Renting), mismo patron de interaccion (drag-reorder/inline-form/toggle-active).
- **`ServiceReview` expuesto en API publica (2026-07-18):** antes existia el modelo con datos reales pero 0 exposicion. Ahora `TechnicalServiceViewSet` (publico) tiene `GET /services/services/{uuid}/reviews/` (AllowAny) y `POST /services/services/{uuid}/review/` (IsAuthenticated) — mismo patron exacto que `renting.EquipmentViewSet.reviews`/`.review`, mismo shape de serializer (`ServiceReviewSerializer` con `user_name`/`user_email` derivados). La condicion de "ya recibiste el servicio" usa `ServiceOperation.objects.filter(order__user=user, order__service_detail__bookings__service_variant__service=service, status=ServiceOperation.CLOSED)` (no existe un modelo "request" unico como `RentalRequest` en este dominio — el camino real es `Order -> OrderServiceDetail -> ServiceBooking -> ServiceVariant -> TechnicalService`, y el estado terminal vive en `ServiceOperation`, no en `ServiceBooking`). Frontend: `components/services/detail/ServiceReviews.vue` (nuevo, ambar `#d97706`, mismo markup/logica que `renting/detail/EquipmentReviews.vue` en violeta/azul), montado en `ServiceDetailView.vue` en la seccion "Opiniones" (antes de "Cross selling"). Verificado end-to-end via Django test Client (anon GET, POST sin historial->400, POST con ServiceOperation CLOSED->201, duplicado->400) — no via Playwright esta vez (chequeo de backend puro).
- **FAQ del detalle publico YA estaba conectado a datos reales (verificado 2026-07-18):** el computed `faqs` de `ServiceDetailView.vue` (ya existia antes de esta fase) lee `service.value.faqs` con shape `question`/`answer` — coincide exactamente con `ServiceFAQSerializer` (Fase 2). Cero cambios de frontend necesarios para FAQ; confirmado creando un `ServiceFAQ` de prueba y verificando el payload de `GET /services/services/{uuid}/` directamente.
- **Bloque "Profesionales" nuevo en el detalle publico (2026-07-18):** `GET /services/services/{uuid}/technicians/` (AllowAny, nuevo) usa `TechnicianSelector.get_available_for_category(service.category)` (ya existia, sin cambios) + `AvailableTechnicianSerializer` (nuevo, solo `uuid`/`full_name`/`avatar` — `accounts.TechnicianProfile` no tiene calificacion ni anios de experiencia, no se inventaron esos campos). Frontend: `components/services/detail/ServiceProfessionals.vue`.
- **[CORREGIDO 2026-08-05] `ServiceDetailView.vue` -- la afirmacion original de esta nota (8
  subcomponentes: `ServiceGallery`, `ServiceFeatureList`, `ServiceScopeList`,
  `ServiceSpecificationTable`, `ServiceFAQAccordion`, `ServiceProfessionals`, `ServiceReviews`) era
  incorrecta/desactualizada -- verificado en codigo (auditoria previa a la reingenieria SDP): el
  archivo real de la vista publica es `frontend/src/views/customer/detail/ServiceDetailContent.vue`
  (no `ServiceDetailView.vue` -- ese archivo era codigo muerto, eliminado 2026-08-05), y usa
  componentes **compartidos** (`BaseGallery`, `BaseAccordion`, `BaseReviews`, de `components/base/`)
  mas un unico componente propio real (`ServiceProfessionals.vue`, en `components/services/detail/`).
  `ServiceFeatureList`/`ServiceScopeList`/`ServiceSpecificationTable` si existieron pero solo
  renderizaban `SERVICE_FALLBACK` (datos inventados en el `.vue`, nunca conectados a un modelo) --
  se eliminaron en la reingenieria SDP (ver nota siguiente), no antes.

- **Reingenieria SDP -- catalogo enriquecido + orquestacion de bloques (2026-08-05):** la vista
  publica renderizaba casi todo con `SERVICE_FALLBACK` (arrays hardcodeados en el `.vue`: alcance,
  beneficios, ficha tecnica, garantia, proceso, caso de exito, relacionados -- **nunca conectados a
  ningun modelo real**). Se cerro esa brecha con 7 modelos nuevos en `models.py` (mismo shape que
  `shop.Product*`/`renting.Rental*`: `ServiceIncludedItem`, `ServiceExcludedItem`,
  `ServiceRequirement`, `ServiceSpecificationGroup`/`ServiceSpecification`, `ServiceDocument`,
  `ServiceVideo`, `ServiceProcessStep` -- este ultimo sin equivalente en Shop/Renting, genuinamente
  nuevo) + 3 campos de texto en `TechnicalService` (`scope`/`warranty`/`coverage_notes`) +
  `services/catalog.py` (service layer, mismo patron factorizado que `shop/services/catalog.py`).
  `ServiceMaterial` (ya existia, referencia `shop.ProductVariant`) se expone al cliente por primera
  vez. Orquestacion de orden/visibilidad y relaciones (compatibles/relacionados/productos
  recomendados) reusa la infraestructura generica ya construida para Shop
  (`shared.models.ContentBlockConfig`/`CatalogRelation`, identificados por `ContentType`+`uuid`) --
  `CatalogRelation` ya soportaba relacion cruzada entre modulos por diseno, asi que "Productos
  recomendados" (servicio -> `shop.Product`) es el primer uso real de esa capacidad, sin cambios al
  modelo. `TechnicalServiceDetailSerializer` (nuevo, hereda de `TechnicalServiceSerializer`) expone
  todo esto en `GET services/services/{uuid}/detail/` (accion ya existia, antes usaba el serializer
  liviano). Endpoints admin: `dashboard/service-included-items/`, `-excluded-items/`,
  `-requirements/`, `-specification-groups/`, `-specifications/`, `-documents/`, `-videos/`,
  `-process-steps/` (mismo contrato REST que sus equivalentes de Shop) +
  `dashboard/service-content-blocks/`/`dashboard/service-relations/` (orquestacion). Frontend
  admin: `ServiceForm.vue` gano 8 tabs (Incluye/No incluye/Requisitos reusan
  `CatalogListManager.vue` con `parent-key="service"`; Ficha tecnica/Documentacion/Videos/Proceso
  son managers nuevos y dedicados en `modules/technical_services/catalog/`; "Contenido del
  Servicio" reusa `ContentBlocksTab.vue` de Shop, generalizado con prop `entity-type`). Frontend
  publico: `ServiceDetailContent.vue` reescrito, `SERVICE_FALLBACK` eliminado por completo, todas
  las secciones ahora orquestables via `content_blocks` (orden por defecto propio de
  **[CORREGIDO 2026-08-14: 18]** bloques -- originalmente 19,
  `ContentBlockConfig.SERVICE_DEFAULT_ORDER`, distinto del de Shop). "Caso de exito" (sin
  estructura de datos clara) se elimino sin reemplazo, "Oferta de valor" (copy comercial ya
  parcialmente real via `ServiceMarketing`) se dejo fuera de la orquestacion sin tocar. Ver
  `technical_services/.AGENT/docs/UI_MODULO_SERVICES.md` para el detalle fase por fase y
  `technical_services/.AGENT/SERVICES_FASE7_DETALLE_CUSTOMER_2026-08-14.md` para la auditoria
  que quito el bloque `support` (huerfano, sin render ni tab propio) y corrigio el gating del
  CTA publico (`is_active`/`is_purchasable`).
- **Sidebar de resumen persistente en el wizard (Fase 5, 2026-07-18):** `ServiceRequestWizard.vue` gano un sidebar sticky (`ServiceRequestSummary.vue`, `components/customer/services/`) visible en los pasos 2 y 3 (grid `col-lg-8`/`col-lg-4`, mismo layout que Renting), mostrando servicio+variante, paquete (si aplica), desglose de precio via `ServicePriceBreakdown` (ya existia, reutilizado tal cual) y fecha/jornada elegida una vez seleccionada. 100% aditivo — no toca `useServiceCheckoutStore` ni el payload de envio.
- **`CheckoutStepper.vue` unificado entre Renting y Technical Services (Fase 5, 2026-07-18):** `RentalBookingWizard.vue` y `ServiceRequestWizard.vue` reemplazaron su barra de progreso propia (CSS/markup duplicado) por `components/shared/checkout/CheckoutStepper.vue` (ya existia, usado solo por `CheckoutModal.vue`) — se le agrego un prop opcional `clickable` (navegacion a pasos ya completados, usado por Renting; Services lo deja en `false`, igual que su comportamiento original). Ver `cards.md` §2.
- **`OperationTimeline.vue` — verificado, NO requeria migracion (2026-07-18):** el plan de unificacion asumia que este componente tenia logica de render propia pendiente de migrar a `StatusTimeline.vue`; al verificar el codigo real se confirmo que **ya delega** a `TrackingTimeline.vue` -> `StatusTimeline.vue` (la migracion ya habia ocurrido, ver `cards.md` §2 nota FE-M4). No se toco codigo, solo se corrigio la suposicion desactualizada en el plan.
- **Campos SEO editables en el admin (2026-07-18):** `meta_title`/`meta_description`/`meta_keywords` se agregaron al tab General de `ServiceForm.vue` (subseccion "SEO", solo visible en modo edicion) — NO se creo un tab dedicado (a diferencia de FAQ/Marketing) porque son solo 3 campos de texto. `TechnicalServiceInputSerializer` (`api/serializers.py`) los acepta ahora como opcionales; `og_image` (ImageField) quedo fuera a proposito -- exigiria el mismo plumbing de multipart que ya usa el tab Imagen (`uploadImage()`), no se justifico duplicarlo para un campo secundario sin pedido explicito.

- **Servicios sin costo (2026-09-30):** si el total de la orden es 0, `ServiceCommands.request_service()` la confirma al crearla vía `payment.shared.commands.confirm_order_payment(order, 'FREE-SERVICE')` (mismo camino post-pago que Wompi/Nequi/COD). No crear un segundo camino de confirmacion. El wizard y el detalle publico detectan el precio 0 (`isFreeService`/`serviceIsFree`) y cambian a "Agendar visita" sin abrir el modal de pago. Ver `.AGENT/docs/ARQUITECTURA_COMPLETA_SERVICES.md` §24.
- **Cotizacion una sola vez por variante (2026-09-30):** `ServiceVariantSerializer` cachea la cotizacion por instancia (`_get_quotation`); no volver a llamar `ServiceSelector.get_variant_quotation` por separado desde cada campo. En `_get_automatic_quotation` los materiales usan el prefetch si esta cargado; conservar el `select_related` cuando no lo esta.
- **SKU de variante (max 100):** se autogenera del nombre del servicio (`<NOMBRE>-FIX-STD-01`); un nombre largo rompe la creacion con HTTP 500. Mantener el nombre corto o pasar un `sku` explicito.

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
