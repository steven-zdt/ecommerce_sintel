# WHITE_LABEL_ARCHITECTURE_TARGET.md
Fase 25-29 — Arquitectura objetivo (diseño conceptual, nada implementado)

## Fase 25 — Visión

```
PLATFORM
    │
    ▼
BUSINESS PROFILE
    │
    ├── Identity        → organization.Company + Branding (EXISTE, falta UI panel)
    ├── Organization     → organization app completa (EXISTE)
    ├── Theme            → NUEVO: ThemeConfig + CSS runtime tokens
    ├── Modules          → NUEVO: Module Registry (extiende core.HomeModuleConfig)
    ├── Features         → NUEVO: capa fina sobre Module Registry
    ├── Navigation       → core.NavbarLink + FooterGroup/Link (EXISTE)
    ├── Content          → core Home*/AboutUs*/BrandSlider* + NUEVO modelo de contenido legal
    ├── SEO              → seo app + organization.SeoSettings (EXISTE)
    ├── Legal            → organization.LegalEntityInfo (metadata, EXISTE) + NUEVO contenido T&C/Privacidad
    └── Domains          → organization.DomainSettings (EXISTE, sin conectar a infra)
            │
            ▼
        BUSINESS RUNTIME
            │
        ┌───┼────┬────┬──────┐
        ▼   ▼    ▼    ▼      ▼
       SHOP SERVICES RENTING QUOTES SUPPORT   (todos EXISTEN, ya operan sobre datos de DB)
```

Lo que YA EXISTE (no reconstruir): Django+DRF, Vue 3+Vite+Pinia, dashboard BFF, Service Layer/Commands/Selectors, `organization` (identidad), `core` (contenido/config), Design System (estructura), Home Builder, Navbar/Footer configurables, SEO, About Us, Brand Slider, Shop/Services/Renting/Quotes/Orders/Payment/Support, AI Engine, Project Knowledge Graph, AI Editor.

Lo que debe EVOLUCIONAR (no reescribir): `organization` necesita UI de panel y defaults neutrales; `core` necesita limpieza de seeds y `HomeModuleConfig` necesita convertirse en un Module Registry real; frontend necesita reemplazar los ~95 puntos hardcoded por lectura de `appConfigStore` extendido.

Lo que debe CREARSE: modelo de contenido legal versionado, `ThemeConfig` + inyección runtime de CSS vars, Module Registry con flags enable/disable consumidos por guards de router, endpoint `runtime-config` consolidado (opcional, evaluar frente a mantener los endpoints actuales).

## Fase 26 — Business Profile (diseño conceptual)

No crear una app `business` nueva — **extender `organization`** (ver justificación en [WHITE_LABEL_DECISION_RECORD.md](WHITE_LABEL_DECISION_RECORD.md)).

- `BusinessIdentity` → ya es `organization.Company` + `Branding`. Cambio: quitar default `'Sintel'`, usar placeholder neutral vacío o `"Mi Negocio"` genérico solo en fixtures de desarrollo, nunca en migración de producción.
- `BusinessTheme` → NUEVO modelo en `core` o nueva app pequeña `theme`: `primary_color`, `secondary_color`, `font_family`, `radius_scale`, `shadow_scale` — expuesto en `site-config` y aplicado como CSS custom properties en el `<html>` root al cargar la app.
- `BusinessModuleConfig` → evolución de `core.HomeModuleConfig`: agregar campo `is_route_enabled` (o reutilizar `is_active`) que el router del frontend consulte antes de registrar cada rama de rutas.
- `BusinessFeatureConfig` → capa fina opcional sobre Module Registry, solo si en el futuro se necesitan sub-features dentro de un módulo (ej. "renting con o sin logística propia") — no crear hasta que un caso real lo pida (evitar sobre-ingeniería, ver `feedback` de estilo de trabajo del usuario).
- `BusinessNavigationConfig` → ya es `core.NavbarLink`/`FooterGroup`/`FooterLink`, reutilizable tal cual.
- `BusinessContentConfig` → ya es `core.Home*`/`AboutUs*`/`BrandSlider*`, más un **modelo nuevo** para contenido legal versionado (ver Fase 30).

## Fase 27 — Business Runtime Config (contrato conceptual, NO implementar todavía)

Endpoints actuales ya cubren gran parte de lo necesario: `site-config`, `home-feed`, `footer`, `about-us`, `enums`. Evaluación: **no urge consolidar en un único `GET /api/v1/core/runtime-config/`** — los endpoints actuales están cacheados, versionados por sección y ya consumidos correctamente por el frontend. Consolidar agregaría una migración de contrato sin beneficio claro hoy. Sí falta exponer ahí:
- `theme` (NUEVO, no existe en ningún endpoint hoy)
- `modules` con flag de activación (parcialmente en `home-feed`, falta el flag consumible por el router)
- `legal` (contenido T&C/Privacidad, no existe en ningún endpoint hoy)

Recomendación: agregar estos 3 campos a `site-config` (que ya es el punto de entrada que el frontend carga al inicio) en vez de crear un endpoint nuevo.

## Fase 28 — Theme Runtime (diseño)

> **ACTUALIZACIÓN (2026-08-14, F4 implementado y probado en vivo):** `organization.Branding` ahora tiene `primary_color`/`accent_color`, expuestos en `core/site-config/theme` e inyectados en runtime como `--landing-primary`/`--landing-accent` vía `appConfig.js`. Verificado en navegador: cambiar el valor en DB cambia la CSS custom property correctamente. **Pero, probado también en vivo:** en la home actual, **cero elementos renderizados consumen `var(--landing-primary)` para color** — el botón CTA principal usa su propia clase `.hcta-primary` con estilos propios, no el token compartido. El mecanismo (backend→API→runtime) queda listo y correcto; la migración real de componentes para que lo consuman (los ~3100 hex hardcoded documentados en el audit) sigue siendo trabajo de F7, no incluido aquí. No sobrestimar "F4 completo" como "cambiar un color ya cambia el sitio" — hoy no lo hace todavía.

`ThemeConfig` con: colors (primary/secondary/accent/surface/ink), typography (font_family, scale), spacing, radius, shadows, y un mapeo explícito a los ~25 CSS custom properties que ya existen en `landing-design-system.css`. El frontend, al cargar `appConfigStore.fetchConfig()`, aplicaría `document.documentElement.style.setProperty('--landing-primary', theme.primary_color)` etc. — no reemplaza el archivo CSS, lo sobreescribe en runtime. Componentes que ya usan `var(--landing-*)` (≈220 usos) se benefician inmediatamente sin tocarlos. Los ~3100 usos de hex hardcoded en otros componentes (tienda, servicios, renting, admin) requieren migración incremental módulo por módulo — no es bloqueante para el Business A (Sintel) funcionando, sí lo es para que un Business B tenga un look realmente distinto fuera del landing.

## Fase 29 — Module Registry (diseño)

`ModuleDefinition`: `slug`, `label`, `icon`, `route`, `enabled`, `dependencies` (lista de slugs), `permissions`, `features`. Regla: sin dependencias circulares (verificar en `clean()` del modelo, como ya hace `HomeModuleConfig.clean()` para module_key custom). Consumido por: (a) `core.HomeModuleConfig` para la home (ya existe), (b) NUEVO — guard de router en frontend que registra/oculta rutas de `/tienda`, `/servicios`, `/alquiler`, `/cotizar` según `enabled`. Implementación recomendada: extender `HomeModuleConfig` en vez de crear un modelo paralelo, ya que su estructura (`MODULE_META` + overrides custom) ya resuelve el 80% del problema — solo falta que el frontend lo consulte también para gating de rutas, no solo para la home.
