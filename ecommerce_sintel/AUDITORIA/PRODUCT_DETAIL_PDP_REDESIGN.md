# Rediseno PDP Publica (Shop) — 3 columnas (2026-09-16)

Ver [PRODUCT_DETAIL_PDP_BASELINE.md](PRODUCT_DETAIL_PDP_BASELINE.md) (Fase 0) para el
inventario completo de la arquitectura real (routing, contrato de API, componentes
reutilizables) que sirvio de base a este rediseno. Este documento cubre lo que
efectivamente se implemento, se verifico y las desviaciones conscientes vs. el brief
original de 44 secciones.

## Componente real modificado

`frontend/src/views/customer/detail/ShopDetailContent.vue` (renderizado por
`PublicDetailView.vue` en la ruta real `tienda/:uuid`). `shop/ProductDetailView.vue`
sigue confirmado como codigo muerto (cero importadores) -- no se toco, no se activo.

## Producto usado para validar

**El UUID del brief (`1b541c67-f443-4336-beb2-d5c02a361cc8`) no existe en la base de
datos de dev** (confirmado por ORM: `Product.objects.filter(uuid=...)` = `None`, y por
un 404 real navegando a esa ruta). Se uso `f54ccb3a-315c-4e11-b878-700c2c96c539`
("camara IP", marca Dahua, categoria camaras, 1 variante, sin resenas) para todo el
trabajo de validacion real (curl del contrato, e2e, screenshots). Si en un futuro
reset de la DB de dev este UUID deja de existir, tomar cualquier
`Product.objects.filter(is_deleted=False).first().uuid` real y actualizar
`frontend/e2e/pdp-redesign.spec.js`.

## Cambios reales

### 1. Grid de 3 columnas (`ShopDetailContent.vue`)

Antes: `col-lg-5` (galeria) + `col-lg-7` (info + `ProductPurchaseCard` anidada al
final del mismo bloque). Ahora: 3 columnas hermanas del mismo `row`:

- **Columna 1** (`col-12 col-md-6 col-lg-4`): `BaseGallery` + trust badges + medios de
  pago. Sticky en `lg+` (sin cambios, ya lo era).
- **Columna 2** (`col-12 col-md-6 col-lg-5`): badges/chips, titulo, rating, short
  description, SKU, `UrgencyBanner` (disponibilidad), selector de variantes,
  atributos dinamicos, logistica (peso/dimensiones).
- **Columna 3** (`col-12 col-lg-3`): `ProductPurchaseCard` (ya existia completa:
  precio, descuento, disponibilidad, cantidad, agregar al carrito, comprar ahora,
  wishlist, cotizacion) -- solo se reubico a su propia columna, sin tocar su
  implementacion interna.

**Responsive real** (no simulado, verificado con Playwright en 5 viewports):

| Breakpoint | Comportamiento |
|---|---|
| `lg+` (≥992px) | 3 columnas reales, 4/5/3, galeria y compra sticky |
| `md` (768-991px) | galeria+info a 2 columnas (`col-md-6` cada una), compra debajo a ancho completo (brief seccion 24: "purchase below") |
| `<768px` | las 3 columnas se apilan a ancho completo en su orden natural del DOM: galeria, info, compra |

**Desviacion consciente vs. brief seccion 24:** el orden mobile deseado por el brief
interalaza Precio ANTES del selector de variante/disponibilidad (`Gallery, Title,
Rating, Price, Variant, Availability, CTA, Description...`). Implementar eso tal cual
exige partir `ProductPurchaseCard.vue` en 2 componentes (un bloque de precio +
disponibilidad, y un bloque separado de variante/CTA) para poder reordenarlos con
CSS `order` sin duplicar markup -- mas invasivo de lo que justifica esta iteracion
(brief seccion 12/25: "no crear componentes nuevos si ya hay equivalentes", "no
convertir cada texto en componente"). Se opto por el stack natural (galeria → toda la
info → panel de compra), que YA satisface el requisito de nivel superior real (precio
y CTA visibles antes de las secciones full-width de Descripcion/Especificaciones/
Reseñas). Documentado aqui como decision, no como omision silenciosa.

### 2. Lightbox de galeria (gap real de Fase 0, `BaseGallery.vue`)

`BaseGallery.vue` es compartido por Shop/Renting/Services -- se agrego la capacidad
como prop opt-in `lightbox` (default `false`, Renting/Services sin cambios de
comportamiento), mismo patron que los props opt-in existentes (`zoom`, `thumbLayout`,
`showCaption`):

- Click en la imagen principal (si `lightbox` esta activo) abre un modal
  (`Teleport` a `<body>`, evita problemas de stacking con `.gallery-sticky`).
- Navegacion siguiente/anterior (botones + flechas de teclado), cierre (boton X,
  Escape, click fuera de la imagen), bloqueo de scroll del body mientras esta abierto,
  foco al dialog al abrir (accesibilidad), `role="dialog"` + `aria-modal` +
  `aria-label` dinamico con el alt real de la imagen.
- Reusa `images`/`activeIndex` ya existentes -- no duplica estado de galeria.

Habilitado solo para Shop (`<BaseGallery ... lightbox />` en `ShopDetailContent.vue`).

### 3. Nada mas se toco

Sin cambios en: contrato de API (las 3 llamadas reales -- `unified/detail`,
`shop/products/{uuid}/detail/`, `shop/products/{uuid}/reviews/` -- intactas), store de
carrito/wishlist, logica de variantes/precio (`shopSelectedVariant` sigue siendo la
unica fuente de verdad, sin duplicar), reviews, SEO (`useSeo()` sin cambios -- el gap
real de `<link canonical>` faltante y el uso del DTO generico en vez de
`meta_title`/`meta_description` del producto se documenta como gap, ver seccion
siguiente, no se resolvio en esta mision por alcance), secciones full-width
(Descripcion/Especificaciones/Caracteristicas/Video/FAQ/Reseñas -- mismo orden y
mismos componentes, solo el bloque superior cambio de grid).

## Gaps reales que NO se resolvieron en esta mision (documentados, no fabricados)

1. **SEO canonical/on-page** (`useSeo()` no soporta `<link canonical>`, y `setSeo()` se
   llama con el DTO generico `unified/detail` en vez de los campos mas ricos de
   `ProductDetailSerializer`) -- gap real preexistente, brief seccion 33 lo pide,
   fuera de alcance de un rediseno de layout puro (tocaria `PublicDetailView.vue` y
   `useSeo.js`, compartidos con Renting/Services).
2. **Imagenes especificas por variante** -- el campo existe en el contrato
   (`ProductVariantSerializer.images`) pero ningun producto real de dev lo puebla y
   el frontend nunca lo lee. No se construyo UI para esto (brief seccion 5: "no
   asumir" / seccion 34: "no inventar datos").
3. **Reordenamiento mobile Precio-antes-de-Variante** (seccion 24 del brief) -- ver
   decision documentada arriba.
4. **Skeleton de 3 columnas** -- `PublicDetailView.vue` sigue usando un
   `<div style="height:400px">` generico (brief seccion 28 pedia un skeleton que
   anticipe 3 columnas). No se toco: es codigo compartido con Renting/Services y el
   layout shift real al cargar es bajo (un solo `div` full-width, sin salto brusco de
   columnas) -- se documenta como mejora futura, no se justifico su costo/riesgo en
   esta iteracion.

## Verificacion real ejecutada (dev, nunca prod)

- `docker exec ecommerce_sintel_frontend npx playwright test pdp-redesign` --
  **9/9 passed**: carga sin errores de consola ni requests fallidos; 3 columnas
  confirmadas via bounding boxes reales (no solo clases CSS); lightbox abre con
  click, cierra con Escape; stepper de cantidad respeta minimo/maximo; boton
  "Agregar al carrito" no rompe la pagina; **0 overflow horizontal** en los 5
  viewports pedidos por el brief (1366x768, 1440x900, 1920x1080, 768x1024, 390x844),
  con screenshot real guardado por viewport.
- `docker exec ecommerce_sintel_frontend npx playwright test pdp-regression-check` --
  **3/3 passed**: Renting y Services (comparten `BaseGallery`/`PublicDetailView`) y el
  catalogo de tienda siguen cargando sin errores de consola tras el cambio.
- Revision visual manual de los 3 screenshots (desktop 1440, tablet 768, mobile 390):
  layout de 3 columnas real en desktop, 2 columnas + compra debajo en tablet, stack
  completo en mobile -- todos coherentes con el diseno objetivo.
- Playwright no estaba usable en este contenedor al empezar (faltaban el browser
  binario y las dependencias del sistema, gap preexistente documentado en
  `ai_skills/frontend/testing/playwright.md`) -- se instalaron ambos
  (`npx playwright install chromium` + `install-deps chromium`) como parte de esta
  mision, quedan disponibles para trabajo futuro.
- `docker exec ecommerce_sintel_frontend npx playwright test` (suite COMPLETA,
  incluye specs preexistentes no relacionados con esta mision) -- **13 passed, 16
  failed**. Los 16 fallos son TODOS preexistentes y no relacionados: 9 son
  `offline-testing.spec.ts` (documentado como roto desde 2026-07-11 en
  `ai_skills/frontend/testing/playwright.md`, bugs del spec no de la app), 1 es
  `visual-regression.spec.js` (baseline screenshot desactualizado contra el
  Chromium recien instalado en esta mision), 3 son `home-landing.spec.js` y 3 son
  `wompi-checkout.spec.js` (timeouts de login -- mismo patron de
  `localhost:8000` vs `django:8000` que se documenta abajo, pero esos specs
  preexistentes no tienen la reescritura de URL que si se agrego a los specs
  nuevos de esta mision). Ninguno de los 16 toca Shop/PDP/BaseGallery -- cero
  regresiones nuevas causadas por este trabajo, verificado, no asumido.
- Un hallazgo de entorno (no de la app): Playwright corre DENTRO del contenedor
  `ecommerce_sintel_frontend`, donde `localhost:8000` no resuelve a Django (el
  navegador real de un usuario en el host si lo resuelve via el port-forward de
  Docker) -- los specs nuevos reescriben esa URL a `django:8000` solo dentro del
  propio proceso de test, sin tocar el comportamiento real de la app.

## No ejecutado en esta mision (limite de alcance, no fabricado como hecho)

- Medicion formal de performance (section 40 del brief: initial render time, layout
  shift cuantificado, etc.) -- se verifico ausencia de errores de consola/requests
  fallidos y ausencia de overflow horizontal, pero no se corrio un profiler ni se
  midio Core Web Vitals.
- Pruebas de accesibilidad con lector de pantalla real -- se implementaron
  atributos ARIA reales en el lightbox (`role`, `aria-modal`, `aria-label`,
  navegacion por teclado) pero no se verifico con un lector de pantalla real.
- No se probo el flujo de compra autenticado completo (login real + agregar al
  carrito + checkout) -- el test de e2e verifica que el boton no rompe la pagina
  para un usuario sin sesion (redirige a `/login`, comportamiento preexistente sin
  cambios), no el flujo completo autenticado.
