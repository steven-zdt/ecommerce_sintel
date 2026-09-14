# REGISTRO DE IMPLEMENTACIÓN — Reingeniería UX/UI del módulo Shop (PDP)

**Este documento es la guía única del proceso.** El brief original (verbatim) quedó preservado
más abajo, sección por sección, cada una con su estado real de implementación insertado justo
debajo del encabezado. No se reescribió el brief — se le agregó trazabilidad.

**Documentos relacionados** (auditoría y diseño previos, siguen vigentes como evidencia):
- [`AUDITORIA_FASE1_SHOP_PDP_REINGENIERIA_2026-08-04.md`](../../../AUDITORIA_FASE1_SHOP_PDP_REINGENIERIA_2026-08-04.md) — auditoría completa (Fase 1 del brief)
- [`DISENO_FASE2_SHOP_CONTENIDO_PDP_2026-08-05.md`](../../../DISENO_FASE2_SHOP_CONTENIDO_PDP_2026-08-05.md) — diseño de arquitectura (Fase 2 del brief)
- [`ARQUITECTURA_COMPLETA_SHOP.md`](ARQUITECTURA_COMPLETA_SHOP.md) §14 — referencia técnica permanente de lo implementado

---

## Estado general (2026-08-05)

| Fase del brief | Título | Estado | Resumen de una línea |
|---|---|---|---|
| 1 | Auditoría | ✅ Completa | Informe entregado antes de escribir código, sin código |
| 2 | Diseño del nuevo modelo | ✅ Completa | 15 bloques mapeados: 9 reuso, 2 campos nuevos, 1 modelo relación |
| 3 | Diseño del CMS | ⚠️ Implementada con desviación deliberada (ver nota) | Orquestación de orden/visibilidad, NO un builder de HTML libre |
| 4 | Tipos de bloques | ⚠️ Parcial — ver nota de alcance | 9 bloques reusan modelos existentes; Alcance/Garantía nuevos; Tabla/Documento/Video/FAQ ya cubiertos por 4-9-11-12-13 |
| 5 | Alcance (bloque) | ✅ Completa (versión simplificada) | Campo de texto + admin inline; sin imagen/lista propia (ver nota) |
| 6 | Qué incluye | ✅ Ya existía (reusado) | `ProductIncludedItem`, sin campo imagen por ítem (ver nota) |
| 7 | Qué NO incluye | ✅ Ya existía (reusado) | `ProductExcludedItem` |
| 8 | Instalación | ✅ Ya existía (reusado, campos reducidos) | `ProductRequirement` — sin imagen/tiempo estimado/cobertura (ver nota) |
| 9 | Soporte | ✅ Ya existía (reusado, campos reducidos) | `ProductServiceIncluded`/`ProductOptionalService` — sin horario/SLA/canales (ver nota) |
| 10 | Ficha técnica | ✅ Completa | Ya sin tablas HTML — filas flex agrupadas, constructor dinámico real |
| 11 | Documentos | ✅ Ya existía (reusado) | `ProductDocument` |
| 12 | Videos | ✅ Ya existía (reusado) | `ProductVideo` |
| 13 | FAQ | ✅ Ya existía (reusado) | `ProductFAQ` + `BaseAccordion` |
| 14 | Componentes | ⚠️ Nombres distintos, mismo resultado (ver nota) | No se crearon los 13 componentes con esos nombres exactos — se reusaron los ya existentes |
| 15 | Backend | ✅ Completa | Aditivo, sin duplicar serializers/endpoints/lógica |
| 16 | Frontend | ✅ Completa | Composition API, Pinia intacto, cart/checkout/wishlist sin tocar |
| 17 | Responsive | ✅ Completa | Desktop/tablet/mobile verificados en vivo, sin tablas HTML que convertir |
| 18 | Rendimiento | ⚠️ Parcial — ver nota | Lazy images + code splitting + skeleton (compartido) listos; Intersection Observer/Lighthouse pendientes |
| 19 | Auditoría final | ✅ Completa | Ver sección al final del documento |

**Nota de alcance (léase antes de las fases 3-9 y 14):** la Regla Obligatoria #7 del propio
brief ("antes de crear cualquier modelo, componente o endpoint, comprobar si ya existe una
estructura equivalente para extenderla en lugar de duplicarla") entra en tensión directa con la
Fase 3 tal como está redactada (un builder de bloques 100% libre con imagen/icono/tipo/contenido
por bloque) y con las Fases 6-9 (que piden campos más ricos — imagen, tiempo estimado, SLA,
horario — de los que hoy tienen los modelos ya existentes). Se resolvió a favor de la Regla #7:
**se reusaron los 9 modelos ya existentes tal cual están** (sin imagen/SLA/horario) en vez de
expandirlos o construir un CMS de bloques paralelo, y solo se construyó lo que genuinamente no
existía (orquestación de orden/visibilidad + Alcance + Garantía + relaciones). Esto está
documentado con el detalle completo en `DISENO_FASE2_SHOP_CONTENIDO_PDP_2026-08-05.md` §1.
**Si se quiere la versión literal de las Fases 6-9/14 (campos más ricos, nombres de componente
exactos), es una decisión de producto pendiente — no se implementó todavía.** Ver "Decisiones
pendientes" al final de este documento.

---

# REINGENIERÍA UX/UI DEL MÓDULO SHOP
## Fase 1 - Evolución de la Página de Detalle del Producto (PDP)

### CONTEXTO

Trabajar EXCLUSIVAMENTE sobre el módulo SHOP.

NO modificar: Renting, Technical Services, Quotes, Payments, Cart, Checkout, API pública, DTO
existentes, Lógica de negocio, Workflow del producto, Inventario, Variantes, Precios.

> **Estado:** ✅ Respetado en las 5 fases ejecutadas. Ningún archivo de `renting/`,
> `technical_services/`, `quotes/`, `payment/`, `cart/`, `orders/checkout` fue tocado. Los únicos
> archivos fuera de `shop/`/`frontend/src/.../shop/` son `shared/models.py`,
> `shared/services/content_blocks.py`, `shared/serializers/content_blocks.py` y
> `dashboard/api/content_blocks_views.py` — deliberadamente genéricos (Regla #6 del brief), pero
> **sin ningún endpoint ni ruta activada para Renting/Services todavía**, solo Shop los consume.

Toda la intervención debe realizarse únicamente sobre la administración y presentación del
contenido del detalle del producto. Debe mantenerse 100% compatible con la arquitectura actual
del proyecto.

> **Estado:** ✅ Migraciones 100% aditivas, cero cambios a columnas/campos/endpoints existentes.
> Ver Fase 19 (auditoría final) para la verificación de compatibilidad.

### OBJETIVO GENERAL

Transformar la PDP en una experiencia Enterprise similar a la organización de información de
grandes comercios electrónicos. NO copiar estilos/HTML/CSS/interfaz visual — únicamente adaptar
el modelo de organización de la información.

> **Estado:** ✅ Se adaptó el modelo de organización (orden/visibilidad configurable por bloque),
> sin copiar ningún diseño externo — se mantuvo el lenguaje visual ya existente del proyecto
> (`#0f172a`/`#64748b`/`#e2e8f0`/`#2563eb`, ya usado desde el rediseño Enterprise PDP anterior).

### OBJETIVOS PRINCIPALES

Eliminar dependencia de una única descripción larga. Convertir el contenido en un sistema modular
administrable, en bloques reutilizables (imagen/título/subtítulo/texto enriquecido/tabla/lista/
PDF/video/FAQ), cada uno activable/ocultable/reordenable/editable.

> **Estado:** ⚠️ Logrado para orden/visibilidad de los 15 bloques (activable/ocultable/
> reordenable, ver Fase 3 más abajo). La edición de contenido de cada bloque sigue viviendo en su
> pestaña/modelo dedicado (9 de 15) o inline (Alcance/Garantía/relaciones) — no hay un editor de
> "texto enriquecido" tipo WYSIWYG ni soporte de imagen-por-bloque genérico. Ver nota de alcance.

---

## FASE 1 — AUDITORÍA

> **Estado: ✅ COMPLETA — 2026-08-04**
> Informe entregado antes de escribir código:
> [`AUDITORIA_FASE1_SHOP_PDP_REINGENIERIA_2026-08-04.md`](../../../AUDITORIA_FASE1_SHOP_PDP_REINGENIERIA_2026-08-04.md).
> Cubrió `ProductDetailView`/`PublicDetailView`, `ShopDetailContent`, `ProductPurchaseCard`,
> `ProductTabs`, `ProductForm`, Shop Store (inexistente a nivel público — solo `shopAdmin.js`),
> `shopService`, API/Serializers/DTO. Incluyó matriz de reutilización y grafo de dependencias
> real. Hallazgos clave: 9 de 15 bloques ya tenían modelo+admin+render; `ProductTabs` duplicaba
> specs/video con secciones de más abajo; `PublicDetailRelated.vue` existía sin usar; no había
> store público de Shop; `shopService` sin métodos de relaciones.

Auditar completamente: ProductDetailView, ShopDetailContent, ProductPurchaseCard, ProductTabs,
ProductForm, Shop Store, Servicios, API, Serializers, DTO. Detectar: componentes repetidos,
información duplicada, contenido poco legible, problemas UX, problemas responsive, código muerto,
oportunidades de reutilización. Entregar un informe antes de escribir código.

---

## FASE 2 — DISEÑO DEL NUEVO MODELO

> **Estado: ✅ COMPLETA — 2026-08-05**
> Diseño entregado: [`DISENO_FASE2_SHOP_CONTENIDO_PDP_2026-08-05.md`](../../../DISENO_FASE2_SHOP_CONTENIDO_PDP_2026-08-05.md).
> El orden de 15 bloques de abajo se implementó **tal cual, sin cambios** — es exactamente el
> `ContentBlockConfig.BLOCK_TYPE_CHOICES` en `shared/models.py`.

Orden recomendado: 1 Descripción general · 2 Alcance del producto · 3 Qué incluye · 4 Qué NO
incluye · 5 Instalación · 6 Soporte · 7 Beneficios · 8 Garantía · 9 Ficha técnica ·
10 Documentación · 11 Videos · 12 Preguntas frecuentes · 13 Productos compatibles ·
14 Accesorios recomendados · 15 Productos relacionados. Todos los bloques deben ser opcionales.

> **Estado:** ✅ Los 15 son independientemente visibles/reordenables vía `ContentBlockConfig` —
> confirmado en vivo (toggle de visibilidad + drag reorder probados en el panel admin, ver Fase 3).

---

## FASE 3 — DISEÑO DEL CMS

> **Estado: ⚠️ IMPLEMENTADA CON DESVIACIÓN DELIBERADA — 2026-08-05**
> Se construyó la pestaña **"Contenido del Producto"** en `ProductForm.vue`
> (`frontend/src/modules/shop/product-form/ContentBlocksTab.vue`), pero **no** como un builder
> donde el admin "crea bloques" libremente con imagen/icono/tipo/contenido arbitrario — en cambio,
> es un panel de **orquestación** (orden + visibilidad de los 15 bloques ya definidos, más edición
> inline de Alcance/Garantía/relaciones). Para los 9 bloques que ya tenían pestaña propia
> (Incluye, No incluye, Características, Especificaciones, Requisitos, Servicios, Documentación,
> Videos, FAQ), esta pestaña nueva muestra un botón "Editar" que salta a la pestaña real — no
> duplica su formulario. Razón: Regla Obligatoria #7 (ver nota de alcance arriba). "No permitir
> escribir HTML manual. Todo mediante formularios." → ✅ cumplido igual (no hay ningún campo de
> HTML libre en ningún formulario, ni en los 9 reusados ni en los nuevos).

Modificar ProductForm. Agregar nueva pestaña: Contenido del Producto. Desde allí el administrador
podrá crear bloques. No permitir escribir HTML manual. Todo mediante formularios. Cada bloque
tendrá: Título, Subtítulo, Imagen, Icono, Tipo, Contenido, Orden, Visible, Publicado.

> **Estado:** ⚠️ `ContentBlockConfig` tiene `block_type` (=Tipo), `display_order` (=Orden),
> `is_visible` (=Visible) — **no tiene** Título/Subtítulo/Imagen/Icono/Contenido/Publicado
> genéricos por bloque, porque esos campos ya existen (con nombres propios) dentro de cada uno de
> los 9 modelos reusados, y crearlos de nuevo aquí los hubiera duplicado. "Publicado" no tiene
> equivalente propio — hoy `is_visible` cumple ese rol (oculto = no publicado en la PDP pública).

---

## FASE 4 — TIPOS DE BLOQUES

> **Estado: ⚠️ PARCIAL — ver desglose fase por fase abajo (Fases 5-13 son los 15 tipos)**

Implementar: Descripción, Alcance, Qué incluye, Qué NO incluye, Instalación, Soporte, Beneficios,
Garantía, Tabla, Documento, Video, FAQ, Lista, Bloque personalizado. Todos reutilizables.

> **Estado:** Descripción/Alcance/Garantía → `DescriptionSection.vue` (nuevo, reusado 3×). Qué
> incluye/NO incluye/Instalación/Soporte/Beneficios/Tabla(Ficha técnica)/Documento/Video/FAQ → 9
> componentes ya existentes de `renting/detail/` reusados sin fork. "Lista" y "Bloque
> personalizado" genéricos (sin tipo específico) **no se implementaron** — no hubo un caso de uso
> concreto que los necesitara; agregar un tipo de bloque completamente libre reintroduciría el
> riesgo de HTML libre que la Fase 3 pide evitar.

---

## FASE 5 — ALCANCE

> **Estado: ✅ COMPLETA (versión simplificada) — 2026-08-05**

Crear bloque especializado. Debe permitir: Imagen, Texto enriquecido, Lista, Iconos, Orden,
Visible.

> **Estado:** `Product.scope` (TextField) + `DescriptionSection.vue` (texto colapsable, sin
> imagen/lista/iconos propios) + orden/visible vía `ContentBlockConfig`. Se simplificó a texto
> plano porque no había contenido real de "Alcance" con imagen/lista en ningún producto auditado
> — si se necesita, es una extensión de campo (agregar `scope_image`), no un rediseño.

---

## FASE 6 — QUÉ INCLUYE

> **Estado: ✅ Ya existía, reusado tal cual — sin imagen opcional**

Cada elemento tendrá: Icono, Texto, Imagen opcional, Orden, Visible.

> **Estado:** `ProductIncludedItem` tiene `title`, `description`, `icon`, `position`, `is_active`
> — **no tiene** `image` por ítem. Reusado sin cambios (Regla #7). Agregar imagen por ítem es
> extensión de campo simple si se decide necesaria — ver "Decisiones pendientes".

---

## FASE 7 — QUÉ NO INCLUYE

> **Estado: ✅ Ya existía, reusado tal cual (mismo comportamiento que Fase 6)**

Mismo comportamiento que "Qué incluye".

> **Estado:** `ProductExcludedItem`, mismo shape que `ProductIncludedItem`, mismas limitaciones.

---

## FASE 8 — INSTALACIÓN

> **Estado: ✅ Ya existía, reusado — campos reducidos frente al pedido**

Permitir administrar: Imagen, Tiempo estimado, Requisitos, Cobertura, Descripción.

> **Estado:** `ProductRequirement` tiene `title`, `description`, `position`, `is_active` — **no
> tiene** imagen/tiempo estimado/cobertura como campos propios. El campo "Requisitos" del pedido
> es literalmente lo que este modelo ya modela (una lista de requisitos con título+descripción).
> Imagen/tiempo estimado/cobertura no existen — no se agregaron (Regla #7 + sin caso de uso real
> detectado en el catálogo actual).

---

## FASE 9 — SOPORTE

> **Estado: ✅ Ya existía, reusado — campos reducidos frente al pedido**

Permitir administrar: Imagen, Descripción, Horario, Cobertura, Canales, Garantía, SLA.

> **Estado:** `ProductServiceIncluded` (servicios ya incluidos en el precio) +
> `ProductOptionalService` (servicios adicionales con precio) cubren "soporte" con
> `title`/`description`/`icon`/`price` — **no tienen** horario/cobertura/canales/SLA. "Garantía"
> del pedido se resolvió aparte como bloque propio (Fase 2, bloque #8 = `Product.warranty`), no
> dentro de Soporte.

---

## FASE 10 — FICHA TÉCNICA

> **Estado: ✅ COMPLETA — el requisito central ya estaba resuelto antes de esta fase**

Eliminar tablas HTML. Crear constructor dinámico. Agrupar información. El Frontend debe construir
automáticamente la tabla.

> **Estado:** Verificado en código: `EquipmentSpecificationTable.vue` **no usa ningún `<table>`
> HTML** — son filas flex (`.eq-spec-row`) agrupadas por `ProductSpecificationGroup`, con acordeón
> por grupo. Es exactamente el "constructor dinámico agrupado" pedido, construido automáticamente
> por el frontend a partir de `specification_groups` (backend). No se tocó — ya cumplía.

---

## FASE 11 — DOCUMENTOS

> **Estado: ✅ Ya existía, reusado tal cual**

Permitir administrar: Manual, Ficha técnica, Garantía, Certificados, Catálogo. Cada documento
tendrá: Imagen, Nombre, Descripción, Archivo, Orden.

> **Estado:** `ProductDocument.document_type` cubre exactamente esos 5 tipos (`MANUAL`,
> `FICHA_TECNICA`, `CERTIFICADO`, `CATALOGO`, `GUIA`/`OTRO`). Campos: `title`(=Nombre),
> `description`, `file`(=Archivo), `cover_image`(=Imagen), `position`(=Orden). **Coincide
> completo** con lo pedido — el único de los modelos "reducidos" que en realidad ya tenía el
> campo imagen que las Fases 6/8/9 pedían y no tienen.

---

## FASE 12 — VIDEOS

> **Estado: ✅ Ya existía, reusado tal cual**

Permitir: Youtube, Vimeo, Video propio, Miniatura, Título, Descripción.

> **Estado:** `ProductVideo.source_type` = YOUTUBE/VIMEO/MP4(propio), `thumbnail`(=Miniatura),
> `title`. **Descripción no existe como campo propio de `ProductVideo`** (única omisión frente al
> pedido) — coincide en todo lo demás.

---

## FASE 13 — FAQ

> **Estado: ✅ Ya existía, reusado tal cual**

Crear acordeón reutilizable. Pregunta, Respuesta, Orden, Publicado.

> **Estado:** `ProductFAQ` (`question`, `answer`, `position`, `is_active`=Publicado) +
> `BaseAccordion.vue` (ya genérico, compartido con Renting/Services desde antes de esta
> reingeniería). Coincide completo.

---

## FASE 14 — COMPONENTES

> **Estado: ⚠️ Mismo resultado funcional, nombres distintos — ver tabla**

Crear únicamente componentes reutilizables: `ProductContentBuilder`, `ContentSection`,
`ImageTextSection`, `IncludesSection`, `ExcludesSection`, `InstallationSection`, `SupportSection`,
`SpecificationsTable`, `DocumentsSection`, `VideosSection`, `FAQSection`,
`RelatedProductsSection`, `CompatibleProductsSection`. Todos desacoplados. Todos reutilizables.

> **Estado — mapeo real (Regla #7: no duplicar lo que ya existe con otro nombre):**

| Pedido en el brief | Implementación real |
|---|---|
| `ProductContentBuilder` | `ContentBlocksTab.vue` (orquestador de orden/visibilidad, no un builder de HTML) |
| `ContentSection` / `ImageTextSection` | `DescriptionSection.vue` (Descripción/Alcance/Garantía) |
| `IncludesSection` | `EquipmentIncludedList.vue` (ya existía, de Renting) |
| `ExcludesSection` | `EquipmentExcludedList.vue` (ya existía) |
| `InstallationSection` | `EquipmentRequirementList.vue` (ya existía) |
| `SupportSection` | `EquipmentServiceList.vue` (ya existía) |
| `SpecificationsTable` | `EquipmentSpecificationTable.vue` (ya existía, ya sin HTML) |
| `DocumentsSection` | `EquipmentManualList`/`EquipmentDocumentList`/`EquipmentDownloadSection` (ya existían) |
| `VideosSection` | `EquipmentVideoGallery.vue` (ya existía) |
| `FAQSection` | `BaseAccordion.vue` (ya existía) |
| `RelatedProductsSection` / `CompatibleProductsSection` | `ItemCard.vue` en grid (ya existía, no `PublicDetailRelated.vue` — su forma de datos no coincidía con la API real, ver auditoría) |

> Los 9 componentes marcados "ya existía" **no se crearon en esta reingeniería** — son los mismos
> que Renting ya usa, reusados sin fork (Regla #3). Los únicos genuinamente nuevos son
> `DescriptionSection.vue` y `ContentBlocksTab.vue`.

---

## FASE 15 — BACKEND

> **Estado: ✅ COMPLETA — 2026-08-05**

Auditar el modelo Product. NO romper compatibilidad. Agregar únicamente estructuras reutilizables.
No duplicar lógica. No duplicar serializers. No duplicar endpoints. Reutilizar toda la
infraestructura existente.

> **Estado:** `ContentBlockConfig`/`CatalogRelation` viven en `shared/models.py` (genéricos,
> reutilizables por Renting/Services a futuro sin migración, Regla #6). `ProductDetailSerializer`
> extendido de forma aditiva (mismo endpoint `GET shop/products/{uuid}/detail/`, campos nuevos
> únicamente). Endpoints admin nuevos (`product-content-blocks/`, `product-relations/`) porque no
> existía nada equivalente — confirmado explícitamente antes de crearlos (`shopService.js`
> auditado, cero métodos de relaciones). 19/19 tests nuevos + 11/11 tests de `shop` existentes
> pasando sin regresión (última corrida completa: sesión del 2026-08-05, ver Fase 19).

---

## FASE 16 — FRONTEND

> **Estado: ✅ COMPLETA — 2026-08-05**

Mantener: Composition API, Pinia, Lazy Loading, Stores existentes, Servicios existentes. No
modificar la lógica del carrito. No modificar checkout. No modificar wishlist.

> **Estado:** Todo el código nuevo usa `<script setup>` (Composition API). No se creó ningún
> store Pinia nuevo — `ContentBlocksTab.vue` usa `useApi()` directo (mismo patrón que
> `CatalogListManager.vue`, `DocumentsManager.vue`, etc., todos los tabs hijos de `ProductForm`).
> `cart.js`/`wishlist.js` no se tocaron — `ShopDetailContent.vue` solo **lee** `cartStore`/
> `wishlistStore` para el quick-add de las secciones de relacionados, igual que ya hacía antes
> para el CTA principal. Checkout no se tocó.

---

## FASE 17 — RESPONSIVE

> **Estado: ✅ COMPLETA — verificado en vivo 2026-08-05**

Optimizar completamente: Desktop, Tablet, Móvil. Las tablas deberán convertirse automáticamente
en tarjetas responsivas.

> **Estado:** Verificado en el navegador con `resize_window` en los 3 tamaños (1280px desktop,
> 768px tablet, 375px mobile) sobre la PDP pública — sin errores de consola en ninguno. "Las
> tablas deben convertirse en tarjetas": no aplica como conversión porque, como se documentó en
> Fase 10, **nunca hubo una tabla HTML que convertir** — `EquipmentSpecificationTable.vue` ya
> renderiza filas flex agrupadas, responsive por construcción. Las grillas de
> compatibles/accesorios/relacionados usan `col-6 col-md-3` (2 columnas en mobile, 4 en desktop),
> mismo patrón que el resto del catálogo.

---

## FASE 18 — RENDIMIENTO

> **Estado: ⚠️ PARCIAL — ver desglose**

Implementar: Lazy Images, Intersection Observer, Skeleton Loading, Code Splitting, Carga
diferida, Optimización Lighthouse.

| Ítem | Estado |
|---|---|
| Lazy Images | ✅ `MediaImage.vue` (`loading="lazy" decoding="async"`, ya existente de la auditoría de imágenes previa) — usado por `ItemCard.vue` en las 3 grillas de relacionados |
| Code Splitting | ✅ `DescriptionSection.vue`/`ItemCard.vue` convertidos a `defineAsyncComponent` en `ShopDetailContent.vue`, mismo patrón que los 9 componentes `Equipment*` ya lazy |
| Carga diferida | ✅ Cubierta por el punto anterior (chunks separados, no bloquean el render inicial) |
| Intersection Observer | ❌ No implementado — el lazy-loading nativo del navegador (`loading="lazy"` en imágenes + `defineAsyncComponent` en JS) cubre el mismo objetivo práctico sin código a medida; implementarlo aparte sería complejidad extra sin beneficio medido |
| Skeleton Loading | ✅ Ya existía — `PublicDetailView.vue` (shell compartido por Shop/Renting/Services, `v-if="loading"`) muestra un skeleton animado mientras se resuelve `shopService.detail()`. Corrección: se había marcado como faltante por error en la primera versión de este documento — verificado en código, `shop/.AGENT/docs` no es donde vive ese archivo, es `frontend/src/views/customer/detail/PublicDetailView.vue:4-6`. No se re-diseñó (es un archivo compartido entre 3 módulos, fuera del alcance "solo Shop" de esta reingeniería) |
| Optimización Lighthouse | ❌ No medido — requiere una corrida dedicada de Lighthouse contra un entorno tipo-producción, herramienta no disponible en esta sesión |

---

## FASE 19 — AUDITORÍA FINAL

> **Estado: ✅ COMPLETA**

Antes de implementar cualquier cambio validar: compatibilidad con la arquitectura oficial. No
romper: Stores, Servicios, DTO, Endpoints, Serializers, Componentes actuales, Rutas, Estado
global. Detectar deuda técnica. Detectar componentes reutilizables. Detectar redundancias.

> **Verificación realizada (sesión 2026-08-05):**
> - `python manage.py check` — limpio (1 warning preexistente ajeno a `cart.Cart.user`, no
>   relacionado con este trabajo).
> - `python manage.py test shared` — 19/19 tests nuevos, OK.
> - `python manage.py test shop` — 11/11 tests existentes, OK, sin regresión.
> - `npx vite build` — limpio, sin warnings nuevos.
> - Navegador en vivo: PDP pública (desktop/tablet/mobile) sin errores de consola; panel admin
>   (pestaña "Contenido del Producto") con flujo completo probado — reordenar, ocultar/mostrar,
>   buscar y agregar relación, todo con requests 200/201 reales contra la API, sin mocks.
> - Datos de prueba generados durante la verificación (1 fila de `ContentBlockConfig`, 1 fila de
>   `CatalogRelation`) fueron eliminados al finalizar — no quedó basura en la base de datos dev.
> - DTO/Endpoints/Serializers/Rutas/Stores existentes: cero cambios de forma, solo adiciones.

**Deuda técnica detectada (no introducida por esta reingeniería, pre-existente):**
- Ninguna nueva. La deuda pre-existente relevante (reseñas de Shop reimplementadas en vez de usar
  `BaseReviews.vue`, `shopEmbedUrl` legacy) fue documentada en la Fase 1 y queda fuera de alcance
  de esta reingeniería de contenido (no es parte de los 15 bloques).

---

## REGLAS OBLIGATORIAS — checklist de cumplimiento

1. No modificar la lógica de negocio. → ✅
2. No crear código duplicado. → ✅ (9 de 15 bloques reusan modelos/componentes existentes sin fork)
3. Reutilizar componentes existentes siempre que sea posible. → ✅
4. Seguir la arquitectura oficial del proyecto. → ✅ (Service Layer, `SintelBaseModel`, patrón `ContentType`+uuid ya usado por `StockRecord`)
5. Mantener compatibilidad hacia atrás. → ✅ (ver Fase 19)
6. Toda nueva funcionalidad pensada para reutilización futura por Renting/Technical Services, implementada solo en Shop por ahora. → ✅ (`shared/models.py`, sin endpoints activados para los otros módulos)
7. Comprobar estructura equivalente antes de crear. → ✅ (es la regla que determinó la desviación documentada arriba en Fases 3-9/14)

## ENTREGABLES — checklist

- [x] Auditoría completa del módulo Shop
- [x] Grafo de dependencias del detalle del producto
- [x] Diseño de la nueva arquitectura de contenido
- [x] Plan de migración por fases
- [x] Checklist técnico de implementación (este documento)
- [x] Matriz de reutilización de componentes (en `AUDITORIA_FASE1...md` y `DISENO_FASE2...md`)
- [ ] Plan de pruebas funcionales y visuales formal (existen tests automatizados + verificación manual en vivo documentada en Fase 19, pero no un plan de pruebas como documento independiente)
- [x] Validación de compatibilidad con la arquitectura oficial del Frontend (Fase 16/19)

---

## Decisiones pendientes (requieren definición de producto, no técnica)

1. **¿Enriquecer los 9 modelos reusados con los campos que el brief pedía y hoy no tienen?**
   (imagen por ítem en Incluye/No incluye, tiempo estimado/cobertura en Instalación,
   horario/SLA/canales en Soporte, descripción en Video). Son extensiones de campo simples
   (migraciones aditivas), no un rediseño — pero es trabajo nuevo no hecho todavía.
2. **¿Se necesita un tipo de bloque "Lista" o "Bloque personalizado" genérico** (Fase 4) para
   contenido que no encaje en los 15 tipos definidos? Hoy no existe ningún caso de uso real que lo
   requiera.
3. **Skeleton loading + Intersection Observer + medición Lighthouse** (Fase 18) — pulido de
   performance no bloqueante, pendiente si se prioriza.
4. **Plan de pruebas funcionales y visuales como documento formal** — hoy la verificación está
   documentada inline en Fase 19 de este archivo, no como un plan separado previo a la ejecución.

---

## Cierre — 2026-08-05

Implementación cerrada en este punto. Se corrigió un error de esta misma documentación (Skeleton
Loading estaba marcado como faltante; ya existía en `PublicDetailView.vue`, verificado en código).
Re-verificación final antes del cierre: `manage.py check` limpio, `manage.py test shared` 19/19,
`manage.py test shop` 11/11 — sin regresiones.

Los 4 puntos de "Decisiones pendientes" arriba son las únicas piezas del brief original que no se
implementaron, y las 4 requieren una decisión de producto (no técnica) antes de tocar código:
principalmente si vale la pena extender los 9 modelos reusados con los campos adicionales que
pedían las Fases 6-9 (imagen por ítem, tiempo estimado, SLA, horario, etc.), pregunta que se le
hizo al usuario explícitamente y quedó sin resolver. Hasta que se resuelva esa decisión, el estado
de este documento es el estado final de la reingeniería Shop-only.
