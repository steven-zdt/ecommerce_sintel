# App: frontend (Vue.js 3) — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
frontend/.AGENT/doc/ARQUITECTURA_COMPLETAFRONEND.md
```

## Skills de referencia

| Tema | Ruta |
|------|------|
| **Imports validos — LEER PRIMERO** | `ai_skills/frontend/FRONTEND_COMPONENT_REGISTRY.md` |
| Stack, composables, endpoints, routing | `ai_skills/frontend/FRONTEND_SKILL.md` |
| Patrón CRUD offcanvas (receta copy-paste) | `ai_skills/frontend/FRONTEND_OFFCANVAS_SKILL.md` |
| Paleta de colores, tipografia, componentes UI | `ai_skills/frontend/FRONTEND_UI_RULES.md` |
| Prompt base copy-paste para tareas frontend | `ai_skills/frontend/FRONTEND_PROMPT_BASE.md` |
| Endpoints shop (products/categories/brands) | `Documentacion/fuente_unica_conocimiento/GUIA_PRODUCTOS_CATEGORIAS_MARCAS.md` |

## FLUJO OBLIGATORIO PARA CUALQUIER COMPONENTE VUE

```
1. Leer FRONTEND_COMPONENT_REGISTRY.md → confirmar que los imports existen
2. Identificar la vista padre donde se integrara el componente
3. Leer esa vista para conocer imports existentes y no duplicar logica
4. Verificar el store/composable que se usara (firmas exactas en el REGISTRY)
5. Escribir el componente
6. Modificar la vista padre para importar y usar el componente nuevo
```

Saltarse el paso 1 es la causa raiz de componentes con imports inventados (Badge, Rating, Button...).

## Responsabilidad de esta app

SPA Vue.js 3 con panel admin y módulos de negocio. Autenticación JWT,
routing con guardias de acceso, y comunicación con la API Django via Axios.

## Archivos clave

| Archivo | Propósito |
|---------|-----------|
| `src/apps/admin/router.js` | Rutas del panel admin + navigation guards |
| `src/store/auth.js` | ÚNICO Pinia store — tokens JWT, user, roles |
| `src/composables/useAuth.js` | login(), logout(), refreshAccessToken(), fetchProfile() |
| `src/composables/useApi.js` | Cliente Axios con interceptores JWT (auto-refresh en 401) |
| `src/composables/useToast.js` | success/error/info/warning |
| `src/composables/useOffcanvas.js` | Estado CRUD: show/mode/selected + openCreate/openEdit/close |
| `src/components/ui/SintelOffcanvas.vue` | Panel lateral deslizable — v-model + slots |
| `src/components/layout/AppShell.vue` | Layout principal: Sidebar 270px + Navbar 70px + RouterView |
| `src/components/layout/Sidebar.vue` | 5 grupos colapsables con colores por módulo |
| `src/views/auth/LoginView.vue` | Formulario de login |
| `src/modules/shop/ProductList.vue` | Ejemplo de módulo CRUD completo con offcanvas |

## Regla de endpoints — CRITICA

```
LECTURA  (GET)                → shop/ | renting/ | technical_services/ | ...  (ReadOnly, sin auth)
ESCRITURA (POST/PATCH/DELETE) → dashboard/products/ | dashboard/categories/ | ...  (requiere JWT admin)
```

Antes de escribir un endpoint de escritura, verificar contra `dashboard/api/urls.py`.
Los ViewSets públicos son ReadOnly — POST/PATCH/DELETE retornan 405.

## Lookup fields

- `uuid` → clave de v-for, FK en payloads (`category: cat.uuid`)
- `id` (PK entero) → URL de writes: `dashboard/products/${item.id}/`

## Rutas publicas orientadas al cliente — CRITICA

Toda ruta que un cliente final visita fuera del panel admin (login, registro,
registro-profesional, verificacion, etc.) DEBE declararse como `children` de
la ruta raiz `/` que usa `component: CustomerLayout` en
`src/apps/admin/router.js` (unico router, sirve tanto `/panel/*` como el
portal de cliente). NUNCA como ruta top-level independiente.

```javascript
// INCORRECTO — top-level, sin CustomerLayout -> sin navbar/footer
{ path: '/registro-profesional', name: 'register-contractor', component: RegisterContractorView }

// CORRECTO — child de CustomerLayout, path relativo (sin '/')
{ path: '/', component: CustomerLayout, children: [
  { path: 'registro-profesional', name: 'register-contractor', component: RegisterContractorView, meta: { requiresGuest: true } },
]}
```

**Por que:** `CustomerLayout.vue` (`src/components/customer/CustomerLayout.vue`) es
el unico lugar que renderiza `CustomerNavbar` + `CustomerFooter` + carrito +
chat de soporte. Una ruta declarada fuera de sus `children` se renderiza sola,
sin navbar ni footer, aunque visualmente use estilos de "pagina completa".
Bug real: `/register` y `/registro-profesional` se declararon top-level y
quedaron sin navbar/footer durante meses hasta corregirse (2026-07-06).

Antes de agregar una ruta nueva, verificar si es "cliente" (debe ir dentro de
`CustomerLayout`) o "admin" (dentro de `AppShell`, bajo `/panel`). Las excepciones
legitimas top-level son las paginas que deliberadamente NO llevan navbar/footer de
cliente: `/panel/login` (admin-login, aislado), `/verificar-cuenta` (destino de un
link de correo, publico por diseno), y desde el rediseno de autenticacion
(2026-07-17) tambien `/login` y `/register` — ambas usan su propio
`CustomerAuthLayout.vue` (`src/components/auth/CustomerAuthLayout.vue`, layout de
pantalla completa con logo propio) en vez de la navbar/footer de marketing. Esto
reemplaza la regla anterior para estas 2 rutas especificamente (el bug de 2026-07-06
arriba seguia aplicando cuando `/register` no tenia NINGUN layout propio — ahora si
lo tiene).

## Patrones obligatorios

- `<script setup>` siempre — Options API prohibido
- **Prohibido `v-html`** en el chat de soporte y en todo lo que pinte texto del asistente o de otros usuarios (`components/customer/ui/SupportChatWidget.vue`, `components/customer/communication/**`, `modules/support/**`): usar interpolacion `{{ }}` (escapada). HARDENING F8/C3 (2026-09-24): hoy no hay ninguno; si se necesita formato, sanear con una libreria dedicada y documentarlo. El proyecto no tiene ESLint, por eso la regla vive aqui.
- `useApi()` siempre — nunca `axios` directo en componentes (excepcion: los stores Pinia de admin, que YA SON la capa de servicio del panel — no envolverlos en otra capa)
- `useOffcanvas()` + `SintelOffcanvas.vue` para todo CRUD con panel lateral
- try/catch en toda llamada async con `toast.error(...)` en catch
- Confirmación de borrado: fila inline `bg-danger-subtle` — no modales flotantes
- Debounce 400ms en inputs de búsqueda
- Lazy loading en router: `() => import('@/modules/...')`
- Precios: `formatCOP(num, { withSymbol })` desde `@/utils/money` — nunca instanciar `Intl.NumberFormat('es-CO', ...)` inline en componentes

## Design System de "Mi Cuenta" (2026-07-17)

Toda vista bajo `views/customer/account/` (Perfil, Pedidos, Operaciones, Wishlist,
Direcciones, Metodos de Pago, Cotizaciones, "Solicitar cuenta como Asociado de Negocio")
DEBE consumir la libreria compartida en `@/components/customer/account/` (`CustomerAccountShell`,
`CustomerPageHeader`, `CustomerCard`, `CustomerStatusBadge`, `CustomerEmptyState`,
`CustomerErrorState`, `CustomerSkeleton`, `CustomerButton`, `CustomerConfirmInline`,
`CustomerOverlayPanel`, `CustomerDetailRow`, `CustomerSection`, `CustomerAvatar`,
`CustomerPagination` — API completa en `ai_skills/frontend/components/cards.md` sec. 4.0)
en vez de reinventar card/badge/empty-state/skeleton por archivo — esa duplicacion (padding
y radios ligeramente distintos, 2 gradientes de skeleton, 2 nombres de overlay para el
mismo patron) fue exactamente el problema que esta libreria resuelve. Para Timelines dentro
de "Mi Cuenta" reusar `@/components/shared/StatusTimeline.vue` (`mode="steps"|"events"`) —
no crear un timeline nuevo, ya es el componente unificado de todo el proyecto.

## Manejo de errores — patrón único (SPRINT 4, 2026-07-16)

`composables/useErrorHandler.js` centraliza la extracción de mensaje desde un
error de axios/DRF (`detail` → primer error de campo del serializer →
fallback). Código nuevo debe usarlo en vez de repetir la extracción inline:

```javascript
import { useErrorHandler } from '@/composables/useErrorHandler';
const { handleError } = useErrorHandler();
try { ... } catch (err) { handleError(err, 'Mensaje de fallback.'); }
```

Casos que NO deben migrarse a esto: cuando el catch necesita mostrar **todos**
los errores de campo (no solo el primero) o cuando el error se renderiza en
el template en vez de via toast — ahí seguir usando la extracción manual.

## Estado de loading — patrón único (SPRINT 4, 2026-07-16)

Dos variantes válidas, elegidas por si el estado vive en un store Pinia o no:

- **Módulo con store Pinia (CRUD admin):** two-tier `loading` (para GETs) +
  `actionLoading` (para POST/PATCH/DELETE) en el `state()` del store — patrón
  ya usado por todos los stores admin (`rentingAdmin/*`, `quotesAdmin/*`,
  `technicalServicesAdmin/*`). No usar un solo flag genérico para ambos casos
  (un fetch en curso y una mutación en curso son estados de UI distintos:
  el primero normalmente reemplaza el contenido con un skeleton, el segundo
  deshabilita un botón puntual).
- **Vista/composable sin store (flujo puntual, ej. wizards):** `const loading
  = ref(false)` local en el componente, exactamente como ya hacían
  `RentalBookingWizard.vue`/`ServiceRequestWizard.vue` antes de esta fase.

No introducir un tercer patrón (`store.loading` leído directo desde un store
que no distingue reads de writes) en código nuevo.

## Estructura de nuevo módulo Vue

```
src/modules/{nombre}/
├── {Nombre}List.vue    # Tabla + paginación + offcanvas + confirmación delete
└── {Nombre}Form.vue    # Form con props item/mode, emits success/cancel
```

## Flujo de token expirado (automático)

```
Request → 401 → interceptor → POST /auth/token/refresh/
→ nuevo token → reintentar request original
→ Si refresh falla → authStore.logout() → redirect /login
```

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
