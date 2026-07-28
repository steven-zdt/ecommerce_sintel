---
description: Stores Pinia disponibles — firmas exactas de state/getters/actions. No inventar stores que no aparezcan aqui.
metadata:
  domain: architecture
  supersedes: FRONTEND_SKILL.md (seccion 6), FRONTEND_COMPONENT_REGISTRY.md (raiz seccion 2, ecommerce_sintel seccion 11)
  last_audited: "2026-07-11"
---

# State Management — Pinia

## Regla de oro

Estado global **solo en Pinia** — nunca `provide/inject` para autenticacion ni para carrito.
Los nombres de store siempre llevan el prefijo `use`: `useCartStore`, nunca `cartStore`.

## `useAuthStore` — `@/store/auth`

```js
import { useAuthStore } from '@/store/auth';
const authStore = useAuthStore();

// State:
authStore.accessToken   // string | null
authStore.refreshToken  // string | null
authStore.user          // object | null

// Getters:
authStore.isAuthenticated  // boolean
authStore.isAdmin          // boolean (is_staff === true)
authStore.isCustomer       // boolean (!is_staff)
authStore.fullName         // string
authStore.initials         // string (primera letra, para avatar)

// Actions:
authStore.setTokens({ access, refresh });
authStore.setUser(userData);
authStore.logout();
```

## `useCartStore` — `@/store/cart`

```js
import { useCartStore } from '@/store/cart';
const cartStore = useCartStore();

// State:
cartStore.items; cartStore.totalFromApi; cartStore.totalItemsFromApi; cartStore.loading;

// Getters:
cartStore.itemCount; cartStore.total; cartStore.isEmpty;

// Actions:
await cartStore.fetchCart();
await cartStore.addItem(variantUuid, quantity = 1);
await cartStore.addServiceItem(serviceVariantUuid, quantity = 1);
await cartStore.updateQuantity(variantUuid, serviceVariantUuid, quantity);
await cartStore.removeItem(itemUuid);
await cartStore.clearCart();
cartStore.reset();
```

## `useAppConfigStore` — `@/store/appConfig`

Brand del sitio y links del navbar publico (alimentado por `core/home-feed/`). Ver
[[project_home_page]] en memoria.

## `useRentingAdminStore` — `@/store/rentingAdmin`

```js
import { useRentingAdminStore } from '@/store/rentingAdmin';
const store = useRentingAdminStore();

// Equipment / Variants / Logistics / Categories / Brands / Labor / CostRules — mismo patron:
await store.fetchEquipment(params);      await store.createEquipment(payload);
await store.updateEquipment(uuid, p);    await store.deleteEquipment(uuid);
await store.fetchVariants(equipUuid);    await store.createVariant(equipUuid, p);
await store.fetchLogisticsConfig(uuid);  await store.upsertLogisticsConfig(uuid, p);
await store.fetchCategories();           await store.createCategory(payload);
await store.fetchBrands();               await store.createBrand(payload);
await store.fetchLabor();                await store.createLabor(payload);
await store.fetchCostRules();            await store.createCostRule(payload);
await store.deactivateCostRule(uuid);
await store.assignCostRule(ruleUuid, variantUuid);

// Rental requests (2026-07-07) — pegan a renting/rental-requests/ directo, NO a dashboard/:
store.rentalRequests; store.totalRentalRequests;
await store.fetchRentalRequests(params);
await store.approveRentalRequest(uuid);
await store.rejectRentalRequest(uuid, reason);
await store.markDelivered(uuid);
await store.markReturned(uuid);
await store.releaseRentalPeriod(uuid);
await store.extendRentalPeriod(uuid, newEndDate, reason); // 2026-07-14, solo modo dias, sin cobro automatico
await store.registerReturnInspection(uuid, { hasDamage, conditionNotes, missingAccessories }); // 2026-07-14, opcional/aparte, has_damage=true crea EquipmentBlock automatico

// Equipment blocks (2026-07-14) — mantenimiento/daño/inventario, pegan a
// renting/equipment-blocks/ directo, NO a dashboard/ (misma excepcion que rental requests):
store.equipmentBlocks;
await store.fetchEquipmentBlocks(equipmentUuid);   // ?equipment=<uuid>
await store.createEquipmentBlock(payload);         // { equipment_variant, block_type, start_date, end_date, reason, quantity }
await store.releaseEquipmentBlock(blockUuid, reason);
```

## `useTechnicalServicesAdminStore` — `@/store/technicalServicesAdmin`

Mismo patron que `useRentingAdminStore` para Services / Images / Variants / Categories / Levels /
CostRules:

```js
await store.fetchServices(params); await store.createService(payload);
await store.uploadImage(serviceUuid, file, altText, isPrimary);
await store.deleteImage(serviceUuid, imageUuid);
await store.setPrimaryImage(serviceUuid, imageUuid);
```

## `useBookingStore` — `@/store/renting/bookingStore`

`draft` (borrador del wizard de renta, persistido en `localStorage`), `step`, `created` — usado
**solo** por `RentalBookingWizard.vue`.

## `useAvailabilityStore` — `@/store/renting/availabilityStore`

`checking`, `result`, `error`. Acciones: `check()` (legacy `check-availability/`) y
`fetchAvailability()` (endpoint nuevo `availability/`, retorna `next_available_date` /
`next_available_time` / `occupied_slots`). Ver [[project_renting_availability_engine_phase2]].

## `useWishlistStore` — `@/store/wishlist` (2026-07-23)

```js
import { useWishlistStore } from '@/store/wishlist';
const wishlistStore = useWishlistStore();

// State:
wishlistStore.items; wishlistStore.loaded; wishlistStore.loading;

// Getters:
wishlistStore.isInWishlist(variantUuid);   // boolean
wishlistStore.findByVariant(variantUuid);  // item | undefined

// Actions:
await wishlistStore.fetchWishlist();       // GET cart/wishlist/ — precargado por CustomerLayout.vue on mount/login, resuelto on logout
await wishlistStore.add(variantUuid);      // POST cart/wishlist/
await wishlistStore.remove(itemUuid);      // DELETE cart/wishlist/{uuid}/
await wishlistStore.toggle(variantUuid);   // add o remove segun isInWishlist; retorna true si quedo agregado
wishlistStore.reset();
```

Consumido por `ProductDetailView.vue`, `ItemCard.vue` (boton corazon) y `CustomerWishlistView.vue`
(dashboard) — los tres leen el mismo estado reactivo, sin re-fetch independiente por componente.

## `useSecurityAdminStore` — `@/store/security` (2026-07-27)

```js
import { useSecurityAdminStore } from '@/store/security';
const store = useSecurityAdminStore();

// State: store.events; store.health; store.loading; store.error
await store.fetchEvents({ event_type, severity });  // GET dashboard/security-events/
await store.fetchHealth();                          // GET dashboard/security-events/health/
```

Primer incremento de la migración P1-4 (doc 13 §4.1, 40 módulos admin sin store dedicado) — elegido
por ser el módulo más chico (`SecurityDashboardView.vue`, solo lectura, sin mutaciones). Sirve de
plantilla mínima del patrón para módulos sin CRUD (sin `actionLoading`, ya que no hay POST/PATCH/DELETE).

## `useNotificationsAdminStore` — `@/store/notificationsAdmin` (2026-07-27)

```js
import { useNotificationsAdminStore } from '@/store/notificationsAdmin';
const store = useNotificationsAdminStore();

// State: store.templates; store.templatesLoading; store.logs; store.logsTotalCount;
// store.logsPagination; store.logsLoading; store.actionLoading; store.error
// Getter: store.logsTotalPages

await store.fetchTemplates();                    // GET dashboard/notification-templates/
await store.updateTemplate(uuid, payload);        // PATCH ..., retorna {ok, error?}, refetch automatico
await store.fetchLogs(page, { status, channel, template_slug });  // GET dashboard/notification-logs/
```

**No confundir con `store/notifications.js`** (`useNotificationsStore`) — ese es el feed personal de
la campana del navbar (`NotificationLog` del usuario autenticado), dominio distinto que ya existia
con ese nombre. Segundo incremento de P1-4 (primero fue `store/security.js`). A diferencia de ese,
este SI tiene una mutacion (`updateTemplate`) — usa `actionLoading` para ella, y mantiene
`templatesLoading`/`logsLoading` separados en vez de un solo `loading` porque ambos recursos se
cargan en paralelo al montar la vista (dos pestañas independientes).

## `usePaymentAdminStore` — `@/store/paymentAdmin` (2026-07-27)

```js
import { usePaymentAdminStore } from '@/store/paymentAdmin';
const store = usePaymentAdminStore();

// State: store.wompiTx; store.nequiTx; store.codTx; store.totalCount; store.loading;
// store.cardApiFlowEnabled; store.widgetFlowEnabled; store.flagLoading;
// store.transactionEvents; store.historyLoading; store.actionLoading; store.error
// Getter: store.totalPages

await store.fetchTransactions(tab, page, status);   // GET dashboard/payment-transactions/(nequi|cod)/
await store.fetchFeatureFlags();                    // GET .../feature-flags/
await store.toggleCardApiFlow(checked);             // PATCH .../feature-flags/ -> {ok, error?}
await store.toggleWidgetFlow(checked);              // idem, flag independiente
await store.resyncTransaction(uuid);                // POST .../resync/ -> {ok, data, error?}; actualiza el item en wompiTx in-place
await store.fetchTransactionEvents(uuid);           // GET .../events/
```

Tercer incremento de P1-4 (anteriores: `store/security.js`, `store/notificationsAdmin.js`). El tab
activo (`wompi`/`nequi`/`cod`), el filtro de estado y la página actual quedan como estado local del
componente (interacción de UI) — el store solo guarda datos que vienen de la API.

## `useOrganizationAdminStore` — `@/store/organizationAdmin` (2026-07-27)

```js
import { useOrganizationAdminStore } from '@/store/organizationAdmin';
const store = useOrganizationAdminStore();

// State (datos "de servidor", 8 secciones): store.company; store.branding; store.contact;
// store.socialLinks; store.emailSettings; store.domainSettings; store.seoSettings; store.legalEntity
// store.loading; store.actionLoading; store.error

await store.fetchAll();                       // 8 GETs en paralelo
await store.saveCompany(payload);             // -> {ok, error?}
await store.saveBranding(formData);           // multipart, idem
await store.saveContact(payload);
await store.createSocialLink(payload);        // push in-place a store.socialLinks
await store.deleteSocialLink(uuid);           // filter in-place
await store.saveEmailSettings(payload);
await store.saveDomainSettings(payload);
await store.saveSeoSettings(formData);        // multipart
await store.saveLegalEntityInfo(payload);
```

Cuarto incremento de P1-4. Los formularios de edicion (draft antes de guardar), previews de
archivos y el uuid en confirmacion de borrado quedan como estado local del componente — solo
`socialLinks` se lee directo del store via `storeToRefs` (es una lista, no un draft, y debe
reflejar altas/bajas inmediatamente).

## `useOrdersAdminStore` — `@/store/ordersAdmin` (2026-07-27)

```js
import { useOrdersAdminStore } from '@/store/ordersAdmin';
const store = useOrdersAdminStore();

// State: store.orders; store.ordersLoading (OrderList.vue)
// store.order; store.orderLoading (OrderDetailView.vue)
// store.shipments; store.dispatchers; store.metrics; store.opsLoading (ShopOperationBoard.vue)
// store.timeline; store.timelineLoading; store.actionLoading; store.error

await store.fetchOrders(params);              // -> ordersService.list()
await store.fetchOrder(uuid);                 // -> ordersService.detail()
await store.fetchOperations(filters);         // ordersService.operations() + dashboard/dispatchers/ + operationsDashboard(), en paralelo
await store.fetchTimeline(orderUuid);         // -> ordersService.timeline()
await store.pack(uuid, payload);              // -> {ok, data, error?}
await store.scheduleDispatch(uuid, payload);
await store.assignDispatcher(uuid, payload);
await store.transition(uuid, action);
```

Quinto incremento de P1-4. Unico de los 5 que delega en una capa de servicio ya existente
(`services/orders/ordersService.js`, SPRINT 4) en vez de llamar a `useApi()` directo — el store
orquesta estado, el service resuelve endpoints. El shipment seleccionado y los 3 formularios de
accion (empaque/programacion/asignacion) quedan locales al componente.

**Cierre de FE-H5 residual (2026-07-27):** `store.order`/`store.orderLoading`/`store.fetchOrder`
se agregaron al consolidar `OrderDetailView.vue` (`/panel/ordenes/:uuid`), que tenia su PROPIO store
paralelo no descubierto en el quinto incremento (`store/orders/orderStore.js`, `useOrderStore`,
llamando a un service distinto `modules/orders/services/orderService.js`). Se eliminaron ambos
archivos duplicados (mas `modules/orders/services/timelineService.js`, que ya estaba huerfano sin
ningun consumidor) -- un solo store/servicio de ordenes para todo el dominio. De paso se agrego
`ordersService.serviceOrderDetail(uuid)` (`orders/service-orders/{uuid}/`) para migrar el ultimo
`useApi()` directo que quedaba en `CustomerOrdersView.vue` (vista de cliente, no admin).

## `useKycAdminStore` — `@/store/kycAdmin` (2026-07-27)

```js
import { useKycAdminStore } from '@/store/kycAdmin';
const store = useKycAdminStore();

// State: store.items; store.totalCount; store.nextPage; store.prevPage; store.listLoading (KycAdminList.vue)
// store.kpi; store.currentVerification; store.detailLoading (KycAdminDetail.vue)
// store.actionLoading; store.error

await store.fetchList(params);                // -> kycService.adminList()
await store.fetchKpis();                      // -> kycService.adminMetrics()
await store.fetchDetail(uuid);                 // -> kycService.adminDetail()
await store.approve(uuid);                    // -> {ok, error?}
await store.forceApprove(uuid, note);
await store.reject(uuid, reason);
await store.requestInfo(uuid, message);
await store.block(uuid, reason);
await store.reviewDocument(verificationUuid, docUuid, payload);
```

Sexto incremento de P1-4. `KycVerificationPanel.vue` es un componente reusable (recibe
`verification` como prop, emite `changed`) consumido tanto por `kyc/KycAdminDetail.vue` como por
`users/UserDetail.vue` (`reviewable=false`, flujo "Dar de alta") — el store centraliza sus 5
acciones de nivel-verificación (approve/forceApprove/reject/requestInfo/block, todas comparten
`actionLoading`) para que ambos consumidores las compartan. `viewDocument` y la revisión
documento-por-documento (`reviewDocument` con loading per-documento via `reviewingDocUuid` local)
se dejaron llamando a `kycService` directo a propósito — no comparten `actionLoading` con las
acciones de nivel-verificación en el componente original, meterlas en el store habría fusionado dos
loading states que el diseño original mantenía independientes.

## `useMarketingAdminStore` — `@/store/marketingAdmin` (2026-07-27)

```js
import { useMarketingAdminStore } from '@/store/marketingAdmin';
const store = useMarketingAdminStore();

// State: store.campaigns; store.offers; store.agentRuns; store.loading
// store.actionLoading; store.error

await store.fetchAll();                       // 3 GETs en paralelo (campaigns/offers/agent-runs)
await store.createCampaign(payload);          // -> {ok, error?}
await store.updateCampaign(uuid, payload);
await store.deleteCampaign(uuid);             // filter in-place + {ok, error?}
```

Séptimo incremento de P1-4. Delega en `services/marketing/marketingService.js` ya existente (mismo
criterio que `ordersAdmin`). `AgentRunDetail.vue` no se tocó — es un componente de solo display
(prop `run`, sin llamadas a la API). El formulario de campaña (VeeValidate, via
`useFormValidation`) queda local al componente.

## `useOperationsAdminStore` — `@/store/operationsAdmin` (2026-07-27)

```js
import { useOperationsAdminStore } from '@/store/operationsAdmin';
const store = useOperationsAdminStore();

// State: store.ops; store.opsLoading (OperationBoard.vue)
// store.dispatchers; store.dispatchersLoading (DispatcherList.vue)
// store.currentTicket; store.ticketLoading; store.availableStaff; store.staffLoading (OperationDetail.vue)
// store.actionLoading; store.error

await store.fetchOps(filters);                // GET dashboard/operations/
await store.fetchDispatchers();                // GET dashboard/dispatchers/
await store.createDispatcher(payload);         // -> {ok, error?}, refetch automatico
await store.deleteDispatcher(uuid);            // filter in-place + {ok, error?}
await store.fetchTicket(uuid);                 // GET dashboard/operations/{uuid}/
await store.fetchAvailableStaff(uuid);         // -> {ok, error?}
await store.transition(uuid, status);          // -> {ok, error?}, refetch del ticket automatico
await store.schedule(uuid, payload);
await store.autoAssign(uuid);
await store.assign(uuid, payload);
await store.reviewDoc(uuid, docUuid, approved);
```

Octavo incremento de P1-4. Ninguno de los 3 archivos tenía capa de servicio previa — el store llama
a `useApi()` directo (a diferencia de `ordersAdmin`/`marketingAdmin`, que delegaban en un service ya
existente). El autocompletado de usuarios de `DispatcherList.vue` (`GET users/?search=`) queda local
al componente — búsqueda transitoria de UI, no dato compartido.

## `useUsersAdminStore` — `@/store/usersAdmin` (2026-07-27)

```js
import { useUsersAdminStore } from '@/store/usersAdmin';
const store = useUsersAdminStore();

// State: store.items; store.totalCount; store.nextPage; store.prevPage; store.listLoading (UserList.vue)
// store.currentDetail; store.detailLoading; store.auditLog; store.auditNext; store.auditLoading;
// store.groupsCatalog (UserDetail.vue); store.actionLoading; store.error

await store.fetchList(endpoint);              // GET users/?... (querystring construido por el componente)
await store.createUser(payload);              // -> {ok, data, error?}
await store.patchUser(uuid, payload);         // PATCH users/{uuid}/ -> {ok, data, error?} (toggle activo, editar, form de edicion)
await store.deleteUser(uuid);                 // DELETE users/{uuid}/erase/ -> {ok, error?}
await store.fetchDetail(uuid);                // GET users/{uuid}/
await store.fetchAudit(uuid, url);            // GET users/{uuid}/audit-log/ o url de paginacion, append si url
await store.resetPassword(uuid);              // -> {ok, error?}
await store.resendVerification(uuid);         // -> {ok, error?}
await store.fetchGroupsCatalog();             // cachea -- solo hace el GET la primera vez
await store.saveGroups(uuid, groupIds);       // PUT users/{uuid}/groups/ -> {ok, data, error?}
```

Noveno incremento de P1-4. Sin capa de servicio previa — llama a `useApi()` directo. `actionLoading`
es único y compartido entre las 6 mutaciones (mismo criterio que `organizationAdmin`/`kycAdmin`) —
en `UserDetail.vue` esto simplificó 4 flags de loading independientes (`resetting`/`resending`/
`togglingActive`/`savingGroups`) a un solo `actionLoading` del store.

## `useShopAdminStore` — `@/store/shopAdmin` (2026-07-27)

```js
import { useShopAdminStore } from '@/store/shopAdmin';
const store = useShopAdminStore();

// State: store.brands/categories/taxes/products + *TotalCount + *Pagination + *Loading por recurso
// Getters: store.brandsTotalPages / categoriesTotalPages / taxesTotalPages / productsTotalPages
// store.productCategories (dropdown de ProductList.vue, endpoint distinto a fetchCategories)
// store.actionLoading; store.error

await store.fetchBrands(page);                // GET shop/brands/
await store.deleteBrand(uuid);                // -> {ok, error?}
await store.bulkDeleteBrands(uuids);           // -> {ok, failed, total}
await store.fetchCategories(page);             // GET shop/categories/ (CategoryList.vue)
await store.fetchProductCategories();          // GET dashboard/categories/ (dropdown de ProductList.vue)
await store.deleteCategory(uuid);
await store.fetchTaxes(page);                  // GET shop/taxes/
await store.createTax(payload); await store.updateTax(uuid, payload); await store.deleteTax(uuid);
await store.fetchProducts(params);             // GET dashboard/products/
await store.patchProductInline(uuid, payload); // -> {ok, data, error?}
await store.deleteProduct(uuid);
```

Décimo incremento de P1-4. Cubre `BrandList.vue`/`CategoryList.vue`/`TaxList.vue`+`TaxForm.vue`/
`ProductList.vue`. **Alcance deliberadamente parcial en este incremento**: `ProductForm.vue` (1.324
LOC — variantes, imágenes, reglas de costo, múltiples tabs) NO se migró aquí — ver duodécimo
incremento más abajo, donde sí se migró. `BrandForm.vue`/`CategoryForm.vue` tampoco se tocaron — son
wrappers finos sobre `BaseBrandForm.vue`/`BaseCategoryForm.vue`, componentes genéricos compartidos
con `renting` (`RentingBrandForm.vue`/`RentingCategoryForm.vue`); atarlos a un store de `shop`
rompería su reusabilidad.

**Bug real encontrado y corregido durante la migración** (no relacionado con Pinia): `BrandList.vue`,
`CategoryList.vue`, `TaxList.vue`/`TaxForm.vue`, y los componentes compartidos
`BaseBrandForm.vue`/`BaseCategoryForm.vue` usaban `item.id` (PK entero) en las URLs de
edición/borrado, pero `AdminBrandViewSet`/`AdminCategoryViewSet`/`AdminTaxViewSet`
(`dashboard/api/views.py`) declaran `lookup_field = 'uuid'` — cualquier edición o borrado fallaba
con `500` (`"2" no es un UUID válido`). Corregido a `item.uuid` (los serializers ya exponen ambos
campos). El mismo patrón existe en `renting` (`RentingBrandList.vue`/`RentingCategoryList.vue`) —
no corregido aquí, quedó como tarea de seguimiento separada (spawneada como background task).

### `useShopAdminStore` — extensión para `ProductForm.vue` (duodécimo incremento, 2026-07-27)

```js
// State agregado: store.productBrands; store.activeTaxes;
// store.variants; store.variantsLoading; store.costRules;
// store.productImages; store.imagesLoading
// (comparten store.actionLoading / store.error con el resto del store)

await store.fetchProductBrands();              // GET dashboard/brands/ (dropdown de ProductForm.vue)
await store.fetchActiveTaxes();                 // GET dashboard/taxes/, filtrado is_active (idem)
await store.createProduct(payload);             // POST dashboard/products/ -> {ok, data, error?}
await store.updateProduct(uuid, payload);       // PATCH dashboard/products/{uuid}/ -> {ok, data, error?}

await store.fetchVariants(productUuid);         // GET dashboard/products/{uuid}/variants/
await store.createVariant(productUuid, payload);
await store.updateVariant(productUuid, variantUuid, payload);
await store.deleteVariant(productUuid, variantUuid);

await store.fetchCostRules();                   // GET dashboard/shop-cost-rules/
await store.createCostRule(payload);
await store.toggleCostRule(rule);               // activa/desactiva segun rule.is_active
await store.assignCostRule(ruleUuid, variantUuid);

await store.fetchProductImages(productUuid);    // GET dashboard/products/{uuid}/ -> .images
await store.uploadProductImage(productUuid, formData);
await store.deleteProductImage(productUuid, imgUuid);
await store.setPrimaryImage(productUuid, imgUuid);
```

`ProductForm.vue` (1.324 LOC — pieza mas grande diferida del décimo incremento) migrada aquí. El
draft de creación/edición (`form` general/SEO, `newVariant`, `editingVariant`, `costForm`) sigue
local al componente — mismo criterio que el resto de la migración; `variants`/`costRules`/
`productImages` sí viven en el store porque son datos del servidor listados y mutados desde el mismo
componente. `fetchProductCategories` (ya existente para `ProductList.vue`) se reutilizó tal cual para
el dropdown de categoría de `ProductForm.vue` — mismo endpoint exacto (`dashboard/categories/`), sin
duplicar. `variantLoading`/`costLoading`/`uploading`/`imagesLoading` (mutación) del componente
original se colapsaron en el `actionLoading` único del store — mismo criterio que `usersAdmin`/
`organizationAdmin`; efecto secundario menor: el spinner de "cargando" de la lista de imágenes ya no
se re-dispara durante un delete/set-primary de imagen (antes reusaba el mismo flag que el fetch,
causando un parpadeo de la lista completa), solo el botón puntual se deshabilita ahora.

**Verificado en vivo** con admin temporal (creado y eliminado solo para esto): producto real creado
(`POST` → 201) con transición interna create→edit (mismo offcanvas); variante por defecto (creada
automáticamente por el backend) visible con `price_info` calculado (IVA 19% aplicado); regla de costo
existente asignada a la variante (`POST .../assign/` → 201); imagen real subida (`POST .../add_image/`
→ 201) y eliminada (`DELETE .../delete_image/{uuid}/` → 204); variante editada (`PATCH .../variants/
{uuid}/` → 200) y eliminada (`DELETE .../variants/{uuid}/delete/` → 204); producto de prueba eliminado
al final (`DELETE dashboard/products/{uuid}/` → 204). `npx vite build` y `npx vitest run` (25/25) sin
regresiones.

## `useCoreAdminStore` — `@/store/coreAdmin` (2026-07-27, ampliado 2026-07-27)

```js
import { useCoreAdminStore } from '@/store/coreAdmin';
const store = useCoreAdminStore();

// State — Nosotros: store.config; store.values; store.valuesLoading
// State — Home Builder: store.modules/modulesLoading; store.banners/bannersLoading;
//   store.cards/cardsLoading; store.cardGroups/cardGroupsLoading;
//   store.footerLinks; store.footerContact; store.footerLoading;
//   store.footerGroups/footerGroupsLoading; store.brand/brandLoading;
//   store.navbarLinks/navbarLoading; store.footerCta/ctaLoading;
//   store.brandItems/brandItemsLoading; store.brandSliderConfig/brandConfigLoading
// store.actionLoading; store.error (compartidos por todas las acciones de arriba)

await store.fetchConfig(); await store.fetchValues();
await store.saveConfig(formData);             // -> {ok, error?}
await store.createValue(payload); await store.updateValue(uuid, payload); await store.deleteValue(uuid);

// Home Builder (HomeConfigView.vue, 12 sub-dominios) + ModuleBuilderModal.vue:
await store.fetchModules(); await store.createModule(payload); await store.updateModule(uuid, payload);
await store.deleteModule(uuid);
await store.fetchBanners(); await store.createBanner(payload); await store.updateBanner(uuid, payload);
await store.deleteBanner(uuid);
await store.fetchCards(); await store.createCard(payload); await store.updateCard(uuid, payload);
await store.deleteCard(uuid);
await store.fetchCardGroups(); await store.upsertCardGroup(payload); await store.deleteCardGroup(uuid);
await store.fetchFooter();                    // -> footerLinks + footerContact
await store.saveFooterContact(payload);
await store.createFooterLink(payload); await store.updateFooterLink(uuid, payload);
await store.deleteFooterLink(uuid); await store.reorderFooterLinks(uuids);
await store.fetchFooterGroups(); await store.createFooterGroup(payload); await store.updateFooterGroup(uuid, payload);
await store.deleteFooterGroup(uuid); await store.reorderFooterGroups(uuids);
await store.fetchSiteBrand(); await store.updateSiteBrand(payload);
await store.fetchNavbarLinks(); await store.createNavLink(payload); await store.updateNavLink(uuid, payload);
await store.deleteNavLink(uuid);
await store.fetchFooterCta(); await store.updateFooterCta(payload);
await store.fetchBrandItems(); await store.createBrandItem(payload); await store.updateBrandItem(uuid, payload);
await store.deleteBrandItem(uuid); await store.reorderBrandItems(uuids);
await store.fetchBrandSliderConfig(); await store.updateBrandSliderConfig(payload);
```

Onceavo incremento de P1-4 (2026-07-27): cubria solo `AboutUsAdminView.vue` (301 LOC).

**Decimotercer incremento (2026-07-27): ampliado para cubrir `HomeConfigView.vue` (2.629 LOC, 12
sub-dominios) y `ModuleBuilderModal.vue` (1.588 LOC) — esto cierra P1-4 al 100%.** Todas las
acciones de creacion/actualizacion detectan `payload instanceof FormData` para decidir el
Content-Type (helper `_headersFor`), en vez de necesitar un parametro de headers en cada call site
— el componente sigue decidiendo lo mismo que antes (FormData solo si hay un archivo adjunto o a
eliminar). El draft de cada formulario (banner/tarjeta/grupo/enlace/columna/marca/navbar/CTA/item de
marca/modulo) sigue local al componente, igual que en los 12 incrementos anteriores.

**P1-3 (descomponer `HomeConfigView.vue` en subcomponentes por seccion) se dejo deliberadamente FUERA
de este incremento** — es un refactor distinto y de riesgo mucho mayor (mismo componente, pero
tocando limites de componente en un editor CMS en vivo cuyo panel de preview lee estado de las 8
secciones simultaneamente). Se completo en un incremento propio inmediatamente despues — ver la
seccion siguiente.

## P1-3 — Decomposicion de `HomeConfigView.vue` en subcomponentes (2026-07-27)

`frontend/src/modules/core/HomeConfigView.vue` bajo de **2.629 a 715 LOC**. Las 8 secciones del
Home Builder (modulos, banners, tarjetas, footer, marca, navbar, CTA final, slider de marcas) ahora
son componentes propios en `frontend/src/modules/core/home-builder/`:

```
home-builder/
├── ModulesSection.vue       (110 LOC) -- incluye ModuleBuilderModal.vue
├── BannersSection.vue       (264 LOC)
├── CardsSection.vue         (618 LOC) -- tarjetas + grupos de tarjetas
├── FooterSection.vue        (448 LOC) -- contacto + enlaces + columnas + redes sociales
├── BrandSection.vue         (106 LOC)
├── NavbarSection.vue        (149 LOC)
├── CtaSection.vue           (114 LOC)
├── BrandSliderSection.vue   (339 LOC) -- items + configuracion
└── cardGroupsUtil.js        (14 LOC)  -- funcion pura compartida, ver abajo
```

**Por que esto era mas seguro DESPUES de P1-4, no antes:** con todas las listas (modules/banners/
cards/footerLinks/footerGroups/brand/navbarLinks/footerCta/brandItems/brandSliderConfig) ya viviendo
en `store/coreAdmin.js`, cada seccion puede leer/escribir el store directo sin necesitar props/emits
para los datos — la unica coordinacion real que quedaba era el panel de preview compartido
(`HomeRenderer`/`CustomerNavbar`/`CustomerFooter`, en el padre), que en varios casos necesita el
**borrador sin guardar** de una seccion, no solo los datos ya persistidos.

**Patron para el borrador compartido con el preview — `defineModel()`:** 4 de las 8 secciones tienen
un formulario inline (no modal) cuyo draft el preview necesita ver en vivo mientras se edita:

| Seccion | v-model expuesto | Por que lo necesita el padre |
|---|---|---|
| `FooterSection.vue` | `contactForm` | `CustomerFooter` preview (misma pestaña 'footer') |
| `BrandSection.vue` | `brandForm`, `brandPreviewLogo` | `CustomerNavbar` preview en **2 pestañas**: 'brand' Y 'navbar' — unico caso realmente cross-tab |
| `CtaSection.vue` | `ctaForm` | `HomeRenderer` preview (misma pestaña 'cta') |
| `BrandSliderSection.vue` | `brandConfigForm` | `HomeRenderer` preview (misma pestaña 'brand_slider') |

El padre es dueño del `ref()` real (inicializado reactivamente vía `watch(store.xxx, ..., {immediate:
true})`, no una copia puntual en `onMounted`, para que funcione sin importar el orden de montaje);
cada seccion lo recibe via `defineModel('xxxForm')` y lo edita como si fuera un ref propio. Como el
padre retiene el valor incluso cuando la seccion se desmonta (`v-if`), el caso cross-tab de
`BrandSection`/`NavbarSection` funciona sin necesitar `v-show` ni montaje permanente — se verifico en
vivo navegando directo a la pestaña 'navbar' sin pasar por 'brand' antes.

Las otras 4 secciones (Modulos, Banners, Tarjetas, Navbar) son completamente autonomas: su CRUD es
via modal (no hay draft-en-vivo que el preview necesite) y `Navbar` solo recibe `:site-name` como
prop de solo lectura (no v-model) para su propio mini-preview inline.

**`cardGroupsUtil.js` — `buildGroupMaps(cardGroups)`:** funcion pura que transforma la lista cruda de
`store.cardGroups` en los mapas `{nombre: titulo}`/`{nombre: config}`. La usan `CardsSection.vue` (via
un `watch(cardGroups, ..., {immediate: true})`, ya no una copia puntual mutada a mano) Y el padre (para
`previewCardGroups`), ambos derivando de la MISMA `store.cardGroups` — sin estado duplicado que se
pueda desincronizar entre la lista y el preview.

**Fetch inicial centralizado en el padre:** el `onMounted` de `HomeConfigView.vue` sigue disparando el
fetch de las 12 sub-secciones (igual que antes de P1-3) para que los contadores del sidebar y el
preview tengan datos sin importar que pestaña este activa. Las secciones NO repiten ese fetch en su
propio `onMounted` — solo re-fetchean su propia seccion despues de sus propias mutaciones, leyendo el
mismo estado del store (que ya esta poblado o se poblara vía el fetch del padre).

**Hoja de estilos:** el `<style scoped>` del `HomeConfigView.vue` original paso a `<style>` (global,
sin scoped) en el padre — Vue scoped CSS no cruza limites de componente, y las ~370 líneas de clases
`.hcb-*` (design system del builder: botones, inputs, chips, grids, modales) se usan identicas en las
8 secciones. El prefijo `hcb-` evita colisiones con el resto de la app.

**Verificado en vivo, las 8 secciones + el caso cross-tab de Marca/Navbar**, con admin temporal: ciclo
real de creacion+eliminacion en banners/tarjetas/grupos de tarjetas/enlaces de footer/columnas de
footer/logos del slider/enlaces de navbar; guardado real de contacto/marca/CTA/config del slider;
edicion real de un modulo vía `ModuleBuilderModal.vue`. `npx vite build` y `npx vitest run` (25/25)
sin regresiones en cada uno de los 8 incrementos.

## Stores que NO existen — no inventar

```
productStore, shopStore, inventoryStore
```

`store/orders/orderStore.js` (`useOrderStore`) SI existio pero se elimino 2026-07-27 al consolidarse
en `useOrdersAdminStore` (ver arriba) — no recrearlo; usar `store/ordersAdmin.js`.
