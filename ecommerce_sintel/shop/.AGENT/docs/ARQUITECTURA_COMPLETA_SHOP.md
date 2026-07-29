# Arquitectura Completa: Modulo Shop (Catalogo de Productos)

Ultima revision: 2026-06-11

---

## 1. Resumen Ejecutivo

El modulo **Shop** implementa el catalogo de productos central de la plataforma e-commerce.
Utiliza el patron Service Layer (Commands + Selectors) para separar logica de negocio de la
API REST. Los productos se organizan jerarquicamente por categorias, pueden tener multiples
variantes (SKU), y generan resenas de usuarios. Integra con **Inventory** para gestionar stock
mediante GenericForeignKey a traves de StockRecord, y con **Orders** para registrar compras.

El panel admin SPA consume los endpoints de escritura a traves del **dashboard BFF**
(`/api/v1/dashboard/products/`, `/api/v1/dashboard/categories/`, etc.), no directamente
a traves de `/api/v1/shop/`. Las rutas `/api/v1/shop/` sirven el catalogo publico (lectura)
y el endpoint de resenas (autenticado).

---

## 2. Capas de Arquitectura

```
REST API (DRF ViewSets)
  ProductViewSet, ProductVariantViewSet
  CategoryViewSet, BrandViewSet, TaxViewSet
         |
Serializers (Input / Output)
  ProductSerializer / ProductInputSerializer
  ProductVariantSerializer / ProductVariantInputSerializer
  CategorySerializer / CategoryInputSerializer
  BrandSerializer / BrandInputSerializer
  TaxSerializer / TaxInputSerializer
  ProductReviewSerializer
         |
Service Layer (Commands & Selectors)
  ProductCommands / ProductSelector
  ProductVariantCommands / ProductVariantSelector
  CategoryCommands / CategorySelector
  BrandCommands / BrandSelector
  TaxCommands / TaxSelector
  ProductReviewCommands
  PricingService (calculos financieros)
  ShopSummaryProvider (datos para marketing)
         |
Modelos Django ORM
  Product, ProductVariant, ProductImage
  Category, Brand, ProductReview, Tax
         |
Integraciones Externas
  Inventory (StockRecord GenericForeignKey)
  Orders (OrderItem referencia a ProductVariant)
  Marketing (ShopSummaryProvider pull-based)
  dashboard BFF (Orchestrators consumen Commands y Selectors de esta app)
```

---

## 3. Modelos de Datos

### 3.1 Category

```python
class Category(SintelBaseModel):
    parent      = ForeignKey('self', null=True, blank=True, related_name='children')
    name        = CharField(max_length=100, unique=True)
    slug        = SlugField(max_length=150, unique=True, db_index=True)
    description = TextField(blank=True, null=True)
    is_active   = BooleanField(default=True)
```

- Taxonomia jerarquica; las categorias pueden tener subcategorias via `parent`.
- Slug generado automaticamente en `save()` si no existe.
- `is_deleted` heredado de `SintelBaseModel`.
- Relacion inversa `children` para acceder a subcategorias.

### 3.2 Brand

```python
class Brand(SintelBaseModel):
    name = CharField(max_length=100, unique=True)
    slug = SlugField(max_length=150, unique=True, db_index=True)
```

- Slug generado automaticamente en `save()`.
- No tiene campo `is_active` propio.
- Relacion inversa `products` con Product.

### 3.3 Product

```python
class Product(SintelBaseModel):
    vendor      = ForeignKey(settings.AUTH_USER_MODEL, related_name='products')
    category    = ForeignKey(Category, on_delete=CASCADE)
    brand       = ForeignKey(Brand, null=True, blank=True, on_delete=CASCADE)
    name        = CharField(max_length=255)
    slug        = SlugField(max_length=255, unique=True, db_index=True)
    description = TextField(blank=True, null=True)
    condition   = CharField(choices=Condition.choices, default=Condition.NEW)
    is_active   = BooleanField(default=True)
    is_featured = BooleanField(default=False)

    class Condition(TextChoices):
        NEW         = "new"
        USED        = "used"
        REFURBISHED = "refurbished"
```

- Slug con UUID para evitar colisiones: `{base_slug}-{uuid4().hex[:6]}` generado en `save()`.
- `is_deleted` heredado de `SintelBaseModel`.
- Relaciones inversas: `variants`, `images`, `reviews`.

### 3.4 ProductVariant (SKU)

```python
class ProductVariant(SintelBaseModel):
    product         = ForeignKey(Product, related_name='variants')
    sku             = CharField(max_length=100, unique=True, db_index=True)
    price           = DecimalField(max_digits=12, decimal_places=2)
    discounted_price = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    stock           = PositiveIntegerField(default=0)
    is_default      = BooleanField(default=False)
```

- `stock` es cache/shadow; fuente de verdad es `StockRecord` en Inventory.
- `is_default` marca la variante principal del producto.
- `is_deleted` heredado de `SintelBaseModel`.

### 3.5 ProductImage

```python
class ProductImage(SintelBaseModel):
    product   = ForeignKey(Product, related_name='images')
    variant   = ForeignKey(ProductVariant, related_name='images', null=True, blank=True)
    image     = ImageField(upload_to='products/')
    alt_text  = CharField(max_length=255, blank=True, null=True)
    is_primary = BooleanField(default=False)
```

- Puede ser de nivel Producto (galeria general) o Variante (especifica del SKU).

### 3.6 ProductReview

```python
class ProductReview(SintelBaseModel):
    user    = ForeignKey(settings.AUTH_USER_MODEL, related_name='reviews')
    product = ForeignKey(Product, related_name='reviews')
    rating  = PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = TextField()
```

- Un usuario no puede resenir el mismo producto dos veces (enforcement en serializer).
- `avg_rating` y `review_count` se calculan como anotaciones en `ProductSelector`.

### 3.7 Tax (Impuestos)

```python
class Tax(SintelBaseModel):
    class TaxType(TextChoices):
        PERCENTAGE = "percentage"
        FIXED      = "fixed"

    name     = CharField(max_length=100)
    tax_type = CharField(choices=TaxType.choices, default=TaxType.PERCENTAGE)
    value    = DecimalField(max_digits=5, decimal_places=2)
    is_active = BooleanField(default=True)
```

- Tipo: porcentaje o cantidad fija.
- Utilizado por `PricingService`.

---

## 4. API REST — ViewSets y Endpoints

### 4.1 ProductViewSet

```
GET    /api/v1/shop/products/                  Lista (publico)
POST   /api/v1/shop/products/                  Crear (admin)
GET    /api/v1/shop/products/{uuid}/           Detalle (publico)
GET    /api/v1/shop/products/{uuid}/detail/    Detalle completo enterprise [AGREGADO 2026-07-29]
PUT    /api/v1/shop/products/{uuid}/           Actualizar (admin)
PATCH  /api/v1/shop/products/{uuid}/           Actualizar parcial (admin)
DELETE /api/v1/shop/products/{uuid}/           Soft-delete (admin)
GET    /api/v1/shop/products/{uuid}/reviews/   Listar resenas (publico)
POST   /api/v1/shop/products/{uuid}/review/    Crear resena (IsAuthenticated)
```

**[AGREGADO 2026-07-29]:** Nuevo endpoint `/detail/` retorna producto completo unificado 
(`ProductSerializer`), reusable por frontend como alternativa a N+1 requests. Aditivo, no 
rompe API existente.

**Permisos:** `create`, `update`, `partial_update`, `destroy` → `IsAdminUser`; resto → `AllowAny`

**Filtros:**
- `filter_backends`: `DjangoFilterBackend`, `SearchFilter`, `OrderingFilter`
- `filterset_fields`: `is_active`, `is_featured`, `category`
- `search_fields`: `name`, `slug`, `description`
- `ordering_fields`: `created_at`, `name`

**Paginacion:** `StandardResultsSetPagination` (page_size=25, max=100)

**Queryset segun rol:**
- Staff admin → `ProductSelector.list_all_for_admin()` (incluye inactivos, excluye eliminados)
- Publico → `ProductSelector.list_active()` (solo activos)

**Flujo create:**
1. `ProductInputSerializer.is_valid()`
2. `ProductCommands.create_product(vendor=request.user, **validated_data)`
3. Re-fetch con `ProductSelector.get_by_uuid(product.uuid)` (para anotaciones)
4. Responder con `ProductSerializer`

**Flujo update:**
1. `ProductInputSerializer.is_valid(partial=...)`
2. Excluir `price` y `sku` del dict (no se actualizan por integridad historica)
3. `ProductCommands.update_product(product, data)`
4. Re-fetch y responder

**Flujo destroy:** `ProductCommands.delete_product()` → `is_active=False` + `is_deleted=True`

### 4.2 ProductVariantViewSet

```
GET    /api/v1/shop/variants/?product=<uuid>   Lista variantes del producto
POST   /api/v1/shop/variants/                  Crear variante
PATCH  /api/v1/shop/variants/{uuid}/           Actualizar variante
DELETE /api/v1/shop/variants/{uuid}/           Soft-delete variante
```

**Permisos:** `IsAdminUser` para todas las acciones.

**Notas:**
- `list` requiere el param `?product=<uuid>`; sin el retorna 400.
- `create` acepta `product` en el body como UUID del producto padre.
- Soft-delete: solo `is_deleted=True` (variante no tiene `is_active`).

### 4.3 CategoryViewSet

```
GET    /api/v1/shop/categories/
POST   /api/v1/shop/categories/
GET    /api/v1/shop/categories/{uuid}/
PUT    /api/v1/shop/categories/{uuid}/
PATCH  /api/v1/shop/categories/{uuid}/
DELETE /api/v1/shop/categories/{uuid}/
```

**Permisos:** writes → `IsAdminUser`; reads → `AllowAny`

**Filtros:** `filterset_fields`: `is_active`, `parent`; `search_fields`: `name`, `description`

**Serializer por accion:** `create`/`update`/`partial_update` usan `CategoryInputSerializer`;
resto usan `CategorySerializer`.

### 4.4 BrandViewSet

```
GET    /api/v1/shop/brands/
POST   /api/v1/shop/brands/
GET    /api/v1/shop/brands/{uuid}/
PUT    /api/v1/shop/brands/{uuid}/
PATCH  /api/v1/shop/brands/{uuid}/
DELETE /api/v1/shop/brands/{uuid}/
```

**Permisos:** writes → `IsAdminUser`; reads → `AllowAny`

**IMPORTANTE:** BrandViewSet es `ModelViewSet` con CRUD completo. No es ReadOnly.

**Filtros:** `SearchFilter`, `OrderingFilter` en `name`.

**Delete:** `BrandCommands.delete_brand()` hace DELETE fisico (Brand no tiene `is_active`
ni se usa soft-delete; verificar impacto en productos relacionados antes de eliminar).

### 4.5 TaxViewSet

```
GET    /api/v1/shop/taxes/
POST   /api/v1/shop/taxes/
GET    /api/v1/shop/taxes/{uuid}/
PUT    /api/v1/shop/taxes/{uuid}/
PATCH  /api/v1/shop/taxes/{uuid}/
DELETE /api/v1/shop/taxes/{uuid}/
```

**Permisos:** writes → `IsAdminUser`; reads → `AllowAny`

**Filtros:** `filterset_fields`: `is_active`, `tax_type`; `search_fields`: `name`

**Delete:** soft-delete via `is_active=False`.

---

## 5. Serializers

### 5.1 ProductSerializer (Output)

```python
fields = [
    'id', 'uuid', 'name', 'slug', 'description', 'condition',
    'category', 'category_name', 'category_uuid',
    'brand', 'brand_name', 'brand_uuid',
    'is_featured', 'is_active',
    'variants',       # ProductVariantSerializer (nested, read_only)
    'avg_rating',     # float — anotacion BD
    'review_count',   # int  — anotacion BD
    'stock',          # int  — SerializerMethodField (suma de variantes)
    'sku',            # str  — SerializerMethodField (primer variant)
]
```

### 5.2 ProductInputSerializer (Create / Update)

```python
fields = {
    'name'        : CharField(max_length=255),
    'category'    : SlugRelatedField(slug_field='uuid', queryset=Category.objects.filter(is_active=True)),
    'brand'       : SlugRelatedField(slug_field='uuid', required=False, allow_null=True),
    'condition'   : ChoiceField(choices=Condition.choices, default=NEW),
    'description' : CharField(required=False, allow_blank=True),
    'is_featured' : BooleanField(default=False),
    'is_active'   : BooleanField(default=True),
    'price'       : DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01')),
    'sku'         : CharField(max_length=100, required=False, allow_blank=True),
}
```

**Validaciones:**
- `category` y `brand` se resuelven por UUID (SlugRelatedField) — NO por PK.
- `validate_sku`: si se provee, debe ser unico en ProductVariant.
- `price` acepta `Decimal` — usar `Decimal('0.01')` como min_value, NUNCA `float`.

### 5.3 ProductVariantSerializer (Output)

```python
fields = ['id', 'uuid', 'sku', 'price', 'discounted_price', 'stock', 'is_default', 'images']
# images: ProductImageSerializer nested
```

### 5.4 ProductVariantInputSerializer (Create / Update)

```python
fields = {
    'sku'             : CharField(max_length=100),
    'price'           : DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01')),
    'discounted_price': DecimalField(required=False, allow_null=True, min_value=Decimal('0')),
    'is_default'      : BooleanField(default=False),
}
```

### 5.5 CategorySerializer / CategoryInputSerializer

Output: `id`, `uuid`, `name`, `slug`, `description`, `parent`, `parent_name`, `is_active`

Input:
```python
fields = {
    'name'        : CharField — unico case-insensitive; validate_name() en serializer
    'parent'      : PrimaryKeyRelatedField, optional — validate_parent() evita auto-referencia
    'description' : CharField, optional
    'is_active'   : BooleanField, default=True
}
```

### 5.6 BrandSerializer / BrandInputSerializer

Output: `id`, `uuid`, `name`, `slug`

Input: `name` — `validate_name()` verifica unicidad case-insensitive.

### 5.7 TaxSerializer / TaxInputSerializer

Output: `id`, `uuid`, `name`, `tax_type`, `value`, `is_active`

Input: `name`, `tax_type` (ChoiceField), `value` (`min_value=Decimal('0')`), `is_active`

---

## 6. Service Layer

### 6.1 ProductCommands

#### create_product(vendor, category, name, price, ...) -> Product
```python
@transaction.atomic
def create_product(vendor, category, name, price,
                   condition=Product.Condition.NEW, description='',
                   brand=None, is_active=True, is_featured=False, sku=None) -> Product
```
1. Crear registro `Product`.
2. Crear `ProductVariant` por defecto: `sku=sku or f"SKU-{uuid4().hex[:8].upper()}"`,
   `price=price`, `is_default=True`, `stock=0`.
3. Retornar producto (sin anotaciones; la vista hace re-fetch).

#### update_product(product, data: dict) -> Product
- Actualiza campos via `setattr`; llama `product.save()`.
- La vista excluye `price` y `sku` del dict antes de llamar este metodo.

#### delete_product(product) -> None
```python
product.is_active = False
product.is_deleted = True
product.save()
```
Ambos flags obligatorios. Ver seccion 9.2.

### 6.2 ProductVariantCommands

#### create_variant(product, sku, price, discounted_price=None, is_default=False) -> ProductVariant
- Si `is_default=True`, resetea el flag en las demas variantes del producto.

#### update_variant(variant, data: dict) -> ProductVariant
- Si `data['is_default']=True` y la variante no era default, resetea las demas.

#### delete_variant(variant) -> None
- Solo `is_deleted=True`. Variante no tiene `is_active`.

### 6.3 ProductSelector

| Metodo | Comportamiento |
|--------|---------------|
| `list_active()` | `is_active=True`; select_related + prefetch + annotate; catalogo publico |
| `list_all_for_admin()` | `is_deleted=False`; incluye inactivos; ordenado por `-created_at` |
| `get_by_uuid(uuid)` | Retorna con full prefetch/anotaciones; no filtra por is_active |
| `get_by_slug(slug)` | Filtra `is_active=True`; full prefetch/anotaciones |
| `get_by_id(id)` | Acceso por PK; sin filtro is_active |

**Anotaciones:** `avg_rating=Avg('reviews__rating')`, `review_count=Count('reviews')`

### 6.4 ProductVariantSelector

| Metodo | Comportamiento |
|--------|---------------|
| `list_for_product(product_uuid)` | Variantes del producto con `is_deleted=False` |
| `get_by_uuid(uuid)` | `get_object_or_404(ProductVariant, uuid=uuid)` |

### 6.5 CategoryCommands

#### create_category(name, description='', parent=None, is_active=True)
Slug generado automaticamente en `Category.save()`.

#### update_category(category, data: dict)
Actualiza: `name`, `description`, `parent`, `is_active`.

#### delete_category(category) -> None
```python
category.is_active = False
category.save()
```
**ADVERTENCIA:** Solo marca `is_active=False`. A diferencia de Product, NO marca
`is_deleted=True`. Esto significa que la categoria sigue apareciendo en
`list_all_for_admin()` si ese selector no filtra por `is_active`. Verificar el
selector antes de asumir que la categoria "desaparece" del admin.

### 6.6 BrandCommands

#### create_brand(name) -> Brand
#### update_brand(brand, data: dict) -> Brand
#### delete_brand(brand) -> None
```python
brand.delete()  # DELETE FISICO — Brand no tiene is_active ni is_deleted logico
```
Verificar que no haya productos activos referenciando la marca antes de eliminar.

### 6.7 TaxCommands

#### create_tax(name, tax_type, value, is_active=True)
#### update_tax(tax, data: dict)
#### delete_tax(tax) -> None — soft-delete via `is_active=False`

### 6.8 ProductReviewCommands

#### create_review(user, product, rating, comment) -> ProductReview
Validacion de unicidad delegada al serializer. La transaccion garantiza integridad.

### 6.9 PricingService

#### calculate_tax_amount(base_price: Decimal, tax: Tax) -> Decimal
```python
if tax.tax_type == PERCENTAGE:
    return (base_price * tax.value) / Decimal('100.0')
elif tax.tax_type == FIXED:
    return tax.value
```

#### calculate_total_tax(base_price, taxes: Iterable[Tax]) -> Decimal
Suma todos los impuestos aplicados al precio base.

#### calculate_final_price(base_price, discount=0, taxes=None) -> Decimal
```
base_price → (-discount) → (+taxes sobre precio con descuento)
```

#### calculate_variant_price(variant: ProductVariant, include_active_taxes=False) -> Decimal
```python
base = variant.discounted_price or variant.price
if include_active_taxes:
    taxes = TaxSelector.list_active()
    return calculate_final_price(base, taxes=taxes)
return base
```

### 6.10 ShopSummaryProvider

Pull-based; marketing llama activamente `ShopSummaryProvider.get_summary()`.

```python
@staticmethod
def get_summary() -> dict:
    return {
        'app': 'shop',
        'total_active_variants': int,
        'in_stock': int,
        'out_of_stock': int,
        'total_stock_units': int,
        'stale_stock_count': int,
        'stale_stock_record_ids': [int],
        'top_selling_products': [
            {'sku': str, 'item_name': str, 'units_sold': int}
        ]
    }
```

---

## 7. Integracion con Otros Modulos

### 7.1 dashboard BFF (consumidor admin)

El panel admin SPA NO usa directamente `/api/v1/shop/`. Usa el BFF:

```
/api/v1/dashboard/products/    → ShopAdminOrchestrator → ProductCommands/ProductSelector
/api/v1/dashboard/categories/  → ShopAdminOrchestrator → CategoryCommands/CategorySelector
/api/v1/dashboard/brands/      → ShopAdminOrchestrator → BrandCommands/BrandSelector
/api/v1/dashboard/taxes/       → ShopAdminOrchestrator → TaxCommands/TaxSelector
```

Los serializers del dashboard re-exportan los de esta app — no los duplica.

### 7.2 Inventory (StockRecord)

```
ProductVariant
    ↓ (GenericForeignKey via StockRecord)
StockRecord (content_type=ProductVariant, object_id=variant.id)
    ↓
InventoryTransaction (ENTRY, EXIT, RESERVE)
```

- `stock` en ProductVariant es cache. Fuente de verdad: `StockRecord.stock`.
- Al crear un producto NO se crea StockRecord automaticamente.
- Orders usa `InventorySelector.get_current_stock(variant)` para validar disponibilidad.

### 7.3 Orders (OrderItem — Snapshot Pattern)

```python
OrderItem.price = variant.price  # capturado en el momento de la orden
```

Si el precio de `ProductVariant` cambia despues, la orden conserva su precio historico.

### 7.4 Marketing (ShopSummaryProvider)

Pull-based: Marketing llama `ShopSummaryProvider.get_summary()`. Shop no emite signals.
`MarketingAdminOrchestrator.get_consolidated_dashboard()` agrega shop + renting + services.

---

## 8. Patrones criticos

### 8.1 Soft-Delete — Producto (CRITICO)

```python
# CORRECTO — ambos flags siempre en delete_product():
product.is_active = False   # oculta del catalogo publico
product.is_deleted = True   # oculta de la vista de admin
product.save()

# INCORRECTO — solo is_active deja el producto en la lista de admin con badge Inactivo:
product.is_active = False
```

El selector de admin filtra `is_deleted=False`, NO `is_active`:
```python
Product.objects.filter(is_deleted=False)  # correcto
Product.objects.all()                     # NUNCA — devuelve eliminados
```

### 8.2 Soft-Delete — Variante

Solo `is_deleted=True`. Variante no tiene `is_active`.

### 8.3 Soft-Delete — Categoria

Solo `is_active=False`. Este es el comportamiento actual en commands.py.
A diferencia del producto, no se marca `is_deleted=True`.

### 8.4 Delete fisico — Marca

`Brand.delete()` — eliminacion fisica. No hay `is_active` ni `is_deleted` logico para marca.

### 8.5 SlugRelatedField en Input serializers

`ProductInputSerializer` acepta `category` y `brand` como UUID (string):
```python
category = SlugRelatedField(slug_field='uuid', queryset=Category.objects.filter(is_active=True))
```
No acepta ID numerico ni objeto. El cliente debe enviar el UUID de la categoria/marca.

### 8.6 price y sku no actualizables via update_product

La vista excluye `price` y `sku` al llamar `update_product()`. Para actualizar
precio/sku de una variante usar `ProductVariantCommands.update_variant()`.

---

## 9. Optimizaciones de Consulta

### 9.1 Prefetch en ProductSelector

```python
Product.objects
    .select_related('category', 'brand')
    .prefetch_related('variants', 'images', 'reviews__user', 'variants__images')
    .annotate(avg_rating=Avg('reviews__rating'), review_count=Count('reviews'))
```

### 9.2 Indices en BD

- `slug` (unique=True, db_index=True): Product, Category, Brand
- `sku` (unique=True, db_index=True): ProductVariant

---

## 10. Seguridad

| Aspecto | Implementacion |
|---------|---------------|
| Autenticacion | JWT (simplejwt) |
| Admin writes | `rest_framework.permissions.IsAdminUser` (verifica solo `is_staff`) |
| Lectura catalogo | `AllowAny` |
| Resenas | `IsAuthenticated` |
| Un review por usuario | Validacion en `ProductReviewSerializer` |

**Gap de permiso conocido:** Las vistas en `shop/api/views.py` usan
`rest_framework.permissions.IsAdminUser` (solo `is_staff=True`) en vez de
`users.api.permissions.IsAdminUser` (`is_staff=True AND role=ADMIN`).
El impacto es bajo porque el admin SPA usa el dashboard BFF (que si usa el permiso correcto).
Pendiente: migrar en un pase global para coherencia con `.AGENT.md §5.1`.

---

## 11. URLs completas

```
# Catalogo publico + acciones de usuario
GET    /api/v1/shop/products/
POST   /api/v1/shop/products/
GET    /api/v1/shop/products/{uuid}/
PUT    /api/v1/shop/products/{uuid}/
PATCH  /api/v1/shop/products/{uuid}/
DELETE /api/v1/shop/products/{uuid}/
POST   /api/v1/shop/products/{uuid}/review/

GET    /api/v1/shop/variants/?product=<uuid>
POST   /api/v1/shop/variants/
PATCH  /api/v1/shop/variants/{uuid}/
DELETE /api/v1/shop/variants/{uuid}/

GET    /api/v1/shop/categories/
POST   /api/v1/shop/categories/
GET    /api/v1/shop/categories/{uuid}/
PUT    /api/v1/shop/categories/{uuid}/
PATCH  /api/v1/shop/categories/{uuid}/
DELETE /api/v1/shop/categories/{uuid}/

GET    /api/v1/shop/brands/
POST   /api/v1/shop/brands/
GET    /api/v1/shop/brands/{uuid}/
PUT    /api/v1/shop/brands/{uuid}/
PATCH  /api/v1/shop/brands/{uuid}/
DELETE /api/v1/shop/brands/{uuid}/

GET    /api/v1/shop/taxes/
POST   /api/v1/shop/taxes/
GET    /api/v1/shop/taxes/{uuid}/
PUT    /api/v1/shop/taxes/{uuid}/
PATCH  /api/v1/shop/taxes/{uuid}/
DELETE /api/v1/shop/taxes/{uuid}/

# Admin panel (via dashboard BFF)
/api/v1/dashboard/products/
/api/v1/dashboard/categories/
/api/v1/dashboard/brands/
/api/v1/dashboard/taxes/
```

---

## 12. Dependencias entre modulos

```
shop/
  exports → ShopSummaryProvider     → marketing.services (pull)
  exports → ProductVariant          → orders.models.OrderItem (FK)
  exports → ProductSelector/Commands → dashboard.services.admin_orchestrators
  imports → inventory.services.InventorySelector (para validar stock en ordenes)
  imports → ecommerce.base_models.SintelBaseModel
```

- Shop NO depende de Orders ni Marketing (desacoplado).
- Orders depende de Shop (FK a ProductVariant).
- Dashboard depende de Shop (Commands + Selectors via Orchestrators).
- Marketing depende de Shop (pull ShopSummaryProvider).
