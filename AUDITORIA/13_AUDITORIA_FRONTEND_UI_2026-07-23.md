# 13 — Auditoría Frontend UI + Plan de Correcciones

**Fecha:** 2026-07-23
**Alcance:** `ecommerce_sintel/frontend/src` (SPA Vue 3 + Pinia + Vue Router)
**Objetivo:** eficiencia, eliminación de redundancias, escalabilidad y depuración de código muerto.
**Método:** análisis estático directo (grep/glob/lectura) de los 328 componentes Vue + 64 módulos JS
(~68.300 LOC). Cada hallazgo tiene evidencia concreta (archivo/conteo verificable).

> Reemplaza en la práctica a `AUDITORIA/07_FRONTEND.md` (2026-07-16, métricas ya desfasadas: 280
> componentes entonces → 328 hoy). El bug CRÍTICO **FE-C1** de ese documento (ruta
> `ordenes/renting` inalcanzable por sombra de `ordenes/:uuid`) **ya está corregido** en el router
> actual (`apps/admin/router.js:214-216`: `ordenes/renting` ahora precede a `ordenes/:uuid`).

---

## 0. Resumen ejecutivo

| Dimensión | Estado | Hallazgo principal |
|---|---|---|
| **Código muerto** | 🔴 Real y removible | 12 componentes huérfanos + 1 store huérfano + 24 archivos basura (22 scripts `.cjs`/`.mjs` + `plan.md` + `.backup`) |
| **Redundancia** | 🟠 Focalizada | 63 archivos con formateo de moneda inline (sin util); 61 archivos con extracción de error inline (existe `useErrorHandler`, solo 2 lo usan) |
| **Eficiencia** | 🟠 Media | Componentes monolíticos (HomeConfigView 2.629 LOC/250 decls); ~28 `onMounted` async con posibles `Promise.all` |
| **Escalabilidad** | 🟠 Media | Migración a stores Pinia a medias (40 módulos admin siguen con `useApi` directo); sidebar hardcodeado |
| **Disciplina existente** | 🟢 Buena | Solo 3 imports `axios` directos (auth, legítimo); badges/timelines son adaptadores finos sobre maquinaria compartida (`useEnums`/`StatusTimeline`); 2 TODOs; 0 `.bak` en `src` salvo 1 |

**Veredicto:** la base es más disciplinada de lo que sugiere el tamaño (la duplicación de
badges/timelines resultó ser wrappers de 9-64 LOC sobre componentes compartidos, **no** copias).
Los problemas reales y de mayor ROI son: (1) purga de código muerto — **ya ejecutada**, ver §5;
(2) dos utilidades transversales ausentes (moneda + errores) que 60+ archivos reimplementan; (3)
tres o cuatro god-components que conviene descomponer; (4) terminar la migración a stores.

---

## 1. Código muerto — 🔴 P0 (YA EJECUTADO, ver §5)

### 1.1 Componentes Vue huérfanos (0 referencias de import en todo el repo — verificado)

| Archivo | LOC |
|---|---|
| `components/customer/renting/EquipmentHero.vue` | — |
| `components/customer/renting/ProjectInformationCard.vue` | — |
| `components/customer/renting/RentalCustomerCard.vue` | — |
| `components/customer/renting/RentalScheduleCard.vue` | — |
| `components/customer/renting/RentalSummaryCard.vue` | — |
| `components/customer/ui/DateRangePicker.vue` | — |
| `components/ui/landing/GlassCard.vue` | — |
| `components/ui/landing/SectionHeader.vue` | — |
| `modules/orders/components/OrderDetail.vue` | (la ruta usa `modules/orders/views/OrderDetailView.vue`, no este) |
| `modules/quotes/AdditionalCostsView.vue` | — |
| `modules/renting/RentingDetail.vue` | — |
| `modules/technical_services/ServiceCategoryForm.vue` | — |

**Método de verificación:** por cada `*.vue`, grep de su basename como palabra completa (`\b…\b`)
en todo `src` + `e2e`, excluyéndose a sí mismo → 0 hits. Confirmado además que no hay registro
global de componentes (`app.component(...)`) en `main.js`. Las únicas "referencias" residuales de
`GlassCard`/`SectionHeader` estaban en `src/components/ui/landing/plan.md` (un doc de planeación,
no código — también basura, ver 1.4). Total ≈ 927 LOC.

### 1.2 Store Pinia huérfano

- `store/rentingAdmin/taxonomy.js` (`useRentingTaxonomyAdminStore`, ~42 LOC) — 0 usos. Fue
  segregado de `rentingAdmin.js` en "SPRINT 4" pero su responsabilidad (categorías/marcas/labor)
  la absorbió `store/rentingAdmin/catalog.js` (`useRentingCatalogAdminStore`), que es el que
  realmente consumen los 7 paneles de Renting. `taxonomy.js` quedó como duplicado muerto.

### 1.3 Scripts ad-hoc de depuración en la raíz (22 archivos, trackeados por git)

`debug_admin_login.cjs`, `debug_admin_login2.cjs`, `e2e_admin_panel.cjs`, `e2e_packages.cjs`,
`e2e_packages2.cjs`, `e2e_toggle.cjs`, `inspect_prod.cjs`, `ss_verify.mjs`, y 14
`verify_*.cjs`. Son scripts Playwright de verificación puntual de sesiones de desarrollo pasadas
(la suite E2E real y estructurada vive en `frontend/e2e/`). No los referencia ningún npm script
ni `playwright.config.js`. Ruido en la raíz del proyecto.

### 1.4 Archivos sueltos dentro de `src` / backups

- `src/components/ui/landing/plan.md` — doc de planeación dentro del árbol de componentes.
- `src/modules/technical_services/ServiceForm.vue.backup` — **backup de código**, exactamente lo
  que la regla 14 de `CLAUDE.md` desaconseja dejar en el repo.
- 10 `console.log`/`console.debug`/`console.warn` residuales en código de producción (no en tests)
  — limpieza menor, no bloqueante.

---

## 2. Redundancia — 🟠 P1

### 2.1 Formateo de moneda reimplementado en 63 archivos (sin utilidad compartida)

**Evidencia:** 122 llamadas inline a `Intl.NumberFormat('es-CO', …)` repartidas en **63 archivos
distintos**, con **≥12 variantes textualmente diferentes** (con/sin `style:'currency'`, con/sin
redondeo, con/sin `|| 0`, distintos `maximumFractionDigits`). No existe ningún util de moneda
(`utils/` solo tiene `formatQuoteAnswer.js`).

**Impacto:** no es solo duplicación — es **inconsistencia visible al usuario**: unos sitios
muestran "$ 1.216.180" (style currency) y otros "1216180" (número plano). Un cambio de política de
formato (ej. mostrar decimales, cambiar símbolo) hoy exige tocar 63 archivos.

**Corrección propuesta:** crear `src/utils/money.js` (`formatCOP(value, { withSymbol })`) y migrar
los 63 sitios. La regla de `CLAUDE.md` ("Precios: `new Intl.NumberFormat('es-CO')…`") debe
reescribirse a "usar `formatCOP()`". Migración mecánica pero amplia → hacerla por dominio, con
revisión visual por pantalla (el cambio de "número plano" a "con símbolo" es intencional en
algunos sitios; confirmar cuáles antes de unificar el estilo).

### 2.2 Extracción de error de axios/DRF inline en 61 archivos (existe `useErrorHandler`, 2 lo usan)

**Evidencia:** 61 componentes hacen extracción manual (`e.response?.data`, `.detail`, primer error
de campo…) mientras el composable `composables/useErrorHandler.js` — creado justamente para esto
(SPRINT 4, y `CLAUDE.md` dice "Código nuevo debe usarlo") — solo se usa en 2 archivos.

**Corrección propuesta:** adoptar `useErrorHandler().handleError(err, fallback)` en los catch que
solo muestran un toast (la mayoría). Dejar la extracción manual únicamente donde se necesitan
**todos** los errores de campo o render en template (excepciones ya documentadas en `CLAUDE.md`).

### 2.3 Duplicación de UI — evaluada y **mayormente descartada** (reportado para no reabrirla)

- **6 componentes de badge** (`BaseStatusBadge`, `CustomerStatusBadge`, `ShipmentStatusBadge`,
  `OperationStatusBadge`, `PaymentBadge`, `StockBadge`): 5 de 6 son wrappers finos (9-43 LOC)
  sobre `useEnums`/`BaseStatusBadge`. Solo `StockBadge` (42 LOC) tiene lógica propia (semáforo de
  stock, dominio distinto). **No es duplicación real** — no consolidar.
- **10 componentes de timeline**: 9 de 10 son adaptadores de 19-64 LOC que delegan en
  `components/shared/StatusTimeline.vue` (el unificado). Único con render propio: `PaymentTimeline`
  (37 LOC). **Oportunidad menor (P2):** hay un anidamiento de 3 capas
  (`<Dominio>Timeline` → `TrackingTimeline` → `StatusTimeline`); se podría colapsar `TrackingTimeline`
  si sus consumidores pasan a `StatusTimeline` directo, pero el beneficio es marginal.

---

## 3. Eficiencia / mantenibilidad — 🟠 P1/P2

### 3.1 Componentes monolíticos (god-components)

| Archivo | LOC | Nota |
|---|---|---|
| `modules/core/HomeConfigView.vue` | **2.629** | 250 declaraciones top-level en un solo SFC. Candidato #1 a descomponer por sección de home. |
| `modules/core/ModuleBuilderModal.vue` | 1.588 | Constructor visual de módulos; acoplado a HomeConfigView. |
| `views/customer/renting/RentalBookingWizard.vue` | 1.582 | Wizard 4 pasos. |
| `modules/technical_services/ServiceForm.vue` | 1.448 | Form de 7 tabs. |
| `views/customer/account/ContractorOnboardingWizard.vue` | 1.422 | Wizard con lógica de pasos inline (19 hits de step-logic). |
| `modules/renting/RentingForm.vue` | 1.349 | Form de equipo. |
| `modules/shop/ProductForm.vue` | 1.326 | Form de producto. |
| Catálogos (`ServicesCatalogView`, `RentalCatalogView`, `ServiceRequestWizard`, `RentalDetailView`, `ProductDetailView`, `ServiceDetailView`, `ShopCatalogView`) | 780-1.102 c/u | — |

**Impacto:** mantenibilidad (difícil de revisar/probar), y **bundle**: cada uno es un chunk lazy
grande. Descomponer por responsabilidad (secciones/tabs/pasos en subcomponentes) reduce superficie
de bug y mejora el code-splitting. **P1 solo para `HomeConfigView`** (tamaño atípico); el resto es
P2 (grandes pero coherentes; los 3 forms ya comparten patrón de tabs).

### 3.2 `onMounted` async con fetch secuencial

28 componentes tienen `onMounted(async …)`. Varios encadenan `await` secuenciales de recursos
independientes que podrían paralelizarse con `Promise.all` (ej. catálogo + config + enums en la
misma vista de detalle). **Requiere revisión por archivo** — no todos son paralelizables (algunos
dependen del resultado anterior). Ganancia: menor tiempo a primer render en vistas de detalle.

### 3.3 Estado de loading — patrón ya definido, verificar adopción

`CLAUDE.md` define two-tier `loading`/`actionLoading` para stores admin. Los stores migrados lo
respetan; los 40 componentes que aún usan `useApi` directo (§4.1) tienden a un solo `loading`
genérico. Se normaliza al migrar a stores (§4.1).

---

## 4. Escalabilidad — 🟠 P1/P2

### 4.1 Migración a stores Pinia incompleta (40 módulos admin con `useApi` directo)

De 54 componentes en `modules/` (panel admin) que usan `useApi`, **40 no consumen ningún store
Pinia** — pegan directo a la API desde el componente. Esto contradice la convención de `CLAUDE.md`
("Toda la administración… consuma exclusivamente el store de Pinia (SSoT), eliminando el uso
directo de composables de API"). La migración se hizo solo para `renting`/`quotes`/
`technical_services`; el resto (`shop`, `orders`, `operations`, `kyc`, `marketing`, `core`,
`organization`, `payment`, `security`, `notifications`, `users`) quedó a medias.

**Impacto de escalabilidad:** sin store, no hay caché ni invalidación centralizada, se duplica el
manejo de loading/error por componente, y no hay SSoT del estado admin. **Corrección:** completar
la migración módulo por módulo siguiendo el patrón de `store/rentingAdmin/` (state two-tier +
acciones `{ok, data, error}` + refetch automático post-mutación). Esfuerzo alto, incremental.

### 4.2 Sidebar hardcodeado (no permission/data-driven)

`components/layout/Sidebar.vue` define los grupos/ítems en `<script setup>` (arrays JS estáticos),
no dirigido por permisos ni por un endpoint de menú. Ya documentado en
`Documentacion/Arquitectura_general/MIGRACION_CORE_V4_DOMINIOS_FASE2_NAVEGACION.md` §4.2. No es un
bug, pero limita la escalabilidad (agregar un dominio = editar arrays; no hay ocultamiento por rol
más allá del guard de ruta). P2 — abordar solo si se introduce RBAC granular en el panel.

### 4.3 Router: un solo archivo de 82 rutas

`apps/admin/router.js` es el único router (sirve cliente + `/panel/*`). 82 rutas en un archivo
plano. Funciona, pero a esta escala conviene dividir por dominio (`routes/customer.js`,
`routes/admin.js`) para reducir el riesgo de sombras de ruta como el FE-C1 histórico. P2.

---

## 5. Acciones ejecutadas en esta pasada (2026-07-23)

**Purga de código muerto verificado (P0)** — todo reversible vía git, sin commit (queda en el
working tree para tu revisión):

- [x] Eliminados los 12 componentes `.vue` huérfanos (§1.1) — 0 referencias, verificado.
- [x] Eliminado el store huérfano `store/rentingAdmin/taxonomy.js` (§1.2).
- [x] Eliminados los 22 scripts ad-hoc `.cjs`/`.mjs` de la raíz de `frontend/` (§1.3).
- [x] Eliminados `src/components/ui/landing/plan.md` y `src/modules/technical_services/ServiceForm.vue.backup` (§1.4).

**No ejecutado (requiere decisión/refactor más amplio):** §2 (utils de moneda/error — tocan 60+
archivos), §3 (descomposición de monolitos), §4 (migración de stores, sidebar, split de router).
Los `console.log` residuales (§1.4) se dejaron para una pasada de linting dedicada.

---

## 6. Plan priorizado

> ✅ **Sincronizado 2026-07-27** contra `01_AUDITORIA_GENERAL.md` §6-7: **P1-1, P1-2 y P1-4 están
> cerrados.** P1-3 es hoy el único ítem abierto de toda la punch list de deuda técnica del proyecto
> — diferido a propósito a su propia sesión, decisión explícita del usuario.

| # | Acción | Prioridad | Esfuerzo | Riesgo | Estado (2026-07-27) |
|---|---|---|---|---|---|
| P1-1 | Crear `utils/money.js` (`formatCOP`) y migrar los 63 sitios de moneda; unificar estilo (con/sin símbolo) por pantalla | Alta | Medio (amplio) | Bajo (visual, revisable) | ✅ Resuelto — 0 instanciaciones inline restantes, 62 archivos con `formatCOP`, 6/6 tests (doc 01 §7.4) |
| P1-2 | Adoptar `useErrorHandler` en los ~61 catch de solo-toast | Alta | Medio | Bajo | ✅ Resuelto — 48 archivos adoptando el composable (13 migrados en la sesión de cierre), 2 exclusiones deliberadas y verificadas (doc 01 §7.5) |
| P1-3 | Descomponer `HomeConfigView.vue` (2.629 LOC) por secciones | Alta | Alto | Medio | 🔶 **Sigue abierto** — diferido a propósito a su propia sesión dedicada (doc 01 §6 punto 5, §7.6, §7.21) |
| P1-4 | Completar migración a stores Pinia de los módulos admin restantes (`shop`, `orders`, `operations`, …) | Alta | Alto (incremental) | Medio | ✅ Resuelto 100% — los 11 dominios de §4.1 migrados en 13 incrementos verificados en vivo, incluida la pieza más grande (`HomeConfigView.vue`/`ModuleBuilderModal.vue`, 43+2 llamadas API) (doc 01 §7.7-§7.21) |
| P2-1 | Revisar los 28 `onMounted` async → `Promise.all` donde aplique | Media | Bajo/Medio | Bajo | ⚪ Sin re-verificar |
| P2-2 | Descomponer forms/wizards restantes (>1.000 LOC) por tabs/pasos | Media | Alto | Medio | ⚪ Sin re-verificar |
| P2-3 | Split del router por dominio | Media | Bajo | Bajo | ⚪ Sin re-verificar |
| P2-4 | Colapsar capa `TrackingTimeline` si aporta | Baja | Bajo | Bajo | ⚪ Sin re-verificar |
| P2-5 | Sidebar dirigido por datos/permisos (solo si entra RBAC de panel) | Baja | Medio | Medio | ⚪ Sin re-verificar |
| P3-1 | Barrido de `console.*` residuales + regla de lint | Baja | Bajo | Nulo | ⚪ Sin re-verificar |

**Recomendación de secuencia (histórica):** P1-1 y P1-2 primero (alto ROI, bajo riesgo, base para lo demás),
luego P1-3, luego P1-4 dominio por dominio. Cada ítem P1 merece su propia rama + verificación
visual/`npm run build` antes de mezclarse. **Estado real de ejecución:** se completaron P1-1, P1-2 y
P1-4 antes que P1-3 (orden inverso al recomendado aquí, decisión explícita del usuario en la sesión
de 2026-07-27) — P1-3 sigue como el único pendiente.
