---
description: Arquitectura real del frontend Sintel — Vue 3 SPA dual (admin + customer) sobre DRF JWT. Punto de entrada del dominio architecture/.
metadata:
  domain: architecture
  supersedes: FRONTEND_SKILL.md (seccion 1, 9)
---

# Frontend Architect — Vision general

> Arquitectura vigente desde la migracion 2026-05. El stack HTMX + django-tables2 + crispy-forms
> fue eliminado por completo. Todo corre como SPA Vue 3.

## 1. Stack

| Capa | Tecnologia |
|---|---|
| Framework UI | Vue 3 Composition API (`<script setup>`) |
| Build | Vite 8 |
| Estado global | Pinia — ver [state_management.md](state_management.md) |
| Routing | Vue Router 4 con navigation guards — ver [routing.md](routing.md) |
| HTTP | Axios via `useApi()` composable — ver [vue_patterns.md](vue_patterns.md) |
| Estilos | Bootstrap 5.3.3 + Bootstrap Icons (`bi-*`) — ver [../design_system/](../design_system/) |
| Notificaciones | `useToast()` composable |
| Validacion de forms | `vee-validate` + `yup` (dependencias presentes en `package.json`; no hay skill dedicado aun — ver gap en [../editor/architecture_audit.md](../editor/architecture_audit.md)) |

JS puro es la regla — **una unica excepcion conocida**: `composables/useEnums.ts` (20
consumidores, migrado deliberadamente 2026-07-01, revisado y dejado como esta 2026-07-11 — ver
[vue_patterns.md](vue_patterns.md#useenums--srccomposablesuseenumsts-named-export)). No usarlo
como precedente para escribir `.ts` nuevo — todo composable nuevo va en `.js`.

## 2. Dos SPA, dos entry points

El build de Vite genera **dos bundles independientes** desde `vite.config.js` (`rollupOptions.input`):

| Bundle | Entry point | Monta en | Publico |
|---|---|---|---|
| `admin` | `src/apps/admin/main.js` | `#shop-spa-root` | Panel `/panel/*` |
| `customer` | `src/apps/customer/main.js` | mount condicional | Portal publico + `/mi-cuenta/*` |

Cada uno tiene su propio router (`src/apps/admin/router.js` para el panel). No compartir estado de
Pinia entre ambos asumiendo que corren en el mismo proceso de navegador salvo que la ruta lo permita.

## 3. Vite: `base` distinto por comando — REGLA CRITICA

`vite.config.js` es el **mismo archivo** para `npm run dev` (`command==='serve'`) y `npm run build`
(`command==='build'`), pero cada uno necesita un `base` distinto:

```js
base: command === 'build' ? '/static/panel/js/bundle/' : '/',
```

- **dev**: `'/'` — el servidor Vite en `localhost:5173` sirve todo desde la raiz (HTML, HMR,
  fallback SPA para rutas como `/panel/dashboard`). Fijar aqui el prefijo de produccion sin
  condicionar por comando rompe el dev server completo (bug real 2026-07-10: `/panel/dashboard`
  devolvia 404 en `localhost:5173`).
- **build**: `'/static/panel/js/bundle/'` — DEBE coincidir con `static_url_prefix` en
  `DJANGO_VITE` (`settings/base.py`) y con donde `collectstatic` deja los archivos
  (`staticfiles/panel/js/bundle/...`). Con `base:'/'` en produccion las URLs de chunks
  dinamicos salen mal, Nginx devuelve el shell HTML (catch-all), y el navegador rechaza el
  modulo por MIME type incorrecto — pantalla en blanco.

Ver [[feedback_shared_config_dev_prod]] en memoria — probar SIEMPRE dev y build tras tocar
`vite.config.js`.

## 4. Docker + HMR (desarrollo)

- Dev server: contenedor `ecommerce_sintel_frontend`, puerto `5173`.
- `server.host: '0.0.0.0'` — necesario para que el contenedor `django` alcance a `frontend` por
  la red Docker (`'localhost'` solo seria accesible dentro del mismo contenedor).
- `hmr.host: 'localhost'`, `hmr.port: 5173` — el navegador necesita la URL publica del servidor.
- **`watch.usePolling: true`, `interval: 300`** — OBLIGATORIO. Sin esto, inotify no propaga
  eventos del filesystem NTFS (Windows) al contenedor Linux y el HMR queda silenciosamente
  inactivo. Ver [[feedback_vite_docker_windows_hmr]].
- Hard refresh tras cambios de config: `docker restart ecommerce_sintel_frontend`.

## 5. Convencion de endpoints — REGLA CRITICA

```
LECTURA (GET)  → endpoint publico ReadOnly:   shop/products/, renting/equipment/, services/services/
ESCRITURA       → BFF admin (requiere JWT admin): dashboard/products/, dashboard/categories/, ...
(POST/PATCH/DELETE)
```

**Nunca** hacer POST/PATCH/DELETE a `shop/`, `renting/`, `technical_services/`/`services/`
directamente — son ViewSets ReadOnly, retornan 405. Solo el BFF `dashboard/` acepta escrituras.
Detalle completo de prefijos por app en [../components/cards.md](../components/cards.md) y en la
doc de arquitectura del backend correspondiente. Ver [[feedback_frontend_bff_endpoints]].

**Excepciones conocidas** (no "corregir" a `dashboard/`, son deliberadas):
- `RentingRequestList`/`RentalRequestActionsPanel` escriben directo a
  `renting/rental-requests/{uuid}/...` via `useRentingAdminStore` — el permiso es por-accion
  (`IsAdminUser` en cada `@action` del backend), no por namespace de URL.
- `cart/` escribe directo a sus propias actions (`add_item/`, `update_item/`).

## 6. Contratos de API conocidos — shop products

### 6.1 Endpoints de imagen (dashboard)

```
POST   dashboard/products/{uuid}/add_image/              multipart/form-data
  body: image(File), alt_text(str, opcional), is_primary('true'|'false')
  → 201 { id, uuid, image, alt_text, is_primary, display_order }

DELETE dashboard/products/{uuid}/delete_image/{img_uuid}/     → 204 No Content
POST   dashboard/products/{uuid}/set_primary/{img_uuid}/      → 200 { id, uuid, image, alt_text, is_primary, display_order }
```

```js
const fd = new FormData();
fd.append('image', fileRef.value);
fd.append('alt_text', 'Texto alternativo');
fd.append('is_primary', 'true');
await api.post(`dashboard/products/${product.uuid}/add_image/`, fd, {
  headers: { 'Content-Type': 'multipart/form-data' },
});
```

### 6.2 Endpoints de variante (dashboard)

```
GET    dashboard/products/{uuid}/variants/
POST   dashboard/products/{uuid}/variants/create/
PATCH  dashboard/products/{uuid}/variants/{variant_uuid}/    <- partial, mantiene SKU existente
DELETE dashboard/products/{uuid}/variants/{variant_uuid}/delete/
```

### 6.3 Shape de `ProductSerializer` (GET publico `shop/products/{uuid}/`)

```json
{
  "id": 4, "uuid": "...", "name": "...", "slug": "...",
  "short_description": null, "description": "", "video_url": null, "condition": "new",
  "category": 1, "category_name": "...", "category_uuid": "...",
  "brand": null, "brand_name": null, "brand_uuid": null,
  "is_featured": false, "is_active": true, "meta_title": "", "meta_description": "",
  "variants": [{
    "id": 1, "uuid": "...", "sku": "...", "price": "280000.00", "discounted_price": null,
    "stock": 10, "is_default": true, "attributes": { "Color": "Negro" },
    "effective_price": "280000.00",
    "price_info": { "base_price": "...", "has_discount": false, "applied_taxes": [], "final_price_net": "..." },
    "weight": null, "length": null, "width": null, "height": null
  }],
  "images": [{ "id": 1, "uuid": "...", "image": "/media/products/foto.png", "alt_text": "...", "is_primary": true, "display_order": 0 }],
  "avg_rating": 4.5, "review_count": 3, "stock": 10, "sku": "SKU-001"
}
```

```js
// Acceso estandar a imagen y precio en componentes Vue
const primaryImage = computed(() =>
  product.value?.images?.find(i => i.is_primary)?.image || product.value?.images?.[0]?.image || null);
const defaultVariant = computed(() =>
  product.value?.variants?.find(v => v.is_default) || product.value?.variants?.[0] || {});
const price = computed(() => parseFloat(
  defaultVariant.value?.discounted_price || defaultVariant.value?.effective_price || defaultVariant.value?.price || 0));
```

## Ver tambien

- [vue_patterns.md](vue_patterns.md) — composables, `<script setup>`, estructura de modulo
- [routing.md](routing.md) — mapa completo de rutas
- [state_management.md](state_management.md) — stores Pinia
- [../editor/architecture_audit.md](../editor/architecture_audit.md) — gaps conocidos y deuda tecnica
