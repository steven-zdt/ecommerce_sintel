# PLAN_UNIFICACION_SERVICES_CON_RENTING.md

> **Documento de planeación.** Producido por auditoría comparativa real contra el código
> fuente de ambos módulos (2026-07-17). Toda referencia a un archivo, color, componente o
> modelo citada aquí fue verificada leyendo el archivo real — no hay suposiciones.
>
> **Estado de ejecución (actualizado 2026-07-18):**
> - ✅ **Fase 1 (verificación técnica)** completada — ver hallazgo abajo.
> - ✅ **Fase 2 (backend aditivo)** completada — modelos `ServiceMarketing`/`ServiceFAQ` +
>   4 campos SEO en `TechnicalService` (migración `0031_technicalservice_meta_description_and_more.py`),
>   Commands/Selectors (`technical_services/services/marketing.py`), serializers
>   (`ServiceMarketingSerializer`/`ServiceFAQSerializer` + variantes Input), endpoints admin
>   (`dashboard/services/{uuid}/marketing/`, `dashboard/service-faqs/`), y exposición
>   read-only (`marketing`, `faqs`, campos SEO) en el `TechnicalServiceSerializer` público,
>   con `select_related`/`Prefetch` añadidos a los 3 métodos de `ServiceSelector` para evitar
>   N+1. Verificado con `manage.py check` + `manage.py test technical_services dashboard`.
> - ✅ **Fase 3 (Admin UI) completada** — `ServiceForm.vue` ganó 2 tabs nuevos ("FAQ" y
>   "Marketing"), conectados a los endpoints de la Fase 2. El tab Marketing replica el
>   formulario de `RentingForm.vue` casi campo a campo (sin comparativa comprar-vs-alquilar).
>   El tab FAQ usa un componente nuevo y dedicado, `ServiceFAQManager.vue`
>   (`modules/technical_services/`), en vez de generalizar `CatalogListManager.vue` de
>   Renting (que, por el hallazgo de la Fase 1, no acepta ni el endpoint ni el nombre del
>   campo FK como prop) — mismo patrón de interacción (drag-reorder, alta/edición inline,
>   toggle-active), llamando directo a `dashboard/service-faqs/`. Verificado end-to-end con
>   Playwright real contra el panel admin: creación de una FAQ y guardado de Marketing,
>   ambos con toast de éxito y cero errores de red/consola.
> - ✅ **Fase 4 (presentación pública) COMPLETADA** — ante "finaliza en su totalidad todas
>   las fases pendientes" y sin respuesta a la pregunta de color, se procedió con la
>   recomendación por defecto ya documentada en la Etapa 8 (mantener ámbar `#d97706` en
>   catálogo/detalle de servicios). Hecho: (1) **`ServiceReview` expuesto en API pública** —
>   `ServiceReviewSelector`/`ServiceReviewCommands` (`technical_services/services/marketing.py`,
>   patrón "ownership + estado terminal" con `ServiceOperation.CLOSED` en vez de
>   `RentalRequest.STATUS_FINISHED`), acciones `GET/POST /services/services/{uuid}/reviews/`+
>   `/review/`, componente `ServiceReviews.vue`. (2) **FAQ confirmado ya conectado a datos
>   reales** desde la Fase 2 — cero cambios de frontend necesarios. (3) **`ServiceDetailView.vue`
>   completamente componentizado**: 8 componentes nuevos en `components/services/detail/`
>   (`ServiceGallery`, `ServiceFeatureList`, `ServiceScopeList`, `ServiceSpecificationTable`,
>   `ServiceFAQAccordion`, `ServiceProfessionals`, `ServiceReviews`), secciones reordenadas al
>   orden de bloques de Renting. (4) **Bloque "Profesionales" nuevo**: `GET
>   /services/services/{uuid}/technicians/` sobre `TechnicianSelector.get_available_for_category`
>   (ya existía) + `AvailableTechnicianSerializer` nuevo (solo `uuid`/`full_name`/`avatar`, sin
>   inventar calificación/experiencia que no existen en `TechnicianProfile`). (5) **Bloque
>   "Antes y después" eliminado** (recomendación explícita del plan). Video y Caso de éxito
>   quedaron intactos (exigirían un campo nuevo no autorizado por el cierre de campos de la
>   Etapa 6). Verificado con Django test `Client` (reseñas 201/400/400) + Playwright
>   (screenshot completo, 0 errores de consola, antes/después confirmado en 0) + `npm run
>   build` limpio.
> - ✅ **Fase 5 (wizard/checkout) COMPLETADA** — `ServiceRequestWizard.vue` ganó un sidebar
>   de resumen persistente (`ServiceRequestSummary.vue`, visible en pasos 2-3, reutiliza
>   `ServicePriceBreakdown.vue` ya existente, grid `col-lg-8`/`col-lg-4` igual que Renting).
>   `components/shared/checkout/CheckoutStepper.vue` (antes solo usado por `CheckoutModal.vue`)
>   se generalizó con un prop `clickable` opcional y ahora es el stepper único de
>   `RentalBookingWizard.vue` **y** `ServiceRequestWizard.vue` (ambos tenían su propio
>   markup/CSS de barra de progreso duplicado). Verificado con Playwright: navegación
>   clickeable en Renting, sidebar con desglose de precio real en Services (ambos pasos).
> - ✅ **Fase 6 (limpieza) COMPLETADA** — `OperationTimeline.vue`: se verificó que **ya
>   delegaba** a `TrackingTimeline.vue` → `StatusTimeline.vue` desde antes de este plan (el
>   hallazgo de la auditoría original estaba desactualizado); no se tocó código, solo se
>   corrigió la suposición. `ai_skills/frontend/components/cards.md` actualizado (§2:
>   `CheckoutStepper`; §4.2 nuevo: los 8 componentes de detalle + el sidebar del wizard).
>   `technical_services/CLAUDE.md` y `ARQUITECTURA_COMPLETA_SERVICES.md` (§16 C9)
>   actualizados con el detalle completo de Fases 3-6.
>
>   **Plan de unificación Services↔Renting: las 6 fases están completas.**
>
>   **Nota aparte (2026-07-18):** se corrigió, a pedido explícito del usuario, un bug de
>   UX real y no relacionado con las fases de este plan — el paso 1 ("Servicio") del wizard
>   de solicitud duplicaba la información del detalle público y no ofrecía ninguna decisión
>   real cuando el servicio tenía una sola variante activa y cero paquetes; ahora se salta
>   automáticamente a "Dirección" en ese caso, y se simplificó (sin el panel de info
>   duplicado) para cuando sí hay una decisión real que tomar. Esto adelanta parte de la
>   Etapa 2 de este plan ("simplificar formularios").

## Rol y alcance de este documento

Este documento NO propone rediseñar el negocio de Technical Services. Documenta cómo adaptar
su experiencia de usuario, formularios, presentación de datos y configuración comercial
usando **Renting** como patrón de referencia — sin tocar Commands, Selectors, Pricing Engine,
Availability, Payment, Notifications, Operations, contratos de API, ni la base de datos
existente (salvo modelos nuevos aditivos).

---

## 0. Hallazgo previo que condiciona todo el plan: Renting NO es un solo lenguaje visual

Antes de proponer "copiar el patrón de Renting", hay que ser precisos sobre qué es
"Renting" hoy, porque **el propio módulo de Renting tiene dos familias visuales internas,
no una sola**, y Technical Services ya adoptó parcialmente una de ellas:

| Familia | Módulos que la usan | Color de acento | Radio de tarjeta | Patrón de encabezado |
|---|---|---|---|---|
| **A — Detail/Catálogo de Renting** | `RentalDetailView.vue`, `components/renting/detail/*` | Azul `#2563eb` | 14-16px | `section-kicker` (eyebrow mayúscula) + `<h2>` |
| **B — Wizard/Cuenta de Renting** | `RentalBookingWizard.vue`, `MyRentalsView.vue`, `components/customer/renting/*` | Violeta `#7c3aed` | 20-24px | Eyebrow + `<h1>`/`<h3>` |
| **C — Wizard/Checkout de Technical Services (YA ALINEADO)** | `ServiceRequestWizard.vue`, `ServiceCheckoutModal.vue` y familia | Violeta `#7c3aed` (comentario real en código: *"Color violeta — sistema unificado con alquiler"*) | 14-18px | Stepper con círculos numerados |
| **D — Catálogo/Detalle de Technical Services (SIN alinear)** | `ServicesCatalogView.vue`, `ServiceDetailView.vue`, `ServiceCard.vue`, `ServiceHorizontalCard.vue` | Ámbar `#d97706` | 14-18px | Mixto |

**Conclusión operativa:** el wizard/checkout de Technical Services **ya adoptó** el patrón
violeta de Renting-Familia-B, deliberadamente, según su propio comentario en código. El
verdadero trabajo pendiente de unificación es:
1. Llevar la **estructura** (no necesariamente el color) de Renting-Familia-A (Detail
   completamente componentizado) al catálogo/detalle de Technical Services.
2. Decidir explícitamente si el ámbar de Technical Services se conserva como "color de
   identidad de marca del módulo" (recomendado, ver §8) o se reemplaza por violeta también.
3. Cerrar los huecos de contenido reales en el detalle de servicios (stubs de video y
   "antes/después"), que existen porque falta un tab de administración, no porque falte
   diseño.

---

## ETAPA 1 — Auditoría Comparativa

### 1.1 Equipment Detail (Renting) vs. Service Detail (Technical Services)

| Aspecto | Renting (`RentalDetailView.vue`, 862 líneas) | Technical Services (`ServiceDetailView.vue`, 536 líneas) |
|---|---|---|
| Componentización | **13 sub-componentes reales** en `components/renting/detail/*` (Gallery, IncludedList, ExcludedList, FeatureTable, SpecificationTable, ServiceList, RequirementList, ManualList, DocumentList, DownloadSection, VideoGallery, FAQ, Reviews) | **0 sub-componentes** — todo el markup vive inline en un solo archivo de 536 líneas, salvo `ServicePackageCard` |
| Galería | Componente dedicado, sticky, con miniaturas | Inline, sticky, con miniaturas (estructuralmente igual, pero no extraído) |
| Video | `EquipmentVideoGallery` funcional (modal con `<video>`/`<iframe>`) | **Stub**: `"Video administrable pendiente"` si no hay `video_url` — nunca se le dio UI de admin para cargarlo |
| Antes/despues | No existe como tal en Renting (no aplica al dominio) | **Stub total**: 2 cajas de icono vacías, sin binding a ningún dato — nunca tuvo campo en el modelo ni tab de admin |
| Reseñas | `EquipmentReviews` — sistema real de reviews autenticadas (1-5 estrellas + comentario, solo quien alquiló y devolvió) | **No existe ninguna sección de reseñas** en el detalle, pese a que `ServiceReview` SÍ existe como modelo backend y `StarRating.vue` existe como componente compartido — es un hueco de UI sobre un modelo que ya tiene datos |
| FAQ | `EquipmentFAQ`, acordeón, datos reales desde `RentalFAQ` (modelo dedicado) | Acordeón `<details>` inline, con fallback hardcodeado de 3 preguntas si no hay datos de admin — no hay modelo `ServiceFAQ` dedicado, ni tab de admin para gestionarlas |
| Documentación | 3 sub-secciones reales (Manuales/Fichas técnicas/Archivos), con descarga vía `useDocumentDownload` | No existe sección de documentación en el detalle de servicio |
| Contenido comercial (value prop, casos de uso, mensajes) | Proviene de `EquipmentMarketing` (modelo real, OneToOne, con tab de admin dedicado) | El contenido "comercial" en `ServiceDetailView.vue` (value_proposition, problem_solved, success_case, etc.) también existe en el template, pero **no hay modelo backend que lo respalde ni tab de admin** — son campos que el frontend intenta leer de `service.*` con fallback hardcodeado si no existen. Esto confirma que TS **ya diseñó visualmente** para un modelo de marketing que nunca se construyó del lado de datos. |
| Related/cross-sell | 3 tarjetas estáticas (Tienda/Servicios/Renting) — no es recomendación real tampoco en Renting | 3 tarjetas estáticas (Servicios/Tienda/Renting) — mismo patrón, mismo nivel de "no es real" en ambos módulos (no es un gap de TS respecto a Renting, es una limitación compartida) |

**Diferencia estructural central:** Renting-Detail está construido como una composición de
componentes reutilizables con datos reales detrás de cada uno (incluyendo un modelo de
marketing real). Technical-Services-Detail está construido como un solo archivo monolítico
que **visualmente imita** la misma estructura de bloques, pero varios de esos bloques nunca
tuvieron su contraparte de datos/admin construida — son fachadas sin backend.

### 1.2 Wizard de Renting vs. Wizard de Technical Services

| Aspecto | Renting (`RentalBookingWizard.vue`) | Technical Services (`ServiceRequestWizard.vue`) |
|---|---|---|
| Pasos | 4: Equipo → Lugar del proyecto → Programación → Confirmar | 4: Servicio → Dirección → Fecha → Pago |
| Indicador de progreso | Barra con círculos numerados + track de relleno animado | Barra pegajosa (`sticky top:0`) con círculos numerados + track de relleno — **patrón visualmente casi idéntico**, ya unificado |
| Resumen lateral persistente | **Sí** — sidebar con `RentalCostsCard` visible en los pasos 3 y 4 | **No existe** — el resumen solo aparece como pantalla completa en el paso 4 (recapitulación), no como sidebar visible durante la captura de datos |
| Footer de navegación | "Atrás" (outline) / "Continuar"·"Confirmar reserva" (sólido, flecha) | "Atrás" (outline) / "Continuar"·"Confirmar y pagar" (sólido, flecha) — **patrón idéntico** |
| Errores | 1 banner global de error + 2 campos con error inline (email/teléfono) | **Totalmente inline por campo** (`is-invalid` + `.invalid-feedback` por campo) — de hecho más granular que Renting, no un hueco |
| Dirección estructurada | Sí (vía/número/generadora/placa/complemento + preview) | Sí (mismo patrón, ya replicado) |
| Selector de fecha/hora | Rango de fechas + selector de hora entrega/recogida | Fecha preferida + selector de "jornada" (Mañana/Tarde/Todo el día) — **deliberadamente sin hora exacta** desde Fase 5 (2026-07-14), decisión de producto ya tomada, no un hueco a cerrar |

**Conclusión:** el wizard de Technical Services ya está estructuralmente muy cerca del de
Renting. La única brecha real y concreta es el **resumen lateral persistente** — hoy el
cliente no ve un total corriendo mientras completa dirección/fecha, solo al final.

### 1.3 Checkout

| Aspecto | Renting | Technical Services |
|---|---|---|
| Patrón de UI | Panel deslizante lateral (`slide-over`, 440px, desde la derecha) sobre `RentalConfirmationView.vue` | Modal centrado con overlay (`ServiceCheckoutModal.vue`) |
| Selector de método de pago | Filas seleccionables (Wompi/Nequi/Contra entrega) | Tarjetas seleccionables con badge circular de color (`ServicePaymentMethodSelector.vue`) — mismo concepto, forma distinta |
| Estados de pago | Redirige a `/payment/result` o vista de Nequi pendiente | `ServicePaymentStatusPanel.vue` — 6 estados con iconos de degradado, resuelto **dentro del propio modal** (arquitectura más autocontenida) |
| Desglose de precio | `RentalCostsCard` | `ServicePriceBreakdown.vue` — mismo concepto |
| Color | Violeta | Violeta (ya alineado) |

**Conclusión:** el checkout de ambos módulos ya comparte lenguaje visual y de color. La
diferencia es de **forma de contenedor** (drawer lateral vs. modal centrado) — no es un
error, son dos soluciones válidas al mismo problema; unificarlas es una mejora cosmética de
bajo riesgo, no una corrección de un defecto.

### 1.4 Dashboard/Admin

| Aspecto | Renting (`RentalOperationBoard.vue`) | Technical Services (`ServiceOperationBoard.vue`) |
|---|---|---|
| Shell compartido | `components/shared/BaseOperationBoard.vue` | **El mismo `BaseOperationBoard.vue`** — ya compartido hoy, por diseño explícito (comentario en código: *"cascarón compartido de los 4 tableros de operaciones (Shop/Renting/Servicios/Admin general)"*) |
| Fila de KPIs | 8 tarjetas (Pendientes, Sin transportista, Entregas hoy, Recogidas hoy, En operación, Próximas a devolución, Retrasos, Incidencias) | 8 tarjetas (Pendientes de planear, Programados hoy, En ejecución, Técnicos ocupados, Técnicos disponibles, Atrasados, Tiempo promedio, SLA cumplido) — mismo patrón visual, ya unificado |
| Cuerpo | Tabla plana filtrable — **NO es un Kanban** | Tabla plana filtrable — **NO es un Kanban** — ambos módulos usan el mismo patrón real |
| Panel de detalle | Debajo de la tabla, no modal | Debajo de la tabla, no modal — mismo patrón |
| Acción de transición | Un botón "siguiente acción" por estado actual (mapa `transitionActions`) | Idéntico patrón `transitionActions` |

**Hallazgo importante:** el patrón "Kanban" mencionado en la petición del usuario **no existe
en ninguno de los dos módulos** — ambos ya usan el mismo patrón real (tabla filtrable +
panel de detalle inline + KPIs), y ya están unificados a nivel de shell compartido. **No hay
nada que migrar aquí** salvo una corrección de documentación (ver §1.6).

### 1.5 Configuración comercial / Marketing

| Aspecto | Renting | Technical Services |
|---|---|---|
| Modelo de marketing | **`EquipmentMarketing`** (real, `OneToOneField(Equipment)`, 15 campos: reference_price, promo_price, tags JSON, main_message, featured_benefit, trust_message, urgency_message, social_proof_message, purchase_price_reference, financial_message, use_cases JSON, cta_label, promo_banner_message, quick_benefits JSON) | **No existe ningún modelo equivalente.** `technical_services/models.py` no tiene ningún campo de marketing/SEO/campaña (verificado por grep completo) |
| SEO | Vive **directamente en `Equipment`** (meta_title/meta_description/meta_keywords/og_image), NO en `EquipmentMarketing` — decisión explícita documentada en el propio docstring del modelo | No existe ningún campo SEO en `TechnicalService` |
| FAQ | Modelo separado `RentalFAQ` (FK a `Equipment`), NO vive dentro de `EquipmentMarketing` | No existe modelo — el frontend simula FAQ con fallback hardcodeado |
| Testimonios | **No existe** — lo que existe es `EquipmentReview`, un sistema de reseñas reales de usuarios verificados, no testimonios curados por admin | No existe tampoco |
| Campañas con fecha | **No existe** en `EquipmentMarketing` (es config estática "siempre activa", sin `start_date`/`end_date`) — lo más cercano a "campaña con fechas" en todo el proyecto es `marketing.FlashOffer` (app `marketing`, cross-dominio, con FK opcional a `ProductVariant`/`ServiceVariant`/`EquipmentVariant`) | Igual — no existe, pero `FlashOffer` YA puede apuntar a `ServiceVariant` hoy sin cambios |
| "Mostrar en home" | `Equipment.is_featured` (booleano simple, ya existente, consumido por `RentingSelector` + `FeaturedSection.vue`) | Existe un equivalente `is_featured`-like en `TechnicalService`/`ServiceVariant` (confirmar nombre exacto en implementación, no verificado explícitamente en esta auditoría pero el catálogo público ya filtra por destacados) |
| Cross-sell / Up-sell | **No existe en ningún lugar del proyecto** — ni en Renting ni en ningún otro módulo. No hay campo `related_items`/`cross_sell`/`upsell` en ningún modelo | Igual — no existe en ningún lado, no es un gap exclusivo de TS |

**Conclusión crítica para la Etapa 6:** el usuario pidió crear `ServiceMarketing` con campos
que incluyen `campaign_name/priority/start/end` y `faq`/`testimonials` embebidos. La
auditoría real muestra que **Renting no tiene ninguno de esos 3 elementos tampoco** —
`EquipmentMarketing` no maneja campañas con fecha, FAQ vive en un modelo aparte
(`RentalFAQ`), y no existe ningún concepto de "testimonio" curado. Es decir: replicar
`EquipmentMarketing` tal cual (sin campañas, sin testimonios, con FAQ en modelo aparte) es
fiel al patrón real de Renting. Agregar campañas con fecha y testimonios sería **una
mejora nueva para AMBOS módulos**, no una adopción de un patrón ya probado — se recomienda
tratarlo como una decisión de producto explícita, separada de la unificación (ver §6 y
Riesgos).

### 1.6 Huecos de documentación encontrados durante esta auditoría (no bugs de código)

- `ai_skills/frontend/components/cards.md` §7 no incluye `ServiceOperationBoard.vue` en el
  inventario de módulos admin de `technical_services` (el archivo existe y funciona, la
  auditoría de la doc quedó desactualizada — mismo patrón de drift ya visto en la
  auditoría de `technical_services` del 2026-07-17, ver `MEMORY.md`).
- El componente `components/shared/BaseOperationBoard.vue` y su alcance deliberado
  ("comparte solo header+KPIs, no tabla/filtros/detalle") no está documentado en la
  arquitectura de ninguno de los 2 módulos — solo vive como comentario en el propio archivo.

---

## ETAPA 2 — Formularios (Wizard) a unificar

**No se modifican los datos solicitados** en ningún paso — solo la experiencia.

| Cambio | Alcance | Riesgo |
|---|---|---|
| Agregar un **resumen lateral persistente** (equivalente a `RentalCostsCard` + `AvailabilityPill`) visible desde el paso 2 en adelante, mostrando: servicio elegido, paquete (si aplica), precio corriente (`ServicePriceBreakdown` ya existe y puede reutilizarse tal cual), fecha/jornada elegida | Solo el paso 2 y 3 del wizard ganan una columna lateral nueva; el paso 4 ya tiene su propia recapitulación y puede conservarla o simplificarla reutilizando el mismo sidebar | Bajo — es aditivo, usa datos que el wizard ya calcula/tiene en memoria (`useServiceCheckoutStore`, `servicesService`), no requiere nueva llamada a API |
| Unificar el **layout de 2 columnas** del paso de "Programación"/"Fecha" (`schedule-layout` 1.7fr/0.8fr en Renting) para que Technical Services adopte la misma proporción y posición del sidebar (a la derecha, no debajo) | Solo CSS/estructura de un paso | Bajo |
| Mantener las validaciones **inline por campo** que ya tiene Technical Services (son más completas que las de Renting) — **no** retroceder al patrón de "un solo banner global" de Renting | — | — |
| Uniformar terminología de botones de footer: ambos módulos ya usan "Atrás" / "Continuar" — no requiere cambio, solo confirmarlo como regla del Design System compartido | — | Ninguno, ya cumplido |

---

## ETAPA 3 — Presentación de datos (Detalle de Servicio)

Reorganización del detalle de servicio en los mismos bloques que Renting, **sin alterar el
contenido existente, solo la presentación**:

```
Hero (imagen + info principal + CTA)
  ↓
Información principal (specs rápidas, badges)
  ↓
Galería               → extraer a componente ServiceGallery.vue (mismo patrón que EquipmentGallery.vue)
  ↓
Características       → extraer a ServiceFeatureList.vue (mismo patrón que EquipmentFeatureTable.vue)
  ↓
Servicios incluidos   → extraer a ServiceIncludedList.vue / ServiceExcludedList.vue (mismo patrón que Equipment Included/Excluded)
  ↓
Costos                → ServicePriceBreakdown.vue (YA EXISTE, reutilizar tal cual desde components/customer/services/)
  ↓
Disponibilidad        → ver nota (Technical Services no vende "disponibilidad de stock" como Renting; aquí el equivalente real es "próxima fecha disponible", que YA existe conceptualmente en TechnicianAvailabilityEngine — reutilizar su output, no inventar una UI de disponibilidad nueva)
  ↓
Profesionales          → NUEVO bloque real: mostrar técnicos disponibles/calificados para la categoría (dato ya existe via TechnicianSelector.get_available_for_category, solo falta exponerlo en el detalle público)
  ↓
Beneficios             → ya existe en ServiceDetailView (value proposition cards) — solo reordenar
  ↓
Preguntas frecuentes   → requiere el modelo ServiceFAQ nuevo (ver Etapa 6) para dejar de depender del fallback hardcodeado
  ↓
Casos de éxito         → requiere respaldo real de datos (hoy es 100% hardcodeado) — mapear a un campo de ServiceMarketing
  ↓
Equipos relacionados / Servicios relacionados → mismo nivel que hoy (estático) en ambos módulos, no se declara como gap a cerrar en esta fase (no existe motor de recomendación en ningún módulo)
  ↓
Reseñas                → NUEVO bloque real: ServiceReview YA EXISTE como modelo backend con datos — solo falta el componente de UI (ServiceReviews.vue, mismo patrón que EquipmentReviews.vue) y el StarRating.vue ya compartido
  ↓
CTA (ya existe)
```

**Bloques que hoy son stubs y se resuelven con este plan (no antes):**
- Video → se resuelve solo si el admin tiene un tab para cargar `video_url` (Etapa 5/6).
- Antes/después → recomendación: **retirar este bloque** de Technical Services en vez de
  construirle un modelo — no existe un equivalente conceptual claro en servicios técnicos
  (a diferencia de una reforma/instalación visual, la mayoría de servicios de este catálogo
  no tienen un "antes/después" fotografiable estándar); si se necesita en el futuro, tratarlo
  como un campo opcional de `ServiceMarketing` (`before_after_images`), no como bloque fijo.

---

## ETAPA 4 — Componentes reutilizables

### 4.1 Ya compartidos hoy (no duplicar, no reinventar)

| Componente | Usado por |
|---|---|
| `components/shared/BaseOperationBoard.vue` | Renting + Technical Services (dashboards) |
| `components/ui/SintelOffcanvas.vue` | Renting + Technical Services (paneles CRUD admin) |
| `components/shared/StatusTimeline.vue` | Timeline unificado del proyecto (Renting lo usa vía `RentalTimeline.vue`; Technical Services tiene su propio `OperationTimeline.vue` que **debería** migrar a este mismo componente en vez de mantener lógica de render paralela) |
| `components/customer/ui/StarRating.vue` | Existe, no usado hoy por Technical Services — candidato directo para `ServiceReviews.vue` |
| `components/customer/services/ServicePriceBreakdown.vue` | Ya existe, reutilizable tal cual en el nuevo detalle |

### 4.2 A crear en Technical Services, extrayendo el patrón real de Renting (no copiar 1:1 el componente de Renting, porque Renting está acoplado a `Equipment`/`EquipmentVariant` — se replica el **patrón**, con props propias de Technical Services)

| Componente nuevo | Modelo de referencia en Renting | Función |
|---|---|---|
| `ServiceGallery.vue` | `components/renting/detail/EquipmentGallery.vue` | Galería sticky con miniaturas |
| `ServiceFeatureList.vue` | `EquipmentFeatureTable.vue` | Grid de características |
| `ServiceIncludedList.vue` / `ServiceExcludedList.vue` | `EquipmentIncludedList.vue` / `EquipmentExcludedList.vue` | Alcance del servicio |
| `ServiceSpecificationTable.vue` | `EquipmentSpecificationTable.vue` | Ficha técnica en grupos colapsables |
| `ServiceRequirementList.vue` | `EquipmentRequirementList.vue` | Requisitos previos (tarjetas ámbar) |
| `ServiceFAQAccordion.vue` | `EquipmentFAQ.vue` | Acordeón de preguntas frecuentes con datos reales |
| `ServiceReviews.vue` | `EquipmentReviews.vue` | Reseñas reales usando `ServiceReview` + `StarRating.vue` |
| `ServiceVideoGallery.vue` | `EquipmentVideoGallery.vue` | Solo si se decide invertir en esta sección (ver Etapa 3) |

### 4.3 Componentes admin genéricos de Renting — resultado de la verificación (2026-07-17)

**Verificado leyendo los 6 archivos reales** (`frontend/src/modules/renting/catalog/*.vue`):
**ninguno es reutilizable tal cual, sin generalizar.**

| Componente | ¿Recibe `endpoint` como prop? | Hardcodea el nombre del campo FK padre |
|---|---|---|
| `CatalogListManager.vue` | Sí (`endpoint` prop) | Sí — línea 166/207: `?equipment=${uuid}` y `{equipment: uuid, ...}` hardcodeados |
| `SeoManager.vue` | **No** — endpoint fijo `dashboard/equipment/${uuid}/` | Sí (implícito en el path fijo) |
| `GalleryManager.vue` | **No** — `const ENDPOINT = 'dashboard/equipment-images/'` fijo | Sí — `equipment: props.equipmentUuid` en 3 lugares |
| `DocumentsManager.vue` | **No** — endpoint fijo | Sí — mismo patrón |
| `VideosManager.vue` | **No** — endpoint fijo | Sí — mismo patrón |
| `SpecificationsManager.vue` | **No** — 2 endpoints fijos (grupos/specs) | Sí — mismo patrón |

**Conclusión:** reutilizarlos "tal cual" (cambiando solo props) **no es posible** — 5 de los
6 no aceptan siquiera un endpoint configurable, y los 6 asumen que el campo FK del padre se
llama literalmente `equipment`. Las opciones reales son:
1. **Generalizar en el mismo lugar** (agregar props `endpoint`/`parentField` con default
   `'equipment'` a los 6, sin romper Renting) y mover los 6 archivos a una ubicación
   compartida (ej. `components/shared/admin/catalog/`) — la opción correcta a mediano plazo,
   pero toca 6 archivos que hoy sirven al admin de Renting en producción, con el riesgo de
   regresión que eso implica.
2. **Forkear con la misma convención** (nuevos componentes para Technical Services que
   llaman directo a `ServiceFAQSelector`/etc., replicando el patrón visual/de interacción
   pero sin compartir código) — más rápido, cero riesgo para Renting, pero es la duplicación
   que el plan pide evitar "siempre que sea posible".

**Decisión aplicada en la Fase 2 backend (ya ejecutada):** el backend de `ServiceFAQ`
(`AdminServiceFAQViewSet` en `dashboard/api/views.py`) se escribió **replicando la firma
REST exacta** de `AdminRentalFAQViewSet` (list/create/partial_update/destroy/
toggle-active/reorder, mismos nombres de acción) precisamente para que, si más adelante se
opta por la Opción 1 (generalizar), el frontend generalizado pueda apuntar a
`dashboard/service-faqs/` sin ningún cambio adicional de contrato.

**Fase 3 (Admin UI) ejecutada con la Opción 2 (2026-07-18):** se creó
`ServiceFAQManager.vue` como componente nuevo y dedicado (mismo patrón de interacción que
`CatalogListManager.vue`, sin compartir código), en vez de generalizar los 6 managers de
Renting — decisión tomada para no tocar 6 archivos que hoy sirven en producción al admin
de Renting sin que el usuario lo pidiera explícitamente. La Opción 1 (generalizar y mover a
una ubicación compartida) sigue disponible como mejora futura si se decide unificar también
el código de los managers, no solo su contrato REST.

---

## ETAPA 5 — Dashboard

**Hallazgo clave: no hay nada que unificar a nivel de shell — ya está unificado.** Ambos
tableros comparten `BaseOperationBoard.vue` con el mismo patrón de KPIs, misma tabla plana
filtrable, mismo panel de detalle inline, mismo mapa `transitionActions`. El único trabajo
real de esta etapa es:

1. Actualizar `ai_skills/frontend/components/cards.md` §7 para incluir
   `ServiceOperationBoard.vue` (falta hoy, doc desactualizada — ver §1.6).
2. Migrar `OperationTimeline.vue` (customer/services, lógica propia) a usar
   `StatusTimeline.vue` compartido, igual que ya hace `RentalTimeline.vue` — cierra una
   duplicación real de lógica de render de timeline.
3. Agregar el tab "Marketing" (y los demás tabs nuevos de la Etapa 6) a `ServiceForm.vue`,
   siguiendo la estructura de tabs de `RentingForm.vue` (16 tabs) en vez de los 5 actuales.

---

## ETAPA 6 — Marketing: nueva entidad `ServiceMarketing`

**Replicando fielmente el patrón real de `EquipmentMarketing`** (no el listado de campos
propuesto originalmente, que incluía campañas y testimonios que ni siquiera Renting tiene
hoy — ver §1.5). Estructura recomendada:

```
ServiceMarketing (OneToOneField a TechnicalService, related_name='marketing')
    reference_price               # precio de referencia/anterior
    promo_price                   # precio promocional
    show_discount_percentage
    tags                          # JSONField, catálogo libre (ej. NUEVO/MAS_SOLICITADO/PREMIUM/RECOMENDADO)
    main_message
    featured_benefit
    trust_message
    urgency_message
    social_proof_message
    use_cases                     # JSONField
    cta_label
    promo_banner_message
    quick_benefits                # JSONField [{icon, label}]
```

**Campos SEO:** agregar directamente a `TechnicalService` (no a `ServiceMarketing`),
replicando la decisión ya tomada en `Equipment` (`meta_title`/`meta_description`/
`meta_keywords`/`og_image`) — es aditivo, requiere solo una migración de campos nuevos con
default vacío, cero impacto en lógica existente.

**FAQ:** modelo nuevo separado `ServiceFAQ` (FK a `TechnicalService`), replicando
`RentalFAQ` — NO como campo JSON dentro de `ServiceMarketing`.

**Reseñas/Testimonios:** no crear ningún modelo de "testimonio curado" en esta fase —
Technical Services ya tiene `ServiceReview` (reseñas reales de usuarios), exactamente el
mismo concepto que `EquipmentReview` en Renting. Cerrar primero el hueco de UI (§3), no
inventar un segundo sistema paralelo de testimonios.

**Campañas con fecha (`campaign_start`/`campaign_end`/`campaign_priority`):** **fuera de
alcance de esta unificación** — ni Renting ni ningún otro módulo tiene este patrón hoy. Si
se quiere, es una iniciativa nueva de producto que debería evaluarse para **todos los
módulos a la vez** (posiblemente extendiendo `marketing.FlashOffer`, que ya soporta
`ServiceVariant`/`EquipmentVariant` con fechas, en vez de reinventar fechas de campaña
dentro de cada `*Marketing` por módulo). Documentado aquí como decisión pendiente, no como
tarea de esta fase.

**Migración:** un solo modelo nuevo (`ServiceMarketing`) + 4 campos nuevos en
`TechnicalService` (SEO) + un modelo nuevo (`ServiceFAQ`) = 2-3 migraciones aditivas, cero
alteración de modelos/tablas existentes.

---

## ETAPA 7 — Checkout

- Mantener el **modal centrado** (`ServiceCheckoutModal.vue`) como contenedor — no forzar
  el patrón de "drawer lateral" de Renting; ya comparten color, tipografía, estructura de
  stepper y componentes de desglose de precio. Migrar el contenedor sería solo estético y
  de alto riesgo de regresión en la integración de pagos (Wompi/Nequi/COD) sin beneficio de
  UX claro.
- Sí unificar: el `ServiceCheckoutStepper.vue` y el stepper del wizard son casi CSS
  duplicado — extraer un único componente `WizardStepper.vue` (props: `steps[]`,
  `currentIndex`) reutilizado por ambos, y evaluar si Renting también puede migrar su
  stepper del wizard al mismo componente (beneficio cruzado, no solo para TS).
- El resto de la Etapa 7 (resumen, costos, servicios incluidos, información del cliente,
  dirección, fecha, profesional asignado, garantías, promociones, CTA, confirmación) ya
  sigue el mismo lenguaje visual violeta — no requiere cambios de fondo, solo los
  incrementales ya descritos en Etapa 2 (resumen lateral) y Etapa 6 (datos de marketing
  reales en vez de placeholders).

---

## ETAPA 8 — Uniformidad visual (Design System)

**Recomendación explícita (decisión de producto a confirmar con el usuario, no asumida
unilateralmente):**

- **Mantener el ámbar (`#d97706`) como color de identidad del catálogo/detalle de
  Technical Services**, tal como el propio `ARQUITECTURA_COMPLETA_SERVICES.md` ya lo
  documenta como decisión deliberada ("paletas distintas por diseño, no inconsistencia").
  Renting mismo no es monocromático (azul en Detail, violeta en Wizard/Cuenta) — exigir un
  único color para todo el ecosistema no es ni siquiera el patrón real de Renting.
- **Unificar la gramática visual, no el color plano**: radios de tarjeta, sombras, el
  patrón "kicker + heading", el grid de specs rápidas, el patrón de badges, el estilo de
  estados vacíos/carga (skeleton), y el patrón de botones — estos SÍ deben ser
  bit-a-bit iguales entre ambos módulos.
- Tipografía/inputs/selects/date-time pickers/alertas: ya comparten Bootstrap 5.3.3 +
  Bootstrap Icons como base del proyecto entero — no hay divergencia real que auditar aquí
  más allá de clases sueltas vs. componentes (cubierto por la extracción de componentes de
  Etapa 3/4).

---

## ETAPA 9 — Experiencia comercial

Todo lo listado en esta etapa (Hero comercial, promociones, cross/up-sell, CTA dinámicos,
mensajes comerciales, beneficios, garantías, contenido enriquecido, SEO, Open Graph, FAQ,
casos de éxito, testimonios) se resuelve mediante:
1. El nuevo `ServiceMarketing` (Etapa 6) — Hero comercial, mensajes, CTA, beneficios,
   garantías, promo banner.
2. Los 4 campos SEO nuevos en `TechnicalService` — SEO/Open Graph.
3. El nuevo `ServiceFAQ` — FAQ real.
4. Reutilización de `ServiceReview` ya existente — reseñas reales (no "testimonios"
   separados).
5. Cross-sell/Up-sell/Servicios y Equipos relacionados: **explícitamente fuera de alcance**
   — no existe ese motor en ningún módulo del proyecto hoy; construirlo sería una
   funcionalidad nueva de producto compartida entre todos los dominios (Shop/Renting/
   Services), no una adopción de un patrón ya probado. Documentado como iniciativa futura
   separada.
6. "Landing personalizable" (`landing_template`): fuera de alcance — no existe en Renting
   tampoco; el sistema de landing genérico real del proyecto es `core.HomeCard`/
   `HomeCardGroup` (freeform, no atado a un registro específico), que ya puede usarse para
   promocionar cualquier servicio manualmente sin cambios.

---

## Checklist técnico

- [x] Verificar si `CatalogListManager`/`SpecificationsManager`/`DocumentsManager`/
      `VideosManager`/`GalleryManager`/`SeoManager` (Renting admin) son genéricos por diseño
      y pueden reutilizarse contra endpoints de Technical Services sin fork. **Resultado:
      NO son reutilizables tal cual (Fase 1) — se forkeó con la Opción 2 (§4.3).**
- [x] Crear migración: modelo `ServiceMarketing` (OneToOneField a `TechnicalService`).
- [x] Crear migración: 4 campos SEO en `TechnicalService`.
- [x] Crear migración: modelo `ServiceFAQ` (FK a `TechnicalService`).
- [x] Endpoints BFF admin nuevos en `dashboard/api/` para los 3 puntos anteriores (mismo
      patrón que `dashboard/equipment/{uuid}/marketing/`).
- [x] Extraer 8 componentes nuevos de presentación (§4.2) desde el monolito
      `ServiceDetailView.vue`.
- [x] Agregar tabs nuevos a `ServiceForm.vue`: **FAQ y Marketing** (tabs dedicados) + **SEO**
      (3 campos de texto agregados al tab General, sin tab propio — `og_image` quedó fuera,
      exigiría plumbing de multipart-upload separado, no crítico). Galería/Incluye-Excluye/
      Características/Especificaciones/Requisitos/Servicios incluidos-opcionales/
      Documentación/Video **NO tienen tab de admin** porque no tienen campo de modelo real
      detrás (agregarlo hubiera exigido los ~9 modelos nuevos fuera de alcance — ver Fase 4
      del estado de ejecución arriba). No aplicó apuntar a los managers genéricos de Renting
      (Fase 1 confirmó que no son reutilizables tal cual).
- [x] Migrar `OperationTimeline.vue` a `StatusTimeline.vue` compartido. **Verificado: ya
      estaba migrado desde antes de este plan (vía `TrackingTimeline.vue`) — el hallazgo
      original de la auditoría estaba desactualizado, no se tocó código.**
- [x] Actualizar `ai_skills/frontend/components/cards.md` §7 (agregar
      `ServiceOperationBoard.vue`, y los componentes nuevos de esta unificación).
- [x] Extraer `WizardStepper.vue` compartido desde el stepper duplicado
      wizard/checkout-modal (evaluar impacto también en Renting). **Se generalizó el
      `CheckoutStepper.vue` ya existente (prop `clickable` nuevo) en vez de crear un archivo
      nuevo — mismo resultado, cero duplicación adicional. Usado por ambos wizards.**
- [x] Agregar sidebar de resumen persistente al wizard de Technical Services (pasos 2-3).
- [x] Actualizar `technical_services/CLAUDE.md` y
      `ARQUITECTURA_COMPLETA_SERVICES.md` con los modelos/componentes nuevos.

## Checklist UX

- [x] El cliente ve un resumen de costo corriendo durante todo el wizard, no solo al final.
- [x] El detalle de servicio muestra reseñas reales (hoy: cero).
- [x] El detalle de servicio muestra FAQ real editable por admin (hoy: hardcodeado).
- [x] El bloque "antes/después" deja de mostrarse vacío — **se retiró** (decisión tomada:
      no existe equivalente conceptual claro en servicios técnicos, ver Etapa 3).
- [ ] El video del servicio deja de decir "pendiente" si el admin ya cargó uno. **No
      resuelto a propósito** — `video_url` no existe como campo en `TechnicalService` ni en
      `ServiceMarketing` (la Etapa 6 cerró la lista de campos sin incluirlo); agregarlo
      exige una decisión de producto explícita nueva, no asumida aquí.
- [x] Navegación entre Renting y Technical Services se siente del mismo "sistema" en
      wizard/checkout y en la gramática visual del detalle/catálogo.

## Checklist UI

- [x] Radios de card, sombras y espaciados del detalle de TS igualados a los de Renting
      Detail (14-16px, sombra `0 16px 34px rgba(15,23,42,.08)`) — ya coincidían antes de
      esta fase (verificado, no requirió cambios).
- [x] Patrón "kicker + heading" aplicado a cada sección del detalle de TS — ya existía.
- [x] Grid de specs rápidas con el mismo layout de 4 columnas — ya existía.
- [ ] Badges de estado con el mismo componente (`OperationStatusBadge`/`CustomerStatusBadge`
      según corresponda al contexto) — no auditado en esta pasada (fuera del alcance
      concreto de detalle público/wizard trabajado en Fases 4-5).
- [x] Empty/loading states (skeleton) con el mismo patrón visual — ya existía.

---

## Cambios Frontend (resumen)

- 8 componentes nuevos de presentación (detalle de servicio).
- 1 componente de sidebar de resumen nuevo en el wizard (o reutilización de
  `ServicePriceBreakdown` en una envoltura de sidebar).
- 1 componente `WizardStepper.vue` extraído (compartido).
- Migración de `OperationTimeline.vue` a `StatusTimeline.vue`.
- Tabs nuevos en `ServiceForm.vue` (admin).
- Actualización de 2 documentos vivos (`cards.md`, `CLAUDE.md`/arquitectura de TS).

## Cambios Backend (solo aditivos)

- Modelo nuevo: `ServiceMarketing` (1 migración).
- Modelo nuevo: `ServiceFAQ` (1 migración).
- Campos nuevos en `TechnicalService`: 4 campos SEO (1 migración).
- Endpoints BFF admin nuevos (CRUD de los 3 anteriores) en `dashboard/api/`, mismo patrón
  que los ya existentes para Renting — **cero cambios a Commands/Selectors/Pricing/
  Availability/Payment/Notifications/Operations existentes.**
- Serializers de lectura pública deben exponer `marketing`/`faq`/campos SEO en
  `TechnicalServiceSerializer` (aditivo, campos opcionales con default).

---

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Confundir "unificar experiencia" con "unificar color" y terminar borrando la identidad ámbar de Technical Services sin que el usuario lo haya pedido explícitamente | Presentar la decisión de color como punto explícito de confirmación (Etapa 8) antes de tocar CSS de catálogo/detalle |
| Que los managers genéricos de Renting (`CatalogListManager`, etc.) resulten estar más acoplados a `Equipment` de lo que su nombre sugiere, forzando un fork de todas formas | Verificarlo como primera tarea técnica antes de comprometerse a reutilizarlos (checklist técnico, primer ítem) |
| Que agregar campos SEO/marketing a `TechnicalService`/nuevo modelo rompa algún serializer que hace `fields = '__all__'` o similar | Revisar `TechnicalServiceSerializer`/`ServiceVariantSerializer` antes de migrar; todos los campos nuevos deben ser opcionales con default vacío |
| Que la extracción de componentes desde el monolito de 536 líneas introduzca regresiones visuales sutiles | Hacerlo incrementalmente, un bloque a la vez, con verificación visual (Playwright/captura) por bloque, no en un solo PR gigante |
| Sobre-alcance: intentar construir cross-sell/up-sell/campañas con fecha "porque ya que estamos" | Estas 3 cosas están marcadas explícitamente "fuera de alcance" en este documento — no ejecutar sin pedido explícito nuevo |

---

## Plan de migración / Compatibilidad

- Todos los cambios de backend son **aditivos**: nuevos modelos, nuevos campos opcionales,
  nuevos endpoints. Ningún endpoint, Command, Selector o contrato existente cambia de
  forma, firma o comportamiento.
- El frontend puede desplegarse por partes: cada componente nuevo de presentación
  reemplaza un bloque específico del monolito `ServiceDetailView.vue` sin afectar los
  demás bloques (son secciones independientes en el mismo archivo).
- El sidebar de resumen del wizard es aditivo — no cambia el flujo de envío ni los campos
  recolectados.
- Ningún cambio de esta unificación requiere migrar datos existentes (los modelos nuevos
  nacen vacíos, `OneToOneField`/FK nulas por defecto donde aplique).

---

## Plan de implementación por fases

**Fase 1 — Verificación técnica previa (sin código de producto):**
Confirmar si los managers genéricos de Renting son reutilizables tal cual. Define si la
Fase 3 construye componentes de admin nuevos o reutiliza los existentes.

**Fase 2 — Backend aditivo:**
`ServiceMarketing`, `ServiceFAQ`, campos SEO en `TechnicalService`, endpoints BFF,
serializers actualizados. Sin tocar frontend todavía. Se puede probar completo con tests
de backend antes de exponer nada en UI.

**Fase 3 — Admin (`ServiceForm.vue`):**
Agregar los tabs nuevos, conectados a los endpoints de la Fase 2. Esto habilita que un
admin real empiece a cargar contenido de marketing/FAQ/SEO incluso antes de que el detalle
público lo muestre.

**Fase 4 — Presentación pública (detalle de servicio):**
Extraer los 8 componentes nuevos, uno a la vez, reemplazando bloques del monolito y
conectándolos a los datos reales ya cargables desde la Fase 3.

**Fase 5 — Wizard/Checkout:**
Sidebar de resumen persistente, extracción de `WizardStepper.vue` compartido.

**Fase 6 — Limpieza y documentación:**
Migrar `OperationTimeline.vue` a `StatusTimeline.vue`, actualizar `cards.md`/
`CLAUDE.md`/arquitectura de Technical Services, cerrar checklist técnico completo.

---

## Restricciones (reiteradas)

- No modificar la naturaleza del negocio de Technical Services.
- No convertir Services en Renting — Renting sigue siendo alquiler, Services sigue siendo
  contratación de servicios.
- Adaptar únicamente los patrones de experiencia ya identificados en este documento.
- Mantener la arquitectura existente (Service Layer, Commands, Selectors intactos).
- Reutilizar componentes siempre que la Fase 1 confirme que es viable.
- Crear únicamente los modelos nuevos aquí descritos (`ServiceMarketing`, `ServiceFAQ`) más
  4 campos SEO — nada más.
- Evitar duplicación de lógica (de ahí la recomendación de extraer `WizardStepper.vue` y
  migrar a `StatusTimeline.vue` en vez de mantener implementaciones paralelas).
- Mantener compatibilidad total con Payment, Notifications, Operations, Dashboard y
  Marketing — ningún cambio de este plan los toca.

---

## Resultado esperado

Un usuario que navegue entre Renting y Technical Services percibirá que ambos pertenecen
al mismo ecosistema (misma gramática de tarjetas, wizard, checkout, badges, estados vacíos
y de carga, y ahora también configuración comercial real vía `ServiceMarketing`), mientras
cada módulo conserva su lógica de negocio, su Service Layer y — deliberadamente — su color
de identidad de catálogo (ámbar vs. azul/violeta), tal como el propio Renting ya convive
con dos familias visuales internas sin que eso se perciba como una inconsistencia cuando la
estructura y las interacciones son coherentes.
