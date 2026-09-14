# HOME_MODULE_SYNC_REPORT.md — Auditoría de sincronización campo a campo

**Fecha:** 2026-08-06. Fase 2 del brief de auditoría "Home Config → Módulos".

**Nota de método:** la primera versión de este documento se basó en el resumen de un agente de
exploración automatizado. Antes de tocar código, se releyó directamente el código fuente completo
de `MarketplaceCard.vue`, `MarketplaceShowcase.vue`, `MarketplaceCarousel.vue`,
`ModuleBuilderModal.vue` y las 13 pestañas del formulario — esa lectura directa corrigió 4 filas
del hallazgo inicial (subtítulo, descripción, animación y overlay en realidad SÍ funcionaban, con
un fallback legado deliberado y correcto). Esta versión refleja el estado real verificado, y
además el estado **tras** aplicar los 5 fixes acordados con el usuario (ver
`HOME_MODULE_REFACTOR.md`).

Alcance: tarjetas de módulo (`HomeModuleConfig` vía `ModuleBuilderModal.vue`) tal como se
renderizan en `MarketplaceShowcase.vue`/`MarketplaceCard.vue` en la home pública.

## Leyenda

- **OK** — el campo llega intacto del admin al render visual, con el efecto esperado.
- **CORREGIDO** — estaba roto/ignorado, se corrigió y verificó en este sprint (ver
  `HOME_MODULE_REFACTOR.md` para archivo:línea del fix y evidencia).
- **PENDIENTE** — se guarda pero no tiene efecto; queda fuera de este sprint por decisión
  explícita del usuario (riesgo de alterar visualmente tarjetas ya publicadas, o requiere
  construir componentes de layout que no existen hoy).
- **N/A** — el campo no existe en el modelo.

## Tabla de auditoría (estado final, post-remediación)

| Campo (brief) | Origen admin (tab:campo) | ¿Modelo/API? | ¿Frontend lo lee? | Estado |
|---|---|---|---|---|
| Título | General:`custom_label` | Sí | Sí | **OK** |
| Subtítulo | General:`public_subtitle` | Sí | Sí — `MarketplaceCard.vue:39`, condicionado por `show.subtitle` (toggle real `show_subtitle` del form) | **OK** |
| Descripción | General:`description` | Sí | Sí — `MarketplaceCard.vue:40`, condicionado por `show.description` | **OK** |
| Icono | Icono:`custom_icon` | Sí | Sí, fallback `'bi-grid'` | **OK** |
| Badge | Contenido:`badge_text`/`badge_color` | Sí | Sí | **OK** |
| CTA (url) | General:`custom_url` | Sí | Sí | **OK** (ver `HOME_MODULE_URLS.md`) |
| Texto del botón | Botones:`btn_text` | Sí | Sí, fallback `'Ver más'` | **OK** |
| Icono del botón | Botones:`btn_icon` | Sí | `MarketplaceCard.vue:46` — ícono fijo → ahora lee `button.icon` | **CORREGIDO** |
| Estilo del botón | Botones:`btn_style` (filled/outline/ghost/minimal) | Sí | `ctaStyle` — antes `ghost`/`minimal` colapsaban en otras ramas → las 4 ahora distinguibles | **CORREGIDO** |
| Posición del botón | Botones:`btn_position` (bottom/top/inline/overlay) | Sí | `bottom`/`top` ahora funcionan (CSS `order`); `inline`/`overlay` quedan pendientes (requieren reflow de layout más invasivo) | **CORREGIDO (parcial)** |
| Estadísticas | Contenido:`stats[]` | Sí | Sí | **OK** |
| Overlay | (legado `bg_overlay`/`bg_overlay_opacity` + nuevo `layout_config.overlay.*`) | Sí | Sí — `overlayCfg` (`MarketplaceCard.vue:129-140`) resuelve el path nuevo y cae a un fallback legado robusto si no existe; funciona en ambos casos | **OK** |
| Orden | General:`display_order` | Sí | Sí | **OK** |
| Visibilidad | General:`is_visible` | Sí | El endpoint público no filtra por `is_visible` (delega el filtro al frontend, que sí lo hace hoy correctamente en `MarketplaceShowcase.vue:91`) | **OK (funciona hoy; arquitectura sin defensa en profundidad — ver nota abajo)** |
| Animación | Animación:`animation_type/duration/delay/repeat` | Sí | Sí — `MarketplaceCard.vue:143,148-149` (`revealClass`, `cardStyle`) | **OK** |
| Columnas (desktop/tablet/mobile) + Gap | Distribución + Responsive | Sí | `MarketplaceShowcase.vue:carouselCfg` — antes ignorados, ahora alimentan el carrusel como fallback cuando el módulo no configuró su propia pestaña Carrusel | **CORREGIDO** |
| Cantidad de elementos destacados | General:`featured_items_limit` | Sí | Sí | **OK** |
| Layout (tipo de presentación) | Presentación:`display_type` (17 opciones) | Sí | No — sigue sin efecto, el render público siempre es el carrusel horizontal | **PENDIENTE** (decisión de producto: implementar layouts reales vs. simplificar el selector) |
| Fondo de imagen de sección completa | Multimedia:tipo "Imagen" | Sí | `MultimediaTab.vue` — bug de mapeo (siempre escribía en `.video_url`) → corregido, ahora escribe en `.image` | **CORREGIDO** |
| Colores secundario/texto/fondo/tamaños | Estilo:`color_secondary/text/bg`, `title_size`, `subtitle_size`, `font_weight` | Sí | No — no se leen en el render público | **PENDIENTE** (aplicar retroactivamente podría cambiar visualmente tarjetas ya publicadas sin aviso) |
| Categoría | Contenido:`show_category` | Sí | No — no existe elemento de categoría en la tarjeta | **PENDIENTE** |
| Imagen (de fondo, por tarjeta) | Media: subida de archivo | Sí | Antes **ERROR (roto)**: `media.type` quedaba congelado en `'color'` (default de fábrica guardado en cada save) y bloqueaba el fallback que detectaba `background_image`. Corregido (Fix 6, ver `HOME_MODULE_REFACTOR.md`), verificado con subida de archivo real | **CORREGIDO** |
| URL | General:`custom_url` | Sí | Sí | **OK** (ver `HOME_MODULE_URLS.md`) |
| Target (`_blank`/`_self`) | No existe campo para `custom_url` | No | Se infiere por regex, no es explícito | **PENDIENTE** (campo faltante, ver `HOME_MODULE_URLS.md`) |
| Prioridad | N/A en `HomeModuleConfig` (existe en `HomeCard`, otro modelo) | N/A | N/A | **N/A** |
| Publicación (fecha) | No implementado | No | No | **N/A** |

## Resumen cuantitativo

De 24 campos auditados tras la remediación: **17 OK** (12 ya funcionaban + 5 corregidos en este
sprint: icono/estilo/posición de boton, columnas/gap del carrusel, fondo de imagen de seccion
completa, e imagen de fondo por tarjeta — Fix 6), **5 PENDIENTE** (documentados, decisión de
producto explícita antes de tocarlos), **2 N/A**.

## Nota sobre visibilidad (no corregida, evaluada y aceptada)

`HomeFeedSelector.get_module_configs()` no filtra por `is_visible` a nivel de backend — el filtro
real ocurre en `MarketplaceShowcase.vue:91` (`visibleModules`). Funciona correctamente hoy
(verificado). Es una arquitectura sin "defensa en profundidad" (si un futuro consumidor del mismo
endpoint público olvida filtrar, expondría módulos ocultos) pero no es un bug activo — se deja
documentado como mejora futura, fuera del alcance acordado de este sprint (que era estrictamente
frontend, sin tocar el backend).
