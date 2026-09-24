# PDP Publica (Shop) — Baseline real (Fase 0, mision "Remodelar PDP", 2026-09-16)

Metodo: lectura directa de router/componentes/serializers + `curl` real contra el
producto de dev. Nada de esto se infiere de documentacion vieja sin releer el codigo.

## 1. Ruta real (CHECKPOINT 0 — CONFIRMADO)

```
frontend/src/apps/admin/routes/customer.routes.js:55
  { path: 'tienda/:uuid', name: 'product-detail',
    component: () => import('@/views/customer/detail/PublicDetailView.vue') }
```

`views/customer/detail/PublicDetailView.vue` → (si `moduleType==='shop'`) renderiza
`views/customer/detail/ShopDetailContent.vue`.

**`views/customer/shop/ProductDetailView.vue` existe en disco pero CERO importadores
en todo `frontend/src`** (grep exhaustivo) — confirmado codigo muerto, tal como
asumia el brief. No tocar, no activar, no borrar en esta mision.

## 2. Contrato de datos real — 3 llamadas, no 1

El brief asume un solo `GET /shop/products/{uuid}/detail/`. La realidad, vista en
`PublicDetailView.vue::fetchDetail()`:

1. `GET /api/v1/unified/detail/{uuid}/?module=shop` — DTO generico (`hero`/`seo`)
   usado SOLO para breadcrumb inicial y `setSeo()` (title/description) mientras
   carga el resto. Compartido con Renting/Services.
2. `GET /api/v1/shop/products/{uuid}/detail/` (`shopService.detail()`) — el payload
   RICO real que consume `ShopDetailContent.vue` via prop `product`. Vista:
   `shop/api/views.py:129` (`@action(detail=True, url_path='detail',
   permission_classes=[AllowAny])`), serializer `ProductDetailSerializer`
   (`shop/api/serializers.py:299`, hereda de `ProductSerializer:262`).
3. `GET /api/v1/shop/products/{uuid}/reviews/` (`shopService.reviews()`) — resuelto
   en paralelo por el padre, pasado como prop `initial-reviews`.

### Campos reales confirmados (curl real, producto `f54ccb3a-315c-4e11-b878-700c2c96c539`
— **el UUID del brief, `1b541c67-f443-4336-beb2-d5c02a361cc8`, NO EXISTE en esta DB
de dev**, ver seccion 6)

```json
{
  "name": "camara IP", "brand_name": "dahua", "category_name": "camaras",
  "avg_rating": null, "review_count": 0,
  "images": [{"uuid":"...", "image":"http://.../media/products/....png",
              "alt_text":"", "is_primary": true, "image_type":"GALERIA",
              "image_type_display":"Galeria", "display_order": 0}],
  "variants": [{
    "uuid":"c9b9538d-...", "sku":"SKU-39CBC020", "price":"350000.00",
    "discounted_price": null, "stock": 8, "is_default": true, "attributes": {},
    "effective_price": 350000.0,
    "price_info": {"base_price":"350000.00","discounted_price":null,
      "has_discount": false,
      "applied_taxes":[{"name":"iva","tax_type":"percentage","rate":"19.00","amount":"66500.00"}],
      "total_tax_amount":"66500.00","final_price_net":"416500.00"},
    "images": [], "weight": null, "length": null, "width": null, "height": null
  }],
  "content_blocks": [{"block_type":"description","display_order":0,"is_visible":true}, "... 15 mas"],
  "specification_groups": 1, "features": 2, "included_items": 2, "excluded_items": 1,
  "requirements": 1, "services_included": 1, "optional_services": 1, "faqs": 3,
  "videos": 0, "documents": 1, "functioning_steps": 0,
  "related_products": 0, "compatible_products": 0, "accessories": 0
}
```

Top-level fields completos de `ProductDetailSerializer`: `id, uuid, name, slug,
short_description, description, video_url, condition, category, category_name,
category_uuid, brand, brand_name, brand_uuid, is_featured, is_active, meta_title,
meta_description, variants, images, avg_rating, review_count, stock, sku,
included_items, excluded_items, features, specification_groups, requirements,
services_included, optional_services, faqs, videos, documents, functioning_steps,
scope, warranty, content_blocks, related_products, compatible_products,
accessories`.

**`stock` (a nivel Product, top-level) y `stock` (a nivel variante) NO son el mismo
campo ni la misma fuente:**
- `ProductVariantSerializer.get_stock()` (linea 143) llama
  `InventorySelector.get_stock_for_variant(obj)` — es decir, el JSON YA trae la
  disponibilidad real calculada desde Inventory/StockRecord, NO el campo cache
  `ProductVariant.stock` crudo. El nombre del campo JSON es `stock` en ambos casos,
  pero a nivel variante su ORIGEN real es Inventory. El frontend actual
  (`shopSelectedVariant.stock`) ya esta leyendo el numero correcto — no hace falta
  ningun cambio de contrato para respetar "Inventory como fuente de verdad", ya lo
  es.
- `price_info.final_price_net` (precio con impuestos incluidos) es el que el
  frontend actual usa como precio principal mostrado (`shopEffectivePrice`) — CORRECTO
  segun el propio comentario del codigo, evita discrepancia con lo que se cobra en
  checkout. Preservar este campo como fuente del precio principal en el rediseño.

## 3. Arbol de componentes real (el que SI se renderiza)

```
PublicDetailView.vue (shell: loading/error/breadcrumb/SEO, dispatch por modulo)
└─ ShopDetailContent.vue (TODA la logica de negocio de Shop vive aqui)
   ├─ BaseGallery.vue (components/base/) — thumbs+imagen principal+zoom hover, YA REUTILIZABLE
   ├─ TagBadge.vue (components/marketplace/)
   ├─ RatingDisplay.vue (components/marketplace/) — usa avg_rating/review_count, no recalcula
   ├─ StarRating.vue (components/ui/) — usado en form de resena Y en cada review individual
   ├─ UrgencyBanner.vue (components/marketplace/) — mensaje de disponibilidad
   ├─ ProductPurchaseCard.vue (components/shop/detail/) — YA ES la tarjeta de compra
   │   completa: precio, precio anterior, %desc, stock, cantidad (stepper YA
   │   construido, botones +/-, input numerico con min/max), add-to-cart, buy-now,
   │   wishlist. **Esto ya es el "Purchase Panel" pedido en la mision.**
   └─ (lazy, defineAsyncComponent) DescriptionSection, EquipmentIncludedList/
      ExcludedList/SpecificationTable/RequirementList/ServiceList/FeatureTable/
      VideoGallery/ManualList/DocumentList/DownloadSection, BaseAccordion (FAQ),
      ItemCard (compatibles/accesorios/relacionados) — todas reusadas de
      `components/renting/detail/` (sin fork) + `components/shop/detail/`
      (DescriptionSection propio) + `components/customer/ui/ItemCard.vue`.
```

## 4. Layout actual real (NO es 3 columnas todavia)

`ShopDetailContent.vue` usa Bootstrap grid **2 columnas**: `col-lg-5` (galeria +
trust badges + medios de pago) y `col-lg-7` (TODO lo demas: badges, titulo, rating,
descripcion corta, SKU, disponibilidad, variantes, atributos, logistica, Y la
`ProductPurchaseCard` al final del mismo bloque, con `position: sticky` propio
`.purchase-sticky`). Breakpoint: `@media (max-width: 991px)` colapsa la galeria
sticky a `static`. **Para llegar a 3 columnas hay que partir ese `col-lg-7` en dos:
una columna central de informacion y una columna derecha que sea SOLO
`ProductPurchaseCard`** (que ya existe completo, solo hay que reubicarlo en su
propia columna del grid en vez de anidarlo al final de la columna de info).

## 5. Estado / composables reales

- Sin Pinia store dedicado a "producto actual" — todo vive en `ref()`s locales de
  `ShopDetailContent.vue` (`shopProduct`, `shopVariants`, `shopSelectedVariant`,
  `shopQty`, `shopReviews`, etc.), sincronizados via `watch(() => props.product, ...)`.
  Coincide con el patron "flujo puntual sin store" del proyecto.
- `shopSelectedVariant` YA es la fuente unica de precio/stock/SKU/atributos
  (computed: `shopOriginalPrice`, `shopEffectivePrice`, `shopDiscountPct`,
  `shopVariantAttributes`, `shopHasLogistics`) — el brief pide exactamente este
  patron y YA esta implementado, no hay que rehacerlo.
- Cart: `useCartStore()` (`store/cart.js`), `cartStore.addItem(variantUuid, qty)`.
  Wishlist: `useWishlistStore()` (`store/wishlist.js`).
- SEO: `useSeo()` (`composables/useSeo.js`) — soporta `title`, `description`,
  `og:title/description/image`, JSON-LD (`upsertJsonLd`). **No maneja `<link
  canonical>`** (gap real, brief seccion 33 lo pide). Se llama HOY con datos del
  DTO `unified/detail` (`hero.name`/`hero.description`), no con los campos mas
  ricos de `ProductDetailSerializer` (`meta_title`/`meta_description` del producto
  real quedan sin usar para SEO on-page).

## 6. Gaps reales vs. lo que asume el brief de 44 secciones

1. **El UUID objetivo del brief no existe en esta base de datos de dev**
   (`1b541c67-f443-4336-beb2-d5c02a361cc8` → 404 real, confirmado por ORM
   `Product.objects.filter(uuid=...)` = `None`). Se uso
   `f54ccb3a-315c-4e11-b878-700c2c96c539` ("camara IP", dahua, categoria camaras,
   1 variante, sin reviews) para validar el contrato real. Cualquier
   implementacion/test debe usar un UUID real verificado en el momento, no el del
   brief tal cual.
2. **No existe lightbox/modal de galeria con navegacion siguiente/anterior ni
   cierre por teclado** — `BaseGallery.vue` solo tiene zoom on-hover (transform
   scale), no click-to-expand. El brief (secciones 6 y 16) pide esto explicitamente;
   habria que extender `BaseGallery` o construir un modal nuevo reusando
   `StarRating`/patrones de accesibilidad ya existentes.
3. **No hay imagenes especificas por variante en uso real** — `ProductVariantSerializer`
   SI declara un campo `images` (linea 128), pero en el producto real de prueba
   viene vacio (`"images": []`) y `ShopDetailContent.vue` nunca lo lee (siempre usa
   `shopProduct.images`, nunca `shopSelectedVariant.images`). El campo existe en el
   contrato pero no hay dato real ni consumo real hoy — no inventar UI para esto sin
   verificar que algun producto real lo pueble.
4. **El endpoint NO es uno solo** — son 3 llamadas reales (unified/detail + shop
   detail + reviews), no la unica `GET .../detail/` que asume el brief. La
   redistribucion a 3 columnas no debe tocar esta orquestacion, solo la presentacion
   de `ShopDetailContent.vue`.
5. **`avg_rating`/`review_count` SI se calculan en el backend** (anotacion en
   `ProductSelector`, confirmado por `ProductSerializer` declarandolos como
   `read_only` planos, no `SerializerMethodField`) — el frontend nunca recalcula,
   cumple la regla del brief seccion 10 ya de fabrica.
6. **`is_verified_purchase` en reviews SI existe y SI se usa** (`ProductReviewSerializer`
   linea 247, renderizado en `ShopDetailContent.vue` linea 380) — no es un campo
   inventado por el brief, es real.
7. **Skeleton actual es un solo `<div style="height:400px">` generico** (`PublicDetailView.vue`
   linea 5), no anticipa 3 columnas — habria que construir un skeleton de 3 columnas
   nuevo (o extender), no existe uno hoy pese a que el brief lo pide en seccion 28.
8. **Quantity stepper YA existe** dentro de `ProductPurchaseCard.vue` (`ppc-qty-stepper`,
   botones +/- + input con min/max ya funcionales) — no crear uno nuevo.

## 7. Inventario de UI reutilizable confirmado

| Necesidad del brief | Componente real | Ruta |
|---|---|---|
| Galeria con thumbs+zoom | `BaseGallery` | `components/base/BaseGallery.vue` |
| Rating estrellas (input) | `StarRating` | `components/ui/StarRating.vue` |
| Rating resumen (display) | `RatingDisplay` | `components/marketplace/RatingDisplay.vue` |
| Badge/tag | `TagBadge` | `components/marketplace/TagBadge.vue` |
| Banner de disponibilidad | `UrgencyBanner` | `components/marketplace/UrgencyBanner.vue` |
| Tarjeta de compra completa | `ProductPurchaseCard` | `components/shop/detail/ProductPurchaseCard.vue` |
| Acordeon (FAQ) | `BaseAccordion` | `components/base/BaseAccordion.vue` |
| Card de item (relacionados/accesorios) | `ItemCard` | `components/customer/ui/ItemCard.vue` |
| Skeleton generico | `LoadingSkeleton` / `CustomerSkeleton` | `components/ui/landing/` / `components/customer/account/` — ninguno especifico para PDP de 3 columnas |
| Modal/lightbox con teclado | **No existe** | — gap real, ver seccion 6.2 |

## 8. Siguiente paso (Fase 1 del brief)

Partir `col-lg-7` de `ShopDetailContent.vue` en columna central (info) + columna
derecha (`ProductPurchaseCard`, ya construida) manteniendo el mismo `product`/
`initial-reviews` props y sin tocar `PublicDetailView.vue` ni las 3 llamadas de
red existentes.
