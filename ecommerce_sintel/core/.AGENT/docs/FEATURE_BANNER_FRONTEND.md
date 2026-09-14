# Feature Banner — Componentes Vue e integracion

Fecha: 2026-08-06.

## Componentes nuevos

| Componente | Rol | Mirror de |
|---|---|---|
| `modules/core/home-builder/FeatureBannerSection.vue` | Admin: CRUD de secciones y bloques | `CardsSection.vue` |
| `components/ui/showcase/FeatureBannerRenderer.vue` | Publico: orquestador de secciones | `MarketplaceShowcase.vue` |
| `components/ui/showcase/FeatureBannerBlock.vue` | Publico: un bloque (imagen+texto+botones) | `MarketplaceCard.vue` |
| `components/ui/showcase/FeatureBannerButton.vue` | Publico: resuelve `url_type` a navegacion real | (nuevo patron, ver `HOME_MODULE_URLS.md`) |

## Store (`store/coreAdmin.js`)

```javascript
state: { featureBannerSections: [], featureBannerSectionsLoading: false }

actions:
  fetchFeatureBannerSections()
  createFeatureBannerSection(payload)
  updateFeatureBannerSection(uuid, payload)
  deleteFeatureBannerSection(uuid)
  createFeatureBannerBlock(payload)      // payload incluye 'section' (uuid)
  updateFeatureBannerBlock(uuid, payload)
  deleteFeatureBannerBlock(uuid)
  reorderFeatureBannerBlocks(sectionUuid, orderedUuids)
```

Mismo patron two-tier de loading que el resto de stores admin (`loading` para GET,
`actionLoading` implicito en cada accion de mutacion via try/catch + toast).

## Integracion en `HomeConfigView.vue`

- `sections` (sidebar): `{ id: 'feature_banner', label: 'Feature Banner', icon:
  'bi-window-stack', count: featureBannerSections.value.length || null }`.
- `SECTION_TO_RENDERER`: `feature_banner: 'feature_banner'` -- necesario para que la Vista
  Previa compartida filtre correctamente por `sections=['feature_banner']` cuando esa pestaña
  esta activa.
- `<FeatureBannerSection v-if="currentSection === 'feature_banner'" />`.
- `<HomeRenderer :feature-banner-sections="featureBannerSections" ... />` (preview).
- `store.fetchFeatureBannerSections()` en `onMounted()`.

## Integracion en `HomeRenderer.vue` / `HomeView.vue`

Ver `FEATURE_BANNER_RENDERER.md` para el bloque exacto agregado a `HomeRenderer.vue`.
`HomeView.vue` mapea la respuesta de `core/home-feed/`:

```javascript
const featureBannerSections = ref([]);
// ...
featureBannerSections.value = data.feature_banner_sections || [];
```

Mismo patron que `modules.value = data.modules || []` ya existente -- sin logica adicional
de transformacion en el cliente (el backend ya entrega el shape final).

## Verificacion realizada

- `npx vite build` limpio (sin errores ni warnings nuevos atribuibles a Feature Banner).
- Prueba real en navegador (login admin temporal, sin mocks): tab "Feature Banner" visible y
  funcional en `/panel/home-config`, modal Seccion y modal Bloque con todos los campos de la
  tabla de `FEATURE_BANNER_ADMIN.md` presentes.
- Bloque de verificacion creado via la capa `Commands` real (layout `fifty_fifty`, badge,
  beneficios, stats, boton primario `INTERNA` + boton secundario `EXTERNA`) se renderizo
  correctamente tanto en el preview del builder como en la home publica real (`/`), con href
  resuelto correctamente para ambos tipos de URL -- confirmando que
  `FeatureBannerRenderer.vue`/`FeatureBannerBlock.vue`/`FeatureBannerButton.vue` funcionan
  end-to-end contra datos reales, no solo contra el build.
