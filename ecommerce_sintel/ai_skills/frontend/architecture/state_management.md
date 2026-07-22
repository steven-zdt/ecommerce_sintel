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

## Stores que NO existen — no inventar

```
productStore, shopStore, inventoryStore, orderStore, wishlistStore
```

Si necesitas estado de wishlist, usa el endpoint directo via `useApi()` — no hay store dedicado.
