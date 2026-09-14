# FASE 1 — Auditoría: Reingeniería UX/UI del Módulo Shop (Product Detail Page)

**Fecha:** 2026-08-04
**Alcance:** exclusivamente `shop` — `ProductDetailView`/`PublicDetailView`, `ShopDetailContent`,
`ProductPurchaseCard`, `ProductTabs`, `ProductForm`, Shop Store, `shopService`, API/Serializers/DTO.
Auditoría de solo lectura, sin código, tal como exige la FASE 1 del brief. No se tocó Renting,
Technical Services, Cart, Checkout, ni ninguna lógica de negocio.

**Rutas reales confirmadas** (no coinciden con las rutas hipotéticas del brief original):
- `frontend/src/components/shop/detail/ProductPurchaseCard.vue`
- `frontend/src/components/shop/detail/ProductTabs.vue`
- `frontend/src/modules/shop/ProductForm.vue` (+ subcomponentes en `product-form/` y `catalog/`)
- `frontend/src/services/shop/shopService.js`
- `frontend/src/views/customer/detail/ShopDetailContent.vue` (renderizado por `PublicDetailView.vue`)
- **No existe** `store/shop.js` público — solo `store/shopAdmin.js` (exclusivo del panel admin)

---

## 1. API / Serializers / DTO (ya auditado en la sesión, resumen aquí para contexto completo)

`shop/api/serializers.py::ProductDetailSerializer` (líneas 296-372) expone los 11 modelos del
catálogo enriquecido completos: `features`, `included_items`, `excluded_items`,
`specification_groups` (con `specifications` anidadas), `requirements`, `services_included`,
`optional_services`, `faqs`, `videos` (con `embed_url` resuelto en backend), `documents`.
`shopService.detail(uuid)` pega a `shop/products/${uuid}/detail/` — un sub-endpoint dedicado, no
al endpoint base. Shop **bypasea** el "DTO unificado" (`shared/dtos/public_detail.py`) porque
`ShopPublicDetailPresenter` tiene un `TODO` sin terminar (`shared/presenters/public_detail.py:70`)
— es la razón real por la que Shop sí puede mostrar los 11 modelos mientras Renting (100% atado a
ese DTO) pierde datos en el camino.

---

## 2. `ProductPurchaseCard.vue` — tarjeta de compra

**Responsabilidad:** 100% presentacional — precio+descuento+ahorro, disponibilidad/entrega/
garantía, stepper de cantidad, y 3 CTAs (Comprar ahora / Agregar al carrito+wishlist / Solicitar
cotización). No llama servicios ni store — todo llega resuelto por props desde `ShopDetailContent.vue`.

**Duplicación real con `ProductHorizontalCard.vue`** (mismo dato, mismo umbral de negocio, escrito
dos veces de forma independiente):
- **Estado de stock**: ambos archivos calculan el mismo umbral (`stock <= 5` = "últimas
  unidades") de forma independiente, con nombres de clase CSS distintos
  (`phc-stock-ok/low/out` vs. `ppc-text-warning`). Candidato a extraer a un helper/composable
  único (`getStockStatus(stock)`), no a un componente compartido (el layout de presentación es
  distinto en cada card).
- **Fórmula de precio/descuento/ahorro**: replicada en al menos 2 lugares del árbol de
  componentes de shop (`ProductHorizontalCard.vue:91-113` y `ShopDetailContent.vue:458-478`) — no
  hay un único helper de precios compartido para esta fórmula específica.
- **Botón "Agregar al carrito"**: mismo propósito e iconografía, implementado dos veces con
  patrones de loading state ligeramente distintos (ref local vs. prop).

**Problemas de UX reales, documentados por el propio código:**
- El comentario del autor (línea 68-69) reconoce explícitamente que "Comprar ahora" domina
  visualmente (sólido, ancho completo, arriba) sobre "Agregar al carrito" (outline, secundario)
  — invierte la jerarquía habitual de e-commerce, donde "agregar al carrito" suele ser la acción
  primaria.
- El CTA dominante puede aparecer **deshabilitado con texto confuso** ("Comprar ahora" →
  "Agrega al carrito primero") en el caso más común: la primera visita de cualquier usuario con
  el carrito vacío.
- 3 niveles de acción (comprar / agregar+wishlist / cotizar) apilados verticalmente con el mismo
  peso visual, sin jerarquía clara entre flujos de conversión distintos.
- Sin `aria-live` en el label de stock pese a cambiar dinámicamente con la variante seleccionada.

**Responsive:** cero media queries de layout (solo `prefers-reduced-motion`, línea 245-247) — la
tarjeta depende 100% de las columnas Bootstrap del padre, sin ningún ajuste propio para mobile
pese a concentrar 2 CTAs + wishlist + stepper + 3 filas de info.

---

## 3. `ProductTabs.vue` — pestañas de la PDP

Componente 100% presentacional (segmented control), el contenido de cada tab lo controla el padre.

**Tabs actuales** (definidas en `ShopDetailContent.vue:506-515`): `desc` (Descripción, siempre),
`specs` (Especificaciones, condicional), `video` (Video, condicional).

**Redundancia confirmada — 2 de 3 tabs duplican contenido con secciones más abajo en la MISMA página:**
- **Especificaciones** (ya conocido): el tab (`:156-173`, atributos de variante) vs. la sección
  "Especificaciones técnicas" (`:222-228`, `ProductSpecificationGroup` real) — mismo label, dos
  fuentes de datos distintas.
- **Video (hallazgo nuevo de esta pasada)**: el tab (`:175-187`) reproduce el campo legacy único
  `product.video_url`; la sección "Videos del producto" (`:251-258`) renderiza la galería
  completa del modelo real `ProductVideo`. Si un producto tiene ambos campos poblados, el usuario
  ve video fragmentado en dos ubicaciones sin relación visual — mismo patrón de duplicación que
  "Especificaciones".
- Solo `desc` es exclusiva del tab, sin redundancia detectada.

**Responsive:** mismo patrón — cero media queries de layout propias. El scroll horizontal de tabs
(`overflow-x: auto`, scrollbar oculta) es el único mecanismo, **sin indicador visual** (gradiente/
flecha) de que hay más tabs fuera de vista — señal real de UX incompleta en mobile.

---

## 4. `ProductForm.vue` (panel admin) — hallazgo que cambia el plan de FASE 3

**Ya existe una pestaña dedicada por cada uno de los 11 modelos del catálogo enriquecido**
(comentario explícito en el propio código, línea 46: *"Catalogo enriquecido (2026-08-03), espejo
de renting.Equipment"*) — 14 tabs en total: `general`, `seo`, `variants`, `costos`, `imagenes`,
`incluye`, `no-incluye`, `caracteristicas`, `especificaciones`, `requisitos`,
`servicios-incluidos`, `servicios-opcionales`, `documentacion`, `videos`, `faq`. 9 de los 11
modelos reusan un componente genérico ya compartido con Renting (`CatalogListManager.vue`, con
comentario explícito documentando por qué se reusa en vez de duplicar).

**Esto contradice la premisa implícita del brief** ("hoy está todo mezclado, agregar una pestaña
nueva 'Contenido del Producto' para organizarlo"). No está mezclado — ya está separado, quizás en
exceso (14 tabs). **Decisión real que hace falta antes de la FASE 3**: ¿la pestaña nueva
"Contenido del Producto" *reemplaza/agrupa* estas 9 pestañas existentes bajo una sola interfaz de
bloques, o es una pestaña #16 adicional? Si es lo segundo, se duplica la superficie de
administración para el mismo dato — el admin tendría dos caminos distintos para editar lo mismo.

**Descripción**: campo `description` es un `<textarea rows="3">` plano (`GeneralTab.vue:46-50`),
sin editor rich-text, **sin límite de longitud ni contador** — a diferencia de `short_description`
(mismo archivo, líneas 8-18) que sí tiene `maxlength="255"` y contador visible. Ningún editor
HTML/WYSIWYG en ningún archivo del formulario (verificado por búsqueda de
`contenteditable|innerHTML|richtext|wysiwyg|v-html` — cero coincidencias).

---

## 5. Shop Store (Pinia) — no existe versión pública

**No hay store Pinia público de Shop.** Solo existe `store/shopAdmin.js` (exclusivo del panel
admin: categorías/marcas/variantes/imágenes/reglas de costo, todo CRUD administrativo).

El detalle público (`ShopDetailContent.vue`) no usa ningún store de shop — todo el estado
(`shopProduct`, `shopVariants`, `shopSelectedVariant`, `shopReviews`, etc.) vive en refs locales
del componente, poblado por el padre vía `shopService` directo. Los únicos stores que sí toca la
PDP pública son transversales (`useCartStore`, `useWishlistStore`, `useAuthStore`), no de shop.
Esto también sugiere que el catálogo (`/tienda`) probablemente resuelve filtros/categorías sin
store intermedio — coherente con lo ya visto, no se re-audita aquí por estar fuera de la PDP.

---

## 6. `shopService` — inventario completo

6 métodos reales (archivo completo de 22 líneas, todos vía `useApi()`):

| Método | Endpoint | Verbo |
|---|---|---|
| `list(params)` | `shop/products/` | GET |
| `categories()` | `shop/categories/` | GET |
| `brands()` | `shop/brands/` | GET |
| `detail(uuid)` | `shop/products/${uuid}/detail/` | GET |
| `reviews(uuid)` | `shop/products/${uuid}/reviews/` | GET |
| `addReview(uuid, payload)` | `shop/products/${uuid}/review/` | POST |

**No existe ningún método para "productos relacionados"/"compatibles"/"accesorios
recomendados"** — ni siquiera como código muerto sin usar. No es una funcionalidad ya construida
esperando conectarse; requiere crearse desde cero (backend y frontend) si se quiere implementar.

---

## 7. Señales adicionales de UX/contenido denso

- **Descripción sin límite ni colapso**: se renderiza completa (`white-space:pre-wrap`,
  `ShopDetailContent.vue:150-152`) sin "leer más" ni max-height — coherente con que el campo de
  admin (punto 4) tampoco tiene límite de longitud. Un texto muy largo desbalancea la tab
  "Descripción" frente a las otras 2 (specs/video).
- **Reseñas sin paginación**: se renderizan todas de una vez (`:321-338`), sin "cargar más" ni
  límite visible — confirma y extiende el hallazgo ya conocido de reseñas reimplementadas en vez
  de usar `BaseReviews.vue` (que si tiene ese control, según auditoría previa).
- No se detectaron tablas HTML anchas sin scroll (la tabla de specs del tab usa filas flex, no
  tabla ancha) ni comentarios de TODOs/bugs de responsive pendientes en los 3 archivos de este
  bloque — los comentarios presentes documentan decisiones ya tomadas, no deuda reconocida.

---

## Matriz de reutilización de componentes (Shop)

| Componente | Ya genérico / reutilizado hoy | Duplica o reimplementa |
|---|---|---|
| `BaseGallery.vue` | Sí — usado por Shop, Renting, Services | — |
| `BaseAccordion.vue` (FAQ) | Sí — usado por Shop, Renting, Services | — |
| `BaseReviews.vue` | Existe, usado por Renting/Services | **Shop NO lo usa** — reimplementa ~170 líneas propias |
| `MediaImage.vue` | Sí — resolvedor de imagen unificado | — |
| `components/renting/detail/Equipment*.vue` (Included/Excluded/Requirement/VideoGallery/Document/Feature/Specification/Manual/Download) | Sí — Shop los consume sin fork | — |
| `CatalogListManager.vue` (admin) | Sí — Shop y Renting comparten el mismo para 9 de 11 modelos | — |
| `ProductPurchaseCard.vue` | No — específico de Shop | Duplica lógica de stock/precio/CTA con `ProductHorizontalCard.vue` |
| `ProductTabs.vue` | No — específico de Shop, pero genérico por diseño (recibe `tabs` por prop) | 2 de sus 3 tabs duplican secciones de la misma página |
| `PublicDetailRelated.vue` | Existe, genérico, **nunca importado en ningún módulo** | N/A — candidato a conectar, no a duplicar |

---

## Grafo de dependencias — PDP de Shop (evidencia real, no especulativo)

```
PublicDetailView.vue
  └─ (module=shop) → shopService.detail(uuid) → GET shop/products/{uuid}/detail/
        └─ ProductDetailSerializer (shop/api/serializers.py:296-372)
              └─ 11 modelos: Feature, IncludedItem, ExcludedItem, SpecificationGroup+Specification,
                 Requirement, ServiceIncluded, OptionalService, FAQ, Video, Document
  └─ ShopDetailContent.vue (recibe `product` como prop, NO usa el DTO unificado)
        ├─ BaseGallery.vue                          (imágenes, compartido)
        ├─ ProductPurchaseCard.vue                  (compra — específico de Shop)
        ├─ ProductTabs.vue                           (desc/specs/video — específico de Shop)
        │     ├─ tab "specs" ──solapa──> sección "Especificaciones técnicas" (EquipmentSpecificationTable, compartido)
        │     └─ tab "video" ──solapa──> sección "Videos del producto" (EquipmentVideoGallery, compartido)
        ├─ EquipmentIncludedList / EquipmentExcludedList / EquipmentFeatureTable /
        │     EquipmentRequirementList / EquipmentServiceList / EquipmentManualList /
        │     EquipmentDocumentList / EquipmentDownloadSection    (compartidos, sin fork)
        ├─ BaseAccordion.vue (FAQ, compartido)
        ├─ reseñas reimplementadas inline           (NO usa BaseReviews.vue, existente y compartido)
        └─ "productos relacionados"                  AUSENTE (PublicDetailRelated.vue existe, nunca conectado)

ProductForm.vue (admin)
  └─ 14 tabs, 9 vía CatalogListManager.vue (compartido con Renting) + 3 dedicados
        (SpecificationsManager / DocumentsManager / VideosManager)
  └─ useShopAdminStore() ← store/shopAdmin.js (solo admin, sin equivalente público)
```

---

## Cierre de FASE 1

Se cubrió exactamente lo pedido por el brief: auditoría de `ProductDetailView`/`PublicDetailView`,
`ShopDetailContent`, `ProductPurchaseCard`, `ProductTabs`, `ProductForm`, Shop Store, servicios,
API/Serializers/DTO — componentes repetidos, información duplicada, problemas UX, problemas
responsive, código muerto, oportunidades de reutilización — sin escribir código, con matriz de
reutilización y grafo de dependencias real (no especulativo).

**No se avanzó a la FASE 2** (diseño de la nueva organización de información) — el brief separa
explícitamente auditoría de diseño, y hay una decisión real pendiente que debería resolverse antes
de diseñar nada: si la pestaña "Contenido del Producto" reemplaza las 9 pestañas ya existentes en
`ProductForm.vue` o convive con ellas. Quedo a la espera de esa definición y de la confirmación
para avanzar a FASE 2.
