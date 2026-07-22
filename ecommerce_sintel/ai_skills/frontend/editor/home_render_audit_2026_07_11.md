---
description: Auditoria completa (Fases 1-7) del modulo /panel/home-config vs Landing publica. HomeRenderer unico implementado y verificado; QA final con metricas reales de performance/SEO/accesibilidad/consola/red.
metadata:
  domain: editor
  status: proceso-de-7-fases-completado
  last_audited: "2026-07-11"
---

# Auditoria Home Config — Dashboard Preview vs Landing Publica

Proceso de 7 fases pedido por el usuario, cada una con autorizacion explicita antes de empezar.
Fases 1 y 2 completadas — **ningun archivo de codigo fue modificado**, solo lectura.

## FASE 1 — Auditoria Arquitectonica

Metodo: lectura directa de `modules/core/HomeConfigView.vue` (1936 lineas),
`views/customer/HomeView.vue`, `renderers/SectionRenderer.vue`, `core/api/views.py`,
`dashboard/api/views.py` — no se toco ningun archivo.

### Resumen ejecutivo

**Confirmado: existen DOS motores de render independientes**, exactamente el problema que el
brief describe. No hay un `<HomeRenderer/>` unico. Hay, de hecho, **tres** implementaciones
distintas de "como se ve una tarjeta/banner/hero", ninguna comparte componente con las otras:

| # | Motor | Donde vive | Que renderiza |
|---|---|---|---|
| 1 | **Landing real** | `HomeView.vue` + 8 componentes de `components/ui/landing/` + `renderers/SectionRenderer.vue` + su familia (`CardsGrid`, `CardsSlider`, `TimelineSection`, `AccordionSection`) | Lo que el usuario final ve en `/` |
| 2 | **Preview del panel admin** | Markup inline dentro de `HomeConfigView.vue` (clases `hcb-pv-*`), ~126 referencias a clases exclusivas de preview | Una maqueta esquematica, NO los componentes reales |
| 3 | **Preview de tarjeta individual** | `CardItemPreview`, un componente definido inline con `defineComponent`+`h()` dentro de `HomeConfigView.vue` (linea 1462) | Reimplementa a mano el render de una card (icono, titulo, badge, gradiente) |

### Hallazgo 1 — La "Vista Previa" del panel NO es una vista previa real

El panel `/panel/home-config` (`HomeConfigView.vue`) tiene un `<aside class="hcb-preview-panel">`
que, segun la seccion activa (`currentSection`), renderiza uno de 7 bloques de markup **totalmente
distintos** a los componentes reales:

- **Modulos**: chips pequeños con icono+color+label (real: `ModuleGrid.vue`, grid completo con
  animaciones de entrada por `IntersectionObserver`).
- **Banners**: `<img>`/placeholder simple con overlay basico (real: `HeroSection.vue` +
  `HeroSlide.vue` + `HeroBackground.vue` — carousel Bootstrap `carousel-fade`, capa de fondo con
  video/Ken-Burns/gradiente animado con orbs).
- **Tarjetas**: grid truncado a 4 items por grupo, usa `CardItemPreview` (el `h()` inline, ver
  Hallazgo 2) — real: `SectionRenderer.vue` + 4 layouts posibles (`CardsGrid`/`CardsSlider`/
  `TimelineSection`/`AccordionSection`) segun `group.layout_type`, con estilo calculado por
  `useLayoutEngine()`.
- **Marca/Navbar**: mockup de navbar con nombre+links (real: `CustomerNavbar.vue`, componente
  global renderizado por `CustomerLayout.vue`, con carrito, estado de auth, glassmorphism).
- **CTA Final**: texto plano con 2 "botones" de `<span>` (real: `FooterCTA.vue`, con gradiente
  animado real).
- **Footer**: lista de contacto+links simplificada (real: `CustomerFooter.vue`, mas rico, con
  redes sociales y grupos).

**Consecuencia directa:** un cambio visual real (ej. ajustar el gradiente de `HeroBackground.vue`,
o el layout `slider` vs `grid` de `SectionRenderer`) **no se refleja en absoluto** en la vista
previa del panel — el admin ve una aproximacion generica, no lo que realmente vera el cliente. Esto
es el nucleo exacto del problema que describe el brief del usuario.

### Hallazgo 2 — Triple implementacion de "como se ve una card"

1. `CardsGrid.vue` / `CardsSlider.vue` / `TimelineSection.vue` / `AccordionSection.vue`
   (`components/ui/home/cards/` y `components/ui/home/sections/`) — usados por `SectionRenderer`
   en la landing real.
2. `CardItemPreview` — definido con `defineComponent({ setup() { return () => h(...) } })` **inline
   dentro de `HomeConfigView.vue`** (no es un `.vue` separado). Reimplementa manualmente icono,
   titulo, subtitulo, badge "Destacado", y los 3 `card_type` (vertical/gradient/dark) con logica de
   color duplicada.
3. El preview esquematico de `hcb-pv-card` (linea ~473-489) — una TERCERA variante, aun mas
   simplificada, usada en el panel de vista previa lateral (no la del modal de edicion).

Estas 3 implementaciones pueden divergir independientemente sin que nada lo detecte — si se agrega
un `card_type` nuevo en el backend, hay que recordar actualizarlo en 3 lugares distintos.

**Nota de estilo de codigo:** `CardItemPreview` usa la API de render functions (`h()`), un patron
que no existe en ningun otro lugar del proyecto (`ai_skills/frontend/architecture/vue_patterns.md`
establece `<script setup>` como regla no negociable). Ya se encontro un intento de reintroducir
`h()` en esta misma sesion (modulo de pagos) y se descarto por inconsistencia — este es un caso
pre-existente que no se habia detectado hasta ahora.

### Hallazgo 3 — Volumen de CSS duplicado

`HomeConfigView.vue` tiene 1936 lineas totales; el bloque `<style scoped>` (linea ~1499 a 1936,
~437 lineas) define un sistema visual **completo y paralelo** con prefijo `hcb-*` (~126
referencias a clases de preview: `hcb-pv-*`, `hcb-cip*`, `hcb-blp*`, `hcb-nav-preview*`,
`hcb-brand-preview*`). Ninguna de estas clases se comparte con `home-root`/`.sr-section` (el
sistema de la landing real en `HomeView.vue`/`SectionRenderer.vue`). Dos paletas de color, dos
sistemas de spacing, dos convenciones de nombres — mantenidos por separado.

### Hallazgo 4 — JSON: contratos distintos por diseno (no necesariamente un problema, pero sin verificar)

- **Landing real** consume `GET core/home-feed/` (`core.api.views.HomeFeedView.home_feed`) —
  endpoint publico, cacheado (`HOME_FEED_CACHE_KEY`), shape optimizado para lectura.
- **Panel admin** consume `dashboard/home-config/`, `dashboard/home-cards/`,
  `dashboard/home-card-groups/`, etc. (`dashboard.api.views.AdminHomeConfigViewSet` y otros,
  delegando a `core.services.selectors.HomeConfigSelector`/`HomeConfigCommands`) — CRUD admin,
  shape orientado a edicion (incluye campos no publicos, sin cache).
- **No se verifico campo por campo** si ambos shapes son compatibles/consistentes entre si (ej. si
  `card_type`, `layout_type`, `background_color` se llaman igual en los dos serializers) — queda
  pendiente para la Fase 1 si se requiere mas detalle, o para la Fase 3 si se decide construir el
  `HomeRenderer` unico (necesitaria consumir DIRECTAMENTE el shape de `home-feed`, no el de
  `dashboard/home-config`, para garantizar el "mismo JSON" que pide el brief).

**Que SI es razonable por diseno:** que el endpoint de lectura publica y el de escritura admin
sean distintos (uno cacheado/publico, otro autenticado/CRUD) no es en si mismo el problema — el
problema es que el FRONTEND no reutiliza el mismo componente de render con ninguno de los dos.

### Hallazgo 5 — Inconsistencias menores adicionales

- `HomeConfigView.vue` mezcla `<script setup>` (patron del resto del proyecto) con
  `defineComponent`+`h()` en el mismo archivo (ver Hallazgo 2) — unico caso conocido en el
  proyecto.
- El archivo tiene 1936 lineas — muy por encima de cualquier otro modulo admin documentado en
  `ai_skills/frontend/components/cards.md` (la mayoria de `List.vue`/`Form.vue` son 100-300
  lineas) — mezcla 7 secciones de configuracion (modulos, banners, cards, marca, navbar, cta,
  footer) + su propio sistema de preview + modales + logica de upload de media, todo en un solo
  archivo.
- No se detecto codigo completamente muerto dentro de este archivo especifico (a diferencia de
  `TrustSection.vue`/`TrustCard.vue`, ya eliminados en esta misma sesion por no usarse en
  ningun lado).

### Componentes/APIs involucrados (inventario para las fases siguientes)

**Landing real (motor 1):**
`HeroSection`, `HeroSlide`, `HeroBackground`, `HeroCTA`, `DividerWave`, `ModuleGrid`, `ModuleCard`,
`AnimatedCounter`, `FlashOffers`, `FlashOfferCard`, `CountdownTimer`, `FeaturedSection`,
`FeaturedCarousel`, `FeaturedCard`, `SectionRenderer`, `CardsGrid`, `CardsSlider`,
`TimelineSection`, `AccordionSection`, `useLayoutEngine`, `FooterCTA`, `CustomerNavbar`,
`CustomerFooter` (estos ultimos 2 fuera de `HomeView.vue`, viven en `CustomerLayout.vue`).

**Preview admin (motores 2 y 3, a eliminar/reemplazar en Fase 3):**
Markup inline `hcb-pv-*` (7 bloques) + `CardItemPreview` (render function inline) — todo dentro de
`HomeConfigView.vue`.

**Backend:**
`core.api.views.HomeFeedView` (publico), `dashboard.api.views.AdminHomeConfigViewSet` (+ viewsets
hermanos de banners/cards/module-config, no listados en detalle en esta pasada),
`core.services.selectors.HomeConfigSelector`/`HomeConfigCommands`.

### Conclusion Fase 1

El diagnostico del brief del usuario es correcto y esta confirmado con evidencia concreta: **no
existe un motor de render unico**. La vista previa del panel es una aproximacion esquematica
separada, no una instancia real de los componentes de la landing.

---

## FASE 2 — Auditoria UI: comparacion modulo por modulo

Metodo: lectura linea por linea de cada componente real (`components/ui/landing/*.vue`,
`components/customer/CustomerNavbar.vue`, `components/customer/CustomerFooter.vue`,
`renderers/SectionRenderer.vue`) contra su bloque `hcb-pv-*` equivalente en `HomeConfigView.vue`.
Ningun archivo fue modificado.

**Nota tecnologica previa (aplica a todos los modulos):** el proyecto usa exclusivamente
**Bootstrap 5.3.3 + CSS scoped por componente**. No hay Tailwind, SCSS, ni CSS Modules en ningun
punto del codebase (confirmado en `ai_skills/frontend/design_system/tokens.md`) — los items del
checklist del usuario referidos a esas tecnologias no aplican a este proyecto, se omiten del
detalle por modulo para no repetir "N/A" 7 veces.

### 1. Hero / Banner

| Propiedad | Landing real (`HeroSection`+`HeroSlide`+`HeroBackground`+`HeroCTA`) | Preview (`hcb-pv-banners`) | Coincide |
|---|---|---|---|
| Altura | `80vh` (min 480px), `85svh` en mobile | `80px` fijo (`.hcb-pv-banner__img`) | ❌ |
| Fondo | Video autoplay / imagen con Ken Burns (`scale 1→1.07`, 10s) / color solido + 2 orbs blur(90px) / gradiente + 3 orbs animados + mesh grid | `<img>` estatica o placeholder con icono | ❌ |
| Overlay | `linear-gradient(108deg, rgba(0,0,0,.72)→rgba(0,0,0,.08))` siempre presente | `linear-gradient(to top, rgba(0,0,0,.6), transparent)` solo en la franja inferior | ❌ (posicion y proposito distintos) |
| Carousel | Bootstrap `carousel-fade`, autoplay 5.5s, indicadores pill animados, controles con blur | Lista vertical estatica, sin carousel | ❌ |
| Texto | `clamp(2rem,5vw,4rem)` title, eyebrow con pill, text-shadow | `.title` en overlay, `.75rem`, sin eyebrow | ❌ |
| Botones (CTA) | 2 botones reales (`HeroCTA`): primary gradiente + arrow SVG animado, ghost con `backdrop-filter: blur(8px)`; hover con `translateY(-2px) scale(1.02)` | 1 `<span>` con texto "CTA" estatico, sin interaccion | ❌ |
| Panel glass flotante | `hsl-glass-panel`: `blur(16px) saturate(160%)`, animacion float 4s infinite, 4 feature-cards con hover | No existe | ❌ |
| Responsive | `@media(max-width:767px)` cambia a `height:auto` | Sin breakpoints propios (hereda el frame de preview desktop/tablet/mobile simulado con CSS de contenedor, no media queries reales del componente) | ❌ |

**Verdict:** 0% de coincidencia real — la preview no reutiliza ningun asset visual del Hero.

### 2. Navbar / Brand

| Propiedad | Landing real (`CustomerNavbar.vue`) | Preview (`hcb-pv-navbar`, `hcb-nav-preview`, `hcb-brand-preview`) | Coincide |
|---|---|---|---|
| Fondo | `rgba(255,255,255,.95)` + `blur(12px)` (glassmorphism CLARO) | `#0f172a` (fondo OSCURO solido, sin blur) | ❌ — hasta el tema de color base es opuesto |
| Logo/marca | Imagen + texto con gradiente `background-clip:text` `#2563eb→#1e3a8a` | Texto plano blanco, sin gradiente | ❌ |
| Links | Pills con hover `background:#eff6ff` + estado activo por ruta | `<span>` de texto plano, sin hover ni estado activo | ❌ |
| Elementos extra reales | Buscador con `input-group`, boton carrito con badge, dropdown de usuario con avatar | Ninguno de estos 3 existe en el preview | ❌ |
| Altura | `70px` fijo | Sin altura fija definida (`padding:.625rem 1rem`) | ❌ |

**Verdict:** 0% — la preview muestra un navbar oscuro simplificado; el real es claro con
glassmorphism. Ni siquiera el esquema de color coincide.

### 3. Cards (Home Cards / Card Groups)

| Propiedad | Landing real (`SectionRenderer`+`CardsGrid`/`CardsSlider`/`TimelineSection`/`AccordionSection`) | Preview (`hcb-pv-cards` + `CardItemPreview`) | Coincide |
|---|---|---|---|
| Layouts soportados | 4 (`grid`, `slider`, `timeline`, `accordion`) segun `group.layout_type`, via `useLayoutEngine()` | 1 solo (grid fijo `repeat(2,1fr)`) — no respeta `layout_type` | ❌ |
| Columnas | `group.columns` configurable | Fijo en 2, ignora el valor configurado | ❌ |
| Cantidad mostrada | Todas las cards activas del grupo | Trunca a 4 (`group.slice(0, 4)`) | ❌ (parcial, sesgo de "vista previa breve") |
| Estilo de card individual | Depende del layout real (`CardsGrid.vue` etc., no auditado a nivel de propiedad en esta pasada) | `CardItemPreview` (h() inline): icono+color, titulo, subtitulo opcional, badge "Destacado"; fondo especial si `card_type` es `gradient`/`dark` | Parcial — replica la LOGICA de `card_type` pero con su propio CSS, no el componente real |
| Header de seccion | `SectionRenderer` muestra eyebrow/title/desc del grupo (`.sr-header`) | Solo un `<div>` con el nombre del grupo, sin eyebrow/desc | ❌ |

**Verdict:** ~10-15% — es el modulo con MAS intento de paridad (la logica de `card_type` si se
replico a mano), pero sigue siendo una reimplementacion separada que no refleja los 4 layouts
reales.

### 4. CTA Final

| Propiedad | Landing real (`FooterCTA.vue`) | Preview (`hcb-pv-cta`) | Coincide |
|---|---|---|---|
| Background gradiente | `linear-gradient(135deg, #0d1526 0%, #1e3a8a 50%, #1d4ed8 100%)` | `linear-gradient(135deg, #0d1526 0%, #1e3a8a 55%, #1d4ed8 100%)` | **Casi** — mismos colores, **el stop intermedio ya diverge (50% vs 55%)** |
| Gradiente de texto destacado | `linear-gradient(135deg, #60a5fa, #a78bfa)` en `<em>` | Identico: `linear-gradient(135deg, #60a5fa, #a78bfa)` en `.hcb-pv-cta__em` | ✅ (unico caso de coincidencia exacta en toda la auditoria) |
| Orbs decorativos | 2 orbs `blur(80px)` con `radial-gradient`, posicionados absolutos | No existen | ❌ |
| Animacion de entrada | `IntersectionObserver` + `opacity`/`translateY(28px)→0` con `cubic-bezier(0.16,1,0.3,1)` 0.7s | Sin animacion (siempre visible) | ❌ |
| Botones | 2 botones reales con hover `translateY(-2px) scale(1.02)` + SVG arrow animado | 2 `<span>` estaticos sin interaccion | ❌ |
| Tipografia titulo | `clamp(2rem,4.5vw,3.5rem)` | `.8rem` fijo | ❌ |

**Verdict:** ~20% — es el modulo con la coincidencia de color MAS alta (alguien copio los valores
a mano), pero **ya demuestra el problema central del brief**: sin un renderer compartido, hasta un
valor copiado a mano diverge con el tiempo (55% vs 50%) y nadie lo detecta.

### 5. Footer

| Propiedad | Landing real (`CustomerFooter.vue`, no leido en detalle esta pasada — pendiente si se requiere mas profundidad) | Preview (`hcb-pv-footer`) | Coincide |
|---|---|---|---|
| Estructura | Grupos de links + redes sociales + contacto (segun inventario previo en `ai_skills/frontend/components/cards.md`) | Contacto (telefono/email) + grid de 6 links max, sin redes sociales | Parcial (estructura similar, estilo no verificado) |

**Nota:** este modulo no se audito a nivel de propiedad CSS linea por linea en esta pasada (tiempo
de la Fase 2) — si se requiere el mismo nivel de detalle que los demas modulos, indicarlo
explicitamente antes de la Fase 3.

### 6. Marca (Brand — logo/nombre/tagline en el formulario de edicion)

| Propiedad | Uso real | Preview (`hcb-brand-preview`, dentro del formulario, no el panel lateral) | Coincide |
|---|---|---|---|
| Logo | `<img>` real si existe, o iniciales | Igual: `<img>` o placeholder — este es el preview MAS fiel de todos (esta en el formulario de edicion, no en el panel lateral) | Parcial ✅ |
| Nombre | Gradiente de texto en `CustomerNavbar` | Texto plano `#0f172a`, sin gradiente | ❌ |

## Resumen cuantitativo Fase 2

| Modulo | Coincidencia estimada | Severidad |
|---|---|---|
| Hero/Banner | ~0% | Critica |
| Navbar/Brand (panel lateral) | ~0% | Critica |
| Cards | ~10-15% | Alta |
| CTA | ~20% | Alta (con evidencia de drift real) |
| Footer | No evaluado a fondo | — |
| Marca (form de edicion) | ~40% (el mas fiel) | Media |

**Conclusion Fase 2:** confirma cuantitativamente el diagnostico de la Fase 1. El modulo con mejor
intento de paridad (CTA) ya presenta una divergencia real medible (50% vs 55% en el gradient stop)
pese a que claramente alguien copio los valores a mano — es evidencia directa de que sin un
`<HomeRenderer/>` compartido, la sincronizacion manual falla con el tiempo, incluso cuando hay
buena intencion.

---

## FASE 3 — Render Engine unico (`<HomeRenderer/>`) — implementada y verificada

El usuario autorizo la Fase 3. Se construyo `<HomeRenderer/>` y se rewireo tanto la Landing como
la Vista Previa del panel admin para consumirlo. **Codigo modificado — ya no es solo auditoria.**

### Arquitectura implementada

```
src/renderers/HomeRenderer.vue   (NUEVO)
  ├─ Hero:      HeroSection + DividerWave
  ├─ Modules:   ModuleGrid + AnimatedCounter (stats)
  ├─ Flash:     FlashOffers
  ├─ Featured:  FeaturedSection x3 (product/rental/service)
  ├─ Cards:     SectionRenderer (igual que antes, sin cambios)
  └─ CTA:       FooterCTA

  Prop `sections: string[] | null` -- filtra que bloques renderizar.
  null (default) = todos -- usado por la Landing.
  ['hero'] / ['modules'] / ['cards'] / ['cta'] -- usado por la Vista Previa,
  una seccion a la vez, igual que el builder ya mostraba antes.
```

- **`views/customer/HomeView.vue`** (Landing, ruta `/`): ahora es un wrapper delgado — solo hace
  `fetch(core/home-feed/)` y pasa los datos a `<HomeRenderer :loading :banners :modules ... />`
  sin `sections` (renderiza todo). Se elimino el fetch muerto a `core/site-config/` (su resultado,
  `brand`, nunca se usaba en el template original).
- **`modules/core/HomeConfigView.vue`** (Vista Previa, `/panel/home-config`): el `<aside
  class="hcb-preview-panel">` ya NO tiene markup `hcb-pv-*` propio. Ahora renderiza:
  - `<HomeRenderer :sections="[sectionRendererKey]" ...>` para `banners→hero`, `modules→modules`,
    `cards→cards`, `cta→cta` — alimentado con el estado **en memoria** de los formularios
    (`banners`, `modulesOrdered`, `cards`, `ctaForm`), no con una llamada a la API. Esto es lo que
    permite ver el cambio "mientras se escribe", antes de guardar.
  - `<CustomerNavbar standalone :brand-override :nav-links-override>` para `brand`/`navbar`.
  - `<CustomerFooter :contact-override :nav-groups-override :social-links-override>` para
    `footer`.
- **`components/customer/CustomerNavbar.vue`** y **`CustomerFooter.vue`**: se agregaron props
  `*Override` **opcionales** (`brandOverride`/`navLinksOverride`;
  `contactOverride`/`socialLinksOverride`/`navGroupsOverride`). Cuando se pasan, reemplazan el
  store/fetch interno. Cuando NO se pasan (uso real en `CustomerLayout.vue`), el comportamiento es
  **identico al anterior** (verificado, ver seccion de pruebas). `CustomerNavbar` tambien gano un
  prop `standalone` (usa `position:relative` en vez de `fixed-top` — necesario para embeberlo en
  el frame acotado de la Vista Previa sin que se salga y tape la pantalla).
- **`CardItemPreview`** (el componente `h()` inline, Hallazgo 2 de la Fase 1) **fue eliminado**.
  El modal de edicion de tarjetas ahora usa `<CardItem :card="cardPreviewData" :visible="true"
  />` — el componente REAL usado por `CardsGrid.vue` en la landing. Como bonus, esto corrige un
  bug de cobertura: `CardItemPreview` solo soportaba 3 variantes de `card_type`
  (`vertical`/`gradient`/`dark`); `CardItem.vue` real soporta 9
  (`image_bg`/`horizontal`/`compact`/`glass`/`dark`/`gradient`/`premium`/`vertical` + default) —
  la vista previa anterior mostraba mal 6 de los 9 tipos de tarjeta posibles.
- **~150 lineas de CSS `hcb-pv-*`/`hcb-cip*`/`hcb-nav-preview*` eliminadas** de
  `HomeConfigView.vue` (confirmado con un script que verifico que las 44 clases ya no se
  referenciaban en ningun lado del template antes de borrarlas).

### Fuera de alcance en esta Fase 3 (decision explicita, no descuido)

- **`hcb-brand-preview`** (mini-preview de logo+nombre dentro del FORM de Marca) y
  **`hcb-banner-live-preview`** (preview de imagen/video dentro del modal de Banner) **no se
  tocaron** — son widgets pequeños que muestran directamente el archivo subido (no reimplementan
  un componente de diseño completo como si lo hacian los `hcb-pv-*` eliminados). Convertirlos
  tambien a componentes reales es posible pero se considero de menor prioridad frente al volumen
  ya cubierto en esta fase.
- Los formularios de edicion en si (listas de modulos/banners/tarjetas en el panel `<main
  class="hcb-editor">`) siguen usando su propio estilo de tarjetas admin (`hcb-module-card`,
  `hcb-banner-row`, `hcb-card-thumb`) — esto es correcto y esperado: son controles de
  administracion (editar/eliminar/reordenar), no una vista previa del sitio publico, no aplica la
  regla de "un solo renderer".

### Verificacion real (no solo "deberia funcionar")

- `npx vite build --mode production`: limpio, sin errores, en cada paso intermedio.
- `npm test` (Vitest): 10/10 tests siguen pasando.
- `npx playwright test visual-regression`: 1/1 (pantalla de login, no afectada).
- **Landing publica (`/`) con datos reales**, verificada con Playwright conectado al backend real
  vía la red de Docker (proxy `localhost:8000` → `django:8000`, unica forma de alcanzar el backend
  desde este contenedor — ver limitacion ya documentada en `testing/playwright.md`):
  - Screenshot completo (guardado durante la verificacion, no commiteado) muestra Hero con
    gradiente+panel de vidrio, seccion de modulos, CTA final con gradiente, y footer — todo
    renderizado correctamente por `HomeRenderer` con datos reales de `core/home-feed/`.
  - `.customer-navbar.fixed-top` presente (1) — confirma que el uso real (no-`standalone`) del
    navbar sigue exactamente igual que antes del cambio.
  - `.customer-footer`, `.hs-section` (hero real, no skeleton), `.fcta-root` (CTA) todos presentes.
  - **Cero errores de consola o de pagina** en ambas corridas (antes y despues de agregar las
    props `*Override`).
- **No se pudo verificar visualmente la Vista Previa del panel admin en el navegador** — requiere
  estar autenticado como admin, y la credencial de prueba disponible (`notas.txt`) da
  "Credenciales invalidas" contra este entorno (mismo problema ya documentado en
  `design_system/tokens.md` para el dark mode). La verificacion de esa mitad del cambio se hizo
  por: build limpio + revision manual linea por linea del mapeo de props (`previewCardGroups`,
  `previewBrand`, `previewNavGroups`, `previewSocialLinks`, `cardPreviewData`) contra los shapes
  reales que esos mismos componentes ya consumen en produccion (confirmados en la Fase 1/2:
  `ctaForm` coincide exactamente con el prop `config` de `FooterCTA`, `banners` coincide con lo
  que `HeroSlide`/`HeroBackground`/`HeroCTA` esperan, etc.).

---

## FASE 4 — Sincronizar efectos visuales

El usuario autorizo la Fase 4. Hallazgo principal: **la mayor parte de esta fase ya quedo resuelta
por construccion en la Fase 3** — al ser literalmente el mismo componente Vue (mismo
`<style scoped>`) el que renderiza Landing y Vista Previa, cualquier hover/animacion/gradiente/etc
definido en ese componente aplica identico en ambos lados sin trabajo adicional. Se verifico esto
efecto por efecto en vez de asumirlo, y se confirmo que items del checklist original simplemente
no existen en el proyecto (para no fabricar "sincronizacion" de algo que nunca se construyo).

### Efectos confirmados como sincronizados por construccion (Fase 3)

| Efecto | Donde vive | Estado |
|---|---|---|
| Hover (lift, scale) | `HeroCTA` (`translateY(-2px) scale(1.02)`), `CardItem` (`translateY(-4px)`), `ModuleCard`, `FeaturedCard` | ✅ Mismo CSS en ambos consumidores |
| Blur / Glassmorphism | `backdrop-filter` confirmado en 8 componentes activos (`HeroCTA`, `HeroSlide` panel flotante, `GlassCard`, `FooterCTA` boton ghost, `CustomerNavbar`, `CardItem`, etc.) | ✅ |
| Shadow / "glow" | Box-shadows con rgba de color (`HeroCTA`: `0 4px 20px rgba(37,99,235,.45)`) — implementado como valores directos, no como variable `--shadow-glow` nombrada (el plan original de 2026-06-28, `components/ui/landing/plan.md`, proponia esa variable pero la implementacion final uso valores inline; sin impacto en la sincronizacion, es el mismo valor en ambos lados de todas formas) | ✅ |
| Gradientes | `HeroBackground`, `FooterCTA`, `HeroCTA`, `CustomerFooter` (`footer-brand` text-gradient) | ✅ |
| Border-radius | Definido por componente (`9999px` pills, `14-24px` cards/paneles) | ✅ |
| Transiciones/timing/delay | `cubic-bezier(0.16,1,0.3,1)` consistente en Hero/CTA/Cards; stagger de reveal via `transition-delay` en `CardsGrid` (`i * 60ms`) | ✅ |
| Fade / Zoom / Reveal al aparecer | `IntersectionObserver` + clase `.visible`/`sectionVisible` — patron identico en 7 componentes (`AnimatedCounter`, `FeaturedCarousel`, `FlashOffers`, `FooterCTA`, `ModuleGrid`, `SectionHeader`, `CardsGrid`) | ✅ — el `root` del observer es el viewport del documento (no un contenedor con scroll propio, ninguno pasa `root:` explicito), por lo que se comporta igual dentro del frame acotado de la Vista Previa que en la pagina completa |
| Skeleton | `HeroSection` (`.hs-skeleton` shimmer), `HomeRenderer` (`.sk-card` shimmer para cards) | ✅ |
| Counter (count-up) | `AnimatedCounter.vue` (`requestAnimationFrame` + easeOutExpo) | ✅ |
| Carousel/autoplay | Bootstrap `carousel-fade`, `data-bs-ride="carousel"`, intervalo 5.5s en `HeroSection` | ✅ codigo compartido — **ver limitacion abajo** |
| Video/Imagen de fondo | `HeroBackground.vue` (video autoplay / imagen con Ken Burns) | ✅ |
| Overlay | Gradiente `rgba(0,0,0,...)` en `HeroBackground`, `CardItem` (`image_bg` variant) | ✅ |

### Efectos del checklist que NO existen en este proyecto (no es un gap de sincronizacion — nunca se construyeron)

Verificado por busqueda directa en todo `components/ui/landing/`, `components/ui/home/` y
`renderers/`:

- **Parallax**: cero referencias en el codebase.
- **Ripple** (efecto de click tipo Material): cero referencias.
- **Mouse effect** (seguimiento del cursor, `mousemove`): cero referencias.
- **Progress bar**: no existe como elemento de UI distinto (solo aparece la palabra en
  `AnimatedCounter.vue`, referida al progreso interno de la animacion de conteo, no un componente
  `<ProgressBar>`).

Esto coincide con `components/ui/landing/plan.md` (doc de arquitectura original, 2026-06-28): la
estrategia de animacion documentada ahi es explicitamente "CSS first, JS solo para trigger... Sin
librerias externas" — nunca se planeo parallax/ripple/mouse-follow, no es una omision de esta
auditoria.

### Limitacion no resuelta, honesta

**Autoplay del carousel de Hero dentro de la Vista Previa**: no se pudo verificar en navegador con
multiples banners reales (la BD de este entorno dev no tiene banners de sobra sembrados, y el
login de admin sigue bloqueado por la credencial invalida de `notas.txt` — mismo problema ya
documentado en Fase 3 y en `testing/playwright.md`). El codigo es identico al de la Landing
(mismo `HeroSection.vue`), asi que en teoria funciona igual, pero no se confirmo con Bootstrap JS
inicializando un carousel de 2+ slides dentro del frame acotado del panel admin.

### Conclusion Fase 4

No se requirieron cambios de codigo adicionales — la Fase 3 ya logro la sincronizacion de efectos
visuales al unificar el componente de render. Esta fase fue de **verificacion**, no de
implementacion: se confirmo item por item que el checklist del usuario esta cubierto (o
honestamente no aplica).

---

## FASE 5 — Responsive

El usuario autorizo la Fase 5. Se hicieron dos cosas: (1) verificacion real en navegador de la
Landing publica en los 8 breakpoints pedidos, (2) analisis de un limite tecnico real en el
mecanismo de "simular dispositivo" del panel admin, que **no se resolvio** (requiere una decision
del usuario sobre como abordarlo, ver abajo).

### Verificacion real — Landing publica (`/`), 8 breakpoints

Playwright con viewport real (no simulado) en cada ancho, conectado al backend real via red
Docker, contra `home-feed` real:

| Ancho | Overflow horizontal | Navbar visible | Hero visible | Errores de consola |
|---|---|---|---|---|
| 320px | No | Si | Si | 0 |
| 375px | No | Si | Si | 0 |
| 414px | No | Si | Si | 0 |
| 768px | No | Si | Si | 0 |
| 1024px | No | Si | Si | 0 |
| 1280px | No | Si | Si | 0 |
| 1440px | No | Si | Si | 0 |
| 1920px | No | Si | Si | 0 |

Screenshot a 375px (no commiteado, solo verificacion) confirma visualmente: navbar colapsa a
hamburguesa, Hero apila texto+botones a ancho completo, footer stackea sus columnas
correctamente. **Cero overflow horizontal en los 8 breakpoints** — la Landing real es responsive
de forma correcta y esto aplica igual a cualquier consumidor de `HomeRenderer` (por la misma razon
de la Fase 4: mismo componente, mismo CSS).

### Hallazgo tecnico real — el "simulador de dispositivo" del panel admin tiene un limite de CSS, no de codigo

El panel `/panel/home-config` ya tenia (antes de esta auditoria, sin cambios de la Fase 3) botones
Desktop/Tablet/Mobile que cambian `.hcb-preview-frame--tablet { max-width: 768px }` /
`.hcb-preview-frame--mobile { max-width: 375px }` — es decir, **encogen el contenedor**, no el
viewport real del navegador.

**El problema:** las media queries CSS (`@media (max-width: 767px) { ... }`, usadas en `HeroSection`,
`HeroSlide`, `ModuleGrid`, etc.) evalúan el ancho de la **ventana del navegador**, no el ancho del
`<div>` que las contiene. Si un admin abre el panel en un monitor de 1920px y selecciona "Mobile"
en el selector de dispositivo, el contenedor visualmente se angosta a 375px, pero el CSS interno
de `HeroSection`/`ModuleGrid`/etc. sigue evaluando "el navegador mide 1920px" — por lo tanto
**NO** aplica las reglas mobile (`@media (max-width: 767px)`), y el contenido se ve comprimido con
el layout de escritorio dentro de una caja angosta, no con el layout mobile real.

Esto es una limitacion fundamental de CSS (`@media` vs. ancho de contenedor), **no un bug
introducido por esta auditoria** — ya existia identicamente en la implementacion `hcb-pv-*`
anterior (que tampoco simulaba breakpoints reales, solo mostraba una maqueta fija sin media
queries en absoluto). Con `HomeRenderer` real ahora sí hay media queries de verdad detras del
selector de dispositivo, lo que hace el problema visible por primera vez (antes no importaba,
la maqueta no tenia layout responsive que romper).

### Opciones para resolverlo (requiere decision del usuario, no se implemento ninguna)

1. **`<iframe>` con ancho real** — la unica solucion 100% correcta: montar la vista previa dentro
   de un `<iframe>` cuyo `width` sea 375/768/1920px segun el dispositivo elegido. Un iframe es un
   viewport de navegador real independiente — las media queries evaluarian correctamente. Costo:
   requiere renderizar `HomeRenderer` dentro del iframe (via `srcdoc` + comunicacion postMessage
   para pasarle las props reactivas, o montando una instancia Vue separada dentro del iframe) —
   es una pieza de infraestructura nueva, no trivial.
2. **Migrar los `@media` de los componentes de landing a `@container` (CSS Container Queries)** —
   tecnicamente correcto y sin iframe, pero significa reescribir las media queries en ~10
   componentes reales (`HeroSection`, `HeroSlide`, `ModuleGrid`, `CardsGrid`,
   `FeaturedCarousel`, etc.), verificando que el comportamiento en la Landing real (que si usa el
   viewport completo) no cambie. Riesgo medio-alto de regresion visual en produccion si no se
   prueba a fondo cada breakpoint.
3. **Dejarlo documentado como limitacion conocida** — el selector Desktop/Tablet/Mobile sirve como
   referencia aproximada de ancho (util para ver como se ve el contenido "apretado"), pero **no**
   reemplaza probar la Landing real en un dispositivo/viewport real. Cero riesgo, cero esfuerzo
   adicional, pero no cumple 100% el criterio de aceptacion "responsive en todos los breakpoints
   Vista Previa = Landing".

**Decision del usuario: Opcion 3 — documentar como limitacion conocida.** No se implementa
iframe ni Container Queries. El selector Desktop/Tablet/Mobile del panel sigue siendo util como
referencia aproximada de ancho, pero **no reemplaza** probar la Landing real (`/`) en un
viewport real para validar responsive pixel-perfect. Documentado en
[../design_system/tokens.md](../design_system/tokens.md) (seccion de dark mode/limitaciones) —
ver actualizacion abajo.

**Nota para consumidores futuros de este documento:** si mas adelante se decide invertir en la
Opcion 1 o 2, este es el punto exacto donde retomar — el resto de la arquitectura (`HomeRenderer`,
props `sections`, `CustomerNavbar`/`CustomerFooter` con `*Override`) no necesita cambios para
soportar cualquiera de las dos, son ortogonales al render engine unico ya logrado en la Fase 3.

---

## FASE 6 — Optimizacion

El usuario autorizo la Fase 6. Alcance: lo que emergio de esta auditoria especifica (Home Config
+ Landing), **no** un barrido de codigo muerto de los 287 archivos del frontend completo — eso
seria una auditoria propia, mas grande, fuera de lo que motivo este proceso de 7 fases.

### Componentes muertos eliminados (verificados con 0 referencias antes de borrar)

```
components/ui/landing/HeroCarousel.vue        (reemplazado por HeroSection.vue)
components/ui/landing/ModuleCardsGrid.vue     (reemplazado por ModuleGrid.vue)
components/ui/landing/FlashOffersSection.vue  (reemplazado por FlashOffers.vue)
components/ui/landing/FeaturedItemCard.vue    (reemplazado por FeaturedCard.vue)
components/ui/landing/InfoCardsGrid.vue       (reemplazado por SectionRenderer.vue)
components/customer/renting/EquipmentAvailability.vue (superado por AvailabilityPill.vue)
```

Estos ya estaban documentados como "obsoletos, no importar" desde antes de esta auditoria (ver
[[project_landing_premium]] y [[project_renting_availability_engine_phase2]] en memoria) — la Fase
6 los saco definitivamente del disco en vez de dejarlos como referencia muerta. Sumados a
`TrustSection.vue`/`TrustCard.vue` (eliminados el mismo dia, antes de iniciar este proceso de 7
fases), son **8 componentes muertos eliminados en total** durante la sesion de hoy.

### Props / imports / watchers — sin hallazgos nuevos

Revision especifica de los archivos creados/modificados en la Fase 3
(`HomeRenderer.vue`, `HomeConfigView.vue`, `CustomerNavbar.vue`, `CustomerFooter.vue`):

- Sin props sin usar, sin imports huerfanos (`defineComponent`/`h` ya se habian quitado en la
  Fase 3 al borrar `CardItemPreview`; verificado que `previewDevice`, `displayTypeLabel`,
  `bannerFileInput`/`bannerIsDragging` siguen todos en uso real en el editor del panel, no en la
  vista previa eliminada).
- Sin watchers nuevos agregados por esta auditoria mas alla de los `computed()` (que no requieren
  cleanup — se recalculan solos, Vue los descarta automaticamente al desmontar el componente).
- Los `IntersectionObserver` usados por `FooterCTA`/`ModuleGrid`/`CardsGrid`/etc. (Fase 4) ya
  seguian el patron correcto de `obs.disconnect()` al primer `isIntersecting` — sin memory leak,
  sin cambios necesarios.
- Sin listeners globales (`window.addEventListener` sin cleanup) en ninguno de los archivos
  tocados.

### No evaluado en esta fase (fuera de alcance declarado)

Un barrido de "props innecesarias/imports muertos/duplicaciones" en el resto del frontend
(`modules/`, `views/`, el resto de `components/`) — son ~280 archivos no relacionados con este
flujo especifico de Home Config/Landing. Si se quiere ese barrido, es una auditoria nueva, no
parte de este proceso de 7 fases.

### Verificacion

`npx vite build --mode production` limpio, `npm test` (10/10), `npx playwright test
visual-regression` (1/1) — todo despues de los 6 borrados.

---

## FASE 7 — QA Final

El usuario autorizo la Fase 7. Metodo: metricas reales medidas con Playwright (Performance API
nativa del navegador, sin libreria de Lighthouse — no estaba instalada y agregarla para una
medicion puntual no se justificaba) contra la Landing publica real, con el backend real conectado
via la red de Docker (mismo mecanismo ya usado en Fases 3 y 5).

**Nota de rigor sobre el propio proceso de medicion:** la primera corrida de estas metricas dio
**3 fallos de red (HTTP 400)** en `core/home-feed/`, `core/footer/`, `core/site-config/`. Antes de
reportarlos como hallazgo, se investigo la causa: era un defecto del script de verificacion (el
proxy de Playwright no fijaba el header `Host` de forma confiable en todas las corridas, y
`ALLOWED_HOSTS` de Django es `['localhost', '127.0.0.1']` — cualquier otro `Host` da
`DisallowedHost` → HTTP 400). Se corrigio el proxy de verificacion (forzar `Host: localhost:8000`
explicitamente) y se repitio la medicion. **Los 3 fallos NO eran un bug de la app** — eran un
falso positivo del propio arnes de prueba. Se documenta este proceso para que quede claro que las
metricas de abajo son confiables, no la primera lectura descartada.

### Metricas reales — Landing publica (`/`), viewport 1280×900, backend real

| Metrica | Valor medido | Umbral "bueno" (Web Vitals) | Estado |
|---|---|---|---|
| TTFB | 16-40ms | < 800ms | ✅ (entorno dev local, no es representativo de produccion real) |
| FCP (First Contentful Paint) | 512-588ms | < 1800ms | ✅ |
| LCP (Largest Contentful Paint) | 1212-1276ms | < 2500ms | ✅ |
| CLS (Cumulative Layout Shift) | 0.0053-0.0057 | < 0.1 | ✅ |
| DOMContentLoaded | 599-705ms | — | ✅ |
| Errores de consola | 0 | 0 | ✅ |
| Fallos de red (4xx/5xx) | 0 (tras corregir el arnes de prueba) | 0 | ✅ |

**FID/INP no medidos** — requieren interaccion real del usuario (click/tap) para calcularse; una
corrida automatizada sin interaccion no genera estos eventos. No se simulo una interaccion
artificial para no reportar un numero sin significado real.

**Limitacion del entorno:** estas metricas se midieron en el contenedor Docker de desarrollo
(`ecommerce_sintel_frontend`, servidor Vite sin build de produccion, backend proxeado via red
interna) — no son representativas de latencia de red real de un usuario final ni del bundle de
produccion optimizado. Utiles para detectar regresiones/errores, no como benchmark de produccion.

### SEO — hallazgos reales (pre-existentes, fuera del alcance de esta auditoria de Home Config)

| Item | Hallazgo | Alcance |
|---|---|---|
| `<title>` | "Sintel \| E-Commerce Ecosystem" — presente | OK |
| `<meta name="description">` | **Ausente.** No hay ninguna meta description en `index.html`, y no existe ninguna libreria de gestion de meta tags (`vue-meta`/`unhead`/`useHead`) en el proyecto — aplica a TODA la SPA, no solo Home | Fuera de alcance de este proceso de 7 fases (es una iniciativa de SEO de toda la app, no del render de Home especificamente) |
| `<h1>` — cantidad en pagina | **4 elementos `<h1>`**, no 1 | Hallazgo real, pre-existente, **no introducido por esta auditoria** |

**Detalle del hallazgo de `<h1>` multiple:** `HeroSlide.vue` usa `<h1 class="hsl-title">` para el
titulo de cada slide del banner. El carousel de Bootstrap (`HeroSection.vue`) mantiene TODOS los
slides en el DOM simultaneamente (oculta los inactivos con CSS, no los desmonta), asi que si hay N
banners activos, hay N etiquetas `<h1>` en la pagina a la vez — semanticamente incorrecto (SEO y
lectores de pantalla esperan un unico `<h1>` por pagina). Esto es identico en Landing y en
cualquier renderizado del Hero via `HomeRenderer` (incluida la Vista Previa) — **no es una
diferencia entre Dashboard y Landing**, es un defecto pre-existente del componente `HeroSlide.vue`
que esta fuera del problema especifico que motivo este proceso de 7 fases. **No se corrigio** —
mencionado para que quede registrado, no silenciado.

### Accesibilidad — spot-check real (no una auditoria WCAG completa)

| Item | Resultado |
|---|---|
| Imagenes sin `alt` | 0 de 5 imagenes en pagina |
| Botones sin nombre accesible (sin texto, `aria-label` ni `title`) | 0 |

Consistente con los fixes de accesibilidad aplicados antes en esta misma sesion (ver
`ux/accessibility.md`) — no se encontraron regresiones nuevas introducidas por el trabajo de
Home Config.

### Matriz final — Vista Previa vs Landing, por modulo

| Modulo | Vista Previa = Landing | Estado | Observaciones |
|---|---|---|---|
| Hero / Banners | ✅ (por construccion) | Verificado en codigo (Fase 3), **no visualmente en el panel** (auth bloqueada) | Mismo `HeroSection`/`HeroSlide`/`HeroBackground`/`HeroCTA`; Landing verificada en navegador con datos reales |
| Modulos | ✅ (por construccion) | Idem | Mismo `ModuleGrid` |
| Cards / Card Groups | ✅ (por construccion) | Idem | Mismo `SectionRenderer` + 4 layouts; corrige ademas el bug de cobertura de `CardItemPreview` (3/9 variantes → ahora 9/9 reales) |
| CTA Final | ✅ (por construccion) | Idem | Mismo `FooterCTA`; el drift real detectado en Fase 2 (gradient stop 50% vs 55%) queda imposible de repetir — ya no hay 2 copias del valor |
| Navbar / Marca | ✅ (por construccion) | Idem | Mismo `CustomerNavbar` con props `*Override` + `standalone` |
| Footer | ✅ (por construccion) | Idem | Mismo `CustomerFooter` con props `*Override` |
| Responsive (8 breakpoints) | ✅ en Landing real / ⚠️ el selector del panel no simula viewport real | Verificado empiricamente solo en Landing | Limitacion de CSS documentada y aceptada en Fase 5 (decision del usuario: no corregir) |
| Performance (LCP/CLS/FCP/TTFB) | — | Medido solo en Landing | Por construccion aplica igual, no medido directamente en el panel |
| Consola / Network | 0 errores en Landing | ✅ | No verificado en el panel (auth bloqueada) |
| SEO | N/A al panel (no indexable) | — | Hallazgos (meta description, `<h1>` x4) son pre-existentes y de toda la app, no de esta auditoria |

**Por que la columna "Vista Previa = Landing" dice "por construccion" y no "✅ verificado
visualmente" en la mayoria de filas:** a lo largo de las 7 fases nunca fue posible autenticarse
como admin en este entorno (la credencial de `notas.txt` da "Credenciales invalidas" contra
`ecommerce_sintel_django`) para tomar un screenshot real del panel `/panel/home-config` y
compararlo pixel a pixel con la Landing. La garantia de igualdad no viene de una comparacion visual
directa sino de la arquitectura: ambos consumidores importan **el mismo archivo `.vue`** — es
matematicamente imposible que difieran en estilo mientras compartan el componente (a diferencia del
estado previo a la Fase 3, donde eran dos implementaciones separadas que *si* podian divergir, y
de hecho ya habian divergido — ver el drift del 50%/55% en la Fase 2). Se recomienda, si se
requiere el ultimo tramo de confianza (verificacion visual real), resolver primero el acceso al
panel admin de este entorno (credencial valida o reset de contraseña) y repetir la captura.

---

## RESULTADO FINAL DEL PROCESO DE 7 FASES

### Criterios de aceptacion del brief original — estado real

| Criterio | Estado |
|---|---|
| Vista Previa y Landing comparten un unico motor de render | ✅ `HomeRenderer.vue` + `CustomerNavbar`/`CustomerFooter` con props `*Override` |
| 100% de los estilos configurados se reflejan automaticamente | ✅ por construccion (mismo componente); **excepcion documentada**: el selector Desktop/Tablet/Mobile del panel no simula viewport real (Fase 5, decision aceptada de no corregir) |
| No existe estilo/animacion/componente exclusivo de Vista Previa o Landing | ✅ — se eliminaron ~150 lineas de CSS `hcb-pv-*` + el componente `CardItemPreview` (`h()` inline); quedan sin tocar (decision explicita, no descuido) los mini-previews de logo (form Marca) e imagen/video (modal Banner), que no reimplementan diseño, solo muestran el archivo subido |
| Navbar/Hero/Banners/Cards/Marcas/CTA/Footer con coincidencia visual 100% | ✅ por construccion; sin verificacion visual directa del lado admin (auth bloqueada) |
| Responsive en todos los breakpoints definidos | ✅ en Landing (8/8 breakpoints, 0 overflow); ⚠️ simulador del panel con limitacion de CSS aceptada |
| Sin componentes/estilos/logica duplicados | ✅ — 8 componentes muertos eliminados en total durante la sesion, cero markup/CSS de preview duplicado restante |
| Informe final con evidencias por fase | ✅ este documento |
| Ninguna fase sin autorizacion explicita | ✅ — las 7 fases se pidieron y autorizaron una por una, sin excepcion |

### Resumen de cambios de codigo (Fases 3-6)

- **Nuevo:** `src/renderers/HomeRenderer.vue`
- **Modificados:** `views/customer/HomeView.vue` (wrapper delgado), `modules/core/HomeConfigView.vue`
  (preview real, ~150 lineas de CSS muerta eliminadas, `CardItemPreview` eliminado),
  `components/customer/CustomerNavbar.vue` y `CustomerFooter.vue` (props `*Override` opcionales,
  retrocompatibles)
- **Eliminados:** `TrustSection.vue`, `TrustCard.vue`, `HeroCarousel.vue`, `ModuleCardsGrid.vue`,
  `FlashOffersSection.vue`, `FeaturedItemCard.vue`, `InfoCardsGrid.vue`,
  `EquipmentAvailability.vue` (8 componentes)
- **Documentacion actualizada:** `ai_skills/frontend/components/cards.md`,
  `ai_skills/frontend/architecture/routing.md`, `ai_skills/frontend/ux/responsive.md`,
  `ai_skills/frontend/editor/architecture_audit.md`, este documento

### Pendientes explicitos, no resueltos (decisiones informadas, no descuidos)

1. Simulador Desktop/Tablet/Mobile del panel no representa un viewport real (Fase 5, Opcion 3
   elegida por el usuario).
2. Mini-previews de logo (form Marca) e imagen/video (modal Banner) siguen sin usar componentes
   reales (Fase 3, fuera de alcance declarado).
3. `<h1>` multiple en el Hero cuando hay 2+ banners activos, y ausencia de `<meta
   name="description">` en toda la SPA (Fase 7) — pre-existentes, no relacionados con la
   duplicacion Dashboard/Landing que motivo este proceso.
4. Verificacion visual directa del panel admin en navegador nunca se pudo completar en este
   entorno (credencial de prueba invalida).

**Fin del proceso de 7 fases.**
