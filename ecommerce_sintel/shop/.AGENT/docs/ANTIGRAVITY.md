# App: shop — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
ecommerce_sintel/shop/.AGENT/docs/ARQUITECTURA_COMPLETA_SHOP.md
```

## Responsabilidad de esta app

Catálogo de productos físicos. Gestión de productos, variantes (SKU), categorías,
marcas, reseñas, impuestos y cálculo de precios.

## Archivos clave

| Archivo | Propósito |
|---------|-----------|
| `models.py` | Category, Brand, Product, ProductVariant, ProductImage, ProductReview, Tax |
| `api/views.py` | ProductViewSet, CategoryViewSet (CRUD admin), BrandViewSet (ReadOnly) |
| `api/serializers.py` | ProductSerializer (output), ProductInputSerializer (input), CategoryInputSerializer |
| `services/commands.py` | ProductCommands, CategoryCommands, BrandCommands, TaxCommands |
| `services/selectors.py` | ProductSelector, CategorySelector, BrandSelector, TaxSelector |
| `services/pricing_service.py` | PricingService: calculate_final_price(), calculate_variant_price() |
| `services/summary.py` | ShopSummaryProvider: get_summary() → stats para marketing |

## Patrones obligatorios en esta app

- `create_product()` SIEMPRE crea un `ProductVariant` por defecto en la misma transacción
- **Soft-delete:** `ProductCommands.delete_product()` → `is_active=False`
- SKU único: validar en serializer antes de crear variante
- `stock` en `ProductVariant` es caché — la fuente de verdad es `StockRecord` en inventory
- No usar `float` para precios — usar `Decimal`
- Admin puede ver productos inactivos; catálogo público solo `is_active=True`
- Reseñas: un usuario, una reseña por producto (validar en serializer)
- `ShopSummaryProvider.get_summary()` es consumido por marketing — mantener la firma del dict

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
