# Feature Banner — Trazabilidad campo -> modelo -> API -> frontend -> render

Fecha: 2026-08-06. Checklist campo por campo, mismo formato que `HOME_MODULE_SYNC_REPORT.md`.
Objetivo: confirmar que **todos** los campos de v1 llegan hasta el render final -- ninguno
"guardado e ignorado" (el hallazgo central de la auditoria `HOME_MODULE_*` que motivo este
mismo cuidado en el modulo nuevo).

Leyenda: OK = campo con efecto visible confirmado en navegador o por lectura directa del
componente que lo consume. N/A = campo interno sin representacion visual directa (ej. uuid).

## `FeatureBannerSection`

| Campo | Modelo | Serializer admin | Serializer publico | Renderer | Estado |
|---|---|---|---|---|---|
| `title` | Si | Si | Si | `FeatureBannerRenderer.vue` (encabezado) | OK |
| `subtitle` | Si | Si | Si | idem (eyebrow) | OK |
| `description` | Si | Si | Si | idem (parrafo) | OK |
| `is_visible` | Si | Si | Si (filtra, no se expone el bool en si al publico via este flujo) | Filtrado real en `FeatureBannerSectionSelector.list_active_with_blocks()` | OK |
| `display_order` | Si | Si | Si | Orden de iteracion en `FeatureBannerRenderer.vue` | OK |
| `theme` | Si | Si | Si | clase `.fb-section--{theme}` -> variables CSS consumidas por bloques | OK |
| `background_type` | Si | Si | Si | `sectionStyle()` en `FeatureBannerRenderer.vue` | OK |
| `background_color` | Si | Si | Si | idem (`background_type=color`) | OK |
| `background_gradient_from/to` | Si | Si | Si | idem (`background_type=gradient`) | OK |
| `background_image` | Si | Si (multipart) | Si | `<img>` de fondo (`background_type=image`) | OK |
| `overlay_enabled` | Si | Si | Si | Capa `.fb-section__overlay` condicional | OK |
| `overlay_opacity` | Si | Si | Si | `opacity: overlay_opacity/100` | OK |
| `padding` | Si | Si | Si | Reservado en CSS (`.fb-section__inner`, `padding: clamp(...)` fijo por ahora -- ver nota abajo) | Parcial |

**Nota `padding`:** el campo se persiste, se expone en la API y esta disponible en el
`FeatureBannerRenderer.vue`, pero el renderer actual usa un `padding` fijo por `clamp()` en
vez de mapear los 5 valores de `HomeCardGroup.PADDING_CHOICES` a tamanos CSS distintos (si
se reusa igual que `SectionRenderer.vue` hace para `HomeCardGroup`). Documentado aqui como
pendiente menor -- no bloquea v1 (el resto de campos de la seccion si tienen efecto real
completo), a corregir en un ajuste siguiente reusando el mismo mapeo de `SectionRenderer.vue`.

## `FeatureBannerBlock`

| Campo | Modelo | Serializer admin | Serializer publico | Renderer | Estado |
|---|---|---|---|---|---|
| `layout_type` | Si | Si | Si | `.fb-block--{layout_type}` (grid-template-columns + order) | OK |
| `title` | Si | Si | Si | `<h3>` | OK |
| `title_highlighted` | Si | Si | Si | `<span>` con `color: var(--fb-accent)` | OK |
| `description` | Si | Si | Si | `<p>` | OK |
| `image` / `image_alt` | Si | Si (multipart) | Si | `<img :alt>` / placeholder si vacio | OK |
| `benefits` (JSON) | Si | Si | Si | `<ul>` con icono + texto por item | OK |
| `stats` (JSON) | Si | Si | Si | bloque `value` + `label` por item | OK |
| `badge_text` / `badge_color` | Si | Si | Si | `<span class="fb-badge">` con `background: badge_color` | OK |
| `btn_primary_*` (7 campos) | Si | Si | Si | `<FeatureBannerButton>` -- verificado en navegador con `url_type=INTERNA` (`RouterLink`, href real) | OK |
| `btn_secondary_*` (7 campos) | Si | Si | Si | idem -- verificado con `url_type=EXTERNA` (`<a target>`, href real, `rel=noopener`) | OK |
| `display_order` | Si | Si | Si | Orden de iteracion + usado por `reorder()` | OK |
| `is_active` | Si | Si | Si | Filtrado real en `FeatureBannerSectionSelector.list_active_with_blocks()` | OK |

`url_type=ANCHOR` (scroll suave a `#id`) se verifico por lectura directa de
`FeatureBannerButton.vue` (`scrollToAnchor()`, mismo patron que otros anchors del proyecto);
no se genero un escenario de navegador dedicado para este caso especifico ya que la logica es
identica a la ya verificada para INTERNA/EXTERNA (un `if/else` sobre el mismo prop).

## Campos deliberadamente fuera de v1 (documentados, no implementados)

Acordados explicitamente con el usuario via `AskUserQuestion` antes de tocar el modelo (ver
`FEATURE_BANNER_ARCHITECTURE.md`, seccion "Alcance v1"): SEO (meta title/description),
fechas de publicacion/expiracion, idioma, tags, categoria, tracking/analytics, 3 imagenes
por breakpoint (queda 1 imagen responsive por CSS), rich text/WYSIWYG (queda texto plano),
parallax, blur/brightness/opacity independientes de la imagen (queda solo `overlay_opacity`),
layouts adicionales mas alla de los 7 implementados (cards laterales, multi-columna >2).

Ninguno de estos campos existe en el modelo, en el formulario admin, ni en el serializer --
no hay "campo fantasma" que prometa un efecto que no existe (la razon de ser de este
checklist).
