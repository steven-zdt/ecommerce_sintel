# App: shop — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
ecommerce_sintel/shop/.AGENT/docs/ARQUITECTURA_COMPLETA_SHOP.md
```

Para redactar la ficha comercial/tecnica de un producto (descripcion, componentes,
especificaciones, documentacion asociada), ver
`ecommerce_sintel/shop/.AGENT/docs/GUIA_FICHA_PRODUCTO.md`.

## Responsabilidad de esta app

Catálogo de productos físicos. Gestión de productos, variantes (SKU), categorías,
marcas, reseñas, impuestos y cálculo de precios.

## Archivos clave

| Archivo | Propósito |
|---------|-----------|
| `models.py` | Category, Brand, Product (+ `scope`/`warranty`, Fase 3 PDP 2026-08-05), ProductVariant, ProductImage, ProductReview, Tax, ProductCostRule, ProductCostAssignment, + catalogo enriquecido (2026-08-03, espejo de renting.Equipment): ProductFeature, ProductIncludedItem, ProductExcludedItem, ProductSpecificationGroup/ProductSpecification, ProductRequirement, ProductServiceIncluded, ProductOptionalService, ProductFAQ, ProductVideo, ProductDocument |
| `services/catalog.py` | Selector+Commands del catalogo enriquecido (11 pares), mismo patron factorizado que `renting/services/catalog.py` |
| `api/views.py` | ProductViewSet, CategoryViewSet (CRUD admin), BrandViewSet (ReadOnly) |
| `api/serializers.py` | ProductSerializer (output), ProductInputSerializer (input), CategoryInputSerializer |
| `services/commands.py` | ProductCommands, CategoryCommands, BrandCommands, TaxCommands |
| `services/selectors.py` | ProductSelector, CategorySelector, BrandSelector, TaxSelector |
| `services/pricing_service.py` | PricingService: calculate_final_price(), calculate_variant_price() |
| `services/summary.py` | ShopSummaryProvider: get_summary() → stats para marketing |

Endpoints admin del catalogo enriquecido: `dashboard/api/shop_catalog_views.py` (ver
ARQUITECTURA_COMPLETA_SHOP.md §13.2 para el contrato REST completo). Orden/visibilidad de los 15
bloques de la PDP + relaciones (compatibles/accesorios/relacionados): modelos genericos
`shared.models.ContentBlockConfig`/`CatalogRelation` (NO viven en `shop/models.py` a proposito,
ver ARQUITECTURA_COMPLETA_SHOP.md §14), endpoints en `dashboard/api/content_blocks_views.py`. UI de admin en
`ProductForm.vue` (10 tabs nuevas: Incluye, No incluye, Caracteristicas, Especificaciones,
Requisitos, Servicios incluidos, Servicios opcionales, Documentacion, Videos, FAQ), reusando
`CatalogListManager.vue` de renting (generalizado con prop `parent-key`) mas 3 componentes
propios de shop (`SpecificationsManager.vue`, `DocumentsManager.vue`, `VideosManager.vue`)
en `frontend/src/modules/shop/catalog/`. Desplegado en produccion 2026-08-03.

## Patrones obligatorios en esta app

- `create_product()` SIEMPRE crea un `ProductVariant` por defecto en la misma transacción
- **[CRITICO] Soft-delete COMPLETO:** `delete_product()` marca `is_active=False` + `is_deleted=True`.
  NUNCA solo `is_active=False`: el producto quedaría visible al admin con badge "Inactivo".
- **[CRITICO] Admin selector:** `list_all_for_admin()` filtra `is_deleted=False`.
  NUNCA usar `Product.objects.all()` en el admin: devuelve productos eliminados.
- SKU único: validar en serializer antes de crear variante
- `stock` en `ProductVariant` es caché — la fuente de verdad es `StockRecord` en inventory
- No usar `float` para precios — usar `Decimal`
- Admin puede ver productos inactivos (`is_active=False`), pero NO eliminados (`is_deleted=True`)
- Reseñas: un usuario, una reseña por producto (validar en serializer)
- `ShopSummaryProvider.get_summary()` es consumido por marketing — mantener la firma del dict

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
