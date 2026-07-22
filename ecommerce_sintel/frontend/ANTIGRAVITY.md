# App: frontend (Vue.js 3) — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
frontend/.AGENT/doc/ARQUITECTURA_COMPLETAFRONEND.md
```

## Responsabilidad de esta app

SPA Vue.js 3 con panel admin y módulos de negocio. Autenticación JWT,
routing con guardias de acceso, y comunicación con la API Django via Axios.

## Archivos clave

| Archivo | Propósito |
|---------|-----------|
| `src/apps/admin/router.js` | Rutas del panel admin + navigation guards |
| `src/store/auth.js` | Pinia store — tokens JWT, user, roles |
| `src/composables/useAuth.js` | login(), logout(), refreshAccessToken(), fetchProfile() |
| `src/composables/useApi.js` | Cliente Axios con interceptores JWT (auto-refresh en 401) |
| `src/composables/useToast.js` | Sistema de notificaciones toast |
| `src/components/layout/AppShell.vue` | Layout principal: Sidebar + Navbar + RouterView |
| `src/views/auth/LoginView.vue` | Formulario de login |
| `src/modules/shop/ProductList.vue` | Tabla de productos con filtros y paginación |

## Patrones obligatorios en esta app

- **Siempre `useApi()`** para llamadas HTTP — nunca `axios` directo en componentes
- **Manejo de errores:** try/catch en toda llamada async, mostrar error via `useToast()`
- **Debounce 400ms** en inputs de búsqueda antes de llamar API
- **Lazy loading:** Todas las vistas en router deben ser `() => import('@/views/...')`
- `<script setup>` (Composition API) — no usar Options API en código nuevo
- Estado global solo en Pinia stores — no `provide/inject` para datos de autenticación
- Precios en formato colombiano: `new Intl.NumberFormat('es-CO').format(num)`

## Flujo de token expirado (automático)

```
Request → 401 → interceptor → POST /auth/token/refresh/
→ nuevo token → reintentar request original
→ Si refresh falla → authStore.logout() → redirect /login
```

## Estructura de nuevo módulo Vue

```
src/modules/{nombre}/
├── {Nombre}List.vue       # Tabla con filtros y paginación
├── {Nombre}Detail.vue     # Detalle
└── {Nombre}Form.vue       # Formulario crear/editar (modal o página)
```

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
