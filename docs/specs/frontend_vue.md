# Spec Frontend Vue.js — Sintel E-Commerce

## Tech Stack

| Capa | Tecnología | Versión | Propósito |
|------|-----------|---------|-----------|
| Framework | Vue.js | 3.5.x | Composition API, `<script setup>` |
| Build | Vite | 8.x | Multi-entry SPA, HMR con polling |
| Estado | Pinia | 3.x | Stores reactivos (auth, appConfig, cart) |
| Router | Vue Router | 5.x | Guards de navegación JWT |
| HTTP | Axios (via useApi) | 1.x | JWT auto-refresh en 401 |
| CSS | Bootstrap 5.3 + CSS vars | — | Grid, utilitarios, componentes |
| Iconos | Bootstrap Icons | 1.11 | Clases `bi-{nombre}` |
| Pagos | Wompi | — | Widget embedido en checkout |
| Lenguaje | JavaScript puro | — | Sin TypeScript, sin type annotations |

### Variables de entorno
```
VITE_API_BASE_URL=http://localhost:8000/api/v1/
```

---

## Estructura de directorios

```
frontend/src/
├── apps/admin/main.js        # Entry SPA admin → monta #shop-spa-root
├── apps/admin/router.js      # 40 rutas + guards JWT
├── store/
│   ├── auth.js               # Tokens JWT + user data + roles
│   ├── appConfig.js          # Brand + navbar links del sitio
│   ├── cart.js               # Estado carrito de compras
│   ├── rentingAdmin.js       # Estado módulo renting admin
│   └── technicalServicesAdmin.js
├── composables/
│   ├── useApi.js             # Axios singleton con interceptores JWT
│   ├── useAuth.js            # login(), logout(), fetchProfile()
│   ├── useToast.js           # success/error/info/warning globales
│   ├── useOffcanvas.js       # Estado CRUD: show/mode/selected
│   ├── useOperationTracking.js
│   └── useWompiWidget.js     # Integración widget Wompi
├── components/
│   ├── layout/               # AppShell, Sidebar, Navbar, ToastManager
│   ├── ui/
│   │   ├── SintelOffcanvas.vue   # Panel lateral CRUD reutilizable
│   │   ├── PriceBreakdown.vue
│   │   ├── StarRating.vue
│   │   └── landing/          # 20+ componentes landing page
│   ├── customer/             # CustomerLayout, CartOffcanvas, AccountSidebar, etc.
│   ├── shop/                 # ProductHorizontalCard
│   ├── renting/              # EquipmentHorizontalCard
│   └── services/             # ServiceHorizontalCard
├── modules/                  # Módulos admin dashboard (List + Form)
│   ├── shop/                 # ProductList, ProductForm, CategoryList, etc.
│   ├── inventory/            # InventoryList
│   ├── renting/              # RentingList, RentingForm, panels/
│   ├── technical_services/   # ServiceList, ServiceForm, etc.
│   ├── orders/               # OrderList
│   ├── quotes/               # QuotationList, QuotationDetail
│   ├── users/                # UserList, UserForm
│   ├── core/                 # HomeConfigView
│   ├── marketing/            # MarketingView, CampaignForm
│   ├── operations/           # OperationBoard, DispatcherList
│   └── support/              # SupportDashboardView
└── views/                    # Page-level por contexto
    ├── customer/             # HomeView, shop/, renting/, services/, account/, checkout/
    ├── admin/                # DashboardView, ProfileView, AdminLoginPage
    └── auth/                 # LoginView, RegisterView, RegisterContractorView
```

---

## Patrones de código obligatorios

### 1. Script setup (SIEMPRE)

```vue
<script setup>
import { ref, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'

const api = useApi()
const { toast } = useToast()

const items = ref([])

onMounted(() => fetchItems())

async function fetchItems() {
  try {
    const { data } = await api.get('shop/products/')
    items.value = data.results
  } catch (err) {
    toast.error(err.response?.data?.detail || 'Error al cargar')
  }
}
</script>
```

**PROHIBIDO:** Options API — nunca `export default { data() {}, methods: {} }`.

---

### 2. Llamadas HTTP — useApi (SIEMPRE)

```js
const api = useApi()

// LECTURA (GET) → endpoints públicos sin prefijo dashboard/
const { data } = await api.get('shop/products/')
const { data } = await api.get('renting/equipment/')
const { data } = await api.get('technical_services/services/')

// ESCRITURA (POST/PATCH/DELETE) → SIEMPRE dashboard/
await api.post('dashboard/products/', payload)
await api.patch(`dashboard/products/${item.id}/`, payload)
await api.delete(`dashboard/products/${item.id}/`)
```

**PROHIBIDO:** `import axios from 'axios'` o `fetch()` directamente en componentes.

---

### 3. Regla crítica de endpoints

```
LECTURA  (GET)                → shop/ | renting/ | technical_services/ | orders/ | ...
ESCRITURA (POST/PATCH/DELETE) → dashboard/products/ | dashboard/categories/ | dashboard/renting-items/ | ...
```

Los ViewSets públicos son ReadOnly → POST/PATCH/DELETE retornan 405.

---

### 4. Lookup fields — UUID vs ID

```js
// FK en payload → SIEMPRE uuid
await api.post('dashboard/products/', {
  category: category.uuid,   // ← uuid
  brand: brand.uuid,         // ← uuid
  name: 'Laptop HP'
})

// URL en escritura → id (PK entero)
await api.patch(`dashboard/products/${item.id}/`, { is_active: false })

// v-for key → uuid
<tr v-for="item in items" :key="item.uuid">
```

---

### 5. CRUD con offcanvas (patrón obligatorio)

```vue
<script setup>
import { useOffcanvas } from '@/composables/useOffcanvas'
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue'
import ProductForm from './ProductForm.vue'

const { show, mode, selected, openCreate, openEdit, close } = useOffcanvas()
</script>

<template>
  <button @click="openCreate()">Nuevo</button>

  <table>
    <tr v-for="item in items" :key="item.uuid">
      <!-- Fila de confirmación de borrado — INLINE, nunca modal flotante -->
      <template v-if="pendingDelete?.uuid === item.uuid">
        <td colspan="99" class="bg-danger-subtle p-2">
          ¿Desactivar {{ item.name }}?
          <button class="btn btn-sm btn-danger" @click="executeDelete(item)">Confirmar</button>
          <button class="btn btn-sm btn-secondary" @click="pendingDelete = null">Cancelar</button>
        </td>
      </template>
      <template v-else>
        <td>{{ item.name }}</td>
        <td>
          <button @click="openEdit(item)"><i class="bi bi-pencil"></i></button>
          <button @click="pendingDelete = item"><i class="bi bi-trash"></i></button>
        </td>
      </template>
    </tr>
  </table>

  <SintelOffcanvas v-model="show" :title="mode === 'create' ? 'Nuevo' : 'Editar'" width="560px">
    <ProductForm :item="selected" :mode="mode" @success="fetchItems(); close()" @cancel="close()" />
  </SintelOffcanvas>
</template>
```

---

### 6. Formulario (Form component)

```vue
<script setup>
const props = defineProps({
  item: { type: Object, default: null },
  mode: { type: String, default: 'create' }  // 'create' | 'edit' | 'detail'
})
const emit = defineEmits(['success', 'cancel'])

async function handleSubmit() {
  try {
    if (props.mode === 'create') {
      await api.post('dashboard/products/', form.value)
    } else {
      await api.patch(`dashboard/products/${props.item.id}/`, form.value)
    }
    toast.success('Guardado correctamente')
    emit('success')
  } catch (err) {
    toast.error(err.response?.data?.detail || 'Error al guardar')
  }
}
</script>
```

---

### 7. Búsqueda con debounce (obligatorio)

```vue
<script setup>
import { ref } from 'vue'

let debounceTimer = null
const search = ref('')

function onSearch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => fetchItems(), 400)
}
</script>

<template>
  <input v-model="search" @input="onSearch" placeholder="Buscar..." class="form-control">
</template>
```

---

### 8. Toasts — useToast

```js
const { toast } = useToast()

toast.success('Guardado correctamente')
toast.error('Error al guardar')
toast.info('Procesando...')
toast.warning('Sin stock disponible')
```

---

### 9. Estado global — Pinia stores

```js
import { useAuthStore } from '@/store/auth'
import { useAppConfigStore } from '@/store/appConfig'
import { useCartStore } from '@/store/cart'

const authStore = useAuthStore()

// Verificar rol
if (authStore.isAdmin) { /* admin area */ }
if (authStore.isAuthenticated) { /* logged in */ }

// Datos del usuario
const user = authStore.user  // { id, email, first_name, is_staff, user_type, ... }
```

**STORES EXISTENTES ÚNICAMENTE:** `auth`, `appConfig`, `cart`, `rentingAdmin`, `technicalServicesAdmin`.
No crear stores nuevos sin instrucción explícita.

---

### 10. Router — lazy loading (obligatorio)

```js
// router.js — SIEMPRE importación dinámica
{
  path: '/panel/productos',
  name: 'product-list',
  component: () => import('@/modules/shop/ProductList.vue'),
  meta: { requiresAuth: true, requiresAdmin: true }
}
```

---

### 11. Guards de navegación

```js
// meta flags
meta: { requiresAuth: true }           // cualquier usuario autenticado
meta: { requiresAuth: true, requiresAdmin: true }  // solo admin (is_staff + is_superuser)
meta: { requiresGuest: true }          // solo no autenticados (login, register)
```

---

### 12. Formateo de precios (Colombia)

```js
// SIEMPRE Intl.NumberFormat es-CO
const formatPrice = (num) => new Intl.NumberFormat('es-CO').format(num)
const formatCurrency = (num) => new Intl.NumberFormat('es-CO', {
  style: 'currency', currency: 'COP'
}).format(num)

// PROHIBIDO: toFixed(2), Math.round para precios
```

---

### 13. Formato de fechas

```js
const formatDate = (d) => new Date(d).toLocaleDateString('es-CO', {
  day: '2-digit', month: 'short', year: 'numeric'
})
```

---

## Estructura de un módulo nuevo

```
src/modules/{nombre}/
├── {Nombre}List.vue    # Tabla + filtros + paginación + offcanvas + confirm inline
└── {Nombre}Form.vue    # Form con props item/mode, emits success/cancel
```

---

## Reglas de importación

Solo importar componentes que existan en `FRONTEND_COMPONENT_REGISTRY.md`.

```js
// CORRECTO — existen en el registry
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue'
import LoadingSkeleton from '@/components/ui/landing/LoadingSkeleton.vue'
import GlassCard from '@/components/ui/landing/GlassCard.vue'

// PROHIBIDO — no existen
import { Button } from '@/components/ui/Button.vue'
import { Modal } from '@/components/ui/Modal.vue'
import { Badge } from '@/components/ui/Badge.vue'
import { Spinner } from '@/components/ui/Spinner.vue'
```

---

## Flujo de autenticación JWT

```
Request HTTP
  → interceptor agrega Authorization: Bearer <token>
  → 401 recibido
  → POST /auth/token/refresh/ con refresh token
  → nuevo access token guardado en localStorage
  → request original reintentado
  → si refresh falla → authStore.logout() → redirect /login
```

Tokens en localStorage:
- `sintel_access` → JWT access token
- `sintel_refresh` → JWT refresh token (rotado en cada refresh)
- `sintel_user` → JSON del usuario

---

## Patrones de diseño — Bootstrap 5

```html
<!-- Grid -->
<div class="row g-3">
  <div class="col-md-6">...</div>
</div>

<!-- Tabla estándar admin -->
<table class="table table-hover table-sm">
  <thead class="table-dark">...</thead>
  <tbody>...</tbody>
</table>

<!-- Badge de estado -->
<span class="badge bg-success">Activo</span>
<span class="badge bg-secondary">Inactivo</span>

<!-- Spinner de carga -->
<div v-if="loading" class="d-flex justify-content-center py-4">
  <div class="spinner-border text-primary"></div>
</div>

<!-- Iconos Bootstrap Icons -->
<i class="bi bi-pencil"></i>
<i class="bi bi-trash"></i>
<i class="bi bi-plus-circle"></i>
<i class="bi bi-search"></i>
```

---

## Guardrails — lo que NUNCA se debe hacer

| Prohibición | Motivo |
|-------------|--------|
| Options API `export default { data() {} }` | Solo Composition API con `<script setup>` |
| `import axios from 'axios'` en componentes | Usar `useApi()` siempre |
| POST/PATCH/DELETE a `shop/`, `renting/`, etc. | Son ReadOnly — usar `dashboard/` |
| `item.id` como FK en payloads | Usar `item.uuid` en FKs, `item.id` solo en URL |
| Modal flotante para confirmar borrado | Fila inline `bg-danger-subtle` |
| Inputs de búsqueda sin debounce | Debounce 400ms obligatorio |
| Import de componentes no listados en registry | Rompe el build |
| TypeScript, .ts, interfaces, types | Solo JavaScript |
| Crear stores Pinia sin instrucción | Usar stores existentes |
| `toFixed(2)` o `Math.round` en precios | Usar `Intl.NumberFormat('es-CO')` |

---

## Componentes landing page (glassmorphism)

La landing page usa un sistema de design tokens en `:root`:
- `--accent`: #aa3bff (light) / #c084fc (dark) — morado
- `--text`: #6b6375 (light) / #9ca3af (dark)
- `--text-h`: #08060d (light) / #f3f4f6 (dark)

Componentes disponibles: HeroSection, HeroSlide, HeroBackground, HeroCTA,
ModuleGrid, ModuleCard, FeaturedSection, FeaturedCarousel, FeaturedCard,
FlashOffers, FlashOfferCard, CountdownTimer, TrustSection, TrustCard,
DividerWave, GlassCard, LoadingSkeleton, SectionHeader, AnimatedCounter, FooterCTA.

DividerWave: `<DividerWave from="#color-arriba" fill="#color-abajo" />`

---

## Endpoints por módulo (referencia rápida)

| Módulo | GET (lectura) | POST/PATCH/DELETE (escritura) |
|--------|--------------|-------------------------------|
| Productos | `shop/products/` | `dashboard/products/` |
| Categorías | `shop/categories/` | `dashboard/categories/` |
| Marcas | `shop/brands/` | `dashboard/brands/` |
| Impuestos | `shop/taxes/` | `dashboard/taxes/` |
| Equipos renta | `renting/equipment/` | `dashboard/renting-items/` |
| Servicios técnicos | `technical_services/services/` | `dashboard/technical-services/` |
| Órdenes | `orders/orders/` | `dashboard/orders/` |
| Inventario | `inventory/stock-records/` | `dashboard/stock-adjustments/` |
| Cotizaciones | `quotes/quotations/` | `dashboard/quotations/` |
| Usuarios | `users/` | `dashboard/users/` |
| Home config | `core/home-feed/` | `dashboard/banners/`, `dashboard/modules/`, `dashboard/home-cards/` |
| Marketing | `marketing/dashboard/` | `dashboard/marketing/` |
| Carrito | `cart/` | `cart/add_item/`, `cart/remove_item/` |
| Auth | `auth/profile/` | `auth/login/`, `auth/logout/`, `auth/token/refresh/` |
