---
description: Checklist de auditoria arquitectonica (Fase 1 del editor) y registro de deuda tecnica conocida del frontend. Actualizar cuando se resuelva o descubra un gap.
metadata:
  domain: editor
  last_audited: "2026-07-11"
---

# Architecture Audit

## Checklist de auditoria (Fase 1)

Al revisar o extender una pantalla/modulo, verificar:

- [ ] **Consistencia**: sigue los patrones de [../architecture/vue_patterns.md](../architecture/vue_patterns.md)
      (`<script setup>`, `useApi()` default import, stores con prefijo `use`)
- [ ] **Duplicacion**: no reinventa un componente ya listado en [../components/cards.md](../components/cards.md)
- [ ] **Endpoints**: escrituras van a `dashboard/` salvo excepcion documentada (ver
      [../architecture/frontend_architect.md](../architecture/frontend_architect.md#5-convencion-de-endpoints--regla-critica))
- [ ] **CSS**: sin `font-family` inline, sin `style="color:X"` cuando hay clase Bootstrap
- [ ] **Accesibilidad**: ver gaps reales en [../ux/accessibility.md](../ux/accessibility.md) —
      no afirmar cumplimiento no verificado
- [ ] **Responsive**: `table-responsive` en tablas, breakpoints de [../ux/responsive.md](../ux/responsive.md)
- [ ] **Performance**: lazy loading de rutas, sin imports innecesarios de landing/ en el panel admin (o viceversa)
- [ ] **Seguridad**: sin `axios` directo (evita el interceptor de refresh JWT de `useApi()`), sin
      exponer tokens fuera de `localStorage` (`sintel_access`/`sintel_refresh`)

## Deuda tecnica conocida (no inventar que esta resuelta)

| Area | Estado | Detalle |
|---|---|---|
| ~~Testing unitario (Vitest)~~ | **Resuelto 2026-07-11** | Instalado + configurado en `vite.config.js`, primer test real en `useToast.test.js` (5 tests). Detalle: [../testing/vitest.md](../testing/vitest.md) |
| ~~Testing e2e (Playwright)~~ | **Resuelto 2026-07-11** (infra) | Instalado (`@playwright/test` + Chromium), `playwright.config.js`. Suite pre-existente (`offline-testing.spec.ts`, nunca antes ejecutada) corre pero 9/10 escenarios fallan por bugs reales del spec (falta login, orden de `page.evaluate` vs `page.goto`) — no arreglados, fuera de alcance. Detalle: [../testing/playwright.md](../testing/playwright.md) |
| ~~Regresion visual~~ | **Resuelto 2026-07-11** (1 caso) | `toHaveScreenshot()` de Playwright sobre `/login` (unica ruta publica sin dependencia de datos de API). Baseline commiteado. No es una suite exhaustiva. Detalle: [../testing/visual_regression.md](../testing/visual_regression.md) |
| ~~Accesibilidad WCAG 2.2~~ | **Parcial 2026-07-11** — NO es certificacion completa | Fix real de alto impacto en `SintelOffcanvas.vue` (dialog role + manejo de foco real, usado por casi todo CRUD admin) + `aria-label` en los 3 botones icon-only de `Navbar.vue`. Los ~15+ `List.vue` individuales y el portal customer NO se revisaron. Detalle: [../ux/accessibility.md](../ux/accessibility.md) |
| ~~Dark mode~~ | **Resuelto 2026-07-11** (parcial: solo AppShell/Navbar del panel admin) | `data-bs-theme` nativo de Bootstrap 5.3 + `useTheme.js`. Portal customer sin cubrir. No verificado visualmente en navegador (credencial de prueba invalida en este entorno). Detalle: [../design_system/tokens.md](../design_system/tokens.md#3-dark-mode--solo-panel-admin-2026-07-11) |
| ~~Offline / retry de red~~ | **Resuelto 2026-07-11** | `useApi.js` reintenta GET en error de red (max 2, backoff 500/1500ms); POST/PATCH/DELETE nunca se reintentan (riesgo de duplicar side-effects). Detalle: [../ux/loading_states.md](../ux/loading_states.md#7-offline--retry) |
| ~~Validacion declarativa (`vee-validate`/`yup`)~~ | **Resuelto 2026-07-11** | Documentado en [../components/forms.md](../components/forms.md#validacion-declarativa--vee-validate--yup). De paso se encontro y corrigio `useFormValidation.ts` (TypeScript real en produccion, violaba "sin TypeScript") — convertido a `.js` |
| ~~Exportacion / acciones masivas en tablas admin~~ | **Resuelto 2026-07-11** (parcial) | Patron documentado + primer ejemplo real en `BrandList.vue`: seleccion multi-fila, bulk-delete (`Promise.allSettled` sobre el endpoint individual existente), export CSV client-side. Limitacion: exportacion solo cubre la pagina cargada, no el dataset completo filtrado (necesitaria endpoint `export/` dedicado, no implementado). Detalle: [../components/datatable.md](../components/datatable.md#7-seleccion--acciones-masivas--exportacion-csv) |
| ~~Suspense / Error Boundaries Vue~~ | **Resuelto 2026-07-11** | `components/ui/ErrorBoundary.vue` (nuevo, `onErrorCaptured`) + `<Suspense>` envolviendo `<RouterView>` en `AppShell.vue` y `CustomerLayout.vue` — fallback de carga + fallback de error en las 2 raices de la SPA |
| ~~Indexacion RAG de `ai_skills/drf/`~~ | **Resuelto 2026-07-11** | Movido a `ecommerce_sintel/ai_skills/drf/`, indexado en `ai_engine/loaders.py` (seccion "5b"), `_infer_metadata` corregido para no confundirlo con specs de frontend. De paso se corrigio un ejemplo real erroneo en `DRF_PATTERNS.md` (`request.user.role` no existe). |

## Historial de hallazgos de sincronizacion

- **2026-07-11**: descubierta y resuelta la divergencia entre `ai_skills/frontend/` (raiz del
  repo, desconectado del RAG) y `ecommerce_sintel/ai_skills/frontend/` (ruta real indexada por
  `CODEBASE_PATH`). Ver detalle completo en [synchronization.md](synchronization.md).
- **2026-07-11**: auditoria enterprise_sync — eliminada la ruta huerfana `/inicio`
  (`LandingView.vue`, hardcodeada, fuera de `CustomerLayout`); creados paneles admin de
  Notifications y Payment-transactions (antes solo backend, sin UI); eliminado codigo muerto
  `TrustSection.vue`/`TrustCard.vue` (sin uso, superseded por `SectionRenderer.vue`). Detalle
  completo: [enterprise_sync_audit_2026_07_11.md](enterprise_sync_audit_2026_07_11.md).

## Como actualizar esta tabla

Cuando se resuelve un gap (ej. se instala Vitest y se escriben los primeros tests), actualizar:
1. El archivo de dominio correspondiente (`../testing/vitest.md`) para reflejar el estado real.
2. La fila de esta tabla (o eliminarla si ya no aplica).
3. `metadata.last_audited` de este archivo con la fecha del cambio.

No dejar esta tabla desactualizada — es la fuente que evita que el editor (o cualquier agente)
asuma que algo esta implementado cuando no lo esta.
