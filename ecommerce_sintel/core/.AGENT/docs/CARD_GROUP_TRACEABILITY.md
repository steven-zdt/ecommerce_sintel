# Card Group Section — Trazabilidad campo → modelo → API → frontend → render

Fecha: 2026-08-06. Checklist campo por campo, mismo formato que
`FEATURE_BANNER_TRACEABILITY.md`/`HOME_MODULE_SYNC_REPORT.md`. Objetivo: confirmar que
todos los campos nuevos llegan hasta el render final.

## `HomeCardGroup`

| Campo | Modelo | Serializer admin | Serializer público | Renderer | Estado |
|---|---|---|---|---|---|
| `columns_tablet` | Sí | Sí | Sí | `CardsGrid.vue` (`--cg-cols-tablet`) / `CardsSlider.vue` (`itemsTablet`) | OK |
| `columns_mobile` | Sí | Sí | Sí | idem (`--cg-cols-mobile` / `itemsMobile`) | OK |
| `gap` | Sí | Sí | Sí | idem (`--cg-gap` / `gap`) | OK |
| `carousel_autoplay` | Sí | Sí | Sí | `CardsSlider.vue` → `MarketplaceCarousel` `autoplay` — **solo con efecto si `layout_type='slider'`**, documentado explícitamente en el modelo | OK (condicional por diseño) |
| `carousel_loop` | Sí | Sí | Sí | idem `loop` | OK (condicional) |
| `carousel_speed` | Sí | Sí | Sí | idem `speed` | OK (condicional) |
| `show_arrows` | Sí | Sí | Sí | idem `showArrows` | OK (condicional) |
| `show_indicators` | Sí | Sí | Sí | idem — controla `<MarketplaceIndicators v-if>` | OK (condicional) |

## `HomeCard`

| Campo | Modelo | Serializer admin | Serializer público | Renderer | Estado |
|---|---|---|---|---|---|
| `badge_color` | Sí | Sí | Sí | `CardItem.vue` `:style="{background: card.badge_color}"` — verificado reemplaza el azul hardcodeado | OK |
| `url_type` | Sí (+ validación `clean()`) | Sí | Sí | `CardItem.vue::navigate()` vía `resolveUrlNavigation()` | OK |
| `url_target` | Sí | Sí | Sí | idem — solo relevante si `url_type=EXTERNA` | OK (condicional por diseño) |
| `stats` (JSON) | Sí | Sí (con sanitización HTML) | Sí | `CardItem.vue` — chips `<div class="ci-stats">`, solo en variantes `vertical`/`horizontal`/`premium` | OK (condicional por diseño) |
| `secondary_label/icon/url/url_type/target` (5 campos) | Sí | Sí | Sí | `CardItem.vue` — `<a class="ci-secondary-btn">`, mismo alcance condicional que `stats` | OK (condicional por diseño) |

Los "condicional por diseño" no son campos sin efecto — tienen efecto real, pero
**deliberadamente acotado** a los casos donde aplican (carrusel solo en layout slider,
extras solo en 3 de 9 variantes visuales, target solo relevante para enlaces externos) — no
son la falla que la auditoría `HOME_MODULE_*` encontró (campos que NUNCA se leían en ningún
escenario).

## Campos del brief original excluidos deliberadamente (y por qué)

| Campo pedido | Decisión | Razón |
|---|---|---|
| Rating | Excluido | El proyecto ya tiene un sistema de Reviews real (`AbstractReview`, con datos verificables por compra/uso). Un campo de "rating" manual en una tarjeta promocional simularía un dato de confianza no verificado — riesgo de mostrar una calificación fabricada como si fuera real. |
| Precio / Precio anterior (campos dedicados) | Excluido, cubierto por `stats` | Un campo `price` solo tiene sentido para contenido tipo curso/producto, no para noticias/eventos/personal — iría contra "cualquier colección futura". `stats: [{label:"Precio", value:"$150.000"}]` cubre el mismo caso sin ese acoplamiento. |
| SEO por tarjeta (meta title/description) | Excluido | Sin precedente en ningún otro tipo de sección del Home Builder (Modulos/Banners/Tarjetas/Feature Banner) — el SEO del sitio se gestiona vía `seo/` app, no por tarjeta individual. |
| Fechas de publicación/expiración | Excluido | Sin precedente. `is_active`/`is_visible` ya controlan visibilidad; una fecha de expiración requeriría un job de background para desactivar automáticamente, fuera de alcance. |
| Idioma, Tags, Categoría (campos dedicados) | Excluido | Sin precedente; el sitio no tiene i18n multi-idioma activo. `stats`/`subtitle` ya permiten expresar una categoría como texto libre si el admin lo necesita. |
| Tracking/Analytics por botón | Excluido | Sin precedente en Feature Banner tampoco (mismo criterio ya aplicado 2026-08-06). |
| 3 imágenes por breakpoint | Excluido, 1 imagen responsive por CSS | Mismo criterio que Feature Banner — el `object-fit:cover` de la imagen única ya resuelve el recorte responsive sin triplicar los uploads del admin. |
| Editor rich-text (WYSIWYG) | Excluido, texto plano | Mismo criterio que Feature Banner — sin precedente de un editor WYSIWYG en el proyecto; `description` sigue siendo `TextField` simple. |
| Motor de auto-auditoría (contraste WCAG, teclado, screen reader, 404) | Excluido | Es una herramienta de auditoría de accesibilidad completa, no una funcionalidad de "card group". Se optó por buenas prácticas de markup por defecto (`alt` real en imágenes, `aria-roledescription` ya presente en `MarketplaceCarousel.vue`, `role="group"` por slide) en vez de construir un validador automático sin precedente en el proyecto. |

## Verificación end-to-end en navegador

Login admin real (usuario temporal, eliminado al terminar) → pestaña "Tarjetas" en
`/panel/home-config` → grupo configurado con layout Slider + autoplay/loop/columnas
responsive → tarjeta con `stats`, badge de color y botón secundario (`url_type=EXTERNA`) →
confirmado en el preview del builder Y en la home pública real (`/`) que el carrusel
(autoplay/flechas/indicadores), las columnas responsive, los stats y ambos botones (con
`href` resuelto correctamente) se ven y funcionan. Datos de prueba limpiados al terminar,
sin tocar los grupos/tarjetas reales ya configurados por el usuario.
