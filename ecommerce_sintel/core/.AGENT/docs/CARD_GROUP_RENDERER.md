# Card Group Section — Renderer

Fecha: 2026-08-06. Cómo `layout_type`/campos nuevos se traducen a layout visual real.

## `SectionRenderer.vue` (una instancia por `HomeCardGroup`)

Sin cambios de estructura — sigue resolviendo `layout_type → nombre de componente` vía
`useLayoutEngine.js::resolveGroupLayout()` (`GROUP_LAYOUTS`, sin entradas nuevas: el mapeo
`slider → CardsSlider` ya existía). Cambio real: ahora pasa el objeto `group` completo (no
solo `cards`/`columns`) a `CardsGrid`/`CardsSlider`, para que puedan leer
`columns_tablet`/`columns_mobile`/`gap` (grid) o la config de carrusel (slider).

## `CardsGrid.vue` (layout `grid`/`cards`)

Antes: columnas mobile/tablet estaban **hardcodeadas** en CSS (`@media (max-width:767px) {
2 columnas }`, `@media (max-width:480px) { 1 columna }`), ignorando cualquier configuración
del admin. Ahora usa variables CSS (mismo mecanismo que `MarketplaceCarousel.vue`):

```css
.cg-grid { grid-template-columns: repeat(var(--cg-cols-mobile), 1fr); }
@media (min-width: 576px) { grid-template-columns: repeat(var(--cg-cols-tablet), 1fr); }
@media (min-width: 992px) { grid-template-columns: repeat(var(--cg-cols-desktop), 1fr); }
```

`--cg-cols-desktop/tablet/mobile` y `--cg-gap` se calculan desde `group.columns`/
`columns_tablet`/`columns_mobile`/`gap`, con `clamp(1,6)` de seguridad.

## `CardsSlider.vue` (layout `slider`)

Reescrito para envolver `MarketplaceCarousel.vue` + `MarketplaceIndicators.vue` — el mismo
carrusel ya probado en `MarketplaceShowcase.vue` para Modulos, en vez de la implementación
manual de scroll-snap que tenía antes (sin autoplay/loop/indicadores). Mismo wiring exacto:

```
group.columns/columns_tablet/columns_mobile/gap  -> itemsDesktop/Tablet/Mobile/gap
group.carousel_autoplay/carousel_loop/carousel_speed -> autoplay/loop/speed
group.show_arrows   -> showArrows
group.show_indicators -> <MarketplaceIndicators v-if>
```

`carouselRef` expone `scrollToIndex()`, usado por `onIndicatorSelect()` al hacer clic en un
punto — idéntico al patrón ya usado en `MarketplaceShowcase.vue`. `autoplay` por defecto es
`false`: un grupo `slider` configurado antes de este cambio se ve visualmente igual hasta
que el admin activa autoplay/ajusta columnas explícitamente.

## `CardItem.vue` (una tarjeta, 9 variantes visuales)

Cambios (aplican a las 9 variantes salvo donde se indica):

- **Badge**: `background: card.badge_color || '#2563eb'` en vez del azul hardcodeado.
- **Navegación de la tarjeta** (`navigate()`): usa el helper compartido
  `resolveUrlNavigation(url, urlType, router, target)` en vez de la inferencia por regex
  `redirect_url.startsWith('http')`. Mismo helper que usa `FeatureBannerButton.vue`.
- **Stats y botón secundario**: renderizados **solo** en las variantes `vertical`,
  `horizontal`, `premium` (`showExtras` computed) — las 6 variantes restantes
  (`compact`/`glass`/`dark`/`gradient`/`image_bg`/`logo`) quedan sin estos elementos por
  diseño: son composiciones minimalistas donde un bloque de chips + botón rompería la
  intención visual del tipo. El botón secundario usa `@click.stop.prevent` para no disparar
  también el `navigate()` de la tarjeta completa.

## Integración (sin cambios estructurales en `HomeRenderer.vue`)

`showSection('cards')` sigue siendo el mismo bloque de siempre — Card Group Section no
introduce un nuevo `showSection()` ni una nueva clave de sección; sigue siendo la pestaña
"Tarjetas" existente, ahora con más capacidad visual.
