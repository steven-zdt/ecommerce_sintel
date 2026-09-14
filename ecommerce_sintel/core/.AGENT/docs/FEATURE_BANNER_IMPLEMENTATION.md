# Feature Banner — Resumen de implementacion por archivo

Fecha: 2026-08-06. Ver `FEATURE_BANNER_ARCHITECTURE.md` para el grafo completo y las
decisiones de diseno; este documento es el listado de cambios reales por archivo.

## Backend

| Archivo | Cambio |
|---|---|
| `core/models.py` | +`FeatureBannerSection`, +`FeatureBannerBlock` (despues de `HomeCardGroup`, antes de `FooterCTAConfig`). |
| `core/migrations/0028_featurebannersection_featurebannerblock.py` | Migracion aditiva, generada y aplicada. |
| `core/services/commands.py` | +`FeatureBannerSectionSelector`, +`FeatureBannerSectionCommands`, +`FeatureBannerBlockSelector`, +`FeatureBannerBlockCommands` (antes de `HomeFeedSelector`). |
| `core/api/serializers.py` | +`FeatureBannerBlockSerializer`, +`FeatureBannerBlockInputSerializer`, +`FeatureBannerSectionSerializer` (incluye `blocks` anidado, solo lectura), +`FeatureBannerSectionInputSerializer`. Ambos Input aplican `_strip_html_fields`. |
| `core/api/views.py` | `HomeFeedView.home_feed()`: +`feature_banner_sections = FeatureBannerSectionSelector.list_active_with_blocks()`, +clave `'feature_banner_sections'` en el payload de respuesta. |
| `core/signals.py` | +2 pares `post_save`/`post_delete` (`FeatureBannerSection`, `FeatureBannerBlock`) -- solo `cache.delete(HOME_FEED_CACHE_KEY)`, mismo patron que el resto de modelos del Home Builder. |
| `dashboard/api/views.py` | +`AdminFeatureBannerSectionViewSet`, +`AdminFeatureBannerBlockViewSet` (despues de `AdminHomeCardGroupViewSet`). Multipart para imagenes, `_invalidate_home_feed_cache()` en cada mutacion. |
| `dashboard/api/urls.py` | +2 rutas: `feature-banner-sections/`, `feature-banner-blocks/`. |
| `core/tests/test_feature_banner.py` | 21 tests nuevos (validaciones de modelo, Commands, filtrado de visibilidad, exposicion en home-feed). Ver `FEATURE_BANNER_TESTS.md`. |

## Frontend — admin

| Archivo | Cambio |
|---|---|
| `frontend/src/store/coreAdmin.js` | +estado `featureBannerSections`, `featureBannerSectionsLoading`. +7 acciones CRUD (`fetchFeatureBannerSections`, `create/update/deleteFeatureBannerSection`, `create/update/deleteFeatureBannerBlock`, `reorderFeatureBannerBlocks`). |
| `frontend/src/modules/core/home-builder/FeatureBannerSection.vue` | Nuevo. Componente admin: lista de secciones + modal Seccion + modal Bloque, mirror de `CardsSection.vue`. |
| `frontend/src/modules/core/HomeConfigView.vue` | +import, +`<FeatureBannerSection>` condicional, +entrada en `sections` (sidebar), +`feature_banner` en `SECTION_TO_RENDERER`, +prop en el `<HomeRenderer>` del preview, +`fetchFeatureBannerSections()` en `onMounted()`. |

## Frontend — publico

| Archivo | Cambio |
|---|---|
| `frontend/src/components/ui/showcase/FeatureBannerButton.vue` | Nuevo. Resuelve `url_type` (INTERNA/EXTERNA/ANCHOR) a `RouterLink`/`<a>`/scroll suave. |
| `frontend/src/components/ui/showcase/FeatureBannerBlock.vue` | Nuevo. Un bloque: grid CSS que cambia segun `layout_type`, badge, beneficios, stats, hasta 2 botones. |
| `frontend/src/components/ui/showcase/FeatureBannerRenderer.vue` | Nuevo. Orquestador: itera secciones visibles ordenadas, renderiza fondo/tema/overlay de cada una y sus bloques. |
| `frontend/src/renderers/HomeRenderer.vue` | +import `FeatureBannerRenderer`, +prop `featureBannerSections`, +bloque `<template v-if="showSection('feature_banner')">` entre `modules` y `flash`. |
| `frontend/src/views/customer/HomeView.vue` | +ref `featureBannerSections`, +mapeo `data.feature_banner_sections || []`, +prop al `<HomeRenderer>`. |

## Documentacion

9 documentos en `core/.AGENT/docs/`: este mismo archivo, `FEATURE_BANNER_ARCHITECTURE.md`,
`FEATURE_BANNER_API.md`, `FEATURE_BANNER_RENDERER.md`, `FEATURE_BANNER_ADMIN.md`,
`FEATURE_BANNER_FRONTEND.md`, `FEATURE_BANNER_CACHE.md`, `FEATURE_BANNER_TESTS.md`,
`FEATURE_BANNER_TRACEABILITY.md`.

## Verificacion realizada

- `manage.py check` limpio (unico warning preexistente de `cart.Cart.user`, no relacionado).
- `manage.py makemigrations core` / `migrate core` sin conflictos.
- `npx vite build` limpio (sin errores ni warnings nuevos).
- `pytest core/tests/test_feature_banner.py` -- 21/21 passed.
- Prueba end-to-end en navegador (admin real + home publica real, sin mocks):
  - Login admin real (usuario temporal `is_staff/is_superuser`, eliminado al terminar).
  - Tab "Feature Banner" visible en `/panel/home-config`, formulario de Seccion completo
    (todos los campos de v1 presentes y funcionales).
  - Creacion de un bloque de verificacion via la capa `Commands` real (layout `fifty_fifty`,
    badge, 2 beneficios, 1 stat, boton primario `INTERNA` + boton secundario `EXTERNA`).
  - El bloque se renderizo correctamente tanto en la Vista Previa del builder como en la
    home publica real (`/`), con `href` resuelto correctamente para ambos `url_type`.
  - Bloque de verificacion eliminado (soft-delete) al terminar; la seccion preexistente
    "Nuevas tecnologias" (datos reales del usuario, no creados por esta verificacion) se
    dejo intacta.
