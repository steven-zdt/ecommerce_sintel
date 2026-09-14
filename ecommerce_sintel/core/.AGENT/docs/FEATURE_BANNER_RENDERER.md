# Feature Banner — Renderer (JSON -> layout -> CSS)

Fecha: 2026-08-06. Como el JSON de `core/home-feed/` se traduce a layout visual real, sin
logica condicional de render mas alla de clases CSS (mismo criterio ya usado por
`MarketplaceCard.vue` con `order:-1` para `btn.position`).

## `FeatureBannerRenderer.vue` (orquestador)

- Filtra defensivamente `is_visible !== false` y `blocks[].is_active !== false` (el filtro
  real ya ocurre en el backend; este es un filtro adicional para el caso en que el caller
  -- la Vista Previa del builder -- pase el estado completo del formulario sin guardar).
- Por cada seccion visible con al menos un bloque, renderiza:
  - Fondo: `background_type` -> `color` (CSS `background`), `gradient` (`linear-gradient`
    135deg de `background_gradient_from` a `background_gradient_to`), `image` (`<img>`
    absoluto + `object-fit: cover`).
  - Overlay: si `overlay_enabled`, capa `#000` con `opacity: overlay_opacity / 100`.
  - Tema: clase `.fb-section--{theme}` define variables CSS (`--fb-text`, `--fb-text-muted`,
    `--fb-accent`, `--fb-media-placeholder`) consumidas por los bloques hijos -- 5
    combinaciones predefinidas, no colores sueltos por campo.
  - Encabezado opcional (`title`/`subtitle`/`description`) si al menos uno esta presente.
  - Itera `blocks` -> `<FeatureBannerBlock>`.

## `FeatureBannerBlock.vue` (un bloque)

`layout_type` controla **solo** `grid-template-columns` y `order` -- no hay markup
condicional por layout:

| `layout_type` | `grid-template-columns` | Notas |
|---|---|---|
| `image_left` | `1fr 1fr` | Orden natural del DOM (imagen primero). |
| `image_right` | `1fr 1fr` | `.fb-block__media { order: 2 }` / `.fb-block__content { order: 1 }` -- invierte visualmente sin duplicar markup. |
| `fifty_fifty` | `1fr 1fr` | Igual a `image_left` en proporcion. |
| `sixty_forty` | `3fr 2fr` | Imagen mas ancha. |
| `forty_sixty` | `2fr 3fr` | Texto mas ancho. |
| `full_image` | `1fr` (una columna) | `.fb-block__media` se posiciona `absolute; inset:0`, `.fb-block__content` queda encima con `color:#fff` y gradiente oscuro de scrim (`.fb-block__media-overlay`). Es el "overlay layout" del brief original, cubierto sin un campo nuevo. |
| `text_centered` | `1fr` | Oculta la columna de imagen (`v-if="layout_type !== 'text_centered'"`), texto centrado, `max-width: 720px`. |

Responsive: `@media (max-width: 767px)` colapsa **todos** los layouts de 2 columnas a 1 sola
columna y resetea el `order` de `image_right` a 0 (evita que en mobile la imagen quede
"despues" de forma inconsistente segun el layout).

Dentro del bloque, en orden: badge (si `badge_text`) -> titulo + `title_highlighted` (con
`color: var(--fb-accent)`) -> descripcion -> lista de beneficios (icono `bi-*` + texto) ->
stats (`value` grande + `label` pequeno) -> hasta 2 botones.

## `FeatureBannerButton.vue` (resolucion de URL)

Unica pieza con logica condicional real, dictada por el campo explicito `url_type` (no por
inferencia sobre el valor de la URL):

```
INTERNA  + url no vacio  -> <RouterLink :to="url">
EXTERNA  + url no vacio  -> <a :href :target :rel="noopener noreferrer si target=_blank">
ANCHOR   + url no vacio  -> <a :href @click.prevent="scrollIntoView({behavior:'smooth'})">
(cualquier otro caso)    -> <span> (boton no clicable, se ve pero no navega)
```

`btnStyle` (`filled|outline|ghost|minimal`) resuelve estilos inline con el mismo criterio ya
implementado y corregido en `MarketplaceCard.vue` esta sesion (`filled`: fondo solido +
texto blanco; `outline`: borde del color, fondo transparente; `ghost`: solo texto color,
sin borde; `minimal`: subrayado, sin padding).

## Integracion en `HomeRenderer.vue`

```html
<template v-if="showSection('feature_banner')">
  <FeatureBannerRenderer :sections="featureBannerSections" :loading="loading" />
</template>
```

Posicionado entre `modules` (Marketplace Showcase + stats) y `flash` (ofertas). El orden
ENTRE tipos de seccion (Hero vs Modules vs Feature Banner vs Cards...) sigue siendo fijo en
el template -- igual que hoy con el resto de secciones; el admin solo controla el orden
relativo ENTRE secciones Feature Banner via `display_order` (no se construyo un sistema de
orden global entre tipos de seccion, fuera del alcance de este sprint).
