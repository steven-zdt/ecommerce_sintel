---
description: Composables core, script setup obligatorio, estructura de modulo CRUD y patrones Vue 3 obligatorios en Sintel.
metadata:
  domain: architecture
  supersedes: FRONTEND_SKILL.md (seccion 2, 4, 5), FRONTEND_COMPONENT_REGISTRY.md (seccion 1 y 10)
---

# Vue Patterns

## 1. Regla no negociable

**Siempre `<script setup>`.** Options API (`data()`, `methods{}`, `computed{}`) esta prohibido en
codigo nuevo. Sin excepciones.

## 2. Composables core

### `useApi()` — `src/composables/useApi.js` (DEFAULT export)

```js
// SIEMPRE importar asi — nunca axios directo en componentes, nunca import { useApi }
import useApi from '@/composables/useApi';
const api = useApi();

api.get(url, { params })   // GET
api.post(url, payload)     // POST
api.patch(url, payload)    // PATCH
api.put(url, payload)      // PUT
api.delete(url)            // DELETE
```

Cliente Axios singleton. Inyecta Bearer JWT automaticamente. En 401 hace refresh del token y
reintenta; si el refresh falla, elimina tokens de `localStorage`. La URL **no** lleva `/api/v1/`
— el cliente lo agrega automaticamente. Tokens: `sintel_access` / `sintel_refresh` en `localStorage`.

> **Critico:** `import { useApi }` (con llaves) rompe silenciosamente — es default export.

> **Critico — uploads de archivos (`FormData`):** la instancia de axios fija
> `Content-Type: application/json` como header por defecto (`headers.common`), y ese
> default **gana** sobre la deteccion automatica de `FormData` del navegador. Cualquier
> `api.post/patch/put(url, formData)` que NO pase explicitamente
> `{ headers: { 'Content-Type': 'multipart/form-data' } }` como tercer argumento falla en
> el backend con **415 Unsupported Media Type** (DRF no encuentra un parser que matchee
> `application/json` para un body multipart). Bug real encontrado 2026-07-18 en
> `technicalServicesAdmin/services.js::uploadImage()` (unica llamada de todo el proyecto
> que le faltaba el override — las ~20 llamadas de upload restantes ya lo hacen bien, ver
> `ProductForm.vue`, `ContractorOnboardingWizard` (KYC), `HomeConfigView.vue`, los managers
> de `modules/renting/catalog/*`, etc.). Al escribir un upload nuevo, copiar el patron:
> ```js
> const fd = new FormData();
> fd.append('image', file);
> await api.post(url, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
> ```

### `useToast()` — `src/composables/useToast.js` (named export)

```js
import { useToast } from '@/composables/useToast';
const toast = useToast();
toast.success('Producto creado');
toast.error('Error al guardar');
toast.info('Procesando...');
toast.warning('Revisa los datos');
```

### `useOffcanvas()` — `src/composables/useOffcanvas.js` (named export)

Estado del panel lateral CRUD. Receta completa: [../components/offcanvas.md](../components/offcanvas.md).

### `useAuth()` — `src/composables/useAuth.js` (named export)

```js
import { useAuth } from '@/composables/useAuth';
const auth = useAuth();
auth.isAuthenticated; auth.isAdmin; auth.user;   // computed
await auth.login(email, password);
await auth.logout();
await auth.refreshAccessToken();
await auth.fetchProfile();
```

### `useWompiWidget()` — `src/composables/useWompiWidget.js` (named export)

```js
import { useWompiWidget } from '@/composables/useWompiWidget';
const { openWompiWidget } = useWompiWidget();
openWompiWidget(txData, { onApproved, redirectPath });
// txData: { uuid, amount_in_cents, public_key, integrity_signature, widget_url }
```

### `useEnums()` — `src/composables/useEnums.ts` (named export)

Cache de catalogos de enums (badges de estado, etc.) con fallback local de 4 capas
(memoria → localStorage → API → catalogo hardcodeado) si la API no responde. Usado por 20
archivos consumidores (OrderList, QuotationList, OperationBoard, etc.).

**Excepcion conocida a "sin TypeScript":** este archivo SI es `.ts` (migrado deliberadamente
2026-07-01, ver `frontend/.AGENT/doc/PHASE6_TYPESCRIPT_MIGRATION.md`) — decision consciente
revisada y dejada como esta el 2026-07-11 por el riesgo de tocar 20 consumidores, no un descuido.
No usar como precedente para escribir `.ts` nuevo en otros composables — sigue siendo la unica
excepcion. Ver [[project_enterprise_sync_framework]] en memoria.

```js
import { useEnums } from '@/composables/useEnums';
const enums = useEnums();
await enums.ensure('service-order-statuses');
enums.label('service-order-statuses', key, fallback);
enums.cssClass('service-order-statuses', key, fallback);
enums.icon('service-order-statuses', key, fallback);
```

### `useOperationTracking()` — `src/composables/useOperationTracking.js` (named export)

Tracking de operaciones (`operations.OperationTicket`) en tiempo real. Usado en las vistas de
seguimiento del portal cliente (`OperationTrackingView`).

## 3. Estructura de modulo CRUD admin

```
src/modules/{modulo}/
├── {Nombre}List.vue    # Tabla + paginacion + confirmacion delete inline + SintelOffcanvas
└── {Nombre}Form.vue    # Formulario crear/editar (vive dentro del offcanvas)
```

### Contrato de Form component

```vue
<script setup>
defineProps({
  item: { type: Object, default: null },    // null = crear, objeto = editar
  mode: { type: String, default: 'create' }, // 'create' | 'edit'
});
defineEmits(['success', 'cancel']);
// success → List cierra el offcanvas y refresca la tabla
// cancel  → List cierra el offcanvas sin cambios
</script>
```

Receta completa (List + Form + manejo de errores DRF): [../components/offcanvas.md](../components/offcanvas.md).

## 4. Patrones obligatorios

- **Debounce 400ms** en inputs de busqueda: `setTimeout`/`clearTimeout` o `@input` con delay.
- **Lazy loading** en router: `() => import('@/views/...')`.
- **Precios colombianos**: `new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(num)`.
- **Try/catch** en toda llamada async con `toast.error(...)` en el catch.
- **Estado global solo en Pinia** — nunca `provide/inject` para autenticacion ni para carrito.
- **`useApi()`** siempre — nunca `axios` directo en componentes.
- **Navegacion siempre por `name`**: `router.push({ name: 'product-detail', params: { uuid } })` —
  nunca `router.push('/ruta/hardcodeada')`.

## 5. Lookup field: `uuid` vs `id`

- Los **GETs** del catalogo publico devuelven `uuid` — usarlo como key de `v-for` y para filtros.
- Los **writes** al dashboard (`PATCH`, `DELETE`) usan **`id`** (PK entero) en la URL:
  `dashboard/products/${item.id}/`.
- Los **FK en payload** (ej. `category` en `ProductInputSerializer`) usan **`uuid`** porque son
  `SlugRelatedField(slug_field='uuid')`.

## 6. Patron de nuevo componente customer

```vue
<script setup>
import { ref, computed } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useCartStore } from '@/store/cart';
import { useAuthStore } from '@/store/auth';

const props = defineProps({ item: { type: Object, required: true } });
const emit = defineEmits(['success']);

const api = useApi();
const toast = useToast();
const cartStore = useCartStore();
const authStore = useAuthStore();
const loading = ref(false);

async function handleAction() {
  if (!authStore.isAuthenticated) {
    toast.info('Inicia sesion para continuar');
    return;
  }
  loading.value = true;
  try {
    await api.post('endpoint/', payload);
    toast.success('Accion exitosa');
    emit('success');
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Error inesperado');
  } finally {
    loading.value = false;
  }
}
</script>
```
