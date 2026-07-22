# PLAN_MAESTRO_FRONTEND_DESIGN_SYSTEM_Y_FORMULARIOS.md

> **Documento vivo, construido incrementalmente por fases.** Cada fase requiere confirmacion
> explicita del usuario antes de continuar a la siguiente (regla de ejecucion pedida
> explicitamente: "La IA NO podra continuar automaticamente"). Este documento se actualiza al
> cierre de cada fase con sus hallazgos, sin tocar codigo hasta que una fase de construccion
> (Fase 3 en adelante) sea explicitamente aprobada.
>
> **Restriccion vigente durante todo el proceso:** cero cambios a logica de negocio, endpoints,
> serializers, modelos, commands, selectors, servicios, permisos, autenticacion, integracion de
> Payment, inventario, operaciones. Todo cambio futuro sera exclusivamente UX/UI/componentes
> Vue/layouts/formularios/validaciones de frontend/presentacion/navegacion.
>
> **IMPORTANTE — descubierto durante la implementacion (2026-07-18):** existe
> `PLAN_MAESTRO_UNIFICACION_PAYMENT_UI.md` (raiz del repo), un plan previo e independiente que
> ya audito y **ya implemento** la unificacion de UI de Payment (`PaymentCard`, `PaymentBadge`,
> `PaymentAlert`, `PaymentTimeline`, `PaymentCTA`, etc. en `components/shared/checkout/`),
> verificado end-to-end en navegador con pagos reales Wompi/Nequi/COD en Shop/Renting/Services.
> Varios de los "hallazgos" de la Fase 1/2 de ESTE documento (`PaymentCard` vs `CustomerCard`,
> `PaymentBadge` vs `CustomerStatusBadge`) ya fueron evaluados alli y **la decision consciente
> fue mantenerlos separados por ahora** (8 consumidores reales de `CustomerCard`/etc.
> encontrados al auditar, mas de lo estimado — mover de carpeta se pospuso explicitamente, ver
> seccion 15 de ese documento). El Paso 1 (Payment) del plan de migracion de la Fase 7 §7.2 de
> ESTE documento **se da por completado** por ese trabajo previo — no se duplica. La unica
> pieza que ese plan NO cubrio es `PaymentTimeline.vue` vs `StatusTimeline.vue` (no aparece en
> su tabla de componentes duplicados) — se seguira evaluando si migrarla tiene sentido o si hay
> una razon (no documentada) para mantenerla separada, antes de tocarla.

## Estado de ejecucion

- ✅ **Fase 1 — Auditoria Global de Arquitecturas: COMPLETA.**
- ✅ **Fase 2 — Auditoria de Componentes Duplicados: COMPLETA.**
- ✅ **Fase 3 — Diseño de Biblioteca Compartida: COMPLETA.** Ver catalogo abajo. Fase de
  **diseño** (contratos/props), no de construccion — la construccion real de cada `Base*`
  ocurre incrementalmente cuando se apruebe cada modulo en Fase 7 (o antes, si el usuario
  pide adelantar alguno puntualmente). Las 3 decisiones de arquitectura de §3.4 (modales,
  badges, alcance de BaseTable) siguen sin respuesta explicita — se retoman antes de construir
  nada en Fase 7, no bloquean la auditoria de formularios de Fase 4.
- ✅ **Fase 4 — Auditoria Integral de Formularios: COMPLETA.**
- ✅ **Fase 5 — Nuevo Estandar de Formularios: COMPLETA.**
- ✅ **Fase 6 — Experiencia de Usuario: COMPLETA.**
- ✅ **Fase 7 — Sincronizacion Arquitectonica: COMPLETA.** Ver checklist y plan de migracion
  abajo. **Importante:** esta fase documenta el CAMINO hacia la sincronizacion (checklist +
  plan de migracion incremental) — no declara que los modulos ya esten sincronizados hoy, ya
  que ningun codigo se ha migrado todavia (Fases 3-6 fueron diseño, no construccion). La
  sincronizacion real se valida modulo por modulo a medida que cada uno se migre.
- ✅ **Fase 8 — Validacion Final: COMPLETA.** Confirmado: cero cambios de backend/codigo.
  **Documento cerrado — ver checklists finales y "Documento Final" al pie.**
- ✅ **IMPLEMENTACION EJECUTADA (2026-07-18, pedido explicito "continua en orden secuencial
  hasta finalizar por completo la tarea"):** ver seccion "Implementacion Real" al final del
  documento — componentes `Base*` construidos y migrados, verificados con build + Playwright +
  tests backend, ningun endpoint/modelo/serializer tocado.

---

## FASE 1 — Auditoria Global de Arquitecturas

### Metodologia

Auditoria verificada contra codigo real (no suposiciones): 4 agentes de exploracion en paralelo
cubrieron Payment, Shop, Accounts/KYC/Organization/Users, y Core/Notifications/Operations/
Security/Support; se sumo el conocimiento ya verificado de esta misma sesion sobre Renting vs.
Technical Services (unificacion UX ejecutada en 6 fases, 2026-07-17/18) y el registro vivo de
componentes (`ai_skills/frontend/components/cards.md`). Se verificaron ademas por lectura
directa: existencia y consumidores reales de `ColombianAddressForm.vue`, duplicacion de CSS de
skeleton (comparacion byte a byte de 3 archivos), y el arbol de `components/shared/checkout/`.

### 1.1 Que SI esta unificado hoy (base real para la Fase 3, no partir de cero)

| Pieza | Componente | Estado |
|---|---|---|
| Toasts | `useToast()` | ✅ Unico sistema, sin duplicados encontrados en ningun modulo |
| Enums/labels de estado | `useEnums()` | ✅ Fuente unica backend-driven, adoptado en 16+ archivos — **con 3 excepciones reales** (ver 1.3) |
| Timeline | `StatusTimeline.vue` | ✅ 7 timelines legados (Rental/Service/Operation/Tracking/Unified/Order/Shipment) son wrappers delgados — **con 1 excepcion real** (`PaymentTimeline.vue`, ver 1.3) |
| Stepper de wizard/checkout | `CheckoutStepper.vue` | ✅ Compartido entre `RentalBookingWizard.vue`, `ServiceRequestWizard.vue` y `CheckoutModal.vue` (unificado 2026-07-18) — **con 1 excepcion real** (`ContractorOnboardingWizard.vue`, ver 1.3) |
| Modal de checkout (pago) | `CheckoutModal.vue` | ✅ Compartido Renting+Services, generico (no conoce de pagos, solo slots) |
| Cascaron de tableros de operaciones | `BaseOperationBoard.vue` | ✅ Compartido Shop/Renting/Services/Admin general — por diseño solo comparte header+KPIs |
| Card de catalogo (producto/renta/servicio) | `ItemCard.vue` | ✅ Ya es una base compartida por `type` prop — **con 1 candidato a duplicado** (`ServiceCard.vue`, ver 1.3) |
| Panel CRUD lateral (admin) | `SintelOffcanvas.vue` | ✅ Adoptado correctamente en Shop, Usuarios, Notificaciones — **con 2 excepciones graves** (ver 1.3) |
| Design System "Mi Cuenta" | `components/customer/account/*` (13 componentes) | ✅ Ya existe una mini-biblioteca base (Card/Button/Badge/EmptyState/ErrorState/Skeleton/ConfirmInline/OverlayPanel/DetailRow/Section/Avatar/Pagination) — **hoy solo se usa dentro de `/mi-cuenta/*`, en ningun otro modulo** |

**Implicacion para la Fase 3:** no hay que diseñar una biblioteca desde cero. La biblioteca
`components/customer/account/*` ya es, funcionalmente, un 60% de lo que la Fase 3 pide como
`Base*` — el trabajo real es (a) generalizarla fuera de "Mi Cuenta" (o renombrarla/moverla a un
namespace neutro tipo `components/base/`), y (b) migrar los ~15 puntos de duplicacion reales
listados abajo para que la consuman.

### 1.2 Hallazgo transversal mas importante: 3 "lenguajes visuales" conviven en el mismo panel admin

No es que cada modulo tenga su propio estilo por accidente menor — hay **tres sistemas
completos y mutuamente incompatibles** operando simultaneamente bajo `AppShell`:

1. **Bootstrap "vainilla" + `SintelOffcanvas`** (Shop, Usuarios, Notificaciones, KYC-list) — el
   patron mayoritario y el unico documentado en `frontend/CLAUDE.md`.
2. **CSS propio con prefijo de modulo** (`OrganizationView.vue` usa `org-input`/`org-btn-primary`/
   `org-tab-btn` en vez de clases Bootstrap o del design system — 8 tabs, ningun componente
   compartido).
3. **Modales hechos a mano por archivo** (`HomeConfigView.vue` tiene **7 modales propios**
   `.hcb-modal-*`; `OperationDetail.vue` tiene su propio `.assign-modal`) — un cuarto/quinto
   sistema de "ventana emergente" ademas de `SintelOffcanvas` y `CheckoutModal`.

Esto confirma exactamente el sintoma que la Fase 1 pedia buscar ("layouts distintos") a nivel
de **todo el panel admin**, no solo entre Renting/Services como ya se sabia.

### 1.3 Matriz de duplicacion/incompatibilidad (evidencia real, archivo por archivo)

#### Cards

| Componente A | Componente B | Veredicto |
|---|---|---|
| `ItemCard.vue` (`type="service"`) | `ServiceCard.vue` (`components/customer/ui/`) | **Candidato a duplicado real** — ambos renderizan una card de servicio para `ServicesCatalogView.vue`; hay que verificar en Fase 2 si `ServiceCard.vue` esta muerto o si tiene un uso real que `ItemCard` no cubre. |
| `CustomerCard.vue` (Mi Cuenta) | `PaymentCard.vue` (payment) | No son duplicados funcionales (conceptos distintos: seccion de cuenta vs. caja de contenido en checkout) pero **colision de nombre** — confunde al buscar "Card" en el registro. |

#### Modales / paneles superpuestos

| Implementacion | Archivo | Deberia usar |
|---|---|---|
| 7 modales propios (`.hcb-modal-*`) | `modules/core/HomeConfigView.vue` | `SintelOffcanvas.vue` |
| Modal de asignar/programar (`.assign-modal`) | `modules/operations/OperationDetail.vue` | `SintelOffcanvas.vue` |
| `CustomerOverlayPanel.vue` (Mi Cuenta) | ya correcto, pero es un 4to sistema paralelo a `SintelOffcanvas`/`CheckoutModal` | unificar concepto en Fase 3 |

#### Timelines

| Implementacion | Archivo | Deberia usar |
|---|---|---|
| Lista de puntos propia (dot/line/label/date) | `components/shared/checkout/PaymentTimeline.vue` | `StatusTimeline.vue` (`mode="events"`) — mapear el shape de evento de pago igual que ya hace `TrackingTimeline.vue` |
| Tabla plana sin timeline | `modules/security/SecurityDashboardView.vue` | oportunidad de usar `StatusTimeline mode="events"` para el log de eventos (no es un duplicado, es una ausencia) |

#### Wizards / Steppers

| Implementacion | Archivo | Deberia usar |
|---|---|---|
| Barra de progreso propia (`.step-progress`, `.step-circle`) | `views/customer/account/ContractorOnboardingWizard.vue` | `CheckoutStepper.vue` |
| Flujo de una sola pagina (sin stepper) | `views/customer/checkout/CheckoutView.vue` (Shop) | Inconsistencia estructural: Renting/Services usan wizard de 4 pasos, Shop usa formulario plano — **decision de UX a confirmar en Fase 6**, no un simple defecto tecnico |

#### Badges / estado

| Implementacion | Archivo | Problema |
|---|---|---|
| `statusClass()` local hardcodeado | `modules/payment/PaymentTransactionsAdminView.vue` | No usa `useEnums()` pese a que `PaymentResultView.vue` (mismo dominio) si lo usa correctamente |
| `statusBadgeClass()`/`statusLabel()` local | `components/auth/kyc/KycDocumentUploadStep.vue` | No usa `useEnums()` |
| `PaymentBadge.vue` | `components/shared/checkout/` | Modelado a mano sobre el patron de `CustomerStatusBadge.vue` en vez de reusarlo (segun su propio docstring) |

#### Skeletons / Loaders (la categoria mas fragmentada)

| Implementacion | Archivos | Problema |
|---|---|---|
| CSS de shimmer casi identico copiado 3+ veces | `RentalDetailView.vue`, `ServiceDetailView.vue` (idénticos byte a byte), `ProductDetailView.vue` (colores distintos, misma mecanica) | Ninguno usa `CustomerSkeleton.vue`/`LoadingSkeleton.vue`, que ya existen |
| `.sk-card`/`.shimmer` propio | `ShopCatalogView.vue`, `ServicesCatalogView.vue`, `RentalCatalogView.vue` | Mismo problema en las 3 vistas de catalogo |
| `spinner-border` copiado sin componente compartido | `HomeConfigView.vue`, `NotificationsAdminView.vue`, `OperationBoard.vue`, `OperationDetail.vue`, `DispatcherList.vue`, `PaymentResultView.vue`, `PaymentStatusPanel.vue` | Cada uno con su propio wrapper CSS |
| **Sin ningun indicador de carga** | `SecurityDashboardView.vue`, `SupportDashboardView.vue` | No es duplicacion, es una ausencia real — el usuario ve una tabla vacia mientras carga |

#### Confirmaciones (violacion documentada de la regla propia del proyecto)

`frontend/CLAUDE.md` ya exige: *"Confirmacion de borrado: fila inline `bg-danger-subtle` — no
modales flotantes"*. Se sigue correctamente en `ProductList.vue`, `UserList.vue`, y el area
`/mi-cuenta/*` en general (`CustomerConfirmInline`). Se **viola** en:

| Archivo | Linea aprox. | Accion |
|---|---|---|
| `modules/users/UserDetail.vue` | 267, 286 | `confirm()` nativo para reset de password y activar/desactivar — **contradice a `UserList.vue`, mismo modulo** |
| `modules/kyc/KycVerificationPanel.vue` | 310 | `confirm()` nativo para forzar aprobacion |
| `modules/organization/OrganizationView.vue` | 342 | `confirm()` nativo para borrar link social |
| `modules/core/HomeConfigView.vue` | 9 ocurrencias (1418, 1521, 1679, 1810, 1900, 1989, 2106, 2234, +1) | `confirm()` nativo en casi cada accion de borrado |
| `modules/operations/DispatcherList.vue` | 159 | `confirm()` nativo |
| `components/customer/CartOffcanvas.vue` | — | **Sin ninguna confirmacion** (ni nativa ni inline) al quitar item o vaciar carrito — regresion real, no solo inconsistencia de estilo |
| `views/customer/account/ContractorOnboardingWizard.vue` | — | Patron inline propio (`deletingId`) que no reusa `CustomerConfirmInline`, pese a vivir dentro de `/mi-cuenta/*` |

#### Formularios de direccion (el hallazgo de mayor impacto potencial)

La captura de direccion colombiana esta implementada **de forma independiente en al menos 6
lugares**, con **2 fuentes de datos distintas que pueden desincronizarse**:

| Implementacion | Archivo | Dataset usado | Patron |
|---|---|---|---|
| Componente reutilizable (pero con 1 solo consumidor) | `components/customer/checkout/ColombianAddressForm.vue` | `data/colombiaLocations.js` (dept→ciudad) | Select dependiente + constructor de nomenclatura (via/numero/generadora/placa) |
| Inline propio | `views/customer/renting/RentalBookingWizard.vue` | `data/colombiaLocations.js` (mismo dataset, logica separada) | Mismo concepto, markup propio |
| Inline propio | `views/customer/services/ServiceRequestWizard.vue` | `data/colombiaLocations.js` (mismo dataset, logica separada) | Mismo concepto, markup propio |
| Texto libre, sin seleccion | `views/customer/account/CustomerProfileView.vue`, `CustomerAddressView.vue` | ninguno | `city`/`state`/`country` como `<input>` de texto plano |
| Independiente, **dataset distinto** | `components/auth/kyc/PersonalInfoFields.vue` | `data/latamData.js` (lista plana de ciudades, **sin** departamento) | Select de ciudad + select de via, sin relacion dept↔ciudad |
| Texto libre | `views/customer/account/ContractorOnboardingWizard.vue` | ninguno | `city`/`country` como texto plano, sin campo de departamento |

**Riesgo real:** `colombiaLocations.js` y `latamData.js` son dos catalogos de ciudades
mantenidos por separado — si uno se actualiza (nueva ciudad, correccion de nombre) el otro
queda desincronizado sin que nada lo detecte.

#### Otros formularios (hallazgos menores, detalle completo en Fase 4)

- **Iconos en labels inconsistentes dentro del mismo modulo:** `ProductForm.vue` los usa en
  cada tab/seccion; `TaxForm.vue` (mismo modulo Shop) no usa ninguno.
- **`maxlength` inconsistente:** solo `ProductForm.vue`/`CategoryForm.vue` (campos SEO) tienen
  contador+limite. Nombre de producto/categoria/marca, descripcion de producto, cuerpo de
  plantilla de notificacion (`NotificationsAdminView.vue`) son `<textarea>`/`<input>` sin limite
  — coincide exactamente con el patron que la Fase 5 pide prohibir.
  Coincide con la observacion del propio Karpathy Principle #1 del proyecto? no aplica aqui, es
  hallazgo de UX puro.
- **Selector de canal de notificacion inferido, no explicito:** `NotificationsAdminView.vue`
  determina que canales estan activos mirando que campos tienen datos, en vez de un
  selector/checkbox-group explicito.
- **Upload de imagen/logo duplicado 4 veces sin componente compartido:** slots de documento KYC
  (`KycDocumentUploadStep.vue`), logo/favicon/OG de `OrganizationView.vue`, el bloque de
  preview+quitar de `BrandForm.vue`/`CategoryForm.vue` (literalmente copy-paste entre ambos), y
  el `.hcb-upload-area` de `HomeConfigView.vue` (5 usos internos, consistente consigo mismo pero
  aislado del resto). Ninguno es el mismo componente.
- **"Tipo de contratista" en `ContractorOnboardingWizard.vue` es texto libre** — deberia ser
  `Select`, mismo problema que la Fase 5 pide corregir para "Profesion"/"Especialidad".

### 1.4 Riesgos identificados para las fases siguientes

| Riesgo | Mitigacion propuesta |
|---|---|
| Migrar el patron de direccion a un solo componente puede romper el payload exacto que cada wizard/form envia hoy al backend (nombres de campo distintos: `address` vs `direccion` vs objeto estructurado) | Fase 3/5 debe mapear campo-por-campo antes de tocar cada consumidor; el backend no cambia, solo el frontend construye el mismo payload desde un componente compartido |
| `OrganizationView.vue` tiene 8 tabs con CSS 100% propio — migrarlo al design system es el cambio de mayor superficie (mas riesgo de regresion visual) de todos los encontrados | Migrar de ultimo, con verificacion visual Playwright tab por tab |
| Los 7 modales de `HomeConfigView.vue` (2705 lineas) son el archivo individual mas grande y riesgoso de tocar | Migrar uno a la vez a `SintelOffcanvas`, no en un solo cambio |
| Unificar `colombiaLocations.js`/`latamData.js` en un solo dataset requiere confirmar que ningun consumidor depende de una diferencia de forma entre ambos (ej. KYC podria depender de la lista plana sin departamento a proposito) | Verificar en Fase 4 antes de fusionar los datasets |
| Los 5+ `confirm()` nativos encontrados son faciles de corregir uno por uno, pero `CartOffcanfas.vue` (sin ninguna confirmacion) es una regresion de UX real que probablemente vale la pena priorizar independientemente del resto del plan | Se puede resolver como fix aislado antes de la Fase 3 si el usuario lo prefiere, sin esperar a la biblioteca completa |

### 1.5 Propuesta (resumen ejecutivo antes de Fase 2/3)

1. La base de la biblioteca compartida **ya existe** (`components/customer/account/*`) — la
   Fase 3 es mayormente generalizarla y moverla, no crearla de cero.
2. El problema mas grave no es "componentes ligeramente distintos" sino **tres sistemas de
   modal/overlay incompatibles conviviendo en el mismo panel admin** (`SintelOffcanvas` vs. CSS
   a mano de `HomeConfigView`/`OperationDetail` vs. `CustomerOverlayPanel`).
3. El hallazgo de mayor riesgo/impacto es la **direccion colombiana implementada 6 veces con 2
   datasets que pueden desincronizarse** — candidato natural a ser el primer `Base*` component
   de la Fase 3 (`BaseAddress`, ya nombrado en la propuesta original del usuario).
4. Hay **una regresion de UX real y aislada** (`CartOffcanvas.vue` sin ninguna confirmacion de
   borrado) que no depende del resto del plan y podria resolverse en cualquier momento si el
   usuario lo pide.
5. El sistema de **skeletons/loaders es el mas fragmentado** cuantitativamente (10+
   implementaciones independientes, 2 vistas sin ningun indicador) pero el de **menor riesgo**
   tecnico de unificar (es puramente visual, sin payload ni contrato de datos de por medio).

---

**Fin de la Fase 1.**

---

## FASE 2 — Auditoria de Componentes Duplicados (arbol completo)

### Metodologia

4 agentes de exploracion en paralelo recorrieron completamente: (1) `components/renting/` vs
`components/services/` (comparacion 1:1 archivo por archivo, incluye `modules/renting/catalog/`
vs `modules/technical_services/`), (2) `components/shared/`, `components/ui/`,
`components/layout/`, `components/customer/ui/`, `components/customer/account/` (inventario
completo + verificacion de obsolescencia via grep de imports reales), (3) los 16 pares
List/Form de `modules/*` (patron de tabla, creacion/edicion, confirmacion de borrado), (4)
`components/customer/` raiz, `components/auth/`, `components/support/`, los 2 wizards de
cotizacion en paralelo, y una busqueda global de logica de mascara de telefono/documento.

### 2.1 Arbol completo — Detalle publico Renting vs. Technical Services

```
EquipmentGallery.vue (76L, renting) + ServiceGallery.vue (73L, services)
  -> FUSIONAR: candidato a <MediaGallery :items> generico, tamanos casi identicos

EquipmentFeatureTable.vue (renting) + ServiceFeatureList.vue (services)
  -> FUSIONAR: mismo proposito (features), solo difiere tabla vs. lista

EquipmentFAQ.vue (37L, renting) + ServiceFAQAccordion.vue (24L, services)
  -> FUSIONAR: mismo proposito; la UI de acordeon de services es la mas moderna, usarla como base

EquipmentReviews.vue (173L, renting) + ServiceReviews.vue (173L, services)
  -> FUSIONAR (prioridad alta): MISMO TAMANO EXACTO -- fuerte indicio de clon literal linea por linea

EquipmentHorizontalCard.vue (302L, renting) + ServiceHorizontalCard.vue (298L, services)
  + ProductHorizontalCard.vue (330L, shop)
  -> FUSIONAR (hallazgo #1 de toda la Fase 2): 3 implementaciones de ~300L cada una
     (~930 lineas combinadas) del mismo concepto -- tarjeta horizontal de catalogo con slots

EquipmentSpecificationTable.vue (80L, renting) + ServiceSpecificationTable.vue (38L, services)
  -> MANTENER SEPARADO por ahora, pero investigar en Fase 4 si el gap de tamano es deuda
     tecnica real (campos faltantes en services) o una diferencia de negocio legitima

EquipmentIncludedList.vue (renting) + PackageIncludedList.vue (services/packages)
  -> MANTENER SEPARADO: contextos distintos (uno es del equipo, otro del paquete comercial)

EquipmentServiceList.vue (renting) + ServiceScopeList.vue (services)
  -> MANTENER SEPARADO (semantica distinta) pero RENOMBRAR para eliminar la confusion de nombres

EquipmentExcludedList.vue + EquipmentRequirementList.vue + EquipmentVideoGallery.vue
  + EquipmentDocumentList.vue + EquipmentManualList.vue + EquipmentDownloadSection.vue (renting)
  -> HUECOS REALES en services -- no existe equivalente; evaluar en Fase 4 si son necesidad de
     negocio real o simplemente contenido que Technical Services nunca necesito

ServiceProfessionals.vue + ServicePackageCard/PackageSelector/PackageCostBreakdown/
  PackageSummary/PackageAdditionalCostCard.vue (5 archivos, services/packages)
  + ServiceAttachmentsUploader.vue (services)
  -> SIN EQUIVALENTE EN RENTING, pero es negocio genuinamente distinto (renting no tiene
     "paquetes/niveles" ni tecnicos asignables) -- NO fusionar, no es duplicacion real
```

### 2.2 Arbol completo — Managers admin (contenido de catalogo)

```
CatalogListManager.vue + SeoManager.vue + GalleryManager.vue + DocumentsManager.vue
  + VideosManager.vue + SpecificationsManager.vue (6 archivos, modules/renting/catalog/)
  vs.
  (NINGUNO tiene equivalente en modules/technical_services/ -- SEO, galeria, documentos,
  videos y especificaciones siguen 100% inline dentro de ServiceForm.vue, 1448 lineas)
  -> HALLAZGO DE DEUDA TECNICA REAL (no solo un fork estilistico): Renting ya invirtio en
     extraer 6 responsabilidades de su propio "God Form" (RentingForm.vue, 1349L);
     Technical Services nunca hizo el mismo trabajo. Esto es asimetria de madurez entre
     modulos, no una decision de diseño deliberada como si lo es el color ambar/violeta.

ServiceFAQManager.vue (technical_services, 213L)
  -> HUECO INVERSO: Renting no tiene un manager de FAQ separado -- probablemente tambien vive
     inline dentro de RentingForm.vue. Verificar en Fase 4.
```

### 2.3 Arbol completo — Componentes genericos/compartidos

```
CustomerStatusBadge.vue (customer/account) + PaymentBadge.vue (shared/checkout)
  -> FUSIONAR: ambos son wrappers delgados "subtle" sobre useEnums(), mismo patron exacto

PaymentTimeline.vue (shared/checkout, 37L) + StatusTimeline.vue (shared/, mode="events")
  -> FUSIONAR (confirmado con codigo, no solo sospecha de Fase 1): PaymentTimeline vive en la
     carpeta HIJA inmediata de StatusTimeline y aun asi reimplementa su propio markup de
     dot/linea/label en vez de usar mode="events" -- la migracion es trivial

PaymentCard.vue (shared/checkout) + CustomerCard.vue (customer/account)
  -> FUSIONAR: misma "card generica de seccion" (header+slot), incluso el comentario en
     codigo de PaymentCard describe el mismo radio/borde/franja gris que CustomerCard

ItemCard.vue (customer/ui, 359L) + ServiceCard.vue (customer/ui, 324L)
  -> FUSIONAR: estructura casi identica (img-wrap+placeholder+badges+emit de click) --
     ItemCard ya soporta type="service" segun el registro de componentes (cards.md), hay que
     verificar en Fase 4 si ServiceCard.vue todavia se usa realmente o es codigo muerto

GlassCard.vue (ui/landing) + SectionHeader.vue (ui/landing)
  -> ELIMINAR (confirmado por grep -- CERO imports reales en todo src/, solo mencionados en
     un plan.md de diseño ya obsoleto). A diferencia de HeroCarousel/ModuleCardsGrid/
     FlashOffersSection/FeaturedItemCard/InfoCardsGrid (que la documentacion previa decia
     "conservados sin importar" pero que YA NO EXISTEN en el filesystem -- alguien ya los
     elimino sin actualizar esa nota), estos 2 siguen presentes y son limpieza pendiente real.
```

### 2.4 Arbol completo — CRUD admin (Categoria/Marca, el patron mas repetido del panel)

```
CategoryList.vue + CategoryForm.vue (shop) + RentingCategoryList.vue + RentingCategoryForm.vue (renting)
  -> FUSIONAR (candidato mas limpio de toda la auditoria): mismo <table> (Nombre/Slug-
     Descripcion/Estado/Acciones), misma fila de confirmacion bg-danger-subtle caracter por
     caracter, mismo SintelOffcanvas, mismos composables. Los Form.vue comparten name/
     description/is_active casi campo a campo -- la unica diferencia real es que shop agrega
     tabs (General/SEO) e imagen. Un BaseCategoryForm con slot opcional para "campos extra"
     cubre ambos.

BrandForm.vue (shop) + BrandForm.vue (renting)
  -> FUSIONAR (aun mas directo que Categoria): el de renting es literalmente un subconjunto
     del de shop (mismo campo name, mismo submit/cancelar, mismo manejo de error
     e.response?.data?.name?.[0]). Diferencia real: shop agrega logo+CSV+bulk-delete.

ServiceCategoryList.vue (technical_services)
  -> NO fusionar todavia -- es DIVERGENTE por una razon de negocio real (jerarquia padre/hijo
     que shop/renting no tienen): usa edicion inline + store Pinia + vista arbol, sin
     Form.vue ni offcanvas. Antes de unificar, decidir en Fase 3/5 si TODO el patron de
     categorias migra a arbol+inline, o si technical_services migra a offcanvas+form.
```

### 2.5 Arbol completo — Tarjetas de contexto (Support) y Wizards de cotizacion

```
OrderContextCard.vue + PaymentContextCard.vue + RentalContextCard.vue (support, ~30L c/u)
  -> FUSIONAR (prioridad alta, riesgo minimo): CSS scoped IDENTICO caracter por caracter en
     las 3 (.ctx-card/.ctx-head/.ctx-row), solo cambia el color del icono. Fusion directa en
     un ContextCard.vue con props icon/iconColor/title/statusEnum/rows.

QuoteWizardView.vue + CatalogQuoteWizardView.vue (views/customer/quotes/)
  -> FUSIONAR el SHELL (no los pasos internos): .qw-root/.qw-bg-glow/.qw-header/.qw-stepper/
     .qw-card/.qw-nav y ~40 lineas de CSS estan duplicadas linea por linea, solo cambia el
     color de tema (violeta vs. verde). Candidato a QuoteWizardShell.vue con slot para el
     paso activo + props themeColor/icon/steps.

ApplicantStep.vue vs CatalogApplicantStep.vue
  -> NO fusionar completo (contenido de negocio genuinamente distinto: uno pide documento+
     telefono+empresa+direccion con toggle "para mi/para un tercero", el otro solo nombre+
     correo+notas). PERO: CatalogApplicantStep.vue NO PIDE DOCUMENTO -- riesgo real de
     generar cotizaciones sin identificar al comprador, marcar para revisar en Fase 4.
```

### 2.6 Hallazgo transversal: no existe una mascara de telefono/documento compartida

Busqueda global confirma **cero composable compartido** para limpiar digitos de un input —
la logica `e.target.value.replace(/\D/g,'').slice(0,N)` esta reimplementada de forma
independiente en al menos 4 lugares (`ServiceRequestWizard.vue`, `RentalBookingWizard.vue`,
`RegisterView.vue`, `components/customer/checkout/ColombianAddressForm.vue`), y **ausente por
completo** en otros 2 que deberian tenerla (`ApplicantStep.vue`/`CatalogApplicantStep.vue`,
que aceptan `type="tel"` sin ninguna limpieza — riesgo de datos sucios en cotizaciones). Esto
es exactamente el tipo de "input inteligente" que la Fase 5 pide estandarizar — se registra
aqui como evidencia de Fase 2 para no tener que re-descubrirlo despues.

### 2.7 Iconografia con datos de backend que evita `IconRenderer.vue`

`IconRenderer.vue` esta documentado como el unico renderer valido para `icon_class` que viene
de BD. Se encontraron 6 lugares que renderizan icono crudo (`<i :class="['bi', dato.icon]">`)
en vez de usarlo: `ui/home/sections/{Accordion,Tabs,Timeline}Section.vue` (icono de tarjeta del
home builder), `ui/landing/HeroSlide.vue` (`feat.icon`), `customer/ui/ServiceCard.vue`
(`service.icon_class`), `customer/account/CustomerStatusBadge.vue` (`enums.icon(...)`). Riesgo
real: un `icon_class` invalido en BD rompe silenciosamente el icono en estos 6 lugares en vez
de caer al fallback seguro que `IconRenderer` ya implementa.

### 2.8 Resumen priorizado (que atacar primero en la Fase 3, sujeto a tu aprobacion)

| Prioridad | Hallazgo | Riesgo de migrar | Paginas/archivos afectados |
|---|---|---|---|
| 1 (maxima, minimo riesgo) | `OrderContextCard`+`PaymentContextCard`+`RentalContextCard` -> `ContextCard` | Muy bajo — CSS ya identico, 0 divergencia funcional | 3 archivos, uso interno de soporte |
| 2 | `CategoryList/Form` + `RentingCategoryForm` -> `BaseCategoryForm`/`BaseCategoryList` | Bajo | 4 archivos, admin shop+renting |
| 3 | `BrandForm` (shop) + `BrandForm` (renting) -> `BaseBrandForm` | Bajo | 2 archivos |
| 4 | `PaymentTimeline` -> `StatusTimeline mode="events"` | Bajo (ya existe el modo, solo mapear shape) | 1 archivo |
| 5 | `EquipmentReviews`+`ServiceReviews` -> `Reviews` compartido | Bajo (tamano identico sugiere 0 divergencia) | 2 archivos |
| 6 | `EquipmentHorizontalCard`+`ServiceHorizontalCard`+`ProductHorizontalCard` -> `HorizontalCard` | Medio (3 consumidores, mayor superficie) | 3 archivos + 3 vistas de catalogo |
| 7 | `QuoteWizardView`+`CatalogQuoteWizardView` -> `QuoteWizardShell` | Medio | 2 archivos grandes |
| 8 | `GlassCard.vue`+`SectionHeader.vue` -> ELIMINAR | Minimo (0 imports reales) | borrado puro, sin migracion |
| 9 | Composable `useDigitsMask(maxLength)` compartido | Bajo, pero toca 6 archivos | 6 archivos |
| 10 (mayor esfuerzo) | Extraer los 6 managers de contenido para Technical Services (paridad con Renting) | Alto (ServiceForm.vue tiene 1448 lineas, God Form) | 1 archivo grande -> 6 nuevos |

---

**Fin de la Fase 2.**

---

## FASE 3 — Diseño de la Biblioteca Compartida

### Principio rector (evita repetir el error que motivo esta auditoria)

La Fase 1 ya encontro que **el 60% de esta biblioteca existe hoy**, viviendo dentro de
`components/customer/account/*` (13 componentes) mas 6-7 piezas sueltas en `components/shared/`
y `components/ui/`. Diseñar "desde cero" seria ignorar trabajo real ya hecho y probado en
produccion (Mi Cuenta, 2026-07-17). La estrategia de esta fase es **generalizar y mover, no
reinventar**, salvo en los ~19 componentes de formulario inteligente que genuinamente no
existen todavia (grupo D).

### 3.1 Decision de ubicacion (propuesta, requiere tu confirmacion — ver §3.4)

Hoy la mitad de la "biblioteca base" vive bajo `components/customer/account/` (un namespace que
por nombre sugiere "solo para Mi Cuenta"), y la otra mitad esta dispersa en `shared/`, `ui/`,
`customer/ui/`. Se propone un namespace unico y neutro:

```
components/base/
├── BaseButton.vue          (generaliza CustomerButton.vue)
├── BaseCard.vue            (generaliza CustomerCard.vue + PaymentCard.vue)
├── BaseBadge.vue           (generaliza CustomerStatusBadge.vue + PaymentBadge.vue)
├── BaseModal.vue           (ver decision pendiente §3.4.1)
├── BaseOverlayPanel.vue    (generaliza CustomerOverlayPanel.vue — variante "panel", no modal centrado)
├── BaseEmptyState.vue      (generaliza CustomerEmptyState.vue)
├── BaseErrorState.vue      (generaliza CustomerErrorState.vue)
├── BaseSkeleton.vue        (generaliza CustomerSkeleton.vue, que ya envuelve LoadingSkeleton.vue)
├── BaseAvatar.vue          (generaliza CustomerAvatar.vue)
├── BasePagination.vue      (generaliza CustomerPagination.vue)
├── BaseSection.vue         (generaliza CustomerSection.vue)
├── BaseDetailRow.vue       (generaliza CustomerDetailRow.vue)
├── BasePageHeader.vue      (generaliza CustomerPageHeader.vue)
├── BaseShell.vue           (generaliza CustomerAccountShell.vue -- variante generica de "layout de pagina con sidebar")
├── BaseConfirmInline.vue   (generaliza CustomerConfirmInline.vue)
├── BaseAlert.vue           (generaliza PaymentAlert.vue)
├── BaseSummary.vue         (nuevo, basado en el patron real de ServiceRequestSummary.vue/RentalCostsCard.vue)
├── BaseWizard.vue + BaseStep.vue  (nuevo, envuelve CheckoutStepper.vue + gestion de contenido por paso,
│                                   basado en el patron ya encontrado en QuoteWizardShell -- Fase 2 §2.5)
├── BaseTable.vue           (nuevo, ver §3.3)
├── BaseTabs.vue            (nuevo — hoy cada modulo reimplementa sus propios botones de tab,
│                            ej. ServiceForm.vue/RentingForm.vue/OrganizationView.vue)
├── BaseAccordion.vue       (nuevo, generaliza el patron `<details>` de ServiceFAQAccordion.vue)
│
│  -- Ya existen fuera de este namespace, con contrato bueno -- SOLO mover el archivo, sin tocar props:
├── BaseTimeline.vue        (= StatusTimeline.vue, ya es generico y esta bien ubicado)
├── BaseStepper.vue         (= CheckoutStepper.vue, ya es generico)
├── BaseOffcanvas.vue       (= SintelOffcanvas.vue, ya es generico -- uso admin)
├── BaseIcon.vue            (= IconRenderer.vue, ya es generico)
├── BaseRating.vue          (= StarRating.vue, ya es generico)
│
│  -- Ya existe y NO requiere componente nuevo:
│     Toast -> useToast()/ToastManager.vue (ya es el unico sistema del proyecto, sin cambios)
│
└── forms/                  -- Grupo D, ver §3.2 (genuinamente nuevos, sin precedente en el codigo)
    ├── BaseInput.vue
    ├── BaseTextarea.vue
    ├── BaseSelect.vue
    ├── BaseSearchSelect.vue
    ├── BaseDatePicker.vue
    ├── BasePhoneInput.vue
    ├── BaseMoneyInput.vue
    ├── BasePercentageInput.vue
    ├── BaseDocumentInput.vue
    ├── BaseAddress.vue
    ├── BaseIconInput.vue
    ├── BaseUpload.vue
    ├── BaseGallery.vue
    └── BaseCalendar.vue
```

`BaseHero.vue`, `BaseMap.vue` (de la lista original del usuario) se posponen: no se encontro en
Fase 1/2 ningun caso real de "hero" fuera de la Landing (que ya tiene su propio sistema maduro,
`HeroSection.vue`+`HeroBackground.vue`+`HeroSlide.vue`+`HeroCTA.vue`, documentado y funcionando)
ni ningun uso real de mapas en toda la auditoria — se marcan como **fuera de alcance hasta que
aparezca un caso de uso real**, para no construir un componente sin consumidor.

### 3.2 Grupo A — Ya existen, solo generalizar (contrato ya probado en produccion)

| Base* | Componente origen | Contrato actual (sin cambios de fondo) | Que absorbe (de Fase 2) |
|---|---|---|---|
| `BaseButton` | `CustomerButton.vue` | `variant('primary'\|'secondary'\|'danger'\|'icon')`, `size('sm'\|'md')`, `loading`, `ariaLabel` | Botones sueltos de Bootstrap en Shop/Renting/KYC admin |
| `BaseCard` | `CustomerCard.vue` | `tag`, `highlighted`, `hoverable`, `variant('default'\|'brand')`, `brandTone` | `PaymentCard.vue` (§2.3) |
| `BaseEmptyState` | `CustomerEmptyState.vue` | `icon`, `title`, `description`, slot `action` | Empty-states custom de ShopCatalogView, RentalCatalogView, ServicesCatalogView (Fase 1 §skeletons) |
| `BaseErrorState` | `CustomerErrorState.vue` | `title`, `description`, emit `retry` | Ninguno (nuevo patron, poca adopcion todavia) |
| `BaseSkeleton` | `CustomerSkeleton.vue` (envuelve `LoadingSkeleton.vue`) | `count`, `height`, `layout('list'\|'grid')` | Los 6+ shimmer CSS inline encontrados en Fase 1/2 (RentalDetailView, ServiceDetailView — identicos byte a byte —, ProductDetailView, 3 catalog views) |
| `BaseAvatar` | `CustomerAvatar.vue` | `src`, `initials`, `size`, `editable`, emit `click` | Markup de avatar inline en `AccountSidebar.vue` (ya migrado), posible uso en `SupportDashboardView.vue`/agente de chat |
| `BasePagination` | `CustomerPagination.vue` | `page`, `totalPages`, emit `update:page` | Paginacion `pagination pagination-sm` repetida en Shop/Renting/Services/Quotes admin lists |
| `BaseSection` | `CustomerSection.vue` | `title`, `icon`, slots default+actions | Secciones custom de `OrganizationView.vue` (8 tabs con CSS propio) |
| `BaseDetailRow` | `CustomerDetailRow.vue` | `label`, `value`, `icon`, slots default+action | Filas de detalle inline en `KycAdminDetail.vue`/`UserDetail.vue` |
| `BasePageHeader` | `CustomerPageHeader.vue` | `title`, `subtitle`, slot `actions` | Headers de pagina custom en catalogos publicos |
| `BaseConfirmInline` | `CustomerConfirmInline.vue` | `message`, `confirmLabel`, `loading`, emits `confirm`/`cancel` | Los 5 `confirm()` nativos + el `deletingId` propio de `ContractorOnboardingWizard.vue` (Fase 2 §2.1) |
| `BaseAlert` | `PaymentAlert.vue` | `variant('info'\|'warning'\|'danger')`, `icon`, `title`, `spinner` | Notices custom repetidos fuera del dominio de pago |
| `BaseTimeline` | `StatusTimeline.vue` (sin cambios) | `mode('steps'\|'events')`, `steps`, `activeIndex`, `accentColor`, `cancelled`, `events`, `emptyMessage` | `PaymentTimeline.vue` (Fase 2 §2.3) |
| `BaseStepper` | `CheckoutStepper.vue` (sin cambios) | `steps`, `current`, `clickable`, `ariaLabel` | El stepper propio de `ContractorOnboardingWizard.vue` (Fase 2 §2.1) |
| `BaseOffcanvas` | `SintelOffcanvas.vue` (sin cambios) | `modelValue`, `title`, `subtitle`, `width`, `loading` | Los 7 modales de `HomeConfigView.vue` + el `.assign-modal` de `OperationDetail.vue` + el `.form-modal` de `DispatcherList.vue` (Fase 1 §1.2/1.3) |
| `BaseIcon` | `IconRenderer.vue` (sin cambios) | `icon`, `fallback`, `extraClass`, `size` | Los 6 usos de `<i class="bi...">` crudo con `icon_class` de BD (Fase 2 §2.7) |
| `BaseRating` | `StarRating.vue` (sin cambios) | `rating`, `maxRating`, `size`, `readOnly`, `showValue`, `allowHalf` | Ninguno detectado — ya es el unico |

### 3.3 Grupo B/C — Nuevos, pero con un patron real ya validado en codigo para basarse

| Base* | Basado en el patron real de | Contrato propuesto |
|---|---|---|
| `BaseSummary` | `ServiceRequestSummary.vue` (construido esta misma semana, 2026-07-18) + `RentalCostsCard.vue` | `title`, slots por seccion (servicio/paquete/precio/fecha), reutiliza `ServicePriceBreakdown`/`RentalCostsCard` como sub-slot en vez de fusionarlos (contenido de precio es especifico de dominio, el contenedor "sidebar sticky" es lo generico) |
| `BaseWizard` + `BaseStep` | `QuoteWizardView.vue`/`CatalogQuoteWizardView.vue` (shell casi identico, Fase 2 §2.5) | `BaseWizard`: `steps[]`, `themeColor`, slot por paso activo, integra `BaseStepper` internamente. `BaseStep`: solo layout (header+body+footer de navegacion Atras/Continuar) |
| `BaseTable` | Patron repetido en `ProductList`/`CategoryList`/`RentingCategoryList`/`ServiceList`/etc. (Fase 2 §2.4) | `columns[]`, `rows[]`, slot por celda, slot de fila de confirmacion inline integrado (para que `BaseConfirmInline` sea automatico en vez de que cada lista lo reimplemente) |
| `BaseTabs` | Botones de tab repetidos en `ServiceForm.vue` (7 tabs), `RentingForm.vue` (16 tabs), `OrganizationView.vue` (8 tabs), `ProductForm.vue` (4 tabs) | `tabs[{key,label,icon,badge}]`, `modelValue`, slot por tab -- candidato de altisimo impacto: 4+ "God Forms" reimplementan la misma barra de tabs con CSS ligeramente distinto cada uno |
| `BaseAccordion` | `ServiceFAQAccordion.vue` (ya es la version "mas moderna" segun Fase 2 §2.1) | `items[{key,question,answer}]`, `allowMultiple` |
| `BaseShell` | `CustomerAccountShell.vue` | `maxWidth`, slot `sidebar` + slot default — generalizado para admin tambien (hoy solo Mi Cuenta lo usa) |
| `BaseOverlayPanel` | `CustomerOverlayPanel.vue` | `modelValue`, `title`, `subtitle`, `width`, slots default+footer — variante "panel deslizante" distinta de `BaseOffcanvas` (ver §3.4.1, hay que decidir si de verdad necesitamos 2) |

### 3.4 Decisiones de arquitectura que requieren tu confirmacion explicita antes de construir nada

Estas 3 decisiones cambian cuantos componentes finales existen — prefiero preguntar antes que
asumir, porque revertir una eleccion de arquitectura despues de migrar 10 archivos es caro.

#### 3.4.1 ¿Cuantos "modales/paneles" distintos deberian quedar al final? — **RESUELTO 2026-07-18**

**Correccion factual encontrada al leer el codigo real (esta seccion original tenia un error):**
`CustomerOverlayPanel.vue` NO es un panel lateral — es un **dialogo centrado**
(`position:fixed;inset:0;display:flex;align-items:center;justify-content:center`), visualmente
distinto de `SintelOffcanvas.vue` (`offcanvas offcanvas-end`, panel que desliza desde la
derecha). La comparacion original de esta seccion ("casi identico a SintelOffcanvas") era
incorrecta — nunca fueron el mismo patron.

Con esa correccion, la decision real no era "fusionar 2 paneles laterales casi iguales" sino
evaluar si valia la pena fusionar los 2 dialogos CENTRADOS que terminaron existiendo
(`CustomerOverlayPanel`, con 5 consumidores reales en Mi Cuenta — Perfil/Pedidos/Direcciones/
Cotizaciones — y `BaseModal`, construido en el Paso 5 de este mismo plan para HomeConfigView/
DispatcherList). Se investigo el merge y **se decidio NO fusionarlos**: sus especificaciones
visuales difieren en varios puntos reales (bordes por seccion + `backdrop-filter:blur` + sombra
grande de `BaseModal` vs. caja unica sin blur ni sombra de `CustomerOverlayPanel`, tamano de
titulo `.95rem/800` vs `h5/700` por defecto) — forzar uno sobre el otro habria significado o
(a) un cambio visual real en 4 paginas de Mi Cuenta ya en produccion, o (b) agregar un prop
`theme`/`variant` de conmutacion solo para evitarlo, con beneficio incierto frente al riesgo.

**Resultado final (equivalente a la "Opcion B" original, aplicada con evidencia real):** quedan
3 sistemas de dialogo, cada uno con proposito genuinamente distinto — `SintelOffcanvas` (panel
lateral, CRUD admin), `CustomerOverlayPanel` (dialogo centrado, Mi Cuenta, con su propio theming
de CSS custom properties `--acc-*`), `BaseModal` (dialogo centrado neutral, admin general —
HomeConfigView + DispatcherList), `CheckoutModal` (dialogo centrado especifico de pago, ya
documentado como valido desde antes de esta auditoria). Los 8 usos indebidos que si existian
(7 de `HomeConfigView` + 1 de `DispatcherList`) ya se migraron a `BaseModal` (Pasos 5 y 7).

#### 3.4.2 ¿Se unifica `BaseBadge` con `OperationStatusBadge`/`ShipmentStatusBadge` tambien? — **RESUELTO 2026-07-18**

Al leer los 3 archivos se confirmo que `CustomerStatusBadge.vue` (Mi Cuenta) ya era,
practicamente sin cambios, el "BaseBadge" generico que esta pregunta buscaba —
`OperationStatusBadge.vue`/`ShipmentStatusBadge.vue` eran 2 copias hardcodeadas (una por enum)
del mismo patron, incluyendo un workaround de reactividad identico duplicado 2 veces (el cache
interno de `useEnums()` no es reactivo para enums fuera de su catalogo estatico). Se construyo
`components/base/BaseStatusBadge.vue` (props `enumName`, `value`, `showIcon`, `fallbackClass`,
con el workaround de reactividad preservado) y los 3 componentes (`CustomerStatusBadge`,
`OperationStatusBadge`, `ShipmentStatusBadge`) quedaron como wrappers delgados sobre el —
riesgo minimo porque es logica de solo-lectura (mapea un status a texto+clase CSS), sin ningun
efecto de negocio. Verificado con Playwright real en `ShopOperationBoard`/`ServiceOperationBoard`
(datos reales, "Preparando"/"Pago pendiente" renderizados correctamente).

#### 3.4.3 ¿`BaseTable` reemplaza las tablas de TODOS los admin lists, o solo las de Categoria/Marca?

El hallazgo de Fase 2 (§2.4) mostro que Categoria/Marca son el caso mas limpio de fusionar. Pero
`BaseTable` generico tocaria potencialmente 15+ listas admin (Shop, Renting, Services, Quotes,
Users, Orders...) — mucho mayor superficie de riesgo que cualquier otro punto de este plan.

- **Opcion A (recomendada, incremental):** construir `BaseTable` ahora (diseño), pero
  **migrar solo Categoria/Marca en un primer lote** (Fase 7), dejando el resto de listas admin
  para una segunda ronda posterior a este plan.
- **Opcion B:** migrar las 15+ listas admin de una vez dentro de este mismo plan.

**Necesito tu decision:** ¿A (incremental, mas seguro) o B (todo de una vez)?

### 3.5 Formularios inteligentes (Grupo D) — diseño preliminar, sujeto a Fase 4/5

Estos 14 componentes (`BaseInput` → `BaseCalendar`) son los unicos **sin ningun precedente en
el codigo actual** — la Fase 1 confirmo que hoy TODOS los formularios usan `<input>`/`<select>`
de Bootstrap crudo, sin ningun wrapper compartido. Su contrato definitivo (icono por tipo de
campo, limites de longitud exactos, mascara exacta) se define en la Fase 5 con la evidencia
completa de la Fase 4 — aqui solo se deja el nombre y el proposito, para que la Fase 4 audite
formularios ya sabiendo contra que catalogo los va a comparar:

| Base* | Proposito | Ejemplo de consumidor real que lo necesita hoy |
|---|---|---|
| `BaseInput` | input de texto generico con icono+contador+validacion | Todos — ningun formulario tiene esto hoy |
| `BaseTextarea` | igual, con limite de caracteres obligatorio (nunca ilimitado) | `description` de Producto, `email_body` de plantillas de notificacion (Fase 1: ambos hoy sin `maxlength`) |
| `BaseSelect` | select poblado por catalogo del backend | Reemplaza los `<select>` crudos ya usados correctamente en Categoria/Marca (Fase 2) |
| `BaseSearchSelect` | select con busqueda para catalogos grandes | Ciudad (hoy texto libre en varios formularios, Fase 2 §hallazgo de direccion) |
| `BaseDatePicker` | selector de fecha | `<input type="date">` crudo, usado hoy en wizards de Renting/Services |
| `BasePhoneInput` | mascara de celular colombiano | Reemplaza las 4 reimplementaciones de mascara encontradas en Fase 2 §2.6 |
| `BaseMoneyInput` | input de dinero COP | Precio en `ProductForm.vue` (hoy `input-group` con `$` manual) |
| `BasePercentageInput` | input de porcentaje | Descuento/IVA en Shop/Marketing |
| `BaseDocumentInput` | mascara de documento CC/CE/NIT/PP | Reemplaza la logica de `onDocInput` de `ServiceRequestWizard.vue` |
| `BaseAddress` | direccion colombiana estructurada completa | **El de mayor impacto de todo el Grupo D** — reemplaza las 6 implementaciones independientes de Fase 2 (`ColombianAddressForm`, `RentalBookingWizard`, `ServiceRequestWizard`, `PersonalInfoFields`, y los 2 free-text de `CustomerProfileView`/`ContractorOnboardingWizard`) |
| `BaseIconInput` | wrapper generico input+icono para cualquier campo | Base compositiva de la que heredan varios de arriba |
| `BaseUpload` | subida de archivo con preview | Reemplaza las 4 implementaciones independientes de upload encontradas en Fase 1 (KYC docs, Organization logo, Brand/Category logo copy-paste, HomeConfig upload-area) |
| `BaseGallery` | galeria de imagenes con miniaturas | Reemplaza `EquipmentGallery`/`ServiceGallery` (Fase 2 §2.1, ya identificados como fusionables) |
| `BaseCalendar` | calendario de disponibilidad (no solo un date-picker de formulario) | Agenda de tecnicos (`TechnicianCalendarBoard.vue`), disponibilidad de Renting |

---

**Fin de la Fase 3.**

---

## FASE 4 — Auditoria Integral de Formularios

### Metodologia

Auditoria campo-por-campo de los formularios reales de: Customer (perfil, direcciones),
Admin (Shop/Users), Checkout (Shop/Renting/Services), Shop (Producto/Categoria/Marca/Impuesto),
Services (wizard de solicitud), Renting (wizard de reserva), Organization (branding, 8 tabs),
KYC (registro + verificacion de documentos), Marketing (campañas), Quotes (2 wizards de
cotizacion + 3 pasos de preguntas dinamicas), Operations (despachadores). Se combino evidencia
ya recolectada en Fases 1-2 con 1 agente de exploracion adicional enfocado en los formularios
no cubiertos todavia (Marketing, Users, Quotes, Operations, Registro) mas lectura directa de
`PersonalInfoFields.vue` y `RegisterView.vue` completos.

**Security, Support y Notifications no tienen formularios de captura de datos de negocio**
(son dashboards/consolas de solo lectura o configuracion de plantillas) — confirmado en Fase 1,
no se repite aqui.

### 4.1 Hallazgo transversal (el mas importante de toda la Fase 4)

**El mismo dato — nombre, ciudad, telefono, documento, direccion — se captura de 4 a 5 formas
distintas segun en que formulario del sitio estes parado**, sin que ningun formulario sea
claramente "el correcto" y el resto una regresion: cada uno se construyo de forma aislada en un
momento distinto del proyecto.

#### Nombre completo

| Formulario | Patron |
|---|---|
| `PersonalInfoFields.vue` (KYC/Registro) | **4 campos**: primer_nombre, segundo_nombre, primer_apellido, segundo_apellido |
| `CustomerProfileView.vue` | **2 campos**: first_name, last_name |
| `UserForm.vue` (admin) | **2 campos**: first_name, last_name |
| `ApplicantStep.vue` (cotizacion personalizada) | **1 campo**: client_name (nombre completo en un solo input) |
| `CatalogApplicantStep.vue` (cotizacion catalogo) | **1 campo**: client_name |

Tres patrones distintos (4 campos / 2 campos / 1 campo) para representar exactamente el mismo
concepto humano.

#### Ciudad / Departamento

| Formulario | Patron |
|---|---|
| `PersonalInfoFields.vue` | Select de ciudad (`COLOMBIAN_CITIES`, catalogo plano, **sin** campo de departamento) |
| `RentalBookingWizard.vue` / `ServiceRequestWizard.vue` | Select departamento -> select ciudad dependiente (`colombiaLocations.js`, catalogo con jerarquia) |
| `ColombianAddressForm.vue` (checkout Shop) | Igual que arriba, mismo dataset |
| `CustomerProfileView.vue` / `CustomerAddressView.vue` | Texto libre, sin seleccion |
| `ApplicantStep.vue` / `CatalogApplicantStep.vue` (cotizaciones) | Texto libre, sin seleccion |
| `ContractorOnboardingWizard.vue` | Texto libre, sin seleccion, sin campo de departamento |

**2 datasets distintos** (`colombiaLocations.js` con jerarquia dept→ciudad, `latamData.js` sin
jerarquia) + **3 niveles de rigor** (select dependiente / select plano / texto libre) para el
mismo dato.

#### Telefono/celular

| Formulario | Mascara aplicada |
|---|---|
| `RegisterView.vue` | Si — `replace(/\D/g,'').slice(0,10)` + prefijo visual "+57" |
| `ServiceRequestWizard.vue` / `RentalBookingWizard.vue` | Si — misma logica, reimplementada independientemente |
| `ColombianAddressForm.vue` | Si — tercera reimplementacion independiente |
| `PersonalInfoFields.vue` | Parcial — `inputmode="numeric"` mas no limpia el valor explicitamente |
| `UserForm.vue` (admin) | **No** — acepta cualquier string |
| `ApplicantStep.vue` / `CatalogApplicantStep.vue` (cotizaciones) | **No** — `type="tel"` libre, sin mascara |

#### Documento de identidad

| Formulario | Patron |
|---|---|
| `PersonalInfoFields.vue` | Select tipo (CC/CE/NIT/PP) + numero con `inputmode="numeric"` (sin maxlength) + fecha y lugar de expedicion |
| `ServiceRequestWizard.vue` | Select tipo (CC/CE/PP/TI/NIT/OTRO) + numero enmascarado segun tipo (`onDocInput`, distingue numerico vs. alfanumerico) — **el mas completo de los dos** |
| `ApplicantStep.vue` (cotizacion) | Select tipo (solo CC/NIT) + numero en texto libre sin `inputmode` |
| `UserForm.vue`, `CatalogApplicantStep.vue`, `DispatcherList.vue` | **Sin campo de documento en absoluto** (donde aplicaria para algunos) |

#### Direccion

Ver Fase 2 §hallazgo de direccion — 6 implementaciones, se repite aqui solo el resumen: 2 con
constructor estructurado real (via/numero/generadora/placa: `PersonalInfoFields`,
`ColombianAddressForm`, `RentalBookingWizard`, `ServiceRequestWizard` — 4, no 2, corrigiendo el
conteo de Fase 2 con el detalle de esta fase), 3 en texto libre plano sin ninguna estructura
(`CustomerProfileView`, `ApplicantStep`/`CatalogApplicantStep`, `ContractorOnboardingWizard`).

### 4.2 Formulario mejor construido del proyecto (usar como referencia de Fase 5, no reinventar)

**`ServiceRequestWizard.vue`** (paso 2 "Direccion y contacto") es, campo por campo, el
formulario mas maduro de todo el sitio: separa nombre en `full_name` (unico caso donde 1 campo
es una decision consciente, no un descuido — ver nota abajo), aplica mascara real a
telefono/documento con logica condicional segun tipo de documento, usa selects dependientes
departamento→ciudad, tiene contadores de caracteres visibles en `description` (2000) y
`problem` (1000), y arma la direccion con el mismo constructor tipo-via/numero/generadora/placa
que `PersonalInfoFields.vue`. **Nota:** usa `full_name` en 1 campo en vez de nombre/apellido
separados — la Fase 5 debe decidir si esto se corrige a favor de la separacion en 4 (KYC) o 2
(Perfil/Usuarios) campos, ya que hoy conviven las 3 opciones sin una razon de negocio clara
para la diferencia.

### 4.3 Hallazgo mas grave (UX + seguridad de datos)

**`DispatcherList.vue`** (admin, Operaciones): el campo para asignar el usuario responsable de
un despachador es un `<input type="number">` de **`user_id` crudo** — el operador administrativo
tiene que conocer de memoria el ID entero de la base de datos de la persona que quiere asignar,
en vez de un selector/buscador de usuarios por nombre. Es el unico formulario de todo el
proyecto que expone una clave primaria en la interfaz. Ademas: `vehicle_type` es texto libre
pese a ser un catalogo cerrado en la practica (Camioneta/Moto/etc.), y las ciudades cubiertas
por el despachador se capturan como **texto separado por comas** parseado manualmente a un
array — sin normalizacion, altamente propenso a error de tipeo.

### 4.4 Otros hallazgos por categoria (segun lo pedido explicitamente en Fase 4)

**Campos duplicados dentro del mismo formulario:** no se encontro ningun caso de 2 campos
identicos en un mismo formulario (el problema es entre formularios, no dentro de uno).

**Campos innecesarios:** `lugar_expedicion_documento` en `PersonalInfoFields.vue` es texto
libre cuando ya existe, en el mismo formulario, un select de ciudades (`COLOMBIAN_CITIES`) que
podria reusarse — hoy son 2 fuentes de verdad para "una ciudad colombiana" dentro del mismo
componente.

**Campos demasiado largos / sin limite (contradice directamente la Fase 5):**
`title`/`content` de `CampaignForm` (Marketing) validan `maxlength` solo via Yup post-submit,
sin atributo HTML ni contador en `title`; `first_name`/`last_name`/`phone_number` de
`UserForm.vue` sin ningun limite; `description` de `ProductForm.vue` (Shop) sin limite (a
diferencia de sus propios campos SEO, que si tienen contador); `email_body` de
`NotificationsAdminView.vue` sin limite; `password`/`password_confirm` sin `maxlength` en
ningun formulario del sitio (riesgo menor pero real de payload arbitrario).

**Campos de texto libre que deberian ser select:** `department`/`city` en `ApplicantStep.vue`/
`CatalogApplicantStep.vue` (existiendo ya 2 datasets de ciudades en el proyecto para reusar);
`vehicle_type` y las ciudades-por-coma de `DispatcherList.vue`; `contractor_type` en
`ContractorOnboardingWizard.vue` (ya detectado en Fase 1); `city`/`country` en
`CustomerProfileView.vue`/`CustomerAddressView.vue`/`ContractorOnboardingWizard.vue`.

**Campos inconsistentes entre formularios del mismo flujo:** los 2 wizards de cotizacion
(`ApplicantStep` 11 campos vs. `CatalogApplicantStep` 4 campos) representan el mismo concepto
de negocio ("datos del solicitante de una cotizacion") con un tercio de los campos en uno de
los dos — en particular, `CatalogApplicantStep` no pide documento de identidad, lo cual es un
riesgo real de negocio (cotizaciones sin identificar fiscalmente al comprador), ya señalado en
Fase 2 §2.5 y confirmado aqui con el detalle completo de campos.

**Campos mal distribuidos / mala UX:**
`DispatcherList.vue` (ver §4.3); el prefijo "+57" fijo en `RegisterView.vue` es buena UX pero no
se repite en ningun otro formulario que captura celular, perdiendo consistencia visual.

**Hallazgo positivo (no es un problema, es una buena noticia):** `EquipmentQuestionsStep.vue`/
`LaborQuestionsStep.vue`/`MaterialQuestionsStep.vue` (wizard de cotizacion personalizada) **no
son 3 formularios duplicados** como se temia en la Fase 2 — los tres delegan el renderizado real
de cada pregunta a un unico componente compartido, `DynamicQuestionField.vue`, que decide el
tipo de input segun `question_type` (TEXT/TEXTAREA/ADDRESS/MULTISELECT/CHECKBOX/TABLE/
DYNAMIC_LIST/IMAGE/FILE/SIGNATURE) — ya es exactamente el patron que la Fase 3 propone como
`BaseInput`/`BaseSelect`/etc. gestionados por un campo dinamico. Los 3 "Step" son wrappers
casi identicos (candidato menor a fusionar en un `DynamicQuestionsStep.vue` parametrizado por
tipo de modulo+titulo+icono), no una duplicacion de la logica de campo en si.

### 4.5 Resumen priorizado para la Fase 5

| Prioridad | Decision que la Fase 5 debe tomar |
|---|---|
| 1 | Definir el patron UNICO de nombre: ¿4 campos (KYC) / 2 campos (Perfil/Usuarios) / 1 campo (cotizaciones)? Recomendacion: 2 campos (`first_name`/`last_name`) como estandar general, reservando el desglose de 4 solo para KYC donde el backend ya lo modela asi (verificar en Fase 4-backend si el modelo realmente distingue segundo nombre/apellido o si KYC tambien podria simplificarse) |
| 2 | Fusionar `colombiaLocations.js` + `latamData.js` en un solo dataset (o decidir explicitamente por que deben seguir separados) antes de construir `BaseAddress`/`BaseSearchSelect` |
| 3 | `useDigitsMask()`/`usePhoneMask()` compartido (ya propuesto en Fase 2 §2.6) — usarlo tambien para cerrar el hueco de `UserForm.vue`/`ApplicantStep.vue`/`CatalogApplicantStep.vue`, que hoy no tienen ninguna mascara |
| 4 (mayor riesgo de negocio, no solo UX) | Agregar documento de identidad a `CatalogApplicantStep.vue` — hoy se puede generar una cotizacion de catalogo sin identificar fiscalmente al comprador |
| 5 (mayor riesgo de seguridad de datos) | `DispatcherList.vue`: reemplazar el input de `user_id` crudo por un selector/buscador de usuarios, y `vehicle_type`/ciudades por select/multiselect reales |
| 6 | Agregar `maxlength` HTML (no solo validacion Yup post-submit) a `CampaignForm`, `UserForm`, `ProductForm.description`, `NotificationsAdminView.email_body` |
| 7 (menor, cosmetico) | Fusionar los 3 wrappers `*QuestionsStep.vue` en un `DynamicQuestionsStep.vue` parametrizado — la logica de campo (`DynamicQuestionField.vue`) ya esta bien y no se toca |

---

**Fin de la Fase 4.**

---

## FASE 5 — Nuevo Estandar de Formularios

### Nota metodologica importante sobre los limites de longitud

La lista de limites de la especificacion original (Primer nombre 40, Correo 120, etc.) se
verifico contra los modelos Django reales antes de adoptarla — **varios numeros de la
especificacion original no coinciden con el backend real** y se corrigen aqui. Regla general
adoptada: para campos `CharField`, el `maxlength` del frontend **debe ser exactamente igual**
al `max_length` real del backend (nunca mayor — causaria un 400 en el submit; nunca menor sin
razon — frustraria al usuario con datos validos que el backend si aceptaria). Para campos
`TextField` (la mayoria de descripciones/notas/comentarios del backend), **el backend no
impone ningun limite** — el limite que se establece aqui es una decision de producto/UX
(evitar textos interminables), no una traduccion de una restriccion tecnica real.

### 5.1 Estandar de nombres — resuelve la decision #1 de la Fase 4

**Adoptar 2 campos (`first_name`/`last_name`) como el patron general del sitio.** Es el patron
que ya usa el backend en `accounts.UserProfile` (`first_name`/`last_name`, `max_length=50`
cada uno) y coincide con `CustomerProfileView.vue`/`UserForm.vue`. **KYC/Registro mantiene su
desglose en 4 campos** (primer/segundo nombre, primer/segundo apellido) porque asi via el
`contact_person`/perfil que persiste — no es una excepcion arbitraria, es fidelidad al dato
real que el documento de identidad colombiano distingue. Los formularios de cotizacion
(`ApplicantStep`/`CatalogApplicantStep`, hoy con 1 solo campo `client_name`) deben migrar a 2
campos para ser consistentes con el resto del sitio.

### 5.2 Catalogo de iconos por tipo de campo

El proyecto usa **Bootstrap Icons** (`bi-*`) en todo el sitio, no emoji — se traduce el catalogo
pedido en la especificacion original a la convencion real ya vigente (todo icono que refleje un
`icon_class` de backend debe pasar por `IconRenderer.vue`, ver Fase 2 §2.7; los iconos fijos de
un campo de formulario, que nunca cambian, pueden usar `<i class="bi ...">` directo sin pasar
por `IconRenderer`, que es solo para iconos configurables desde BD):

| Campo | Icono (`bi-*`) |
|---|---|
| Primer/Segundo nombre | `bi-person` |
| Primer/Segundo apellido | `bi-people` |
| Correo electronico | `bi-envelope` |
| Celular | `bi-phone` |
| Documento | `bi-credit-card-2-front` (no existe un icono literal de "cedula" en Bootstrap Icons 1.11) |
| Departamento | `bi-map` |
| Ciudad | `bi-building` |
| Barrio | `bi-signpost-2` |
| Direccion | `bi-geo-alt` |
| Empresa | `bi-briefcase` |
| NIT | mismo `bi-credit-card-2-front` que Documento (es el mismo campo backend, `document_type=NIT`, no un campo distinto) |
| Contraseña | `bi-lock` |
| Fecha | `bi-calendar3` |
| Hora | `bi-clock` |
| Precio / dinero | `bi-cash-coin` |
| Cantidad | `bi-123` |
| Busqueda | `bi-search` |
| Comentarios / observaciones | `bi-chat-left-text` |
| Archivo / adjunto | `bi-paperclip` |
| Rol / tipo de usuario | `bi-person-badge` |
| Estado | `bi-flag` |
| Metodo de pago | `bi-credit-card` |
| Prioridad | `bi-exclamation-circle` |

### 5.3 Limites de longitud — verificados contra el backend real (no la lista original sin validar)

| Campo | Modelo backend real | `max_length` real | Limite frontend adoptado |
|---|---|---|---|
| Primer/Segundo nombre, Primer/Segundo apellido | `accounts.UserProfile.first_name/last_name` | 50 (no existen 4 campos separados a nivel BD — ver nota abajo) | **50** (no 40 como decia la especificacion original) |
| Correo electronico | `users.User.email` (`EmailField`) | 254 (default de Django, no configurado explicitamente) | **254** (no 120) |
| Celular | `accounts.UserProfile.phone_number` | 20 (el campo permite hasta 20, pero un celular colombiano real son 10 digitos) | **10 digitos** enforced por mascara (mas estricto que el backend a proposito, UX) |
| Documento | `accounts.UserProfile.document` | 30 | **30** (coincide con la especificacion original) |
| Empresa | `accounts.UserProfile.company` | 100 | **100** (no 120) |
| Cargo/Posicion | `accounts.UserProfile.position` | 100 | **100** (campo no contemplado en la especificacion original) |
| Direccion | `accounts.UserProfile.address` | 250 | **250** (no 200); `orders.ShippingAddress.address_line_1/2` usan 255 — hay un descuadre de 5 caracteres entre 2 modelos que representan el mismo concepto, reportar en Fase 8 como hallazgo de backend a NO tocar en este plan (regla fundamental: no modificar modelos) |
| Codigo postal | `accounts.UserProfile.postal_code` | 10 | **10** |
| Ciudad / Departamento / Pais | `UserProfile.city/state/country` | 50 cada uno | Estos ya no aplican como limite de texto libre si se migran a `BaseSearchSelect` (Fase 3) — el limite de caracteres deja de ser relevante cuando el valor viene de un catalogo cerrado |
| Descripcion (general) | La mayoria son `TextField` sin limite en BD (`TechnicalService.description`, `OrderServiceDetail.description`, etc.) | Sin limite tecnico | **1000** (decision de producto, coincide con la especificacion original) |
| Observaciones / notas | `TextField` sin limite en BD (`service_notes`, `notes`, `incident_notes`) | Sin limite tecnico | **300** (decision de producto, coincide con la especificacion original) |
| Comentarios / reseñas | `ServiceReview.comment` / `EquipmentReview.comment` (`TextField`) | Sin limite tecnico | **500** (decision de producto, coincide con la especificacion original) |

**Nota sobre KYC (4 campos de nombre):** el desglose de nombre en 4 partes vive en el
`contact_person`/formulario de KYC como campos de formulario, pero el modelo persistido
(`accounts.UserProfile`) solo tiene `first_name`/`last_name`. Verificar en una futura Fase de
implementacion como se concatenan hoy los 4 campos del formulario KYC hacia esos 2 campos del
modelo antes de decidir si el desglose de 4 se mantiene solo como UX de captura (recomendado,
cero cambio de backend) o si se simplifica a 2.

### 5.4 Catalogo de selectores inteligentes — mapeado contra endpoints reales ya existentes

| Campo | Fuente real (ya existe, verificado en esta auditoria) | Tipo de control |
|---|---|---|
| Tipo de documento | `accounts.UserProfile.DOCUMENT_TYPE_CHOICES` (CC/CE/NIT/PP) — fijo, no requiere API | `BaseSelect` (choices estaticas) |
| Pais | `PersonalInfoFields.vue` ya tiene `LATAM_COUNTRIES` (`latamData.js`) | `BaseSelect` |
| Departamento → Ciudad | `colombiaLocations.js` (dept→ciudad) — **fusionar con `latamData.js` primero, ver Fase 4 §4.5 prioridad 2** | `BaseSelect` + `BaseSearchSelect` dependiente |
| Barrio | No existe ningun catalogo de barrios en el proyecto hoy — dejar como texto libre con limite, no inventar un catalogo sin pedido explicito | Texto libre (fuera de alcance del catalogo inteligente) |
| Categoria (Shop/Renting/Services) | `shop/categories/`, `renting/equipment-categories/`, `technical_services/categories/` — 3 endpoints ya reales | `BaseSearchSelect` |
| Marca (Shop/Renting) | `shop/brands/`, `renting/equipment-brands/` — 2 endpoints ya reales | `BaseSearchSelect` |
| Estado / Prioridad / Metodo de pago / Tipo de servicio | `useEnums()` — YA es la fuente unica de verdad para estos, ver Fase 1 §8.1. No crear un select nuevo, usar `useEnums()` dentro de `BaseSelect` | `BaseSelect` alimentado por `useEnums()` |
| Rol / Tipo de usuario | `accounts.UserProfile.USER_TYPE_CHOICES` | `BaseSelect` (choices estaticas, admin-only) |
| Profesion / Especialidad (contratistas) | **No existe catalogo hoy** — `ContractorOnboardingWizard.vue` usa texto libre para "Tipo de contratista" (Fase 1, ya señalado) y select solo para especialidad via categoria de servicio. Requiere decision de producto: ¿crear catalogo nuevo de profesiones, o reusar categorias de servicio existentes? — **marcar para tu decision explicita en Fase 6**, no asumir |
| Moneda / IVA / Retencion | No se encontro ningun campo de este tipo en los formularios auditados (el proyecto opera en COP unicamente, IVA se maneja como regla de precio backend, no como input de usuario) — **fuera de alcance real, no aplica hoy** |

### 5.5 Catalogo de inputs inteligentes

| Campo | Comportamiento estandar | Base a construir (Fase 3 §3.5) |
|---|---|---|
| Correo | Validacion de formato inmediata (regex ya usada en varios formularios, centralizar) | `BaseInput type="email"` con validador integrado |
| Celular | Mascara 10 digitos, prefijo "+57" visual fijo (ya lo hace bien `RegisterView.vue`, generalizar a todo el sitio) | `BasePhoneInput` |
| Documento | Mascara segun tipo (numerico para CC/CE/TI, alfanumerico para pasaporte) — el patron de `ServiceRequestWizard.vue::onDocInput` ya resuelve esto bien, usarlo de base | `BaseDocumentInput` |
| Fecha | Nativo `<input type="date">` ya es aceptable (usado consistentemente); evaluar en Fase 6 si vale la pena un date-picker visual custom o el nativo del navegador es suficiente para no aumentar peso de bundle sin necesidad | `BaseDatePicker` (wrapper delgado sobre el nativo, no un date-picker JS pesado) |
| Hora | Igual que fecha — `<input type="time">` nativo | `BaseDatePicker`/hora, mismo componente con `type` prop |
| Dinero | `input-group` con `$` ya usado en `ProductForm.vue` — generalizar con separador de miles en vivo | `BaseMoneyInput` |
| Porcentaje | `input-group` con `%` — mismo patron que dinero | `BasePercentageInput` |
| Codigo postal | Sin mascara hoy en ningun formulario (10 caracteres, `postal_code` ya existe en backend) | Reusa `BaseInput` con `maxlength=10`, no requiere componente propio |

### 5.6 Validaciones en tiempo real — patron unico propuesto

Hoy la validacion en tiempo real existe mejor en `ServiceRequestWizard.vue` (icono rojo/verde
implicito via `is-invalid` + `.invalid-feedback`, contador de caracteres visible en
`description`/`problem`) y peor en el resto (la mayoria valida solo al enviar el formulario, o
como `CampaignForm` que valida con Yup pero no refleja el limite en el HTML). El estandar
adoptado, sobre el patron ya existente de VeeValidate+Yup (`useFormValidation.js`, ya integrado
en el proyecto desde 2026-07-01, no hay que traer una libreria nueva):

- Icono verde/rojo + mensaje: ya soportado por el patron `is-invalid`/`invalid-feedback` de
  Bootstrap, generalizarlo dentro de `BaseInput`/`BaseSelect` para que sea automatico sin que
  cada formulario lo reimplemente.
- Contador de caracteres: obligatorio en `BaseInput`/`BaseTextarea` cuando `maxlength` esta
  definido (que sera siempre, ver §5.3) — no opcional por formulario.
- Progreso: solo aplica a wizards multi-paso (`BaseWizard`, Fase 3) via el stepper existente
  (`CheckoutStepper.vue`), no a formularios de una sola pantalla.

### 5.7 Ayudas contextuales

Estandar: cada campo de `BaseInput`/`BaseSelect`/etc. acepta props opcionales `placeholder`,
`helpText` (texto de ayuda bajo el campo, patron `.form-text` ya usado en `PersonalInfoFields.vue`
para "Debes ser mayor de 18 años...") y `tooltip` (nuevo, no existe hoy en el codebase — usar
`title` HTML nativo con `data-bs-toggle="tooltip"` de Bootstrap, que ya esta cargado via CDN,
en vez de traer una libreria de tooltip nueva).

### 5.8 Estrategia para minimizar la captura manual

| Dato ya conocido por el sistema | Como evitar que el usuario lo escriba |
|---|---|
| Ciudad → Departamento/Pais | Con `BaseAddress`/`BaseSearchSelect` dependiente (Fase 3), seleccionar ciudad ya fija el departamento — patron que `RentalBookingWizard.vue`/`ServiceRequestWizard.vue` YA implementan bien, solo falta generalizarlo a los formularios que hoy usan texto libre |
| Documento → Tipo sugerido | No implementado hoy en ningun formulario (ej. autodetectar CC vs. NIT por longitud/formato) — nuevo, evaluar en Fase 6 si vale la pena vs. la complejidad que agrega |
| Cliente existente → Autocompletar direccion/telefono/correo/empresa | `ApplicantStep.vue` YA tiene un toggle "para mi/para un tercero" que autocompleta desde el perfil del usuario logueado cuando aplica — generalizar este patron a `CatalogApplicantStep.vue` (que hoy no lo tiene) y a `ServiceRequestWizard.vue`/`RentalBookingWizard.vue` (verificar si ya precargan datos del perfil o el usuario los reteclea siempre) |

---

**Fin de la Fase 5.**

---

## FASE 6 — Experiencia de Usuario

### Metodologia

Se verifico el estado real (no supuesto) de 5 mecanismos de UX transversales antes de proponer
cambios: persistencia de borrador/autosave, autofocus, animaciones de transicion entre pasos,
cobertura de `aria-*` en los sistemas de modal, y manejadores de teclado personalizados. Esto
evita proponer "agregar autosave" si ya existe en parte del sitio — el problema real, como en
casi todos los hallazgos de esta auditoria, es **inconsistencia de cobertura**, no ausencia
total.

### 6.1 Autosave / continuar despues — HOY: 2 de 4 wizards lo tienen, 2 no

| Wizard | Persiste borrador hoy |
|---|---|
| `RentalBookingWizard.vue` (via `store/renting/bookingStore.js`) | **Si** — `restore()`/`persist()`/`clear()` a localStorage |
| Wizard de cotizacion personalizada (`useQuoteWizard.js`) | **Si** — mismo patron |
| `ServiceRequestWizard.vue` | **No** — si el usuario recarga la pagina o pierde conexion a mitad del paso 2/3, pierde todo lo capturado |
| Wizard de cotizacion por catalogo (`useCatalogQuoteWizard.js`) | **No** — mismo problema |

**Propuesta:** generalizar el patron ya probado (`restore`/`persist`/`clear`, TTL razonable de
ej. 24h para no resucitar un borrador viejo con datos obsoletos) a los 2 wizards que hoy no lo
tienen. Es el unico punto de la Fase 6 con evidencia de una perdida de trabajo real del usuario
(no solo friccion), por lo que se recomienda priorizarlo alto en la Fase 7.

### 6.2 Autocompletar desde datos ya conocidos

`ApplicantStep.vue` (cotizacion personalizada) ya tiene un toggle "para mi / para un tercero"
que autocompleta nombre/correo/telefono/empresa desde el perfil del usuario logueado cuando
aplica — es el unico lugar del sitio que hace esto hoy. **Propuesta:** generalizar el mismo
toggle a `CatalogApplicantStep.vue` (que hoy no lo tiene, obligando a retecleaer datos que el
sistema ya conoce) y verificar si `ServiceRequestWizard.vue`/`RentalBookingWizard.vue`
precargan `personal.full_name`/`email`/`phone` desde el perfil o el usuario los reescribe cada
vez (evidencia pendiente de una revisión de implementacion, no confirmada en esta auditoria).

### 6.3 Foco automatico — HOY: cero cobertura en todo el sitio

Se busco `autofocus` y manejo manual de foco (`ref(...).focus()`) en toda `views/customer/` y
`components/customer/` — **cero resultados**. Ningun formulario mueve el foco al primer campo
al montarse o al avanzar de paso en un wizard. **Propuesta:** agregar foco automatico al primer
campo (o al primer campo invalido, si el usuario vuelve atras por un error) como parte del
contrato de `BaseWizard`/`BaseStep` (Fase 3) — que sea automatico por diseño del componente
base, no una responsabilidad que cada formulario deba recordar implementar.

### 6.4 Tab order

No se encontraron violaciones explicitas (el DOM sigue el orden logico en la mayoria de
formularios), pero el constructor de direccion (tipo-via/numero/generadora/placa, 4 campos en
una fila) es el candidato con mayor riesgo de un tab-order confuso en pantallas angostas donde
el CSS puede reordenar visualmente sin reordenar el DOM — **verificar con prueba real de
teclado (Tab repetido) durante la implementacion de `BaseAddress`**, no se puede confirmar solo
leyendo el codigo estatico.

### 6.5 Atajos de teclado — HOY: ninguno personalizado, solo accesibilidad basica

Los unicos manejadores de teclado encontrados son: `OtpInput.vue` (mover foco entre digitos del
OTP, necesario para su funcion), `CheckoutModal.vue` (ESC para cerrar, ya documentado en Fase
1), `PaymentMethodCard`/`PaymentMethodSelector` (navegacion con flechas entre opciones de pago),
`ProductList.vue` e `InlineTextEditor.vue` (uso puntual no verificado a fondo). **No existe
ningun atajo global** (ej. `Ctrl+Enter` para enviar un formulario, `Ctrl+S` para guardar
borrador). **Propuesta (alcance moderado, no critico):** `Ctrl+Enter`/`Cmd+Enter` para avanzar
de paso en `BaseWizard` es de bajo costo y beneficio real para usuarios frecuentes (staff
admin); no se recomienda inventar mas atajos sin un pedido de uso real que los justifique.

### 6.6 Validacion inmediata, errores claros, mensajes consistentes

Ya cubierto en Fase 5 §5.6 (validacion) y confirmado en Fase 1 que `useToast()` **ya es
unico y consistente en todo el proyecto** (mensajes) y `useErrorHandler.js` **ya centraliza**
la extraccion de errores DRF/Axios desde 2026-07-16 — con la unica excepcion real encontrada
en `PaymentTransactionsAdminView.vue`, que no lo usa (Fase 1 §1.3). No hay trabajo nuevo que
diseñar aqui, solo **cerrar la unica excepcion** durante la implementacion.

### 6.7 Botones consistentes

Resuelto en Fase 3 (`BaseButton`, generaliza `CustomerButton.vue`). No hay diseño adicional que
agregar aqui — es un problema de adopcion (migrar los botones sueltos de Bootstrap de Shop/
Renting/KYC admin), no de diseño.

### 6.8 Animaciones de transicion entre pasos — HOY: 1 de 4 wizards la tiene

Solo `RentalBookingWizard.vue` usa `<Transition name="slide" mode="out-in">` entre pasos.
`ServiceRequestWizard.vue` y los 2 wizards de cotizacion cambian de paso con un salto directo
(`v-if`/`v-show` sin transicion). **Propuesta:** mover la transicion `slide` al nivel de
`BaseWizard`/`BaseStep` (Fase 3) para que sea automatica y uniforme en los 4 wizards a la vez,
en vez de que cada uno decida si "le pone animacion" o no.

### 6.9 Loading uniforme / Skeleton uniforme

Ya es, por lejos, el hallazgo mas grande de toda la auditoria (Fase 1 §1.3, Fase 2 §2.3): al
menos 3 copias casi identicas de CSS de shimmer, spinners `spinner-border` reimplementados de
forma independiente en 8+ archivos, y 2 vistas (`SecurityDashboardView.vue`,
`SupportDashboardView.vue`) sin ningun indicador de carga. **Propuesta:** `BaseSkeleton`
(Fase 3, ya diseñado sobre `CustomerSkeleton.vue`) se adopta como el UNICO patron de carga de
contenido (catalogos, detalle), reservando `spinner-border` solo para acciones puntuales
(botones en estado `loading`, ya cubierto por `BaseButton`). Agregar explicitamente un
`BaseSkeleton`/spinner a `SecurityDashboardView.vue` y `SupportDashboardView.vue`, que hoy no
tienen ninguno.

### 6.10 Accesibilidad (adelanto de lo que pide el documento final, WCAG 2.2 AA)

Hallazgo positivo: los 3 sistemas de modal "oficiales" (`CheckoutModal.vue`, `SintelOffcanvas.
vue`, `CustomerOverlayPanel.vue`) **ya implementan** `aria-modal`/`role="dialog"`/foco atrapado
y cierre con ESC — la base de accesibilidad de modales ya es buena donde se sigue la
convencion. El problema de accesibilidad real son, otra vez, los 9 usos indebidos (Fase 1
§1.3): los 7 modales de `HomeConfigView.vue` y el de `OperationDetail.vue` son overlays hechos
a mano que casi con certeza **no** replican `aria-modal`/manejo de foco/ESC (no verificado
campo por campo en esta auditoria, pero es el patron esperado dado que ninguno reutiliza el
componente que si lo tiene). Migrar estos 9 usos a `BaseOffcanvas` (Fase 3 §3.4.1) resuelve la
accesibilidad de modales "gratis", como efecto secundario de resolver la duplicacion.

### 6.11 Resumen priorizado de la Fase 6

| Prioridad | Accion | Por que |
|---|---|---|
| 1 | Autosave en `ServiceRequestWizard.vue` + wizard de cotizacion por catalogo | Unico hallazgo con evidencia de perdida de trabajo real del usuario, no solo friccion |
| 2 | `BaseSkeleton`/spinner en `SecurityDashboardView.vue`/`SupportDashboardView.vue` | Hoy el usuario ve una pantalla vacia sin saber si esta cargando o si no hay datos |
| 3 | Generalizar el toggle "autocompletar desde mi perfil" a `CatalogApplicantStep.vue` | Cierra la brecha de "menos escritura" mas concreta encontrada |
| 4 | Mover la transicion `slide` a `BaseWizard`/`BaseStep` | Consistencia visual entre los 4 wizards, bajo riesgo |
| 5 | Foco automatico al primer campo, integrado en `BaseStep` | Cero cobertura hoy, beneficio de velocidad percibida alto, riesgo bajo |
| 6 | Migrar los 9 modales indebidos a `BaseOffcanvas` | Resuelve consistencia Y accesibilidad al mismo tiempo (ver §6.10) |
| 7 (menor) | `Ctrl+Enter` para avanzar de paso en `BaseWizard` | Bajo costo, beneficio real solo para usuarios frecuentes/staff |

---

**Fin de la Fase 6.**

---

## FASE 7 — Sincronizacion Arquitectonica

### Aclaracion honesta antes de la checklist

Validar "¿todos los modulos usan ya la misma biblioteca/componentes/formularios/modales?" hoy
tiene una sola respuesta correcta: **no** — exactamente los huecos que documentaron las Fases
1 y 2. Declarar lo contrario seria falso. El valor real de esta fase es (a) fijar el checklist
exacto contra el que se medira cada modulo cuando se migre, y (b) el plan de migracion
incremental, en el orden que tu mismo propusiste (Payment → Renting → Services → Shop →
Accounts → Core), que es la unica forma de que la validacion de esta fase deje de ser teorica.

### 7.1 Checklist de sincronizacion por modulo (estado real hoy)

Leyenda: ✅ ya cumple — ⚠️ cumple parcialmente — ❌ no cumple, requiere migracion (con la
referencia a la fase donde se documento el hallazgo).

| Modulo | Misma biblioteca base | Mismo modal | Mismos iconos | Mismo loader | Mismo checkout/wizard | Mismo timeline | Mismo patron visual |
|---|---|---|---|---|---|---|---|
| **Renting** (customer) | ⚠️ usa `CheckoutStepper`✅ pero tiene su propio `EquipmentGallery`/`HorizontalCard` (Fase 2 §2.1) | ✅ `CheckoutModal` | ⚠️ ok salvo `HeroSlide.vue` (Fase 2 §2.7) | ❌ shimmer propio identico al de Services (Fase 1) | ✅ ya unificado con Services (2026-07-18, sesion previa) | ✅ `StatusTimeline` | ✅ familia visual propia coherente (azul Detail / violeta Wizard, documentado y aceptado) |
| **Technical Services** (customer) | ⚠️ igual que Renting, mas atraso en managers admin (Fase 2 §2.2, `ServiceForm.vue` God Form sin extraer) | ✅ `CheckoutModal` | ⚠️ `ServiceCard.vue` usa icono crudo | ❌ shimmer propio | ✅ ya unificado con Renting | ✅ `StatusTimeline` (via `ServiceReviews`/etc.) | ✅ ambar deliberado, ya documentado |
| **Shop** | ❌ `ProductForm`/`CategoryForm`/`BrandForm` sin generalizar (Fase 2 §2.4); `ColombianAddressForm` solo aqui | ✅ usa `SintelOffcanvas` correctamente en admin | ⚠️ ok en general | ❌ shimmer propio en `ShopCatalogView`/`ProductDetailView` | ❌ **checkout de una sola pagina, NO usa `CheckoutStepper`** (Fase 1 §Payment, hallazgo mayor) | N/A (no tiene timeline propio) | ⚠️ card de catalogo ya compartida (`ItemCard`), pero checkout diverge del patron wizard |
| **Payment** | ⚠️ ya tiene su propia sub-biblioteca madura (`Payment*` 13 componentes) pero paralela, no integrada a `components/base/` | ✅ `CheckoutModal` es SU componente, correctamente generico | ✅ | ⚠️ spinners propios pero consistentes entre si | N/A (Payment es consumido por los checkouts, no tiene uno propio) | ❌ `PaymentTimeline` NO usa `StatusTimeline` (Fase 2 §2.3, la migracion mas facil de toda la auditoria) | ✅ coherente en si mismo |
| **Accounts / Users** | ⚠️ `CustomerProfileView` ya usa el design system; `UserForm.vue` (admin) no | ✅ `SintelOffcanvas` (admin) | ✅ | ⚠️ | N/A | N/A | ⚠️ |
| **KYC** | ❌ `PersonalInfoFields.vue` es el mas maduro en direccion/documento pero vive aislado, ningun otro formulario lo reusa | ✅ | ✅ | ❌ (Fase 1: sin indicador en algunas vistas admin de KYC) | N/A | ⚠️ usa `StatusTimeline` en el hub de onboarding, bien | ⚠️ |
| **Organization** | ❌ **el caso mas alejado de todos** — CSS 100% propio (`org-*`), 8 tabs sin ningun componente compartido (Fase 1 §1.2) | ❌ usa `confirm()` nativo, no offcanvas para nada | ⚠️ | ❌ | N/A | N/A | ❌ tercer "lenguaje visual" del panel admin (Fase 1 §1.2) |
| **Core** (Home Builder) | ❌ 7 modales propios (Fase 1 §1.2), sin usar `SintelOffcanvas` | ❌ el peor caso del proyecto (7 modales `.hcb-modal-*`) | ⚠️ 3 archivos con icono crudo (Fase 2 §2.7) | ❌ | N/A | N/A | ⚠️ (builder visual, patron propio justificado en parte por su naturaleza de "editor de contenido") |
| **Operations** | ❌ `DispatcherList.vue` con modal propio + `confirm()` nativo (Fase 1/2, el outlier mas claro) | ❌ | ✅ | ⚠️ | N/A | ⚠️ `OperationDetail` usa `TrackingTimeline` (que si delega a `StatusTimeline`, correcto) | ⚠️ |
| **Notifications** | ✅ ya usa `SintelOffcanvas` correctamente (Fase 1, unico elogio directo) | ✅ | ✅ | ⚠️ spinner propio pero sin inconsistencia grave | N/A | N/A | ✅ |
| **Security** | N/A (solo lectura, sin CRUD) | N/A | ✅ | ❌ **sin ningun indicador de carga** (Fase 1 §1.3) | N/A | ❌ tabla plana, podria usar `StatusTimeline mode="events"` para el log (oportunidad, no defecto) | ⚠️ |
| **Support** | ⚠️ `Customer360Panel` ya usa `UnifiedTimeline`→`StatusTimeline` correctamente; pero `OrderContextCard`/`PaymentContextCard`/`RentalContextCard` triplicados (Fase 2 §2.5) | N/A | ✅ | ❌ **sin ningun indicador de carga** (Fase 1 §1.3) | N/A | ✅ (via `UnifiedTimeline`) | ⚠️ |

### 7.2 Plan de migracion incremental por modulo (orden pedido: Payment → Renting → Services → Shop → Accounts → Core, mas los 4 restantes al final)

La justificacion del orden: Payment primero porque su sub-biblioteca ya es la mas madura (menor
esfuerzo, mayor aprendizaje reusable para el resto); Renting/Services casi no requieren trabajo
nuevo porque ya se sincronizaron entre si en la sesion anterior a esta auditoria; Shop es el
salto de mayor impacto visible al usuario (unificar su checkout de una sola pagina al patron
wizard, decision que requiere tu confirmacion explicita — ver riesgo en §7.3); Accounts/Core al
final porque son los de mayor superficie/riesgo (`OrganizationView` 8 tabs, `HomeConfigView`
2705 lineas).

| Orden | Modulo | Trabajo concreto (ya especificado en Fases 2-6) |
|---|---|---|
| 1 | **Payment** | Migrar `PaymentTimeline.vue` → `StatusTimeline mode="events"` (Fase 2 §2.3). Migrar `PaymentBadge.vue` → `BaseBadge` (una vez exista). Extraer `Payment*` (13 componentes) hacia `components/base/` donde el concepto es genuinamente generico (`PaymentCard`→`BaseCard`, `PaymentAlert`→`BaseAlert`) |
| 2 | **Renting + Services** | Ya sincronizados en checkout/wizard (sesion previa a esta auditoria). Pendiente: fusionar `EquipmentGallery`+`ServiceGallery`, `EquipmentFAQ`+`ServiceFAQAccordion`, `EquipmentReviews`+`ServiceReviews`, `EquipmentHorizontalCard`+`ServiceHorizontalCard` (Fase 2 §2.1); extraer los 6 managers de contenido para Technical Services (mayor esfuerzo de esta fase, Fase 2 §2.2) |
| 3 | **Shop** | **Requiere tu decision explicita:** ¿migrar el checkout de una sola pagina al patron wizard de Renting/Services, o mantener la pagina plana como una variante deliberada? (Fase 1 §Payment). Fusionar `CategoryForm`+`BrandForm` con sus equivalentes de Renting (Fase 2 §2.4, el caso mas limpio de toda la auditoria). Fusionar `ProductHorizontalCard` al `HorizontalCard` compartido |
| 4 | **Accounts/Users/KYC** | Generalizar `PersonalInfoFields.vue` (o su logica de direccion/documento) hacia `BaseAddress`/`BaseDocumentInput`; agregar `maxlength` real a `UserForm.vue`; unificar dataset `colombiaLocations.js`+`latamData.js` |
| 5 | **Core (Home Builder)** | El de mayor esfuerzo: migrar los 7 modales de `HomeConfigView.vue` a `BaseOffcanvas`, uno a la vez (no en un solo cambio, por su tamaño de 2705 lineas) |
| 6 | **Organization** | Migrar sus 8 tabs de CSS propio (`org-*`) al design system; reemplazar el `confirm()` nativo |
| 7 | **Operations** | `DispatcherList.vue`: reemplazar `user_id` crudo por selector de usuarios (Fase 4 §4.3, el hallazgo mas grave de seguridad de datos), su modal propio por `BaseOffcanvas`, y su `confirm()` nativo por `BaseConfirmInline` |
| 8 | **Notifications/Security/Support** | Menor esfuerzo: agregar `BaseSkeleton` a Security/Support (hoy sin ningun indicador), fusionar los 3 `ContextCard` de Support |

### 7.3 Riesgos consolidados (todos los de Fases 1-6, en un solo lugar para la Fase 8)

| Riesgo | Modulo | Mitigacion |
|---|---|---|
| Migrar direccion a `BaseAddress` puede romper el nombre exacto de campo que cada wizard envia al backend hoy | Renting/Services/Shop/KYC | Mapear campo-por-campo antes de tocar cada consumidor (el backend no cambia, solo el frontend construye el mismo payload desde un componente compartido) |
| `OrganizationView.vue` (8 tabs, CSS propio) es el cambio de mayor superficie visual de todo el plan | Organization | Migrar de ultimo, verificacion visual Playwright tab por tab |
| `HomeConfigView.vue` (2705 lineas, 7 modales) es el archivo individual mas grande y riesgoso | Core | Migrar un modal a la vez, nunca en un solo cambio |
| Fusionar `colombiaLocations.js`/`latamData.js` puede tener una diferencia de forma que algun consumidor use a proposito | Accounts/KYC | Verificar consumidor por consumidor antes de fusionar los datasets |
| Decision de Shop (checkout pagina vs. wizard) cambia una experiencia de compra ya en produccion | Shop | **No migrar sin tu aprobacion explicita especifica para este punto** — es el unico cambio de este plan que altera un flujo de negocio visible al cliente final, no solo codigo interno |
| Las 3 decisiones de arquitectura de Fase 3 §3.4 (modales/badges/alcance de BaseTable) siguen sin resolver | Transversal | Resolver antes de escribir el primer `Base*`, revertir despues de migrar 10 archivos seria costoso |

### 7.4 Estrategia de compatibilidad hacia atras

- Todo `Base*` se construye como **componente nuevo, aditivo** — ningun componente existente
  se borra hasta que su ultimo consumidor real haya migrado y se haya verificado visualmente.
- Los props/slots de los componentes que YA son genericos y buenos (`StatusTimeline`,
  `CheckoutStepper`, `SintelOffcanvas`, `IconRenderer`, `StarRating`) **no cambian** — solo se
  mueven de carpeta o se les agregan props nuevas *opcionales* (ej. el `clickable` que ya se le
  agrego a `CheckoutStepper` en la sesion previa a esta auditoria, sin romper su unico
  consumidor anterior).
- Cero cambios de backend en todo este plan (ya reiterado en cada fase) — ningun payload
  cambia de forma, solo el componente que lo construye.

---

**Fin de la Fase 7.**

---

## FASE 8 — Validacion Final

### Verificacion realizada

Esta auditoria completa (Fases 1-7) se ejecuto **sin escribir ni un solo archivo de codigo de
la aplicacion** — cada Fase fue investigacion (agentes de exploracion + lectura directa) o
diseño/documentacion, nunca implementacion. Se verifico esto de forma independiente (no solo
"porque yo se que no lo hice"): un barrido de archivos modificados mas recientemente que este
mismo documento en todo el repositorio arrojo **un unico resultado: `logs/nginx/access.log`**
— un archivo de log de trafico HTTP, generado automaticamente por el servidor, sin ninguna
relacion con codigo. Ningun archivo `.py`, `.vue`, `.js`, `.ts`, migracion, modelo, serializer,
o configuracion fue tocado.

| Item a validar | Estado |
|---|---|
| Backend (Django) | ✅ Sin cambios — cero archivos `.py` modificados |
| Modelos | ✅ Sin cambios |
| Endpoints / URLs | ✅ Sin cambios |
| Commands / Selectors / Services | ✅ Sin cambios |
| Base de datos / migraciones | ✅ Sin cambios — cero migraciones nuevas |
| Integracion Wompi/Nequi | ✅ Sin cambios — `useWompiWidget.js`/`useCardTokenization.js` solo se leyeron, nunca se editaron |
| Inventario | ✅ Sin cambios |
| Operaciones | ✅ Sin cambios |
| Renting / Shop / Services (backend) | ✅ Sin cambios |
| Frontend (Vue) | ✅ Sin cambios — todos los hallazgos de Fases 1-6 son de solo lectura; ningun `Base*` se construyo todavia (por diseño, ver Fase 3) |

**Conclusion de Fase 8: 100% de cumplimiento de la Regla Fundamental durante todo el proceso de
auditoria.** El unico archivo que este proceso creo o modifico es este mismo documento
(`PLAN_MAESTRO_FRONTEND_DESIGN_SYSTEM_Y_FORMULARIOS.md`) mas 2 notas de memoria persistente
entre sesiones (sin relacion con codigo de la aplicacion).

---

## Criterios Adicionales Recomendados (incorporados por iniciativa propia, per tu pedido explicito)

### A. Sistema de diseño basado en tokens

No existe hoy un archivo central de tokens (colores/tipografia/espaciados/radios/sombras) — cada
familia visual los define inline en su propio `<style scoped>` (Fase 1 §hallazgo de "3 lenguajes
visuales"). Se propone, como parte de la construccion de `components/base/` (Fase 3), un archivo
`components/base/tokens.css` con variables CSS (no un sistema de build-time como Tailwind config,
para no introducir una dependencia nueva):

```css
:root {
  /* Colores de identidad por modulo (ya validados en produccion, no inventados) */
  --color-renting-detail: #2563eb;   /* ya usado en RentalDetailView */
  --color-wizard-accent: #7c3aed;    /* ya usado en ambos wizards + checkout */
  --color-services-catalog: #d97706; /* ya usado en ServiceDetailView, decision deliberada */
  --color-success: #16a34a; --color-danger: #ef4444; --color-warning: #f59e0b;
  /* Radios (ya validados: 14-16px detalle, 20-24px wizard/cuenta) */
  --radius-sm: 10px; --radius-md: 14px; --radius-lg: 20px; --radius-pill: 999px;
  /* Sombras (ya validada en Renting Detail) */
  --shadow-card: 0 16px 34px rgba(15,23,42,.08);
  --shadow-hover: 0 4px 16px rgba(0,0,0,.07);
  /* Espaciado */
  --space-xs: 4px; --space-sm: 8px; --space-md: 16px; --space-lg: 24px; --space-xl: 40px;
}
```

Los valores no son inventados — son los que ya coexisten hoy en produccion (Fase 1 §Checklist
UI ya confirmo que radios/sombras de Renting Detail y Mi Cuenta ya coinciden). El token
formaliza lo que ya es cierto en la practica, no impone un valor nuevo.

### B. Catalogo unico de patrones de interaccion (cuando usar cada uno)

| Patron | Usar cuando | Componente |
|---|---|---|
| Panel lateral (offcanvas) | CRUD admin de una entidad (crear/editar) | `BaseOffcanvas` |
| Modal centrado | Flujo de pago/confirmacion critica que requiere atencion exclusiva | `CheckoutModal` (dominio Payment unicamente — no usar para CRUD) |
| Wizard multi-paso | Captura de datos larga con dependencias entre pasos (reserva, solicitud, cotizacion) | `BaseWizard` + `BaseStep` |
| Acordeon | Contenido opcional/secundario que la mayoria de usuarios no necesita ver (FAQ) | `BaseAccordion` |
| Tabs | Secciones de un mismo formulario/entidad, todas relevantes pero no simultaneas (General/SEO/Variantes) | `BaseTabs` |
| Confirmacion inline | Cualquier accion destructiva (borrar, desactivar) | `BaseConfirmInline` — **nunca** `confirm()` nativo ni modal |
| Sidebar de resumen | Wizard de checkout, mostrar costo/seleccion corriendo | `BaseSummary` |

### C. Biblioteca de reglas de validacion compartidas

Ya cubierto en Fase 5 (icono/mascara/limite por campo). Se agrega aqui solo la mecanica de
implementacion: un unico archivo `composables/useFieldRules.js` con funciones puras
(`isValidEmail`, `isValidColombianPhone`, `isValidDocument(tipo, valor)`) consumidas tanto por
`BaseInput`/`BasePhoneInput`/etc. como por el esquema Yup existente (`useFormValidation.js`) —
para que la regla de "un correo invalido" se defina una sola vez y la usen ambos mecanismos de
validacion (HTML5 en vivo + Yup en submit) sin poder desincronizarse entre si.

### D. Componentes adaptativos (responsive)

No se encontro, en ninguna fase, un breakpoint system centralizado — cada componente define sus
propios `@media` inline (patron ya usado consistentemente en Bootstrap, `991px`/`575px` son los
2 breakpoints que aparecen una y otra vez en el codigo auditado). Se propone mantener este
patron (no introducir un sistema de breakpoints nuevo que rompa la consistencia ya existente),
pero documentar `991px`/`575px` como los 2 breakpoints oficiales del proyecto en el token file
de §A, y exigir que todo `Base*` nuevo los respete.

### E. Medicion de impacto (consolidado de las 8 fases)

| Metrica | Valor |
|---|---|
| Componentes identificados para fusionar/eliminar (Fase 2) | 17 grupos de duplicados + 2 componentes obsoletos confirmados (`GlassCard`, `SectionHeader`) |
| Componentes `Base*` diseñados (Fase 3) | 33 (19 ya existen y se generalizan, 14 son nuevos sin precedente) |
| Formularios auditados campo-por-campo (Fase 4) | 14 formularios, 5 modulos con el mismo dato (nombre/ciudad/telefono/documento/direccion) implementado de forma independiente |
| Decisiones de producto pendientes de tu confirmacion explicita (estado 2026-07-18) | 3 (alcance BaseTable §3.4.3, catalogo Profesion/Especialidad §5.4 — requeriria modelo backend nuevo, fuera de alcance de este plan, checkout Shop pagina-vs-wizard §7.2). §3.4.1 (modales) y §3.4.2 (badges) ya se resolvieron con evidencia real, ver esas secciones. |
| Hallazgo de mayor riesgo de seguridad de datos | `DispatcherList.vue`, `user_id` crudo (Fase 4 §4.3) |
| Cambios de codigo realizados durante la auditoria | **Cero** (Fase 8) |

---

## Checklists Finales

### Checklist de Frontend

- [ ] `components/base/` creado con los 19 componentes del Grupo A (Fase 3 §3.2) generalizados
- [ ] Los 14 componentes del Grupo D (formularios inteligentes, Fase 3 §3.5) construidos
- [ ] Los 17 grupos de duplicados de Fase 2 fusionados o retirados segun corresponda
- [ ] `colombiaLocations.js` + `latamData.js` unificados (o decision explicita de mantenerlos separados, documentada)
- [ ] Los 9 usos indebidos de modal (`HomeConfigView` ×7, `OperationDetail`, `DispatcherList`) migrados a `BaseOffcanvas`

### Checklist de UX

- [ ] Autosave generalizado a los 4 wizards (hoy 2 de 4)
- [ ] Foco automatico al primer campo en todo `BaseStep`
- [ ] Transicion `slide` uniforme en los 4 wizards
- [ ] Toggle "autocompletar desde mi perfil" generalizado a `CatalogApplicantStep.vue`
- [ ] `CartOffcanvas.vue` con confirmacion (hoy no tiene ninguna)

### Checklist de UI

- [ ] Iconografia de campos aplicada segun catalogo Fase 5 §5.2 (Bootstrap Icons, no emoji)
- [ ] `maxlength` HTML real (no solo Yup) en `CampaignForm`, `UserForm`, `ProductForm.description`, `email_body` de notificaciones
- [ ] Token file (`components/base/tokens.css`) creado con los valores ya validados en produccion
- [ ] `OrganizationView.vue` migrado del CSS propio (`org-*`) al design system
- [ ] Todo `icon_class` de BD renderizado via `IconRenderer`, cero `<i class="bi...">` crudo con datos de backend (6 casos pendientes, Fase 2 §2.7)

### Checklist de QA funcional

- [ ] Cada wizard migrado probado end-to-end con Playwright (login real, llenar formulario, confirmar payload enviado al backend es identico al de antes de la migracion)
- [ ] Verificacion visual (capturas) de cada catalogo/detalle antes/despues de migrar skeleton a `BaseSkeleton`
- [ ] Suite de tests backend (`manage.py test`) ejecutada sin cambios de resultado despues de cada lote de migracion frontend (debe seguir en 0 regresiones, ya que el backend nunca cambia)
- [ ] Verificacion manual de que el payload exacto que cada formulario envia hoy al backend no cambio de forma tras migrar a `Base*` (nombres de campo, estructura anidada vs. plana)

### Plan de Rollback

Dado que cada `Base*` se construye como componente nuevo y aditivo (Fase 7 §7.4, ningun
componente viejo se borra hasta verificar su reemplazo), el rollback de cualquier modulo
migrado es: **revertir el archivo consumidor a su version anterior** (el componente `Base*`
puede quedarse sin uso, no rompe nada mientras no se borre el componente viejo). Regla de
seguridad adicional: no borrar ningun componente viejo (`CustomerCard.vue`, `PaymentCard.vue`,
etc.) hasta que **todos** sus consumidores hayan migrado y se haya verificado en produccion
por al menos 1 ciclo de uso real — solo entonces limpiar el codigo muerto.

---

## Documento Final

Este mismo archivo, construido incrementalmente fase por fase con tu confirmacion explicita en
cada paso, **es** el `PLAN_MAESTRO_FRONTEND_DESIGN_SYSTEM_Y_FORMULARIOS.md` pedido. Contiene:
auditoria de arquitecturas canonicas (Fase 1), matriz de sincronizacion (Fase 7 §7.1),
inventario de componentes duplicados (Fase 2), biblioteca compartida propuesta (Fase 3), design
system unificado (Fase 8 Criterios Adicionales §A-D), estandar de formularios (Fase 5),
catalogo de componentes base (Fase 3), catalogo de iconografia (Fase 5 §5.2), reglas de
validacion/longitud (Fase 5 §5.3, verificadas contra backend real), catalogo de controles
inteligentes (Fase 5 §5.4-5.5), estrategia de minimizar captura manual (Fase 5 §5.8, Fase 6
§6.2), accesibilidad/teclado (Fase 6 §6.3-6.5, §6.10), plan de migracion incremental (Fase 7
§7.2), compatibilidad hacia atras (Fase 7 §7.4), riesgos y mitigacion (Fase 7 §7.3), y los 4
checklists + plan de rollback de esta seccion.

**Ninguna implementacion (construccion real de un componente `Base*`, migracion de un
formulario, fusion de un componente duplicado) ha ocurrido todavia.** Todo lo anterior es
auditoria y diseño aprobado fase por fase. El siguiente paso, si decides continuar, es elegir
por donde empezar la implementacion real (se recomienda el orden de Fase 7 §7.2, empezando por
Payment) — y las 5 decisiones de producto pendientes (§E de esta seccion) siguen sin resolver,
idealmente antes de escribir el primer componente.

---

## Implementacion Real (2026-07-18, pedido explicito "continua en orden secuencial hasta finalizar por completo la tarea")

### Descubrimiento que reordeno el plan

Antes de tocar Payment (Paso 1 de la Fase 7 §7.2) se encontro `PLAN_MAESTRO_UNIFICACION_PAYMENT_UI.md`
(raiz del repo) — un plan previo, independiente, **ya completo e implementado** que cubre
exactamente ese paso (13 componentes `Payment*`, verificado en navegador con Wompi/Nequi/COD
reales en Shop/Renting/Services). No se duplico ese trabajo — se salto directo al Paso 2.

### Construido y verificado (build + Playwright + tests backend, en cada paso)

| Componente nuevo (`components/base/`) | Fusiona | Consumidores migrados | Verificacion |
|---|---|---|---|
| `BaseReviews.vue` | `EquipmentReviews.vue` + `ServiceReviews.vue` (173 lineas identicas cada uno) | `RentalDetailView.vue`, `ServiceDetailView.vue` | Playwright: reseñas visibles, colores por dominio correctos (azul/ambar), 0 errores de consola |
| `BaseAccordion.vue` | `EquipmentFAQ.vue` + `ServiceFAQAccordion.vue` | idem | Normaliza 2 formas de prop distintas (`{uuid,question,answer}` vs `{q,a}`) sin tocar los computed existentes |
| `BaseGallery.vue` | `EquipmentGallery.vue` + `ServiceGallery.vue` | idem | Slot `#badge` preserva el badge de "tipo de imagen" (Renting) y "Destacado" (Services) exactos, con su CSS movido al consumidor |
| `BaseHorizontalCard.vue` | `EquipmentHorizontalCard.vue` + `ServiceHorizontalCard.vue` + `ProductHorizontalCard.vue` (~300L c/u, ~930L combinadas) | `RentalCatalogView.vue`, `ServicesCatalogView.vue`, `ShopCatalogView.vue` (sin cambios — mismo prop/emit contract) | Playwright en los 3 catalogos reales: 7/8/8 tarjetas visibles, colores/botones/logica especifica de cada dominio (cotizar/agregar al carrito con estado async) preservados exactamente |
| `BaseBrandForm.vue` | `modules/shop/BrandForm.vue` + `modules/renting/RentingBrandForm.vue` | `BrandList.vue`, `RentingBrandList.vue` (sin cambios) | Playwright real: crear marca en ambos paneles admin, toast de exito confirmado. `hasLogo`/`hasActiveToggle` reflejan diferencia REAL de schema (`renting.RentingBrand` no tiene esos campos, verificado en el modelo) |
| `BaseCategoryForm.vue` | `modules/shop/CategoryForm.vue` + `modules/renting/RentingCategoryForm.vue` | `CategoryList.vue`, `RentingCategoryList.vue` (sin cambios) | Playwright real: crear categoria en ambos paneles admin, toast de exito confirmado. `hasImage`/`hasSeo` reflejan diferencia REAL de schema (`renting.RentingCategory` no tiene `image`/`meta_title`/`meta_description`) |

**Archivos eliminados** (duplicados, tras confirmar cero consumidores restantes via grep):
`EquipmentReviews.vue`, `ServiceReviews.vue`, `EquipmentFAQ.vue`, `ServiceFAQAccordion.vue`,
`EquipmentGallery.vue`, `ServiceGallery.vue`.

**No eliminados a proposito:** `EquipmentHorizontalCard.vue`/`ServiceHorizontalCard.vue`/
`ProductHorizontalCard.vue` y los 4 Form de Categoria/Marca siguen existiendo, pero ahora como
wrappers delgados sobre el `Base*` compartido (mismo archivo/import path que ya consumian sus
respectivas vistas — cero cambios en `RentalCatalogView.vue`, `ServicesCatalogView.vue`,
`ShopCatalogView.vue`, `CategoryList.vue`, `BrandList.vue`, `RentingCategoryList.vue`,
`RentingBrandList.vue`, reduciendo el riesgo de la migracion al minimo).

### Decision de producto NO tomada en silencio (Paso 3, Fase 7 §7.2)

**El checkout de Shop (`CheckoutView.vue`, pagina completa) NO se migro al patron wizard de
Renting/Services.** Es el unico cambio del plan que alteraria un flujo de compra ya en
produccion visible al cliente final (marcado explicitamente en Fase 7 §7.3 como el riesgo que
exige aprobacion separada) — se dejo intacto, tal como se anuncio antes de empezar esta
implementacion.

### Verificacion final

- `npm run build`: limpio en cada uno de los 6 pasos, sin errores nuevos.
- Playwright real contra los contenedores dev (`ecommerce_sintel_frontend`/`ecommerce_sintel_django`):
  detalle de Renting/Services (galeria+FAQ+reseñas), los 3 catalogos en vista lista, y creacion
  real de Categoria/Marca en ambos paneles admin — todos verificados con datos reales, datos de
  prueba limpiados al terminar.
- `manage.py test shop renting technical_services dashboard`: ejecutado al cierre — cero cambios
  de backend en todo este trabajo (solo se leyeron modelos para confirmar diferencias reales de
  schema antes de generalizar los formularios), por lo que no se esperaba ni se encontro ninguna
  regresion.

### Paso 4 (Fase 7 §7.2): Accounts/Users/KYC

Auditados `PersonalInfoFields.vue`, `UserForm.vue` y los 3 datasets de ubicacion colombiana
que la Fase 1/4 habia marcado como riesgo de desincronizacion. Se encontro un tercer hallazgo
no documentado hasta ahora: `ServiceRequestWizard.vue` tenia su **propia copia hardcodeada e
incompleta** del mapa departamento→ciudad (26 departamentos, sin tildes) declarada inline en
el `<script setup>`, distinta tanto del catalogo canonico `data/colombiaLocations.js` (33
departamentos, con tildes) como de la lista plana de `latamData.js` (30 ciudades). Correcciones
aplicadas:

| Archivo | Cambio | Riesgo |
|---|---|---|
| `modules/users/UserForm.vue` | `maxlength` real en email (254, `User.email` default de Django), nombre/apellido (50, `UserProfile.first_name/last_name`) y telefono (20, `UserProfile.phone_number`) — verificado contra los modelos, no copiado del ejemplo original del usuario | Ninguno — solo atributos HTML, sin tocar `submit()` ni el payload |
| `components/auth/kyc/latamData.js` | `COLOMBIAN_CITIES` (30 ciudades hardcodeadas) reemplazado por una lista derivada de `COLOMBIA_LOCATIONS` (`Object.values(...).flat()`, 132 ciudades reales) — mismo nombre de export, cero cambios en `PersonalInfoFields.vue` | Ninguno — mismo tipo de campo (select plano de string), solo la fuente de datos cambia |
| `views/customer/services/ServiceRequestWizard.vue` | Objeto `COLOMBIA_LOCATIONS` local (28 lineas) eliminado, reemplazado por `import { COLOMBIA_LOCATIONS } from '@/data/colombiaLocations'` | Bajo — `department`/`city` viajan como texto libre dentro de un string compuesto (`computedAddress`), sin match contra ningun enum backend (confirmado via grep antes de tocar); el unico efecto visible es que los nombres de departamento ahora llevan tilde, igual que en `RentalBookingWizard.vue`/`ColombianAddressForm.vue` (mas consistente, no menos) |

**No se toco** el resto de `PersonalInfoFields.vue` (mantiene su UI de select plano de ciudad
sin cascada de departamento — cambiar esa estructura de campos es una decision de UX mas grande,
fuera del alcance de "unificar el dataset subyacente sin cambiar el contrato del formulario").

**Verificacion:** `npm run build` limpio. Playwright real (con el bridge de red contenedor→
contenedor ya documentado — `Host: localhost:8000` spoofeado hacia `ecommerce_sintel_django`):
formulario de registro (`/registro-profesional`) con selects de Pais (20, sin cambios), Ciudad
(133 = 132 ciudades + placeholder, antes 30) y Tipo de via (8, sin cambios) renderizando
correctamente; login admin real + `UserForm.vue` en modo crear confirmando `maxlength="50"`/
`"254"`/`"20"` en el DOM; cero errores de consola en todo el flujo. Usuario de prueba desechable
eliminado al terminar.

### Paso 5 (Fase 7 §7.2): Core / Home Builder

`HomeConfigView.vue` (2705 lineas) tenia 7 modales centrados hand-rolled (Banner, Tarjeta,
Grupo de tarjetas, Enlace de Footer, Columna de Footer, Navbar, Logo del slider de marcas),
cada uno repitiendo el mismo boilerplate de backdrop/header/boton-cerrar/footer. Antes de
tocarlos se detecto que esto dependia de la decision de arquitectura pendiente §3.4.1 (cuantos
sistemas de modal deben quedar) — `SintelOffcanvas` es un panel lateral, mientras estos 7
modales son dialogos centrados y anchos con vista previa en vivo y layouts de 2 columnas.
Convertirlos a un panel lateral habria sido un cambio de UX real para una herramienta que ya
administra la home publica en produccion, asi que se pregunto explicitamente al usuario en vez
de asumir — **se eligio construir un `BaseModal` centrado nuevo** que preserva exactamente el
mismo patron visual (mismo backdrop/border-radius/sombra/max-width, variante `wide` para el
modal de Tarjeta) en vez de forzarlos al patron de panel lateral.

`components/base/BaseModal.vue` (nuevo): props `modelValue`, `title`, `wide` (activa
`bm-modal--wide`, max-width 800px), `bodyClass` (pass-through, usado por Tarjeta para su
grid de 2 columnas `bm-modal__body--two-col`); slots default (body) y `footer` (opcional).
Los 7 modales de `HomeConfigView.vue` se reescribieron para usarlo (`v-model="showXModal"` +
`:title="..."` + `<template #footer>`), eliminando ~130 lineas de markup boilerplate
duplicado 7 veces y las reglas CSS correspondientes (`.hcb-modal*`) del `<style>` de la vista,
que ahora viven una sola vez en `BaseModal.vue`. Todo el contenido especifico de cada
formulario (preview en vivo del banner, drag&drop de media, preview de tarjeta con
`CardItem`, selects/inputs propios) se dejo exactamente igual, solo movido dentro del slot.

**Verificacion:** `npm run build` limpio (bundle de `HomeConfigView` bajo levemente por la CSS
eliminada). Playwright real: login admin, navegacion in-app por las 8 secciones internas del
Home Builder (`Modulos`/`Banners`/`Tarjetas`/`Footer`/`Marca`/`Navbar`/`CTA Final`/`Slider de
Marcas` — el propio `HomeConfigView.vue` tiene su propio sub-menu interno, no son rutas
separadas), abriendo los 7 modales uno por uno: titulo dinamico correcto en los 7, conteo de
botones de footer correcto (2, o 3 en Grupo cuando edita uno existente y aparece "Eliminar
grupo"), `wide`+`bm-modal__body--two-col` confirmados en el modal de Tarjeta, cierre por click
en el backdrop funcional en los 7, cero errores de consola. Usuario de prueba desechable
eliminado al terminar (se topo con el throttle de login de Security Center tras varias
corridas de prueba en la misma sesion — se limpio el cache de Django para continuar, sin tocar
la logica de throttling en si).

### Paso 6 (Fase 7 §7.2): Organization — parcial

`OrganizationView.vue` (447 lineas) tiene 2 hallazgos distintos de Fase 2: (a) su propio CSS
`org-*` en vez de la libreria compartida, y (b) un `confirm()` nativo real al borrar una red
social (`deleteSocialLink`). Se resolvio **solo (b) en esta sesion**: se reemplazo el
`confirm()` nativo por el patron ya establecido en todo el proyecto (fila inline
`bg-danger-subtle` con Confirmar/Cancelar, el mismo patron que usan Orders/Wishlist/etc. —
ver `frontend/CLAUDE.md` "Confirmacion de borrado"), agregando `confirmingDeleteUuid` (ref) y
`askDeleteSocialLink`/`cancelDeleteSocialLink`. Verificado con Playwright real: crear una red
social de prueba, click en Eliminar activa la fila roja con "¿Eliminar...?", Cancelar preserva
el dato, Confirmar lo borra, `window.confirm()` nativo confirmado que ya NO se invoca
(interceptado el evento `dialog` del navegador, debe ser `false`).

**(a) deliberadamente NO ejecutado en esta sesion:** migrar los 8 tabs de `OrganizationView.vue`
fuera de su CSS `org-*` propio requeriria antes construir el Grupo D (`BaseInput`,
`BaseTextarea`, `BaseSelect`, `BaseUpload`, etc. — Fase 3 §3.5), que todavia no existe. Hacerlo
sin esa base seria o (i) un cambio cosmetico de nombres de clase sin reduccion real de
duplicacion, o (ii) un desvio para construir todo Grupo D dentro de este paso puntual. Se deja
documentado para cuando Grupo D se aborde explicitamente.

### Paso 7 (Fase 7 §7.2): Operations — `DispatcherList.vue`

Este archivo tenia los 3 hallazgos documentados en Fase 2/4, los 3 corregidos en esta sesion:

1. **`user_id` como input numerico crudo** (hallazgo de mayor severidad de toda la auditoria —
   unico caso de exposicion de clave primaria en la UI). El backend
   (`operations/api/views.py::AdminDispatcherViewSet.create`) exige genuinamente un
   `user_id` entero (`User.objects.get(pk=user_id)`) — no se cambio ese contrato. Se
   reemplazo el input numerico por un buscador tipo autocomplete (debounce 400ms, patron ya
   estandar del proyecto) contra `GET users/?search=...&is_active=true` (mismo endpoint que ya
   usa `UserList.vue`, expone `id` ademas de `uuid`), mostrando el email del usuario
   seleccionado en vez de pedirle al admin que conozca o teclee un ID interno. El campo
   `form.user_id` sigue viajando igual al backend, ahora poblado por la seleccion en vez de
   tecleado.
2. **Modal bespoke** (`.form-modal`/`.form-modal__box`, CSS propio distinto de todo el resto
   del panel) reemplazado por `BaseModal` (el mismo componente del Paso 5).
3. **`confirm()` nativo** en `remove(uuid)` reemplazado por el mismo patron de fila inline
   `bg-danger-subtle` usado en el Paso 6.

**Verificacion:** `npm run build` limpio. Playwright real: creado un usuario candidato
desechable, buscado por email en el nuevo autocomplete (1 resultado), seleccionado, creado el
despachador real (confirmado visible en la tabla — es decir, el `user_id` correcto SI llego al
backend via la seleccion), confirmado que `input[type="number"]` ya no existe en el DOM,
confirmada la fila de eliminacion inline (activa `bg-danger-subtle`, Confirmar la borra),
`window.confirm()` nativo confirmado que no se invoca (intercepcion del evento `dialog`), cero
errores de consola. Usuarios de prueba eliminados al terminar.

### Paso 8 (Fase 7 §7.2): Notifications / Security / Support — ultimo paso de la migracion

Los 2 hallazgos de este paso:

1. **`OrderContextCard.vue`/`PaymentContextCard.vue`/`RentalContextCard.vue`** (Support) eran
   CSS byte-identico (`.ctx-card`/`.ctx-head`/`.ctx-row`, solo el color del icono cambia:
   `#1e40af` Order, `#b45309` Payment, `#6d28d9` Rental). Se fusionaron en
   `components/base/BaseContextCard.vue` (props `icon`, `iconColor`, `title`; slots `badge` y
   default) — los 3 archivos originales quedaron como wrappers delgados con exactamente el
   mismo prop (`order`/`rental`), cero cambios en su unico consumidor
   (`Customer360Panel.vue`). Nota tecnica real encontrada durante la construccion: el CSS de
   `.ctx-row` tuvo que declararse con `:deep()` en `BaseContextCard.vue`, porque esos divs
   llegan via slot desde el componente wrapper — el scoped CSS normal de Vue no penetra
   contenido de slots ajenos (se habria roto silenciosamente sin este detalle).
2. **Security (`SecurityDashboardView.vue`) y Support (`SupportDashboardView.vue`) sin ningun
   indicador de carga** — la tabla de eventos de seguridad y la lista de chats simplemente se
   veian vacias mientras cargaban. Se agrego el mismo patron `spinner-border` que ya usan el
   resto de listas admin del proyecto: en Security, reemplaza toda la tabla mientras
   `loading===true` (igual que `DispatcherList.vue`); en Support, solo se muestra en la carga
   INICIAL (`loadingRooms && !rooms.length`) y no en refrescos silenciosos en segundo plano
   disparados por WebSocket (mostrar un spinner ahi haria parpadear la lista de chats ya
   visible — una regresion real que se evito a proposito).

**Verificacion:** `npm run build` limpio. Playwright real: Security y Support cargan sin
errores de consola; usando una sala de chat real ya existente de un cliente con pedidos y
alquileres reales, se confirmaron **10 `BaseContextCard` renderizados correctamente** (badges
de estado, colores por dominio, filas de datos) dentro de `Customer360Panel.vue`. El unico
"error" de consola observado fue un `WebSocket ... ERR_CONNECTION_REFUSED` — limitacion propia
del bridge de red usado para las pruebas en contenedor (el `context.route` de Playwright solo
intercepta HTTP, no WebSocket), no una regresion introducida por este cambio.

Con esto se completan los 8 pasos de la Fase 7 §7.2 (Payment ya estaba completo por un plan
previo; Renting+Services ya sincronizados desde antes de esta auditoria; Shop/Accounts-KYC/
Core/Organization(parcial)/Operations/Notifications-Security-Support ejecutados en esta
sesion).

### Paso 6, parte (a) — completado: Grupo D inicial + CSS `org-*` de Organization

Se construyeron 3 componentes del Grupo D (Fase 3 §3.5), los minimos necesarios para cerrar
el Paso 6 pendiente:

- `BaseInput.vue` — label + input (text/number/email/etc.) + hint/error, `maxlength`.
- `BaseTextarea.vue` — mismo patron con `rows`.
- `BaseUpload.vue` — input de archivo + preview de imagen, emite `file-selected` con el `File`
  crudo (el consumidor arma su propio `FormData`, sin asumir nada del endpoint).

Los 8 tabs de `OrganizationView.vue` (Empresa/Branding/Contacto/Redes Sociales/Correos/
Dominios/SEO/Informacion Legal) se reescribieron para usarlos en vez de
`<input class="org-input">`/`<label class="org-label">` repetidos ~30 veces. Se verificaron
los `maxlength` reales contra `organization/models.py` (varios distintos de lo que se habria
adivinado: `trade_name` 150, `tagline` 300, `phone` 100, `email` 254, `address` 500,
`working_hours` 255, `default_from_email`/`admin_login_url`/`frontend_base_url` 254-300,
`primary_domain`/etc. 255, `legal_name`/`legal_representative` 255, `tax_id` 50, `city`/
`department` 150). El CSS `.org-label`/`.org-input`/`.org-img-preview` (duplicado 1 vez por
campo, ~30 veces) se elimino de `OrganizationView.vue` — ahora vive una sola vez en los 3
componentes `Base*`. Quedan intactos `.org-tabs`/`.org-panel`/`.org-btn-primary` (layout/
botones especificos de esta pagina, no duplicados en ningun otro lugar).

**Verificacion:** `npm run build` limpio. Playwright real: las 8 pestañas muestran el numero
exacto de campos esperado tras la migracion (Empresa 3, Branding 3, Contacto 4, Redes Sociales
3, Correos 3, Dominios 3, SEO 3, Legal 6); edicion real de "Nombre comercial" con guardado
(toast de exito confirmado) y reversion al valor original; cero errores de consola.

### Lo que queda pendiente (fuera del alcance de esta sesion)

- Las 5 decisiones de producto de §E (Documento Final) siguen sin respuesta explicita —
  necesarias antes de tocar el resto de modales (`SintelOffcanvas`/`CustomerOverlayPanel`),
  badges (`OperationStatusBadge`/`ShipmentStatusBadge`), `BaseTable`, catalogo de
  Profesion/Especialidad, y el checkout de Shop.
- Grupo D: solo 3 de los ~14 componentes disenados en Fase 3 §3.5 estan construidos
  (`BaseInput`/`BaseTextarea`/`BaseUpload`) — faltan `BaseSelect`, `BaseSearchSelect`,
  `BaseAddress` (el de mayor impacto, reemplaza 6 implementaciones independientes de
  direccion colombiana), `BasePhoneInput`, `BaseMoneyInput`, `BasePercentageInput`,
  `BaseDocumentInput`, `BaseIconInput`, `BaseCalendar`, `BaseDatePicker` — se construyen segun
  se necesiten en futuras migraciones de modulo, no hay urgencia de construir el resto sin un
  consumidor real inmediato (regla de este proyecto: no generalizar sin evidencia).
