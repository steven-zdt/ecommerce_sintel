---
app_name: shop
layer: service_layer
doc_type: spec
critical_rules:
  - decimal_money
  - soft_delete_double
  - readonly_public_endpoints
associated_models:
  - Product
  - ProductVariant
  - Category
  - Brand
  - Tax
  - ProductReview
cross_app_dependencies:
  - inventory
  - orders
  - marketing
  - cart
permissions_required:
  - AllowAny (lectura publica)
  - IsAdminUser (escritura via dashboard/)
---

# App: shop

## Jerarquia de Modelos

```
Category (auto-referencial: parent)
Brand
Product (requiere Category, opcional Brand)
  └── ProductVariant (precios en Decimal, stock via StockRecord)
        └── Tax (N:M via ProductVariant)
```

## ProductVariant: Precios en Decimal

```python
class ProductVariant(SintelBaseModel):
    product            = models.ForeignKey(Product, related_name='variants')
    sku                = models.CharField(max_length=100, unique=True)
    price              = models.DecimalField(max_digits=12, decimal_places=2)  # Decimal
    discounted_price   = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    is_default         = models.BooleanField(default=False)
    is_active          = models.BooleanField(default=True)
    # stock fisico via inventory.StockRecord (OneToOne)
```

## PricingService.calculate_variant_price

```python
@staticmethod
def calculate_variant_price(variant: ProductVariant, include_active_taxes: bool = True) -> Decimal:
    base = variant.discounted_price or variant.price
    if not include_active_taxes:
        return base
    tax_total = Decimal('0.00')
    for tax in variant.taxes.filter(is_active=True):
        tax_total += (base * tax.rate / Decimal('100'))
    return base + tax_total
```

## Endpoints Publicos (ReadOnly — AllowAny)

```
GET /api/v1/shop/products/
GET /api/v1/shop/products/{uuid}/
GET /api/v1/shop/categories/
GET /api/v1/shop/brands/
GET /api/v1/shop/taxes/
GET /api/v1/shop/variants/?product={uuid}
```

## Endpoints Admin (via dashboard/ — IsAdminUser)

```
POST   /api/v1/dashboard/products/
PATCH  /api/v1/dashboard/products/{id}/
DELETE /api/v1/dashboard/products/{id}/   <- soft-delete
POST   /api/v1/dashboard/products/{id}/variants/create/
PATCH  /api/v1/dashboard/products/{id}/variants/{vid}/
DELETE /api/v1/dashboard/products/{id}/variants/{vid}/delete/
```

## Command: ProductVariantCommands.create_variant

```python
@staticmethod
@transaction.atomic
def create_variant(product, sku, price, ...) -> ProductVariant:
    if is_default:
        product.variants.filter(is_deleted=False, is_default=True).update(is_default=False)
    return ProductVariant.objects.create(
        product=product, sku=sku,
        price=price,  # debe ser Decimal
        ...
    )
```

## Soft-Delete en ProductVariant

```python
# CORRECTO
variant.is_active  = False
variant.is_deleted = True
variant.save(update_fields=['is_active', 'is_deleted', 'updated_at'])

# INCORRECTO
variant.delete()
```

## Regla: Shop es ReadOnly para el Portal de Cliente

Los ViewSets bajo `/api/v1/shop/` usan `ReadOnlyModelViewSet` o `ModelViewSet` con `http_method_names = ['get', 'head', 'options']`. Nunca POST/PATCH/DELETE en rutas publicas de shop.
