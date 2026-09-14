# WHITE_LABEL_FRONTEND_AUDIT.md
Fase 4, 5, 12, 13, 14, 16 — Auditoría del frontend (Vue 3 + Vite + Pinia)

Solo lectura. Alcance: `ecommerce_sintel/frontend/src`.

## Fase 5 — Router

Router único (`src/apps/admin/router.js`); árbol de cliente definido completo en `src/apps/admin/routes/customer.routes.js`.

| Ruta | Origen |
|---|---|
| `/`, `/nosotros`, `/contacto`, `/tienda`, `/alquiler`, `/servicios`, `/cotizar`, `/checkout`, `/contratistas`, `/mi-cuenta/*` (~35 rutas totales) | **Hardcoded**, sin gate de configuración |

No existe `meta.module`, `meta.feature` ni patrón de feature-flag alguno en las rutas (grep de `module.*enabled`, `is_enabled`, `feature_flag`, `meta.module` → cero resultados). No hay mecanismo para deshabilitar p. ej. `/alquiler` o `/servicios` para un negocio que no ofrezca renting o servicios técnicos — cada vertical (tienda, renting, servicios, cotizaciones, marketplace de contratistas) está permanentemente cableada en el router y, por extensión, en los menús de fallback de navbar/footer. Reusar este código para un negocio más angosto exige borrar/comentar entradas de ruta, no apagar un flag.

## Fase 4 — Layout shell (Navbar/Footer/AppShell)

`CustomerNavbar.vue` y `CustomerFooter.vue` (bajo `CustomerLayout.vue`, el único punto de render real según `frontend/CLAUDE.md`):

- **Navbar**: nombre/logo de marca desde `appConfigStore.brand` (`site_name`, `logo`); enlaces de nav desde `appConfigStore.navbarLinks`, obtenidos de `core/site-config/`. Si `navLinks` está vacío, cae a un bloque hardcoded de 5 enlaces fijos (Tienda/Alquiler/Servicios/Cotizar/Contratistas) — **config-driven con fallback hardcoded**.
- **Footer**: contacto/social desde `core/footer/` con fallback hardcoded en español (columnas Tienda/Mi cuenta/Empresa, `info@sintel.co`, `+57 300 000 0000`, "Colombia"). El copyright **no es dinámico en absoluto**: `&copy; {{ year }} Sintel Ecosystem. Todos los derechos reservados.` es un string de plantilla literal, siempre renderizado sin importar la configuración.
- Ambos componentes cargan por API en cada montaje (arquitectura razonablemente dinámica), debilitada por fallbacks hardcodeados de marca y la línea de copyright siempre-activa.

## Home page

`HomeView.vue` obtiene `core/home-feed/` y pasa todo a `HomeRenderer.vue`, que renderiza secciones puramente por props con un gate `showSection(key)`. Sin copy hardcoded de Sintel en el camino de render; el único texto estático es un mensaje de estado vacío genérico. Es la parte del frontend más cerca de ser `THEME_READY` en contenido.

## Fase 13 — Sistema de theming: **HARDCODED**

Existe una capa de tokens pequeña, `apps/admin/landing-design-system.css`, con ~25 variables CSS (`--landing-primary: #2563eb`, escala de espaciado/radio/sombra) compartida por Home/Navbar/Footer. Sin embargo estos tokens son **valores hex estáticos en build-time en un archivo CSS versionado**, no obtenidos del backend ni inyectados en runtime vía `document.documentElement.style.setProperty` (grep sin resultados de inyección de tema en runtime o campos `primary_color`/`brand_color` en la API). Escala del hardcoding: **~3100 literales hex** (`#rrggbb`/`#rgb`) vs. **~220 usos de `var(--...)`** en todo `.vue` — proporción ~14:1 a favor de colores hardcodeados, es decir la mayoría de componentes (tienda, servicios, renting, módulos admin, no solo el landing) hardcodean su propio hex en bloques `<style scoped>` en vez de referenciar los tokens compartidos. Cambiar la paleta de una marca nueva requeriría un find/replace global de hex en cientos de archivos, no un solo cambio de config.

## Fase 12 — Runtime config loading

`store/appConfig.js` (Pinia): `fetchConfig()` hace GET a `core/site-config/`, setea `brand` (`site_name`, `logo`, `tagline`, `uuid`) y `navbarLinks`, marca `loaded = true` (cache fetch-once, sin TTL/refetch). **Ante fallo de API, silencia el error y mantiene el estado default incorporado**: `{ site_name: 'Sintel', logo: null, tagline: '', uuid: null }` — fallback explícito "Sintel" horneado en el estado inicial del store y en su acción `reset()`. Cualquier caída de `core/site-config/` degrada toda la app a mostrar "Sintel" como nombre de marca.

## Fase 14 — Contenido: literales "Sintel" (~95 hits totales, categorías representativas)

- **PLATFORM_DEFAULT_FALLBACK** (solo se renderiza si la API falla/está vacía): `store/appConfig.js:6,26`, `composables/useSeoStructuredData.js:21,35,86,129` (JSON-LD Organization / OG site_name), `composables/useCommunication.js:19`, `components/ui/landing/HeroSlide.vue:14` ("Sintel Technology"), `views/customer/renting/RentalDetailView.vue:441` (`brand_name` fallback), `modules/core/home-builder/NavbarSection.vue:15`, `BrandSection.vue:70`, `HomeConfigView.vue:265` (defaults de formulario admin).
- **HARDCODED_COPY** (siempre se renderiza, no está tras config): `components/customer/CustomerFooter.vue:129` (línea de copyright), `components/auth/CustomerAuthLayout.vue:6`, `AdminAuthLayout.vue:6` (marca en pantalla de login), **`components/auth/kyc/legalDocs.js` (~30 hits — Términos/Privacidad/Garantía completos hardcodeados a "Sintel", incluyendo `razonSocial: 'Sintel Corp [PENDIENTE: razon social exacta...]'` sin resolver — el bloqueador individual más grande, ver [WHITE_LABEL_BUSINESS_RULE_CATALOG.md](WHITE_LABEL_BUSINESS_RULE_CATALOG.md))**, `ServiceTermsModal.vue`, `ServiceRequestWizard.vue:586`, `ServiceDetailContent.vue:80,499`, `KycVerificationView.vue`, `CustomerQuotesView.vue:52`, `OnboardingHub.vue:5,136`, `FloatingButton.vue:27` (comentario).
- **TEST_DATA**: ninguno encontrado.
- **Falsos positivos excluidos**: `SintelOffcanvas.vue` es un nombre de componente UI compartido genérico, no fuga de marca; `Sidebar.vue:5,11` ("Sintel Panel"/"Sintel UI") es chrome del **panel admin**, fuera del scope cliente pero igual bloqueador para blanquear el panel.

## Veredicto general: **PARTIALLY THEMEABLE, no listo para business-agnostic**

La intención arquitectónica es sólida (API site-config, API home-feed, nav/footer dinámicos con fallback), pero tres bloqueadores separan esto de un codebase white-label real:

1. **Documentos legales hardcodeados** nombrando "Sintel" como la entidad contratante (`legalDocs.js`, ~30 hits) — es contenido legal real (Términos, Privacidad, Garantía, Devoluciones), no solo branding; requiere reemplazo completo por despliegue.
2. **Theming ~93% hardcoded en hex** (3100 vs 220 `var()`), sin mecanismo para empujar la paleta de un tenant desde el backend.
3. **Cobertura de verticales todo-o-nada**: renting, servicios técnicos, cotizaciones y marketplace de contratistas están permanentemente compilados en el router y los fallbacks de nav, sin flag de activar/desactivar.

Secundario pero real: el fallback silencioso a `"Sintel"` en el store `appConfig` ante fallo de API, y el string de copyright del footer siempre renderizado, significan que incluso un backend correctamente configurado puede mostrar (momentánea o permanentemente) el nombre de marca anterior durante caídas o si un campo queda sin definir.
