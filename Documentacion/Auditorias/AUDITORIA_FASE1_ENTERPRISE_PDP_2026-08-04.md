# FASE 1 — Auditoría: Presentación de Producto/Equipo/Servicio (Shop + Renting + Technical Services)

**Fecha:** 2026-08-04
**Alcance:** exactamente lo que pide la FASE 1 del "Prompt Maestro — Enterprise Product Detail
Experience": auditoría de solo lectura, sin escribir código. Ejecutada con 3 agentes de
exploración en paralelo (uno por módulo) más síntesis cruzada, con evidencia archivo:línea en
cada hallazgo.

---

## Hallazgo central (explica la mayoría de lo demás)

Existe una capa de "DTO unificado" (`shared/dtos/public_detail.py` +
`shared/presenters/public_detail.py` + `UnifiedPublicDetailViewSet`, servido en
`GET unified/detail/{uuid}/?module=...`) pensada para ser la única fuente de datos del detalle
público en los 3 módulos. **En la práctica, cada módulo tiene un nivel de adopción distinto:**

| Módulo | ¿Usa el DTO unificado? | Consecuencia real |
|---|---|---|
| **Renting** | Sí, 100% (`PublicDetailView.vue` → `RentingPublicDetailPresenter`) | Pierde datos reales: el presenter no mapea `optional_services`/`services_included` (existen en BD, se descartan en silencio); `description` se fija en `None` a propósito aunque el DTO tiene el campo; documentos limitados a un solo tipo de 9 |
| **Shop** | **No** — bypasea el DTO por completo con su propio fetch (`shopService.detail()`) | Por eso Shop sí muestra los 11 modelos enriquecidos completos — pero a costa de duplicar lógica que el DTO debería centralizar (reseñas, resolución de video) |
| **Technical Services** | Parcial — `ServicePublicDetailPresenter` solo llena hero/gallery/pricing/reviews | El resto (incluye/excluye/specs/features/documentos/videos/relacionados) queda con texto hardcodeado en el componente Vue, no datos reales — y en la mitad de los casos **el modelo de datos ni siquiera existe** |

`shared/presenters/public_detail.py:70-145` (`ShopPublicDetailPresenter`) tiene un comentario
explícito: `"TODO: Implementar cuando Shop tenga Presenter propio"` — es decir, el propio código
ya documenta que esta es una brecha conocida, no una sorpresa.

**Esto no es un detalle menor**: cualquier fase posterior (2-20) que asuma "un solo pipeline de
datos" para los 3 módulos tiene que resolver esto primero, o construirá sobre una base que ya
tiene 3 comportamientos distintos disfrazados de "arquitectura unificada".

---

## 1. Componentes reutilizables ya existentes (genéricos, confirmados por uso cruzado real)

| Componente | Usado por | Evidencia |
|---|---|---|
| `components/base/BaseGallery.vue` | Shop, Renting, Services | `ShopDetailContent.vue:23`, `RentingDetailContent.vue:20`, `ServiceDetailContent.vue:18` |
| `components/base/BaseAccordion.vue` (FAQ) | Shop, Renting, Services | `ShopDetailContent.vue:279`, `RentingDetailContent.vue:284`, `ServiceDetailContent.vue:206` |
| `components/base/BaseReviews.vue` | Renting, Services (**no Shop**, ver duplicación) | `RentingDetailContent.vue:293`, `ServiceDetailContent.vue:251-256` |
| `components/ui/MediaImage.vue` | Resolvedor de imagen unificado (auditoría de imágenes, sesión previa) | Usado en tarjetas de los 3 módulos + bloque "relacionados" de Renting |
| `components/renting/detail/EquipmentIncludedList.vue` | Renting, Shop | `RentingDetailContent.vue:222`, `ShopDetailContent.vue:213` |
| `components/renting/detail/EquipmentExcludedList.vue` | Renting, Shop | `RentingDetailContent.vue:225`, `ShopDetailContent.vue:216` |
| `components/renting/detail/EquipmentRequirementList.vue` | Renting, Shop | `RentingDetailContent.vue:257`, `ShopDetailContent.vue:236` |
| `components/renting/detail/EquipmentVideoGallery.vue` | Renting, Shop | `RentingDetailContent.vue:266`, `ShopDetailContent.vue:257` |
| `components/renting/detail/EquipmentDocumentList.vue` | Renting, Shop (alcance desigual, ver duplicación) | ambos |
| `components/renting/detail/EquipmentFeatureTable.vue` | **Solo Shop** (Renting no usa su propio componente) | `ShopDetailContent.vue:202` |
| `components/renting/detail/EquipmentSpecificationTable.vue` | **Solo Shop** (mismo caso) | `ShopDetailContent.vue:227` |
| `components/renting/detail/EquipmentServiceList.vue` | **Solo Shop** | `ShopDetailContent.vue:245-248` |
| `components/renting/detail/EquipmentManualList.vue`, `EquipmentDownloadSection.vue` | **Solo Shop** | `ShopDetailContent.vue:267,269` |
| `technical_services/*` — `ServiceImage`, `ServiceFAQ`, `ServiceMarketing`, `ServiceReview` | Paralelos reales (no huecos) a sus equivalentes de shop/renting | ver tabla de paridad, sección 4 |

**Nota importante**: pese al prefijo `Equipment*` (nombre heredado de cuando solo existía en
Renting), estos 6 componentes ya son genéricos por forma de prop (`groups`, `features`, `items`,
`documents`, `videos`) y Shop los consume tal cual, sin fork. El problema no es que falten
componentes genéricos — es que **Renting mismo no usa la mitad de sus propios componentes**,
reimplementando inline lo que ya tiene construido (ver sección 2).

---

## 2. Componentes/lógica duplicada

### En Shop
- **Reseñas reimplementadas a mano** (`ShopDetailContent.vue:284-338,546-636`, ~170 líneas) en vez
  de usar `BaseReviews.vue`, que Renting y Services ya adoptaron. El propio comentario de
  `BaseReviews.vue:65-71` documenta que esto ya se resolvió para Renting/Services — Shop quedó
  fuera de esa consolidación.
- **Resolución de video duplicada**: `ShopDetailContent.vue:492-500` reimplementa en JS (regex
  YouTube/Vimeo) la misma lógica que el backend ya centraliza en
  `ProductVideoSerializer.get_embed_url()` (`shop/api/serializers.py:595-606`) — pero aplicada al
  campo legacy `Product.video_url` en vez de a la lista real `ProductVideo`. Resultado: **dos
  sistemas de video conviviendo en la misma página** (tab superior con el campo legacy, sección
  inferior con `EquipmentVideoGallery` y los videos reales).
- **Ficha técnica con dos fuentes de datos bajo la misma etiqueta**: tab "Especificaciones"
  (`ShopDetailContent.vue:156-173`, atributos de variante, hardcodeado) vs. sección
  "Especificaciones técnicas" (`:222-228`, dinámica desde `ProductSpecificationGroup` real) — no
  es duplicación de código, es confusión de UX/mantenimiento por reusar el mismo nombre para dos
  cosas distintas.

### En Renting
- **Features y ficha técnica reimplementadas inline** (`RentingDetailContent.vue:198-212` y
  `:231-249`) en vez de usar `EquipmentFeatureTable.vue`/`EquipmentSpecificationTable.vue` — que
  Renting mismo posee y que Shop sí usa. Causa raíz concreta: shape distinto — el DTO unificado
  entrega `group.specs`, pero `EquipmentSpecificationTable.vue:9` espera `group.specifications`.
  Es el hallazgo central (DTO no unificado de verdad) manifestándose como duplicación de código.
- **Documentos con cobertura parcial**: `RentingDetailContent.vue` solo muestra
  `EquipmentDocumentList` filtrado a `FICHA_TECNICA` — los otros 8 tipos de
  `RentalDocument.DOCUMENT_TYPE_CHOICES` (MANUAL, GUIA, CERTIFICADO, PLANO, CATALOGO, FIRMWARE,
  DRIVER, OTRO) no se muestran, pese a que `EquipmentManualList.vue`/`EquipmentDownloadSection.vue`
  ya existen y Shop ya los usa para cubrir exactamente esos casos.
- **Bloque "relacionados" ad-hoc**: `RentingDetailContent.vue:301-323` es markup directo
  (`RouterLink`+`MediaImage`) en vez de un componente reutilizable — mismo patrón que debería
  compartir con Services (que no tiene nada) y con un eventual bloque de Shop.

### En Technical Services
- `ServiceScopeList.vue`/`ServiceFeatureList.vue`/`ServiceSpecificationTable.vue` — reimplementaciones
  paralelas y más pobres de `EquipmentIncludedList`/`EquipmentFeatureTable`/`EquipmentSpecificationTable`:
  reciben strings planos o datos 100% hardcodeados (`SERVICE_FALLBACK`,
  `ServiceDetailContent.vue:317-327`) en vez de objetos reales con icono/título/descripción,
  porque **el modelo de datos real no existe** en este módulo (ver sección 4).
- **Oportunidad de reuso perdida real**: `PackageIncludedList.vue` ya existe, con datos reales
  (`PackageIncludedItem`: título+descripción+icono), pero solo se usa dentro de `PackageSelector.vue`
  — la sección "Incluye" del detalle usa `ServiceScopeList` con strings estáticos en su lugar.
- Bloque "relacionados" de Services (`ServiceDetailContent.vue:222-244`) duplica el markup
  estático del bloque secundario de Renting (`RentingDetailContent.vue:326-345`, mismas clases
  CSS) — 3 `RouterLink` fijos a `/servicios`, `/tienda`, `/alquiler`, sin datos reales.

---

## 3. Componentes candidatos a eliminar (código muerto)

- **`frontend/src/views/customer/detail/components/PublicDetailRelated.vue`** — componente
  completo de "Productos/Servicios Relacionados" (genérico, acepta `items`+`moduleType`), **sin
  un solo import en todo `frontend/src`** (confirmado con búsqueda global). Es irónico: es
  exactamente la pieza que le falta al bloque ad-hoc de Renting y al bloque inexistente de
  Services — está construida y nunca se conectó.
- **`frontend/src/views/customer/services/ServiceDetailView.vue`** — ya confirmado huérfano en
  una auditoría previa de esta sesión (su alias de ruta en realidad apunta a `PublicDetailView.vue`).
  Re-confirmado aquí con evidencia directa de `customer.routes.js:17,63`.
- **`frontend/src/views/customer/renting/RentalDetailView.vue`** — ya confirmado huérfano y
  corregido en una tarea previa de esta sesión (no se re-audita).
- **Placeholder de video en Services** (`ServiceDetailContent.vue:190-199`) y **"Caso de éxito"
  hardcodeado** (`:209-220`, objeto JS fijo en `:426-430`) — sin ningún modelo detrás.
  `technical_services/CLAUDE.md` ya documenta explícitamente que "Caso de éxito" quedó fuera de
  alcance ("exigiría agregar un campo nuevo no autorizado") — son candidatos a eliminarse o a
  implementarse contra un modelo real, no a mantenerse como falsos positivos de "contenido
  dinámico".

---

## 4. Brecha real de paridad — Technical Services vs. Shop/Renting (a nivel de modelo de datos)

| Rol | Shop | Renting | Technical Services |
|---|---|---|---|
| Imagen | `ProductImage` | `EquipmentImage` | `ServiceImage` — **existe** |
| FAQ | `ProductFAQ` | `RentalFAQ` | `ServiceFAQ` — **existe** |
| Marketing/comercial | (campos en Product) | `EquipmentMarketing` | `ServiceMarketing` — **existe** |
| Reseñas | `ProductReview` | `EquipmentReview` | `ServiceReview` — **existe** |
| Feature/característica | `ProductFeature` | `RentalFeature` | **no existe** |
| Ficha técnica (grupo+spec) | `ProductSpecificationGroup`/`ProductSpecification` | `RentalSpecificationGroup`/`RentalSpecification` | **no existe** |
| Qué incluye | `ProductIncludedItem` | `RentalIncludedItem` | **no existe** |
| Qué no incluye | `ProductExcludedItem` | `RentalExcludedItem` | **no existe** |
| Video | `ProductVideo` | `RentalVideo` | **no existe** |
| Documento | `ProductDocument` | `RentalDocument` | **no existe** |

**Technical Services necesita 6-7 modelos nuevos** (`ServiceFeature`, `ServiceSpecificationGroup`,
`ServiceSpecification`, `ServiceIncludedItem`, `ServiceExcludedItem`, `ServiceVideo`,
`ServiceDocument`) más sus migraciones, serializers, exposición en `TechnicalServiceSerializer`,
un `ServicePublicDetailPresenter` completo (hoy solo llena hero/gallery/pricing/reviews) y una
query real de "servicios relacionados" (hoy no existe ninguna, ni siquiera parcial como en
Renting) — para llegar al mismo nivel que Shop/Renting ya tienen. Esto es trabajo de backend real,
no solo de frontend, y es el ítem de mayor esfuerzo de todo lo encontrado en esta auditoría.

---

## 5. Componentes candidatos a convertirse en el estándar reutilizable (base para Fase 2+)

Dado lo anterior, los candidatos reales para ser "el componente único" de cada tipo de bloque
(la premisa de la Fase 4 del prompt maestro) **ya existen en su mayoría** — el trabajo no es
crear 15 componentes desde cero, es:

1. **Resolver el hallazgo central** (unificar el pipeline de datos, o decidir conscientemente que
   Shop seguirá bypaseando el DTO unificado) antes de tocar cualquier componente — si no, cualquier
   componente "genérico" nuevo va a chocar con el mismo problema de shape que ya bloquea a
   `EquipmentSpecificationTable`/`EquipmentFeatureTable` en Renting hoy.
2. **Renombrar y mover** la familia `components/renting/detail/Equipment*.vue` (Feature/
   Included/Excluded/Specification/Requirement/ServiceList/VideoGallery/Manual/Document/Download)
   a una ubicación neutral (ya son cross-módulo en la práctica) — son los candidatos reales a
   `SpecificationsTable`/`IncludesSection`/`ExcludesSection`/`VideoGallery`/`DocumentGallery` que
   pide la Fase 4, no hace falta reescribirlos de cero.
3. **Conectar `PublicDetailRelated.vue`** (ya construido, ya genérico) en los 3 módulos en vez de
   los 3 bloques ad-hoc/duplicados/inexistentes actuales.
4. **Migrar Shop a `BaseReviews.vue`** y a consumir `ProductVideo` real en la tab superior en vez
   del campo legacy — elimina la duplicación real más barata de resolver de toda la auditoría.
5. **Construir los 6-7 modelos faltantes de Technical Services** — el único trabajo de backend
   genuinamente nuevo (todo lo demás en shop/renting ya existe, es cuestión de conectar, no de crear).

---

## Cierre de FASE 1

Esta auditoría cubre exactamente lo pedido: componentes reutilizables, componentes duplicados,
componentes eliminables, componentes candidatos para reutilización — sin escribir código, tal
como exige el brief.

**Lo que sigue (Fases 2-20)** es un programa de trabajo real de varias semanas: constructor de
bloques CMS en el panel admin, 6-7 modelos nuevos de backend para Technical Services, migración/
reorganización de los componentes ya genéricos, resolución del pipeline de datos unificado, y
recién después SEO/performance/responsive sobre la nueva base. No se ejecuta automáticamente a
continuación — requiere que el usuario confirme alcance y prioridad real dentro de esas 19 fases
restantes antes de escribir código.
