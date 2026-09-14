# Card Group Section — Componentes Vue e integración

Fecha: 2026-08-06.

## Archivo nuevo

| Archivo | Rol |
|---|---|
| `frontend/src/utils/urlNavigation.js` | `resolveUrlNavigation(url, urlType, router, target)` — helper compartido INTERNA/EXTERNA/ANCHOR, usado por `CardItem.vue` y (refactorizado) por `FeatureBannerButton.vue`. |

## Archivos modificados

| Archivo | Cambio |
|---|---|
| `frontend/src/components/ui/home/cards/CardItem.vue` | `navigate()` usa `resolveUrlNavigation()` en vez de inferencia por regex. Badge usa `card.badge_color`. Nuevo: chips de `stats` y botón secundario (solo variantes `vertical`/`horizontal`/`premium`). |
| `frontend/src/components/ui/home/cards/CardsGrid.vue` | +props `columnsTablet`/`columnsMobile`/`gap`, columnas responsive reales vía variables CSS (antes hardcodeadas a 2/1). |
| `frontend/src/components/ui/home/cards/CardsSlider.vue` | Reescrito: envuelve `MarketplaceCarousel.vue` + `MarketplaceIndicators.vue` en vez de un scroll-snap manual sin autoplay. |
| `frontend/src/renderers/SectionRenderer.vue` | Pasa `group` completo (antes solo `cards`/`columns`) a `CardsGrid`/`CardsSlider`. |
| `frontend/src/modules/core/home-builder/CardsSection.vue` | Formulario de grupo (Responsive + Carrusel condicional) y de tarjeta (`url_type`, `badge_color`, `stats`, botón secundario) — ver `CARD_GROUP_ADMIN.md`. |
| `frontend/src/components/ui/showcase/FeatureBannerButton.vue` | Refactor: el caso `ANCHOR` delega en `resolveUrlNavigation()` en vez de una segunda implementación de scroll suave. |
| `frontend/src/modules/core/HomeConfigView.vue` | +regla CSS `.hcb-subheading` (subtítulo de sección dentro de un modal — usado por las nuevas secciones "Responsive"/"Carrusel"/"Estadísticas"/"Botón secundario"). |

## Store (`store/coreAdmin.js`)

**Sin cambios.** `createCard`, `updateCard`, `upsertCardGroup` ya existían y aceptan
cualquier campo adicional en el payload sin cambios de firma — Card Group Section no
necesitó ninguna acción nueva en el store.

## Verificación realizada

- `npx vite build --mode development` limpio (sin errores ni warnings nuevos).
- Prueba real en navegador (login admin temporal, sin mocks): pestaña "Tarjetas" con un
  grupo configurado en layout Slider (autoplay + loop + columnas responsive), una tarjeta
  con `stats`, badge de color y botón secundario (`url_type=EXTERNA`) — verificado en el
  preview del builder y en la home pública real, con el carrusel, las columnas responsive,
  los stats y ambos botones funcionando. Ver detalle en `CARD_GROUP_TRACEABILITY.md`.
