# 07 — FRONTEND (Vue 3 + Pinia)
**Fecha:** 2026-07-16

---

## Métricas

| Categoría | Cantidad |
|---|---|
| Componentes Vue totales | 280 |
| Vistas (`src/views/`) | 51 |
| Componentes (`src/components/`) | 119 |
| Componentes de módulos (`src/modules/`) | 106 |
| Stores Pinia | 13 archivos |
| Composables | 18 |
| Archivos de servicio | 4 (solo `services/renting/`) |
| Líneas en mega-stores | 1.530 (3 stores ≥400 líneas) |

---

## CRÍTICO

### FE-C1 — Conflicto de ruta: `/panel/ordenes/renting` inaccesible
**Archivo:** `src/apps/admin/router.js`, líneas 200 y 216

```javascript
{ path: 'ordenes/:uuid',   name: 'order-detail',      component: OrderDetailView },     // L200
{ path: 'ordenes/renting', name: 'renting-operations', component: RentalOperationBoard }, // L216
```

Vue Router evalúa rutas en orden de declaración. `:uuid` en la línea 200 captura la cadena literal `"renting"` antes de que se evalúe la línea 216. `RentalOperationBoard` es permanentemente inaccesible — navegar a `/panel/ordenes/renting` abre `OrderDetailView` con `uuid = "renting"` y falla la llamada API.

**Fix:** Declarar rutas estáticas antes que las dinámicas:
```javascript
{ path: 'ordenes/renting', name: 'renting-operations', component: RentalOperationBoard },
{ path: 'ordenes/:uuid',   name: 'order-detail',       component: OrderDetailView },
```

### FE-C2 — `AppShell.vue:48` tiene `alert()` de debug en producción
```javascript
@click="() => alert('Global Debug Triggered')"
```
Debug code activo en el componente shell del panel admin. Debe eliminarse inmediatamente.

---

## ALTA PRIORIDAD

### FE-H1 — Tres mega-stores con múltiples dominios de responsabilidad
| Store | Líneas | Entidades gestionadas |
|---|---|---|
| `store/rentingAdmin.js` | 557 | Equipment, Variants, Categories, Brands, Labor, CostRules, RentalRequests, Blocks, Logistics |
| `store/quotesAdmin.js` | 557 | Categories, Subcategories, Attributes, Types, Templates (árbol), Quotations |
| `store/technicalServicesAdmin.js` | 416 | Services, Variants, Categories, Levels, CostRules, Packages, PackageItems, PackageCosts |

Un fallo o re-carga en una acción afecta el estado global del store, causando re-renders innecesarios en toda la vista que lo observe.

**Fix propuesto — split por dominio funcional:**
```
rentingAdmin.js →
  rentingEquipmentStore.js  (Equipment + Variants)
  rentingCatalogStore.js    (Categories + Brands + Labor)
  rentalRequestStore.js     (RentalRequests + Blocks)
  rentalLogisticsStore.js   (CostRules + Logistics)
```

### FE-H2 — Capa de servicios API casi inexistente: 193 llamadas Axios directas
Solo `services/renting/` tiene una abstracción de servicio. El resto de módulos (shop, quotes, technical_services, operations, KYC, marketing, orders) llama `useApi().get()/post()` directamente desde stores o componentes. Cambiar un endpoint backend requiere grep-and-replace en decenas de archivos.

**Fix:** Crear `services/{domain}/` para cada módulo, agrupando las llamadas por recurso.

### FE-H3 — `apps/customer/main.js`: entrada muerta
Monta una app Vue en `#customer-spa-root` — elemento DOM que no existe en ningún template. El comentario del archivo confirma que es un "placeholder". Causa confusión sobre el punto de entrada real de la SPA de cliente.

### FE-H4 — `RentalBookingWizard.vue` minificado — código fuente ilegible
El archivo tiene toda la lógica en una sola línea (minificada/comprimida antes de commit). `validate()`, `submit()`, `onMounted()` son una línea inentendible. Debe restaurarse el código fuente.

### FE-H5 — Sin lazy loading de rutas (bundle inicial contiene todo el admin)
Ninguna de las 60+ rutas del router usa `() => import(...)`. El bundle inicial carga `HomeConfigView.vue` (2.705 líneas), `ModuleBuilderModal.vue` (1.588 líneas) y todos los boards de operaciones, aunque el usuario solo quiera ver el dashboard de métricas.

### FE-H6 — `HomeConfigView.vue` (2.705 líneas) y `ModuleBuilderModal.vue` (1.588 líneas) son god-components
4.293 líneas combinadas para el sistema de configuración del home. Deben descomponerse en sub-componentes por panel (banners, módulos, cards, preview).

---

## MEDIA PRIORIDAD

### FE-M1 — Datos de Colombia duplicados
`src/data/colombiaLocations.js` existe como fuente canónica, pero `components/customer/checkout/ColombianAddressForm.vue:228` tiene una copia inline (~40 líneas). Las dos copias divergirán.

### FE-M2 — `useFormValidation.js` específico de campañas con nombre genérico
El composable valida hardcodeado `title`, `content`, `channels`, `scheduled_at` (campos de campaña de marketing). Solo lo importa `CampaignForm.vue`. El nombre implica reutilización pero no existe ningún consumidor genérico.

### FE-M3 — `useQuoteWizard` y `useCatalogQuoteWizard`: implementaciones paralelas sin código compartido
Ambos gestionan un wizard multi-paso con `applicant` reactivo, navegación, persistencia en `localStorage`, submit via API y `createdQuotation`. Duplican la estructura completa. Propuesta: `useWizardBase(steps, storageKey)` compartido.

### FE-M4 — 7 componentes Timeline con lógica de render solapada
| Componente | Ubicación |
|---|---|
| `ShipmentTimeline` | `components/customer/orders/` |
| `RentalTimeline` | `components/customer/renting/` |
| `OperationTimeline` | `components/customer/services/` |
| `ServiceTimeline` | `components/customer/services/` |
| `TrackingTimeline` | `components/customer/ui/` |
| `UnifiedTimeline` | `components/support/` |
| `OrderTimeline` | `modules/orders/components/` |

Todos renderizan listas de eventos con timestamp y estado. La diferencia es el modelo de datos, no la lógica de render. Un componente `<StatusTimeline :events="[]" />` con interfaz normalizada podría reemplazar la mayoría.

### FE-M5 — Patrones de loading inconsistentes
Tres patrones coexisten sin consistencia:
1. Store two-tier: `loading` para reads, `actionLoading` para mutations (mega-stores)
2. Local ref: `const loading = ref(false)` en `<script setup>` (~10 componentes)
3. Store single flag: `store.loading` directo (stores pequeños)

### FE-M6 — Manejo de errores inconsistente
| Patrón | Dónde |
|---|---|
| `toast.error()` via `useToast` | KYC, Cart, ServiceCheckout, auth forms |
| `store.error` renderizado en template | Mega-stores admin |
| `console.error()` solo (silencioso para el usuario) | CustomerFooter, KycAdminList, MarketingView |
| `errorMsg = ref('')` inline | AdminLoginPage, LoginView, ProfileView |
| Sin manejo | Varios `try/catch` con solo `finally` |

### FE-M7 — `useAvailabilityStore` tiene dos actions que hacen lo mismo
`check(uuid, params)` y `fetchAvailability(uuid, params)` — ambas setean `this.checking`, llaman métodos distintos del servicio pero retornan/almacenan el mismo `this.result`. Una debería envolver la otra.

### FE-M8 — `src/shared/` directorio vacío
Debe eliminarse.

### FE-M9 — `useRentalsStore` de 14 líneas innecesariamente como store Pinia
Solo tiene una action que llama `bookingService.list()`. Su único consumidor es `MyRentalsView.vue`. Una función simple o composable sería suficiente.

---

## Código Muerto (Frontend)

| Elemento | Ruta | Tipo |
|---|---|---|
| `CostRulesView.vue` | `components/shared/CostRulesView.vue` | Componente muerto (0 importadores) — 12KB |
| `PriceBreakdown.vue` | `components/ui/PriceBreakdown.vue` | Componente muerto (0 importadores) |
| `apps/customer/main.js` | `apps/customer/main.js` | Entry point muerta (DOM element inexistente) |
| `src/shared/` | `src/shared/` | Directorio vacío |
| `RentingCatalogView.vue` alias | `views/customer/renting/RentingCatalogView.vue` | Wrapper de 2 líneas sin ruta registrada |
| `EquipmentDetailView.vue` alias | `views/customer/renting/EquipmentDetailView.vue` | Wrapper de 2 líneas sin ruta registrada |
| `fetchShipmentAssignments` | `modules/orders/services/orderService.js:12` | Función placeholder (misma URL que `fetchOrder`) |
| `alert('Global Debug Triggered')` | `components/layout/AppShell.vue:48` | Debug code en producción |
| Colombia data inline | `components/customer/checkout/ColombianAddressForm.vue:228` | Copia duplicada de `src/data/colombiaLocations.js` |
| `FilterSidebar.vue` | `components/customer/ui/FilterSidebar.vue` | Sin importadores (posiblemente supersedido por `FilterPanel.vue`) |

---

## Componentes Duplicados

| Duplicado | Ubicación A | Ubicación B | Notas |
|---|---|---|---|
| `EquipmentGallery` | `components/customer/renting/` | `components/renting/detail/` | Dos implementaciones distintas — A: minificada; B: completa con alt text |
| `BrandList` | `modules/shop/BrandList.vue` (258L) | `modules/renting/RentingBrandList.vue` (120L) | Misma tabla CRUD, shop tiene bulk-delete y CSV export |
| `CategoryList` | `modules/shop/CategoryList.vue` (190L) | `modules/renting/RentingCategoryList.vue` (126L) | Mismo patrón |
| Cost rules | `CostRulesView.vue` (muerto) | `CostRulesPanel.vue` (activo) + inline en `ProductForm.vue` | Tres implementaciones |
| `PriceBreakdown` | `components/ui/PriceBreakdown.vue` (muerto) | `ServicePriceBreakdown.vue` (activo) | Genérico sin usar; específico de servicio en uso |
| 7 Timelines | Ver FE-M4 | — | Render idéntico, datos distintos |
| 4 OperationBoards | `operations/OperationBoard.vue` | `ShopOperationBoard`, `RentalOperationBoard`, `ServiceOperationBoard` | Kanban para distintos dominios con misma estructura |

---

## Router — Hallazgos

| Hallazgo | Prioridad |
|---|---|
| `/panel/ordenes/renting` inaccesible (FE-C1) | CRÍTICA |
| Sin `catch-all` para rutas admin desconocidas — redirige a home público | Media |
| 12 rutas hijas de `/mi-cuenta` repiten `meta: { requiresAuth: true }` (redundante, ya está en el padre) | Baja |
| Sin lazy loading en ninguna ruta | Alta |
