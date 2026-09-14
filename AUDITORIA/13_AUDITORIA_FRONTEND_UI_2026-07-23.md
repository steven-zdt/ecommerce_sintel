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

> ✅ **Sincronizado 2026-07-30** contra `01_AUDITORIA_GENERAL.md` §6-7: **P1-1, P1-2, P1-3 y P1-4
> están cerrados — la punch list completa de deuda técnica del proyecto quedó en 4/4.** P1-3 se
> cerró en su propia sesión dedicada (como estaba planeado), verificado de forma independiente
> (lectura directa de `HomeConfigView.vue` antes/después, existencia y consumo real de los 8
> subcomponentes de `home-builder/` y de `store/coreAdmin.js`, y `npm run build` limpio) — no solo
> por el reporte del propio cambio.

| # | Acción | Prioridad | Esfuerzo | Riesgo | Estado (2026-07-27) |
|---|---|---|---|---|---|
| P1-1 | Crear `utils/money.js` (`formatCOP`) y migrar los 63 sitios de moneda; unificar estilo (con/sin símbolo) por pantalla | Alta | Medio (amplio) | Bajo (visual, revisable) | ✅ Resuelto — 0 instanciaciones inline restantes, 62 archivos con `formatCOP`, 6/6 tests (doc 01 §7.4) |
| P1-2 | Adoptar `useErrorHandler` en los ~61 catch de solo-toast | Alta | Medio | Bajo | ✅ Resuelto — 48 archivos adoptando el composable (13 migrados en la sesión de cierre), 2 exclusiones deliberadas y verificadas (doc 01 §7.5) |
| P1-3 | Descomponer `HomeConfigView.vue` (2.629 LOC) por secciones | Alta | Alto | Medio | ✅ Resuelto 2026-07-30 — archivo original en 715 LOC, 8 subcomponentes por sección bajo `frontend/src/modules/core/home-builder/` + `cardGroupsUtil.js`, datos centralizados en `store/coreAdmin.js` (todas las acciones fetch/create/update/delete de los 11 recursos presentes y consumidas), `npm run build` limpio (doc 01 §7.22) |
| P1-4 | Completar migración a stores Pinia de los módulos admin restantes (`shop`, `orders`, `operations`, …) | Alta | Alto (incremental) | Medio | ✅ Resuelto 100% — los 11 dominios de §4.1 migrados en 13 incrementos verificados en vivo, incluida la pieza más grande (`HomeConfigView.vue`/`ModuleBuilderModal.vue`, 43+2 llamadas API) (doc 01 §7.7-§7.21) |
| P2-1 | Revisar los 28 `onMounted` async → `Promise.all` donde aplique | Media | Bajo/Medio | Bajo | ✅ Resuelto 2026-07-30 (ver nota) |
| P2-2 | Descomponer forms/wizards restantes (>1.000 LOC) por tabs/pasos | Media | Alto | Medio | ✅ **Resuelto 2026-07-30 — 9/9 archivos** (ver nota) |
| P2-3 | Split del router por dominio | Media | Bajo | Bajo | ✅ Resuelto 2026-07-30 (ver nota) |
| P2-4 | Colapsar capa `TrackingTimeline` si aporta | Baja | Bajo | Bajo | ✅ **Evaluado 2026-07-30 — NO colapsar** (ver nota), decisión justificada |
| P2-5 | Sidebar dirigido por datos/permisos (solo si entra RBAC de panel) | Baja | Medio | Medio | ⚪ Sin re-verificar |
| P3-1 | Barrido de `console.*` residuales + regla de lint | Baja | Bajo | Nulo | 🔶 **Parcial 2026-07-30** — barrido hecho (ver nota), regla de lint fuera de alcance (ver nota) |

> **Nota P2-2 (2026-07-30, primer archivo):** `views/customer/detail/PublicDetailView.vue`
> (2.091 LOC — componente compartido en vivo por 3 rutas de cliente: `tienda/:uuid`,
> `alquiler/:uuid`, `servicios/:uuid`) descompuesto en un shell de 190 líneas +
> `RentingDetailContent.vue` (813), `ServiceDetailContent.vue` (803), `ShopDetailContent.vue`
> (732). Estrategia de fetch conservadora elegida a propósito (props ya resueltos por el padre,
> no fetch propio por hijo) para no alterar la secuencia de carga percibida (un solo skeleton
> hasta que todo esté listo). Verificado en las 3 rutas reales del navegador con UUIDs reales
> (no solo build): 0 errores de consola, contenido completo renderizado, y estilos computados
> extraídos en vivo (tipografía, colores, radios, grids) comparados 1:1 contra el original para
> descartar regresión visual del corte de CSS scoped (se encontró y corrigió una regla `.badge`
> que vivía en el scoped del padre y dejó de alcanzar a los hijos). Quedan 7 archivos de esta
> nota: `RentalBookingWizard.vue` (1566, wizard de compra), `ServiceForm.vue` (1345),
> `ContractorOnboardingWizard.vue` (1315), `RentingForm.vue` (1300), `ProductForm.vue` (1149),
> `RentalCatalogView.vue` (1052), `ServicesCatalogView.vue` (1037).

> **Nota P2-2 (2026-07-30, segundo archivo):** `modules/core/ModuleBuilderModal.vue` (1727/1845
> LOC — modal admin de configuracion de un modulo de la home, NO es pagina de embudo de compra,
> menor riesgo que el archivo anterior) descompuesto en shell de 779 lineas + 13 componentes de
> pestaña bajo `modules/core/module-builder/` (uno por cada `activeTab`) + `_shared.css`
> (primitivas de estilo comunes, importado con scope propio por hijo) + `constants.js`. `form` es
> `reactive` pasado como prop y mutado en sitio por los hijos (nunca reasignado completo).
> Verificacion exhaustiva sin login de admin disponible: diff vacio de los 63 campos de primer
> nivel + 31 rutas anidadas de `form.*` y de los 68 `v-model` literales antes/despues, `npm run
> build` limpio, y un spec temporal de vitest+@vue/test-utils (creado, corrido con 4/4 tests en
> verde cubriendo render de las 13 secciones, escritura de v-model anidados, repoblacion al
> editar, y bloqueo de guardado por validacion — despues eliminado, `git status` limpio).
> **Hallazgo colateral (bug preexistente, NO corregido a proposito, preservado tal cual segun el
> encargo de "descomponer sin cambiar comportamiento"):** en la pestaña Carrusel,
> `getCarouselItems`/`setCarouselItems` comparan contra `'desktop'`/`'tablet'` pero reciben claves
> reales `'columns'`/`'columns_tablet'`/`'columns_mobile'` — las 3 filas caen al `else` y leen/
> escriben `items_mobile`, por lo que el admin no puede fijar columnas de desktop/tablet por
> separado desde la UI. Documentado con comentario en el archivo y flageado como tarea aparte
> (`task_ec1525a2` — verificado luego como duplicado de `task_e919cea5`, ya corregido en
> `module-builder/CarouselTab.vue` con su propio `CAROUSEL_DEVICES`).

> **Nota P2-2 (2026-07-30, archivos 3-9, punch list completa 9/9):** resumen breve — el detalle
> completo de cada archivo (props exactas, decisiones de fetch-en-hijo vs fetch-en-padre, bugs
> encontrados) vive en la memoria de la sesión (`project_sintel_auditoria_enterprise_remediation.md`).
> - **3/9** `views/customer/renting/RentalBookingWizard.vue` (wizard de reserva real, el mismo
>   archivo del bug crítico de congelamiento por `<Transition>`) → shell ~600 líneas +
>   `booking-wizard/{EquipmentStep,ProjectStep,ScheduleStep,ConfirmStep}.vue` + `helpers.js`, todos
>   leyendo `useBookingStore()` directo. Verificado con sesión real de navegador (JWT generado por
>   Django shell) recorriendo los 4 pasos reales contra un equipo real.
> - **4/9** `modules/technical_services/ServiceForm.vue` (1452 LOC) → shell ~230 líneas + 5 tabs
>   bajo `service-form/`. Verificado con sesión admin real sobre un servicio con 2 variantes.
> - **5/9** `views/customer/account/ContractorOnboardingWizard.vue` (1424 LOC) → shell ~430 líneas +
>   `contractor-onboarding/{OnboardingHub,Step1Info,Step2Skills,Step3Training,Step4Portfolio}.vue`.
>   Verificado con sesión de cliente real; en el proceso se encontró y flageó (no corregido, fuera
>   de alcance) un bug real de backend preexistente: varios `ViewSet.perform_create()` de CV
>   (academic-training, skills, experience, courses) no asignan el registro creado a
>   `serializer.instance`, dejando cada item recién agregado sin `id` hasta recargar la página
>   (`task_24a68d42`).
> - **6/9** `modules/renting/RentingForm.vue` (1390 LOC) → shell ~400 líneas + 5 tabs bajo
>   `equipment-form/`. Verificado con sesión admin real; como efecto colateral natural de la
>   extracción (no una corrección deliberada) se resolvió un bug real donde `toggleCostRule`/
>   `deleteCostRule` llamaban `fetchCostRules()` sin el `equipmentUuid` requerido, reemplazando
>   silenciosamente la lista de reglas por un fetch sin filtrar de todo el catálogo.
> - **7/9** `modules/shop/ProductForm.vue` (1254 LOC) → shell ~230 líneas + 5 tabs bajo
>   `product-form/`. Verificado con sesión admin real sobre un producto con variante y 2 reglas de
>   costo.
> - **8/9** `views/customer/renting/RentalCatalogView.vue` (1120→985 LOC) → 2 componentes
>   presentacionales (`rental-catalog/{RentalCatalogHero,RentalSolutionStrip}.vue`). Verificado en
>   vivo contra `/alquiler` (página pública), cero errores de consola.
> - **9/9** `views/customer/services/ServicesCatalogView.vue` (1101→822 LOC) → 2 componentes
>   presentacionales (`services-catalog/{ServicesCatalogHero,ServicesMarketplaceStrip}.vue`).
>   Verificado en vivo contra `/servicios`: cero errores de consola, y prueba funcional real del
>   `v-model:search` recién introducido (se tipeó en el campo del hijo y la red confirmó
>   `?search=camara` llegando a la API tras el debounce).
>
> **Los 9 archivos >1.000 LOC identificados originalmente están descompuestos y verificados —
> P2-2 100% resuelto.**

> **Nota P2-4 (2026-07-30):** verificada la cadena real de imports: `components/customer/services/
> OperationTimeline.vue` → `components/customer/ui/TrackingTimeline.vue` →
> `components/shared/StatusTimeline.vue`. No es indirección accidental — cada capa hace trabajo
> real y distinto: `StatusTimeline` es el renderer puro (modo `steps`/`events`); `TrackingTimeline`
> mantiene una tabla de ~40 líneas mapeando códigos de milestone (`CREATED`/`ASSIGNED`/
> `SCHEDULED`/`EN_ROUTE`/etc.) a label/icono/color/fecha, y la **reutilizan 3 consumidores
> distintos** (`modules/operations/OperationDetail.vue`, `views/customer/operations/
> OperationTrackingView.vue`, y `OperationTimeline.vue`); `OperationTimeline.vue` traduce los
> códigos específicos de `ServiceOperationEvent` al vocabulario genérico que `TrackingTimeline`
> espera. Colapsar `TrackingTimeline` implicaría duplicar su tabla de mapeo en los 3 consumidores,
> o contaminar el `StatusTimeline` genérico con vocabulario de operaciones — ambas opciones peores
> que la estructura actual. **Conclusión: la capa está justificada, no se colapsa.** Confirma la
> sospecha original del hallazgo de doc 13 §... ("el beneficio es marginal").

> **Nota P2-1 (2026-07-30):** de los 29 archivos con `onMounted(async ...)`, 4 tenían llamadas
> genuinamente independientes que se fusionaron en `Promise.all` (`KycAdminDetail.vue`,
> `TechnicianAssignmentBoard.vue`, `TechnicianCalendarBoard.vue`, `CheckoutView.vue`); el resto
> ya estaban optimizados, tenían un solo `await`, o se dejaron intactos por dependencia real
> entre llamadas. Dos hallazgos de riesgo real evitados a proposito: `RentalConfirmationView.vue`
> tiene un `router.replace` condicional entre los dos `await` que depende del resultado del
> primero (fusionar dispararía la segunda llamada aunque el primer resultado redirija) y, mas
> sutil, `panels/BlocksPanel.vue`/`QuoteTemplateForm.vue` tienen fetches en sí independientes pero
> que comparten el mismo flag `store.loading` (leído por el spinner de la plantilla y por
> componentes hermanos) — paralelizarlas haría que el spinner desaparezca en cuanto termine la
> mas rapida mientras la otra sigue en curso, un cambio de comportamiento observable aunque los
> datos en sí no tengan dependencia. `npm run build` limpio tras los 4 cambios.

> **Nota P2-3 (2026-07-30):** `frontend/src/apps/admin/router.js` (371 líneas, 82 rutas en un solo
> arreglo) dividido en 10 archivos bajo `frontend/src/apps/admin/routes/` (`auth`, `customer`,
> `adminAuth`, `adminShop`, `adminOrders`, `adminUsers`, `adminServices`, `adminQuotes`,
> `adminRenting`, `adminCore`, `adminOps`), cada uno exportando su tramo tal cual estaba (mismo
> orden interno, mismos nombres/paths/meta) — `router.js` quedó en 182 líneas, solo compone los
> arreglos con spread y conserva intacta la lógica de guards/host-isolation. Riesgo real
> identificado antes de tocar nada: este es el mismo archivo del bug histórico FE-C1
> (`ordenes/renting` vs `ordenes/:uuid`), así que el orden relativo DENTRO de cada dominio se
> preservó exactamente y se documentó con un comentario en cada archivo con el patrón (
> `adminOrders.routes.js`, `adminUsers.routes.js`, `adminRenting.routes.js` tienen pares
> estático/dinámico del mismo nivel). Verificado en el navegador real (no solo build): `npm run
> build` limpio, y `router.resolve()` ejecutado en vivo contra 25 paths representativos —
> incluidos los 3 pares estático/dinámico de riesgo — confirmó que cada uno resuelve al `name`
> correcto (`ordenes/renting` → `renting-operations`, no `order-detail`; `renta/solicitudes` →
> `renting-requests`, no `equipment-detail`; `validaciones` → `kyc-admin-list` vs
> `validaciones/:uuid` → `kyc-admin-detail`). `/tienda` cargado en vivo sin errores de consola,
> 8 productos renderizados correctamente.

> **Nota P3-1 (2026-07-30):** de los 15 archivos con `console.*`, se verificó cada uno — la
> mayoría son `console.error`/`console.warn` deliberados en catch blocks o en el interceptor de
> `useApi.js`/`useEnums.ts` (visibilidad de errores real, no ruido) y se dejaron intactos. El
> único hallazgo genuinamente residual: `composables/useOffcanvas.js` tenía 5 `console.log('[UI]
> ...')` de depuración disparándose en cada trigger (init/openCreate/openEdit/openDetail/close) de
> un composable usado por prácticamente todo CRUD admin del panel — eliminados, `npm run build`
> limpio. La "regla de lint" de este ítem no se implementó: el proyecto no tiene ESLint instalado
> en absoluto (sin `.eslintrc`/`eslint.config.*`, sin dependencia en `package.json`), así que
> agregar una regla real significa introducir toda la herramienta desde cero — un alcance mucho
> mayor al "Bajo esfuerzo" estimado originalmente para este punto, y una decisión de tooling que
> merece su propia conversación con el usuario en vez de asumirse dentro de un quick win.

**Recomendación de secuencia (histórica):** P1-1 y P1-2 primero (alto ROI, bajo riesgo, base para lo demás),
luego P1-3, luego P1-4 dominio por dominio. Cada ítem P1 merece su propia rama + verificación
visual/`npm run build` antes de mezclarse. **Estado real de ejecución:** se completaron P1-1, P1-2 y
P1-4 antes que P1-3 (orden inverso al recomendado aquí, decisión explícita del usuario en la sesión
de 2026-07-27); P1-3 se cerró después, en su propia sesión dedicada (2026-07-30), tal como estaba
planeado. **Los 4 ítems P1 de esta punch list están hoy 100% resueltos y verificados de forma
independiente — no queda ninguna acción de mejora P1 por implementar.** Los ítems P2/P3 restantes
en la tabla de arriba no forman parte de esta punch list (son hallazgos de menor prioridad, sin
re-verificar desde 2026-07-23).
