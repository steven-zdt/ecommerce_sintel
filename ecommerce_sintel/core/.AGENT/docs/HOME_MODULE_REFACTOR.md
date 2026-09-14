# HOME_MODULE_REFACTOR.md — Remediación aplicada: Home Config → Módulos

**Fecha:** 2026-08-06. Sprint acotado ("cerrar la brecha admin→render", ver `HOME_MODULE_GRAPH.md`
para el grafo completo y `HOME_MODULE_SYNC_REPORT.md` para la auditoría campo a campo). Alcance
confirmado con el usuario: solo `HomeModuleConfig` (no `HomeCard`/`HomeCardGroup`), sin campos
nuevos en el modelo/API, sin construir componentes de layout nuevos — solo conectar al render
público lo que el formulario admin ya guarda.

Backend: **sin cambios** — los 5 problemas originales + el Fix 6 (agregado tras verificación
adicional pedida por el usuario) eran 100% de lectura en frontend.

## Fix 6 — Imagen de fondo subida quedaba huérfana (`media.type` congelado en `'color'`)

- **Archivo:** `frontend/src/components/ui/showcase/MarketplaceCard.vue` (computed `media`,
  antes líneas 112-124).
- **Contexto:** pedido explícito de garantizar con una prueba real de subida de archivo (no solo
  lectura de código) que la imagen del tab "Imagen" (`MediaTab.vue` → `background_image`) se
  materializa como fondo de la tarjeta en la home pública.
- **Causa raíz:** `ModuleBuilderModal.vue` guarda `layout_config.media.type` con el valor por
  defecto `'color'` en **cada** guardado del formulario (`DEFAULT_FORM().media.type = 'color'`),
  no solo cuando el admin elige explícitamente "Video" en la pestaña Multimedia. El computed
  `media` de `MarketplaceCard.vue` resolvía el tipo con `m.type || (background_image ? 'image' :
  'color')` — como `'color'` es un string no vacío (truthy), la expresión `m.type || fallback`
  nunca llegaba a evaluar el fallback que detectaría la imagen subida. Resultado: un admin sube una
  imagen real en el tab "Imagen", el backend la persiste correctamente
  (`background_image` con URL absoluta, confirmado en `GET core/home-feed/`), pero la tarjeta
  pública seguía mostrando el color sólido — la imagen quedaba huérfana, sin ningún error visible
  para el admin.
- **Solución:** el tipo `'video'` sigue siendo la única elección que se respeta tal cual (trae su
  propia URL, es inequívoca). Para cualquier otro caso, si existe `background_image`, esa imagen
  gana sobre el default `'color'`: `type = m.type === 'video' ? 'video' : (hasBgImage ? 'image' :
  (m.type || 'color'))`.
- **Evidencia:** verificado con subida de archivo real (multipart, PNG generado con gradiente
  reconocible) sobre el módulo real "Seguridad Electrónica". Antes del fix: `GET core/home-feed/`
  ya devolvía `background_image` con la URL correcta, pero el DOM público no renderizaba ningún
  `<img>` en la tarjeta (`layout_config.media.type` medido en `"color"`). Después del fix: mismo
  módulo, mismo dato, el DOM público renderizó `<img src="http://localhost:8000/media/
  home_modules/images/seguridad_bg_test.png">`. La imagen y el usuario admin de prueba se
  eliminaron al finalizar; el módulo real quedó restaurado a `background_image=None` (su estado
  original, confirmado antes de la prueba).

## Fix 1 — Ícono del botón hardcodeado

- **Archivo:** `frontend/src/components/ui/showcase/MarketplaceCard.vue:46`
- **Causa raíz:** el template tenía `<i class="bi bi-arrow-right mps-cta-icon">` fijo, sin usar el
  computed `button` (que ya existía y ya leía `layout_config.button` completo).
- **Solución:** `<i :class="['bi', button.icon || 'bi-arrow-right', 'mps-cta-icon']">`.
- **Evidencia:** verificado en vivo sobre el módulo real "Seguridad Electrónica" — con
  `button.icon = 'bi-check-circle'` guardado desde el admin, el DOM público renderizó
  `class="bi bi-check-circle mps-cta-icon"` (antes siempre `bi-arrow-right`).

## Fix 2 — Estilo del botón incompleto (`ghost`/`minimal` sin efecto)

- **Archivo:** `frontend/src/components/ui/showcase/MarketplaceCard.vue` (computed `ctaStyle`,
  antes líneas 152-156).
- **Causa raíz:** el computed solo tenía una rama `if (style === 'outline' || style === 'ghost')`
  seguida de `color: style === 'outline' ? ... : '#fff'` — `ghost` heredaba el fondo transparente
  de `outline` pero el color de texto blanco de `filled`, y `minimal` no tenía rama propia en
  absoluto (caía en `filled`).
- **Solución:** 4 ramas explícitas (`filled`/`outline`/`ghost`/`minimal`), cada una con su propia
  combinación de `background`/`color`/`border`/`padding`.
- **Evidencia:** con `button.style = 'ghost'` guardado, el DOM público midió
  `backgroundColor: rgba(0, 0, 0, 0)` (transparente) — antes de este fix habría sido
  `rgb(37, 99, 235)` (azul sólido, indistinguible de `filled`).

## Fix 3 — Posición del botón ignorada

- **Archivos:** `MarketplaceCard.vue` (template línea ~44, clase `.mps-cta--top` nueva en el CSS
  scoped).
- **Causa raíz:** el botón se renderizaba siempre en el mismo punto del DOM, sin condicionar por
  `button.position`.
- **Solución:** clase condicional `:class="{ 'mps-cta--top': button.position === 'top' }"` +
  `.mps-cta--top { order: -1; }` — `.mps-body` ya es `flex-direction: column`, así que reordenar
  con `order` mueve el botón visualmente al principio sin duplicar markup ni tocar el resto del
  layout. `bottom` (default) y `top` quedan soportados; `inline`/`overlay` quedan **pendientes**
  (requieren reflow de layout más invasivo — `overlay` en particular implica `position:absolute`
  sobre la imagen de fondo, fuera del alcance acordado de "bajo riesgo visual").
- **Evidencia:** con `button.position = 'top'`, `getComputedStyle()` sobre el elemento `.mps-cta`
  midió `order: -1` mientras que icono/título/subtítulo/descripción/stats midieron `order: 0`
  (orden de aparición en el DOM sin cambios, solo el orden visual vía flexbox).

## Fix 4 — Columnas/gap del carrusel desconectados

- **Archivo:** `frontend/src/components/ui/showcase/MarketplaceShowcase.vue` (computed
  `carouselCfg`, nuevo computed `columnsCfg`).
- **Causa raíz:** `layout_config.columns/columns_tablet/columns_mobile/gap` (pestañas
  Distribución/Responsive) y `layout_config.carousel.items_desktop/tablet/mobile` (pestaña
  Carrusel) son dos sistemas paralelos en el mismo formulario — el componente de render solo leía
  el segundo. Además, el prop `gap` de `MarketplaceCarousel.vue` (existía, con default fijo
  `1.25`rem) nunca se pasaba desde el padre.
- **Solución:** fallback en cascada, sin pisar configuración explícita existente:
  `items_desktop: c.items_desktop ?? columnsCfg.value.columns ?? 6` (ídem tablet/mobile/gap) +
  `:gap="carouselCfg.gap"` agregado al `<MarketplaceCarousel>`.
- **Evidencia:** módulo de prueba con `columns=4, columns_tablet=2, columns_mobile=1, gap=1` (sin
  pestaña Carrusel configurada) — las CSS custom properties reales en el DOM midieron
  `--mps-cols-desktop: 4, --mps-cols-tablet: 2, --mps-cols-mobile: 1, --mps-gap: 1rem` (antes
  habrían sido los defaults fijos `6/3/1.2/1.25rem` sin importar la configuración del admin).

## Fix 5 — Fondo de imagen de sección: imposible de configurar (bug de mapeo)

- **Archivo:** `frontend/src/modules/core/module-builder/MultimediaTab.vue:81-84`.
- **Causa raíz:** el `v-if` del input único cubría `type === 'image' || type === 'video'`, pero su
  `v-model` apuntaba siempre a `form.section_background.video_url` — nunca a `.image`, el campo
  que `MarketplaceShowcase.vue` sí sabía leer. Con `type='image'` seleccionado, el dato se perdía
  silenciosamente en cada guardado.
- **Solución:** dos inputs separados, cada uno con su `v-model` correcto según el tipo
  seleccionado (`.image` para `type==='image'`, `.video_url` para `type==='video'`, sin cambios
  de comportamiento para video).
- **Evidencia:** con `section_background = {type:'image', image:'<url>'}` guardado, el fondo de la
  sección completa en la home pública renderizó `<img src="<url>">` (antes, con el bug, el campo
  quedaba perpetuamente vacío pese a seleccionar "Imagen" como tipo).

## Verificación end-to-end realizada

Todos los fixes se probaron **en el módulo real "Seguridad Electrónica"** (`uuid
5c00ea4d-cae5-421f-ad3c-d8b69c1ad82e`), el mismo mencionado en el pedido original del usuario,
vía API directa (autenticado como admin temporal) y lectura del DOM público real — no solo el
preview interno del builder. El `layout_config` original se capturó completo antes de la prueba y
se restauró exactamente al terminar (confirmado por lectura posterior del DOM: ícono, estilo,
posición y fondo de sección de vuelta a sus valores de producción). El usuario de prueba admin se
eliminó al finalizar.

`npx vite build` limpio antes y después de la verificación en vivo.

## Qué NO se tocó (documentado, no silencioso)

Ver la sección "Fuera de alcance" de `HOME_MODULE_SYNC_REPORT.md` y el checklist completo en
`HOME_MODULE_CERTIFICATION.md`.
