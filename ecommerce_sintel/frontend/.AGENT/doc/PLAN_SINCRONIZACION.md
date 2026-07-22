# Plan de Sincronización: Backend ↔ Frontend
## Sintel E-Commerce — Estado completo y hoja de ruta

> Generado: 2026-05-14
> Backend: Django REST Framework — ~80 endpoints activos
> Frontend: Vue.js 3 — 6 módulos implementados, 7 en placeholder

---

## DIAGNÓSTICO: ESTADO ACTUAL

### Backend (lo que existe)
| App | Endpoints | Estado |
|-----|-----------|--------|
| accounts / auth | 8 rutas | Completo |
| users | 5 rutas | Completo |
| shop | 15 rutas | Completo |
| cart | 4 rutas | Completo |
| orders | 8 rutas | Completo |
| inventory | 6 rutas | Completo |
| wompi | 2 rutas | Completo |
| technical_services | 6 rutas | Completo |
| renting | 8 rutas | Completo |
| quotes | 7 rutas | Completo |
| marketing | 11 rutas | Completo |
| dashboard/metrics | 1 ruta | Completo |

### Frontend (brechas detectadas)
| Ruta Vue | Componente actual | Estado |
|----------|------------------|--------|
| `/panel/dashboard` | `DashboardView.vue` | Implementado parcial |
| `/panel/perfil` | `ProfileView.vue` | Implementado |
| `/panel/productos` | `ProductList.vue` | Implementado |
| `/panel/categorias` | `CategoryList.vue` | Implementado |
| `/panel/inventario` | `DashboardView` (placeholder) | **FALTANTE** |
| `/panel/ordenes` | `DashboardView` (placeholder) | **FALTANTE** |
| `/panel/servicios` | `DashboardView` (placeholder) | **FALTANTE** |
| `/panel/cotizaciones` | `DashboardView` (placeholder) | **FALTANTE** |
| `/panel/renta` | `DashboardView` (placeholder) | **FALTANTE** |
| `/panel/marketing` | `DashboardView` (placeholder) | **FALTANTE** |
| `/panel/usuarios` | `DashboardView` (placeholder) | **FALTANTE** |
| Carrito cliente | — | **NO EXISTE** |
| Checkout / Wompi | — | **NO EXISTE** |
| Catálogo público | — | **NO EXISTE** |

---

## CORRECCIONES INMEDIATAS (Alineación crítica)

### C1 — Discrepancia en la URL de refresco de token

**Problema:** `useApi.js` llama a `/api/v1/auth/token/refresh/` pero el router de simplejwt
también expone `/api/v1/auth/token/`. Verificar cuál es el path real registrado.

**Archivo:** `frontend/src/composables/useApi.js` línea 69
```javascript
// Verificar que coincide con urls.py de accounts
const { data } = await axios.post('/api/v1/auth/token/refresh/', { refresh: refreshToken });
```
**Acción:** Confirmar en `accounts/urls.py` y alinear si difiere.

---

### C2 — Dashboard endpoint migrado (RESUELTO 2026-05-14)

**Resuelto:** `DashboardView.vue` llama a `/api/v1/dashboard/metrics/`.
La app `coreui` fue eliminada. El endpoint ahora vive en `orders/api/dashboard.py`
y se registra via `orders.api.dashboard_urls` en `ecommerce/urls.py`.
URL publica sin cambio: `/api/v1/dashboard/metrics/`.

---

### C3 — CategoryList.vue sin paginación

**Problema:** `CategoryList.vue` recibe la respuesta pero no maneja el formato paginado
`{ count, next, previous, results }` que retorna DRF.

**Acción:** Alinear con el mismo patrón que `ProductList.vue`.

---

### C4 — baseURL hardcodeada a localhost

**Problema:** `useApi.js` y `useAuth.js` usan `http://localhost:8000/api/v1/` hardcodeado.

**Acción:** Usar variable de entorno Vite:
```javascript
// frontend/.env.development
VITE_API_BASE_URL=http://localhost:8000/api/v1/

// frontend/.env.production
VITE_API_BASE_URL=https://api.sintel.co/api/v1/

// useApi.js
baseURL: import.meta.env.VITE_API_BASE_URL,
```

---

## FASE 1 — PANEL ADMIN: MÓDULOS CORE (Semana 1-2)

### F1.1 — Módulo Inventario (`/panel/inventario`)

**Crear:** `frontend/src/modules/inventory/`

```
inventory/
├── InventoryList.vue       # Tabla de StockRecords con stock actual
├── InventoryMovements.vue  # Kardex: historial de movimientos de un item
└── AdjustStockModal.vue    # Modal para ajuste manual de stock
```

**API a consumir:**
```javascript
// Listar stock records
GET /api/v1/inventory/stock-records/
  params: { page, search }
  response: { count, results: [{ uuid, stock, item_name, movement_type }] }

// Ver kardex de un item
GET /api/v1/inventory/stock-records/{uuid}/movements/
  response: [{ movement_type, quantity, balance_after, reference, created_at }]

// Ajuste manual
POST /api/v1/inventory/stock-records/{uuid}/adjust-stock/
  body: { movement_type: 'ENTRY'|'EXIT', quantity, reference }
  response: { stock_record_uuid, new_balance }
```

**Vista: InventoryList.vue**
- Tabla: Item | SKU | Stock actual | Última actualización | Acciones
- Badge: verde (stock > 0), rojo (stock = 0)
- Botón "Ajustar" → AdjustStockModal
- Botón "Ver movimientos" → navegar a InventoryMovements

---

### F1.2 — Módulo Órdenes (`/panel/ordenes`)

**Crear:** `frontend/src/modules/orders/`

```
orders/
├── OrderList.vue       # Tabla de órdenes con filtro por estado
├── OrderDetail.vue     # Detalle completo con items y timeline de estado
└── OrderStatusBadge.vue # Componente badge reutilizable
```

**API a consumir:**
```javascript
// Listar órdenes (admin ve todas)
GET /api/v1/orders/orders/
  params: { page, status, search }
  response: { count, results: [{ uuid, status, total_amount, user_email, created_at }] }

// Detalle de orden
GET /api/v1/orders/orders/{uuid}/
  response: {
    uuid, status, total_amount, created_at,
    user: { email, full_name },
    shipping_address: { address, city, country },
    items: [{ item_name, sku, quantity, price }]
  }
```

**Vista: OrderList.vue**
- Tabla: # Orden | Cliente | Total | Estado | Fecha | Acciones
- Filtro por estado: pending, paid, shipped, delivered, cancelled
- Badge de estado con colores:
  - pending → amarillo | paid → verde | shipped → azul | delivered → gris | cancelled → rojo
- Click en fila → OrderDetail

---

### F1.3 — Módulo Usuarios (`/panel/usuarios`)

**Crear:** `frontend/src/modules/users/`

```
users/
├── UserList.vue        # Tabla de usuarios con filtros
├── UserCreateModal.vue # Modal para crear usuario desde admin
└── UserEditModal.vue   # Modal para editar datos y rol
```

**API a consumir:**
```javascript
// Listar usuarios
GET /api/v1/users/
  response: [{ id, uuid, email, full_name, role, is_active, is_verified }]

// Crear usuario (admin)
POST /api/v1/users/
  body: { email, first_name, last_name, phone_number, role, password, password_confirm }

// Actualizar usuario
PATCH /api/v1/users/{id}/
  body: { role?, is_active?, is_verified?, is_staff? }

// Soft-delete usuario
DELETE /api/v1/users/{id}/
```

**Vista: UserList.vue**
- Tabla: Email | Nombre | Rol | Estado | Verificado | Acciones
- Filtro por rol (Admin/Customer/Vendor) y estado (Activo/Inactivo)
- Botón "Nuevo usuario" → UserCreateModal
- Badge de rol con colores

---

## FASE 2 — PANEL ADMIN: MÓDULOS DE NEGOCIO (Semana 3-4)

### F2.1 — Módulo Cotizaciones (`/panel/cotizaciones`)

**Crear:** `frontend/src/modules/quotes/`

```
quotes/
├── QuoteList.vue       # Tabla de cotizaciones con estados
├── QuoteDetail.vue     # Detalle con productos y servicios
└── QuoteStatusBadge.vue
```

**API a consumir:**
```javascript
// Listar cotizaciones
GET /api/v1/quotes/quotations/
  params: { page, status }
  response: { count, results: [{ uuid, status, total_amount, created_at }] }

// Detalle de cotización
GET /api/v1/quotes/quotations/{uuid}/
  response: {
    uuid, status, total_amount,
    items: [{ item_name, quantity, unit_price, subtotal }],
    services: [{ service_name, labor_cost, material_cost, subtotal }]
  }

// Descargar PDF
GET /api/v1/quotes/quotations/{uuid}/download-pdf/
  response: Blob (PDF)
```

**Vista: QuoteList.vue**
- Tabla: # Cotización | Cliente | Total | Estado | Fecha | Acciones
- Botón "Ver detalle" | "Descargar PDF" (trigger `window.open` o `<a download>`)
- Estado con badge: DRAFT/SENT/ACCEPTED/REJECTED/EXPIRED

---

### F2.2 — Módulo Renta (`/panel/renta`)

**Crear:** `frontend/src/modules/renting/`

```
renting/
├── EquipmentList.vue       # Catálogo de equipos para alquiler
├── EquipmentDetail.vue     # Detalle con variantes y precios
└── RentalOrderModal.vue    # Modal para crear orden de renta
```

**API a consumir:**
```javascript
// Listar equipos
GET /api/v1/renting/equipment/
  params: { page, search, is_active }
  response: { count, results: [{ uuid, name, category, variants }] }

// Detalle de equipo (con variantes y precios)
GET /api/v1/renting/equipment/{uuid}/
  response: {
    uuid, name, description,
    variants: [{
      sku,
      rental_price_per_day,
      rental_price_per_hour,
      is_default
    }]
  }
```

---

### F2.3 — Módulo Servicios (`/panel/servicios`)

**Crear:** `frontend/src/modules/services/`

```
services/
├── ServiceList.vue     # Catálogo de servicios técnicos
└── ServiceDetail.vue   # Detalle con variantes y cotización calculada
```

**API a consumir:**
```javascript
// Listar servicios
GET /api/v1/services/services/
  params: { page, search }
  response: { count, results: [{ uuid, name, category, level }] }

// Detalle con precio calculado
GET /api/v1/services/services/{uuid}/
  response: {
    uuid, name, description,
    variants: [{
      sku, estimated_hours, complexity_factor,
      fixed_price,
      calculated_price,   // calculado dinámicamente por SMLV
      materials: [{ product_sku, product_name, quantity }]
    }]
  }
```

---

## FASE 3 — PANEL ADMIN: MARKETING (Semana 5)

### F3.1 — Módulo Marketing (`/panel/marketing`)

**Crear:** `frontend/src/modules/marketing/`

```
marketing/
├── MarketingDashboard.vue  # Dashboard con KPIs de negocio consolidados
├── CampaignList.vue        # Gestión de campañas (CRUD)
├── CampaignForm.vue        # Formulario crear/editar campaña
├── FlashOfferList.vue      # Ofertas flash activas
└── AgentRunLog.vue         # Log de ejecuciones del agente IA
```

**API a consumir:**
```javascript
// Dashboard consolidado
GET /api/v1/marketing/dashboard/
  response: {
    shop: { total_variants, in_stock, top_selling_products },
    renting: { total_variants, available, top_rented },
    services: { total_variants, available, top_selling_services },
    orders: { total_revenue, paid_count, pending_count }
  }

// Campañas CRUD
GET  /api/v1/marketing/campaigns/
POST /api/v1/marketing/campaigns/
GET  /api/v1/marketing/campaigns/{uuid}/
PUT  /api/v1/marketing/campaigns/{uuid}/

// Ofertas flash
GET /api/v1/marketing/offers/

// Log de agente IA
GET /api/v1/marketing/agent-runs/
  response: [{ uuid, created_at, llm_decision, status }]
```

**Vista: MarketingDashboard.vue**
- KPI cards: Productos en stock | Equipos disponibles | Servicios activos
- Tabla top 5 productos más vendidos
- Tabla top 5 equipos más rentados
- Últimas ejecuciones del agente IA

---

## FASE 4 — FLUJO DE COMPRA CLIENTE (Semana 6-7)

### F4.1 — Catálogo Público

**Crear:** `frontend/src/views/customer/`

```
customer/
├── CatalogView.vue         # Grid de productos con filtros
├── ProductDetailView.vue   # Detalle de producto + variantes + reseñas
├── CartView.vue            # Vista del carrito
└── CheckoutView.vue        # Selección dirección + resumen + pago Wompi
```

**Rutas nuevas en router.js:**
```javascript
// Rutas públicas (sin auth)
{ path: '/catalogo',              component: CatalogView },
{ path: '/catalogo/:slug',        component: ProductDetailView },

// Rutas cliente (requiere autenticación CUSTOMER)
{
  path: '/mi-cuenta',
  meta: { requiresAuth: true },
  children: [
    { path: 'carrito',    component: CartView },
    { path: 'checkout',   component: CheckoutView },
    { path: 'ordenes',    component: CustomerOrderList },
    { path: 'perfil',     component: CustomerProfile },
  ]
}
```

**API a consumir:**
```javascript
// Catálogo
GET /api/v1/shop/products/?is_active=true&search=&category=
GET /api/v1/shop/categories/
GET /api/v1/shop/brands/

// Carrito
GET  /api/v1/cart/
POST /api/v1/cart/add-item/
POST /api/v1/cart/remove-item/{uuid}/
POST /api/v1/cart/clear/

// Checkout
GET  /api/v1/orders/addresses/
POST /api/v1/orders/addresses/
POST /api/v1/orders/orders/create-from-cart/

// Pago Wompi
POST /api/v1/wompi/payments/initialize/
  → Retorna { uuid, amount_in_cents, public_key }
  → Frontend carga Wompi Widget con esos datos
```

---

### F4.2 — Integración Wompi Widget

**Archivo:** `frontend/src/composables/useWompi.js`

```javascript
export function useWompi() {
  async function initializePayment(orderUuid) {
    const api = useApi();
    const { data } = await api.post('wompi/payments/initialize/', {
      order_uuid: orderUuid
    });
    // data: { uuid, amount_in_cents, public_key, currency }
    return data;
  }

  function mountWidget({ amountInCents, reference, publicKey, redirectUrl }) {
    const checkout = new WidgetCheckout({
      currency: 'COP',
      amountInCents,
      reference,        // = transaction.uuid
      publicKey,
      redirectUrl,
    });
    checkout.open((result) => {
      const { transaction } = result;
      if (transaction.status === 'APPROVED') {
        // Wompi enviará webhook al backend
        // Escuchar via WebSocket: event ORDER_PAID_SUCCESS
      }
    });
  }

  return { initializePayment, mountWidget };
}
```

---

## FASE 5 — WEBSOCKET EN TIEMPO REAL (Semana 7)

### F5.1 — Composable WebSocket

**Archivo:** `frontend/src/composables/useWebSocket.js`

```javascript
export function useWebSocket(group) {
  const ws = ref(null);
  const messages = ref([]);

  function connect() {
    const token = localStorage.getItem('sintel_access');
    ws.value = new WebSocket(
      `${import.meta.env.VITE_WS_BASE_URL}/ws/${group}/?token=${token}`
    );

    ws.value.onmessage = (event) => {
      const data = JSON.parse(event.data);
      messages.value.push(data);

      // Dispatch según event_type
      if (data.event_type === 'ORDER_PAID_SUCCESS') {
        useToast().success(`Pago confirmado para orden ${data.payload.order_uuid}`);
      }
      if (data.event_type === 'NEW_SERVICE_REQUEST') {
        useToast().info(`Nueva solicitud de servicio recibida`);
      }
    };
  }

  function disconnect() {
    ws.value?.close();
  }

  onMounted(connect);
  onUnmounted(disconnect);

  return { messages };
}
```

**Eventos disponibles del backend:**
| event_type | group | Descripción |
|-----------|-------|-------------|
| `ORDER_PAID_SUCCESS` | `user_{uuid}` | Pago de orden confirmado |
| `NEW_SERVICE_REQUEST` | `admin_notifications` | Nueva solicitud de servicio |

---

## ESTRUCTURA FINAL DE ARCHIVOS FRONTEND

```
frontend/src/
├── apps/
│   ├── admin/
│   │   ├── router.js          [ACTUALIZAR rutas de módulos]
│   │   └── App.vue
│   └── customer/
│       ├── router.js          [CREAR rutas catálogo]
│       └── App.vue
│
├── views/
│   ├── auth/
│   │   └── LoginView.vue      [✓ OK]
│   ├── admin/
│   │   ├── DashboardView.vue  [CORREGIR endpoint metrics]
│   │   └── ProfileView.vue    [✓ OK]
│   ├── customer/              [CREAR]
│   │   ├── CatalogView.vue
│   │   ├── ProductDetailView.vue
│   │   ├── CartView.vue
│   │   └── CheckoutView.vue
│   └── LandingView.vue        [✓ OK]
│
├── modules/
│   ├── shop/
│   │   ├── ProductList.vue    [✓ OK]
│   │   └── CategoryList.vue   [CORREGIR paginación]
│   ├── inventory/             [CREAR FASE 1]
│   │   ├── InventoryList.vue
│   │   ├── InventoryMovements.vue
│   │   └── AdjustStockModal.vue
│   ├── orders/                [CREAR FASE 1]
│   │   ├── OrderList.vue
│   │   └── OrderDetail.vue
│   ├── users/                 [CREAR FASE 1]
│   │   ├── UserList.vue
│   │   ├── UserCreateModal.vue
│   │   └── UserEditModal.vue
│   ├── quotes/                [CREAR FASE 2]
│   │   ├── QuoteList.vue
│   │   └── QuoteDetail.vue
│   ├── renting/               [CREAR FASE 2]
│   │   ├── EquipmentList.vue
│   │   └── EquipmentDetail.vue
│   ├── services/              [CREAR FASE 2]
│   │   ├── ServiceList.vue
│   │   └── ServiceDetail.vue
│   └── marketing/             [CREAR FASE 3]
│       ├── MarketingDashboard.vue
│       ├── CampaignList.vue
│       └── AgentRunLog.vue
│
├── components/
│   ├── layout/                [✓ OK]
│   │   ├── AppShell.vue
│   │   ├── Sidebar.vue
│   │   ├── Navbar.vue
│   │   └── ToastManager.vue
│   └── common/                [CREAR]
│       ├── StatusBadge.vue    # badge reutilizable (status → color)
│       ├── DataTable.vue      # tabla paginada reutilizable
│       ├── ConfirmModal.vue   # modal de confirmación
│       └── PdfDownload.vue    # helper descarga PDF
│
├── composables/
│   ├── useApi.js              [CORREGIR baseURL a env var]
│   ├── useAuth.js             [CORREGIR baseURL a env var]
│   ├── useToast.js            [✓ OK]
│   ├── useWebSocket.js        [CREAR FASE 5]
│   └── useWompi.js            [CREAR FASE 4]
│
├── store/
│   └── auth.js                [✓ OK]
│
└── .env.development           [CREAR]
    └── .env.production        [CREAR]
```

---

## VARIABLES DE ENTORNO REQUERIDAS

```bash
# frontend/.env.development
VITE_API_BASE_URL=http://localhost:8000/api/v1/
VITE_WS_BASE_URL=ws://localhost:8000
VITE_WOMPI_PUBLIC_KEY=pub_test_...

# frontend/.env.production
VITE_API_BASE_URL=https://api.sintel.co/api/v1/
VITE_WS_BASE_URL=wss://api.sintel.co
VITE_WOMPI_PUBLIC_KEY=pub_prod_...
```

---

## MAPA DE ENDPOINTS: BACKEND → FRONTEND

| Endpoint Backend | Módulo Frontend | Fase |
|-----------------|----------------|------|
| `GET /api/v1/auth/login/` | LoginView.vue | ✓ OK |
| `GET /api/v1/auth/profile/` | ProfileView.vue | ✓ OK |
| `PATCH /api/v1/auth/profile/` | ProfileView.vue | ✓ OK |
| `GET /api/v1/shop/products/` | ProductList.vue | ✓ OK |
| `GET /api/v1/shop/categories/` | CategoryList.vue | CORREGIR paginación |
| `GET /api/v1/dashboard/metrics/` | DashboardView.vue | VERIFICAR endpoint |
| `GET /api/v1/inventory/stock-records/` | InventoryList.vue | Fase 1 |
| `POST /api/v1/inventory/stock-records/{uuid}/adjust-stock/` | AdjustStockModal.vue | Fase 1 |
| `GET /api/v1/orders/orders/` | OrderList.vue | Fase 1 |
| `GET /api/v1/users/` | UserList.vue | Fase 1 |
| `GET /api/v1/quotes/quotations/` | QuoteList.vue | Fase 2 |
| `GET /api/v1/renting/equipment/` | EquipmentList.vue | Fase 2 |
| `GET /api/v1/services/services/` | ServiceList.vue | Fase 2 |
| `GET /api/v1/marketing/dashboard/` | MarketingDashboard.vue | Fase 3 |
| `GET /api/v1/marketing/campaigns/` | CampaignList.vue | Fase 3 |
| `GET /api/v1/cart/` | CartView.vue | Fase 4 |
| `POST /api/v1/orders/orders/create-from-cart/` | CheckoutView.vue | Fase 4 |
| `POST /api/v1/wompi/payments/initialize/` | CheckoutView.vue | Fase 4 |
| WebSocket `user_{uuid}` | useWebSocket.js | Fase 5 |

---

## PATRÓN ESTÁNDAR: MÓDULO LIST + DETAIL

Todos los módulos nuevos deben seguir este patrón:

```vue
<!-- modules/{name}/{Name}List.vue -->
<script setup>
import { ref, reactive, onMounted } from 'vue';
import useApi from '@/composables/useApi';

const api = useApi();
const loading = ref(true);
const items = ref([]);
const totalCount = ref(0);
const currentPage = ref(1);
const filters = reactive({ search: '', status: null });

let searchTimeout = null;
const onSearch = () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => { currentPage.value = 1; fetchItems(); }, 400);
};

const fetchItems = async () => {
  loading.value = true;
  try {
    const params = {
      page: currentPage.value,
      search: filters.search || undefined,
    };
    const { data } = await api.get('{module}/{resource}/', { params });
    items.value = data.results;
    totalCount.value = data.count;
  } catch (err) {
    // useToast().error(...)
  } finally {
    loading.value = false;
  }
};

onMounted(fetchItems);
</script>
```

---

## RESUMEN EJECUTIVO DE TAREAS

### Correcciones inmediatas (antes de iniciar fases)
- [ ] **C1** — Verificar URL de token refresh en `useApi.js`
- [ ] **C2** — Verificar endpoint `/api/v1/dashboard/metrics/` en backend
- [ ] **C3** — Corregir paginación en `CategoryList.vue`
- [ ] **C4** — Mover `baseURL` a variables de entorno (`.env.development`)

### Fase 1 — Admin Core (Semana 1-2)
- [ ] `InventoryList.vue` + `AdjustStockModal.vue` + `InventoryMovements.vue`
- [ ] `OrderList.vue` + `OrderDetail.vue`
- [ ] `UserList.vue` + `UserCreateModal.vue` + `UserEditModal.vue`
- [ ] Actualizar `router.js` con componentes reales (quitar placeholders)

### Fase 2 — Admin Negocio (Semana 3-4)
- [ ] `QuoteList.vue` + `QuoteDetail.vue` + descarga PDF
- [ ] `EquipmentList.vue` + `EquipmentDetail.vue`
- [ ] `ServiceList.vue` + `ServiceDetail.vue`

### Fase 3 — Marketing (Semana 5)
- [ ] `MarketingDashboard.vue` con KPIs consolidados
- [ ] `CampaignList.vue` + `CampaignForm.vue`
- [ ] `AgentRunLog.vue`

### Fase 4 — Flujo Cliente (Semana 6-7)
- [ ] `CatalogView.vue` (catálogo público)
- [ ] `CartView.vue` + `CheckoutView.vue`
- [ ] `useWompi.js` + integración Wompi Widget
- [ ] Rutas de cliente en router

### Fase 5 — Tiempo Real (Semana 7)
- [ ] `useWebSocket.js` composable
- [ ] Notificaciones `ORDER_PAID_SUCCESS` + `NEW_SERVICE_REQUEST`

### Componentes comunes (paralelo a todo)
- [ ] `StatusBadge.vue` — badge de estado reutilizable
- [ ] `DataTable.vue` — tabla paginada base reutilizable
- [ ] `ConfirmModal.vue` — modal de confirmación reutilizable
- [ ] `PdfDownload.vue` — helper descarga de PDF

---

*Total estimado: 7 semanas para sincronización completa Backend ↔ Frontend*
