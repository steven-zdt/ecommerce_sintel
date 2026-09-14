# Arquitectura Completa: Modulo Shop (Catalogo de Productos)

Ultima revision: 2026-08-04 — seccion 13.2 actualizada: UI de admin (10 tabs nuevas en
`ProductForm.vue`) y detalle publico (`ProductDetailSerializer` en `retrieve`/`detail/`) ya
cerrados (ambos el 2026-08-03), y agregado el rediseno Enterprise del hero de la PDP
(`ShopDetailContent.vue`, 2026-08-04) — ver el detalle completo de las 3 fases en 13.2. Revision
anterior (2026-08-03): seccion 3 sincronizada con `models.py` real (campos que faltaban:
`short_description`/`video_url` en Product, SEO/`image` en Category, `logo` en Brand,
`attributes`/logistica/descuento por fecha en ProductVariant, `is_verified_purchase` en
ProductReview, y las clases `ProductCostRule`/`ProductCostAssignment` que no estaban
documentadas en absoluto); agregada seccion 13 "Catalogo Enriquecido de Product" — 11 modelos
nuevos espejo de `renting.Equipment` (features/incluye-no incluye/especificaciones agrupadas/
requisitos/servicios/FAQ/videos/documentos), con service layer, serializers y endpoints admin
completos.

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
    image       = ImageField(upload_to='categories/', blank=True, null=True)
    is_active   = BooleanField(default=True)

    # SEO
    meta_title       = CharField(max_length=70, blank=True, default='')
    meta_description = TextField(blank=True, default='')
```

- Taxonomia jerarquica; las categorias pueden tener subcategorias via `parent`.
- Slug generado automaticamente en `save()` si no existe.
- `is_deleted` heredado de `SintelBaseModel`.
- Relacion inversa `children` para acceder a subcategorias.
- `image` alimenta las tarjetas de categoria del catalogo publico; `meta_title`/`meta_description`
  son los mismos 2 campos SEO minimos que ya usa `Product` (ver 3.3), sin `og_image` propio.

### 3.2 Brand

```python
class Brand(SintelBaseModel):
    name = CharField(max_length=100, unique=True)
    slug = SlugField(max_length=150, unique=True, db_index=True)
    logo = ImageField(upload_to='brands/', blank=True, null=True)
```

- Slug generado automaticamente en `save()`.
- No tiene campo `is_active` propio.
- Relacion inversa `products` con Product.

### 3.3 Product

```python
class Product(SintelBaseModel):
    vendor            = ForeignKey(settings.AUTH_USER_MODEL, related_name='products')
    category          = ForeignKey(Category, on_delete=CASCADE)
    brand             = ForeignKey(Brand, null=True, blank=True, on_delete=CASCADE)
    name              = CharField(max_length=255)
    slug              = SlugField(max_length=255, unique=True, db_index=True)
    short_description = CharField(max_length=255, blank=True, null=True)  # resumen para tarjetas
    description       = TextField(blank=True, null=True)
    video_url         = URLField(blank=True, null=True)  # YouTube/Vimeo, un solo video
    condition         = CharField(choices=Condition.choices, default=Condition.NEW)
    is_active         = BooleanField(default=True)
    is_featured       = BooleanField(default=False)

    # SEO
    meta_title       = CharField(max_length=70, blank=True, default='')
    meta_description = TextField(blank=True, default='')

    class Condition(TextChoices):
        NEW         = "new"
        USED        = "used"
        REFURBISHED = "refurbished"
```

- Slug con UUID para evitar colisiones: `{base_slug}-{uuid4().hex[:6]}` generado en `save()`.
- `is_deleted` heredado de `SintelBaseModel`.
- Relaciones inversas: `variants`, `images`, `reviews`.
- **`video_url` es un campo unico** (no una lista tipada como `renting.RentalVideo`) — un producto
  de shop solo puede enlazar UN video, sin distinguir fuente (YouTube/Vimeo/MP4) ni thumbnail
  propio. Ver seccion 13 para el detalle de esta limitacion frente a `renting`.
- Ver seccion 13 para el estandar de redaccion de `short_description`/`description`.

### 3.4 ProductVariant (SKU)

```python
class ProductVariant(SintelBaseModel):
    product              = ForeignKey(Product, related_name='variants')
    sku                  = CharField(max_length=100, unique=True, db_index=True)
    price                = DecimalField(max_digits=12, decimal_places=2)
    discounted_price     = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discount_start_date  = DateTimeField(null=True, blank=True)
    discount_end_date    = DateTimeField(null=True, blank=True)
    stock                = PositiveIntegerField(default=0)
    is_default           = BooleanField(default=False)
    attributes           = JSONField(default=dict, blank=True)  # especificaciones dinamicas
    # Logistica (para calculo de envio)
    weight = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # kg
    length = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # cm
    width  = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # cm
    height = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # cm
```

- `stock` es cache/shadow; fuente de verdad es `StockRecord` en Inventory.
- `is_default` marca la variante principal del producto.
- `is_deleted` heredado de `SintelBaseModel`.
- `discount_start_date`/`discount_end_date` acotan la ventana de vigencia de `discounted_price`
  (no documentado hasta ahora quien la evalua — verificar `PricingService`/el serializer antes de
  asumir que se aplica automaticamente fuera de esa ventana).
- **`attributes` (JSONField) es el unico lugar donde shop guarda "especificaciones tecnicas"
  hoy** — sin agrupacion ni tipado, a diferencia de `renting.RentalSpecificationGroup` +
  `RentalSpecification` (filas administrables, agrupadas). Ver seccion 13.

### 3.5 ProductImage

```python
class ProductImage(SintelBaseModel):
    product        = ForeignKey(Product, related_name='images')
    variant        = ForeignKey(ProductVariant, related_name='images', null=True, blank=True)
    image          = ImageField(upload_to='products/')
    alt_text       = CharField(max_length=255, blank=True, null=True)
    is_primary     = BooleanField(default=False)
    display_order  = PositiveIntegerField(default=0)
```

- Puede ser de nivel Producto (galeria general) o Variante (especifica del SKU).
- `display_order` controla el orden de la galeria (`Meta.ordering = ['display_order']`); a
  diferencia de `renting.EquipmentImage`, no tiene `image_type` (Principal/Detalle/Instalacion/
  360/Plano/Ejemplo) — solo el flag binario `is_primary`.

### 3.6 ProductReview

```python
class ProductReview(SintelBaseModel):
    user                  = ForeignKey(settings.AUTH_USER_MODEL, related_name='reviews')
    product               = ForeignKey(Product, related_name='reviews')
    rating                = PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment               = TextField()
    is_verified_purchase  = BooleanField(default=False)
```

- Un usuario no puede resenir el mismo producto dos veces — `unique_together = ('user', 'product')`
  a nivel de BD (no solo validacion de serializer, ver 8.x).
- `avg_rating` y `review_count` se calculan como anotaciones en `ProductSelector`.
- `is_verified_purchase` (prueba social) — verificar en el serializer/command real quien lo pobla
  antes de asumir que se marca automaticamente al reseniar tras una compra real.

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

### 3.8 ProductCostRule / ProductCostAssignment

**No documentadas hasta esta revision** — existen en `models.py` pero no aparecian en ninguna
version anterior de este documento. Mismo patron que `renting.RentalCostRule`/
`RentalCostAssignment` (reglas de precio — IVA/descuento — asignables a variantes especificas):

```python
class ProductCostRule(SintelBaseModel):
    name              = CharField(max_length=150)
    description       = TextField(blank=True, default='')
    cost_type         = CharField(choices=[('FIXED', 'Valor fijo (COP)'), ('PERCENTAGE', 'Porcentaje (%)')])
    context           = CharField(choices=[('TAX', 'Impuesto'), ('DISCOUNT', 'Descuento')])
    value             = DecimalField(max_digits=12, decimal_places=4)
    applies_globally  = BooleanField(default=False)
    is_active         = BooleanField(default=True)

class ProductCostAssignment(SintelBaseModel):
    rule    = ForeignKey(ProductCostRule, related_name='assignments')
    variant = ForeignKey('shop.ProductVariant', related_name='cost_assignments')

    class Meta:
        unique_together = ('rule', 'variant')
```

- **Diferencia real frente a `renting`:** aqui `applies_globally=True` SI existe como opcion (a
  diferencia de `RentalCostRule`, donde ese campo fue eliminado deliberadamente en la migracion
  `0027` de renting por no tener casos de uso reales) — verificar en `services/pricing_service.py`
  si ese flag se evalua realmente antes de asumir su comportamiento.
- `unique_together` evita asignar la misma regla dos veces a la misma variante.

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

---

## 13. Catalogo Enriquecido de Product (cerrado 2026-08-03)

**Historia:** esta seccion nacio (2026-08-03, primera pasada) documentando una brecha real de
MODELO frente a `renting` — shop solo tenia `description` (TextField libre) para todo el
contenido comercial/tecnico, sin ningun equivalente a los 8 tipos de contenido estructurado que
`renting.Equipment` ya tenia desde su migracion `0022_catalog_detail_models` (2026-07-16). Esa
brecha se cerro el mismo dia: `shop.Product` ahora tiene el mismo nivel de estructura que
`renting.Equipment`, espejo campo por campo. Ver el producto real
"Alquiler de Arco Detector de Metales para Control de Accesos y Eventos" (`/api/v1/renting/
equipment/`, verificado en vivo contra produccion) como la referencia original que motivo esta
paridad.

### 13.1 Modelos (espejo de renting.Equipment)

11 modelos nuevos en `shop/models.py`, todos con el mismo shape (fila hija de `Product`, con
`position`/`is_active`/`is_deleted`, soft-delete real):

| Modelo | Espejo de (`renting`) | Campos propios |
|---|---|---|
| `ProductFeature` | `RentalFeature` | `title`, `value`, `icon` |
| `ProductIncludedItem` | `RentalIncludedItem` | `title`, `description`, `icon` |
| `ProductExcludedItem` | `RentalExcludedItem` | `title`, `description`, `icon` |
| `ProductSpecificationGroup` | `RentalSpecificationGroup` | `name` (agrupador) |
| `ProductSpecification` | `RentalSpecification` | `group` (FK), `name`, `value` |
| `ProductRequirement` | `RentalRequirement` | `title`, `description` |
| `ProductServiceIncluded` | `RentalServiceIncluded` | `title`, `description`, `icon` |
| `ProductOptionalService` | `RentalOptionalService` | `title`, `description`, `price`, `icon` |
| `ProductFAQ` | `RentalFAQ` | `question`, `answer` |
| `ProductVideo` | `RentalVideo` | `source_type`, `video_url`/`video_file`, `thumbnail` |
| `ProductDocument` | `RentalDocument` | `document_type`, `file`, `cover_image`, `downloads`, `is_public` |

**No mirrorizados a proposito** (pricing/logistica de alquiler, no aplican a venta directa):
`EquipmentLogisticsConfig`, `EquipmentCommercialConfig`, `EquipmentCommercialOption`,
`EquipmentMarketing`. `ProductVariant.attributes` (JSONField) sigue existiendo para
especificaciones rapidas sin estructura formal — `ProductSpecificationGroup`/`ProductSpecification`
son la via recomendada para especificaciones que deben mostrarse agrupadas en el detalle publico.

`ProductImage` (ya existia) gano `image_type` (Principal/Galeria/Detalle/Ejemplo — subconjunto de
`renting.EquipmentImage`, sin Instalacion/360/Plano, que no aplican a un producto de venta).
`Product.video_url` (campo unico legacy) se conserva sin cambios — `ProductVideo` es la forma
nueva recomendada para multiples videos, sin migracion automatica de datos existentes.

### 13.2 Service layer, API y endpoints

`shop/services/catalog.py` — un `Selector`+`Commands` por modelo (11 pares), mismo patron
factorizado que `renting/services/catalog.py` (`_reorder`/`_toggle_active`/`_soft_delete`/
`_duplicate` compartidos a nivel de modulo). Serializers Output+Input en `shop/api/serializers.py`.

Endpoints admin (`dashboard/api/shop_catalog_views.py`, `IsAdminUser`, mismo contrato REST que
`renting_catalog_views.py` via `ProductCatalogChildViewSet`):

```
GET    /api/v1/dashboard/product-features/?product=<uuid>
GET    /api/v1/dashboard/product-included-items/?product=<uuid>
GET    /api/v1/dashboard/product-excluded-items/?product=<uuid>
GET    /api/v1/dashboard/product-specification-groups/?product=<uuid>
GET    /api/v1/dashboard/product-specifications/?product=<uuid>|group=<uuid>
GET    /api/v1/dashboard/product-requirements/?product=<uuid>
GET    /api/v1/dashboard/product-services-included/?product=<uuid>
GET    /api/v1/dashboard/product-optional-services/?product=<uuid>
GET    /api/v1/dashboard/product-faqs/?product=<uuid>
GET    /api/v1/dashboard/product-videos/?product=<uuid>
GET    /api/v1/dashboard/product-documents/?product=<uuid>
GET    /api/v1/dashboard/product-catalog-images/?product=<uuid>

POST   <recurso>/                       crea (body incluye 'product')
PATCH  <recurso>/<uuid>/                actualiza
DELETE <recurso>/<uuid>/                borrado logico
POST   <recurso>/<uuid>/toggle-active/  activa/desactiva
POST   <recurso>/<uuid>/duplicate/      duplica (no aplica a imagenes/videos/documentos)
POST   <recurso>/reorder/               reordena (body: product, ordered_uuids)
```

`ProductDocumentViewSet.create()` valida el archivo con `accounts.services.commands.validate_file`
(extension + magic-bytes, mismo mecanismo que `renting`) antes de guardar — rechaza extensiones
no permitidas con 400, no con un 500 de almacenamiento.

**UI de admin cerrada (2026-08-03)** — `ProductForm.vue` (modo edicion) agrega 10 tabs nuevas
(Incluye, No incluye, Caracteristicas, Especificaciones, Requisitos, Servicios incluidos,
Servicios opcionales, Documentacion, Videos, FAQ) junto a las 5 existentes (General, SEO,
Variantes, Costos, Imagenes). 7 tabs reusan `CatalogListManager.vue` de renting
(`frontend/src/modules/renting/catalog/CatalogListManager.vue`, generalizado con la prop
`parent-key` para aceptar `product` ademas de `equipment`, sin duplicar el componente); las 3
restantes (Especificaciones, Documentacion, Videos) usan componentes propios de shop
(`SpecificationsManager.vue`, `DocumentsManager.vue`, `VideosManager.vue` en
`frontend/src/modules/shop/catalog/`) por su forma anidada o de subida de archivo. Deliberadamente
NO se creo una pestaña "Galeria" separada para el nuevo campo tipado `ProductImage.image_type` —
la pestaña "Imagenes" existente ya cubre ese flujo y duplicarla habria sido una implementacion
paralela; el campo/endpoint queda disponible via API sin exponerse aun en la UI. Build de
produccion verificado (`vite build` limpio) y desplegado.

**Detalle publico cerrado (2026-08-03)** — `GET /api/v1/shop/products/{uuid}/` (usado por
`shopService.detail()`, PDP en `/tienda/:uuid`) ahora retorna `ProductDetailSerializer`
(`shop/api/serializers.py`, espejo de `EquipmentDetailSerializer` de renting) solo en la accion
`retrieve` — `list` sigue usando `ProductSerializer` liviano. Agrega `included_items`,
`excluded_items`, `features`, `specification_groups` (con `specifications` anidadas),
`requirements`, `services_included`, `optional_services`, `faqs`, `videos`, `documents`
(solo `is_public and is_active`), todos filtrados a `is_active` en memoria (ya vienen
prefetcheados via `ProductSelector._get_detail_queryset()`, con `Prefetch(is_deleted=False)`
por relacion — cero queries N+1 adicionales). Nuevo endpoint publico
`POST /api/v1/shop/products/{uuid}/documents/{document_uuid}/register-download/` (espejo del
de renting) para el contador `downloads`.

Frontend: `ShopDetailContent.vue` (`frontend/src/views/customer/detail/`) agrega
`.shop-detail-sections` con una `<section>` por bloque (Caracteristicas, Alcance,
Ficha tecnica, Requisitos, Servicios, Documentacion, Video, FAQ), reusando **directamente**
los componentes de `frontend/src/components/renting/detail/` (`EquipmentFeatureTable`,
`EquipmentIncludedList`, `EquipmentExcludedList`, `EquipmentSpecificationTable`,
`EquipmentRequirementList`, `EquipmentServiceList`, `EquipmentVideoGallery`,
`EquipmentManualList`, `EquipmentDocumentList`, `EquipmentDownloadSection`, `BaseAccordion`)
sin duplicarlos — su forma de datos (title/description/icon/uuid) ya era generica. El unico
cambio compartido: `useDocumentDownload(entityUuid, basePath)` gano un segundo parametro
`basePath` (default `'renting/equipment'`, backward-compatible) y los 3 componentes de
documentos ganaron una prop `basePath` (mismo patron que `parentKey` en
`CatalogListManager.vue`); shop pasa `base-path="shop/products"`. Verificado en vivo con datos
reales sembrados en un producto de dev (secciones renderizan, descarga de documento
incrementa `downloads` via la API) y contra produccion (`GET shop/products/{uuid}/` responde
200 con los 10 campos nuevos, aunque vacios hasta que un admin cargue contenido via el panel).

**Rediseno Enterprise del hero de la PDP (2026-08-04)** — el bloque superior (galeria/precio/CTA),
que se habia quedado con estilo Bootstrap tradicional mientras `.shop-detail-sections` (parrafo
anterior) ya tenia el look premium, se rediseño para igualar el mismo lenguaje visual
(`#0f172a`/`#64748b`/`#e2e8f0`/`#2563eb`, radios 16px/999px, headings peso 850) que
`RentingDetailContent.vue`. Cambio frontend-only, sin tocar backend: `shopService.detail()` ahora
apunta a `GET shop/products/{uuid}/detail/` (antes `GET shop/products/{uuid}/` — mismo
`ProductDetailSerializer`, mismo numero de requests, endpoint ya existente, aditivo desde
2026-07-29). Reusa por primera vez `components/marketplace/{TagBadge,RatingDisplay,
UrgencyBanner}.vue` y `components/ui/StarRating.vue` (existian sin consumidores). `BaseGallery.vue`
gano 2 props opcionales backward-compatible (`thumbLayout`, `zoom`) y un theme `shop`, sin afectar
Renting/Services. 2 componentes nuevos en `frontend/src/components/shop/detail/`:
`ProductPurchaseCard.vue` ("buy box" con precio/descuento/disponibilidad/CTA, "Comprar ahora"
dominante y "Agregar al carrito" secundario, sticky en desktop) y `ProductTabs.vue` (segmented
control pill, reemplaza `nav-tabs`). Registro completo de props en
`ai_skills/frontend/components/cards.md` §4.3-4.4. Deliberadamente NO se uso
`DiscountBadge.vue` (existente) pese a estar en el plan original — su estilo (gradiente rojo,
animacion pulse) contradice el pedido explicito de "colores suaves, sombras minimas" y duplicaba
info que `ProductPurchaseCard` ya muestra; se opto por un pill discreto propio en su lugar.

### 13.3 Plantilla de `description` (contenido libre, complementario a los modelos)

`description` sigue siendo el lugar para la descripcion comercial/tecnica en prosa —
los modelos de 13.1 son para contenido ESTRUCTURADO (listas, tablas, archivos), no lo reemplazan.
Ver `GUIA_FICHA_PRODUCTO.md` para la plantilla completa y un ejemplo desarrollado.

### 13.4 `ProductVariant.attributes` — convencion de claves (complementario)

Para especificaciones rapidas sin necesidad de agrupacion visual (ej. atributos de variante que
difieren SKU a SKU dentro del mismo producto, como color o talla), sigue siendo valido usar
`attributes`. Se recomienda una convencion plana de claves consistente entre productos de la
misma categoria:

```json
{
  "resolucion": "4MP",
  "alcance_ir": "30m",
  "alimentacion": "12V DC / PoE",
  "proteccion": "IP67",
  "conectividad": "WiFi 2.4GHz, RJ45"
}
```

No hay validacion de esquema a nivel de modelo — mantener consistencia de nombres de clave es
responsabilidad de quien carga el producto (convencion, no una garantia del codigo).

---

## 14. Orquestacion de contenido de la PDP — orden/visibilidad y relaciones (Fase 3, 2026-08-05)

**Contexto:** reingenieria UX/UI del modulo Shop, Fase 1 (auditoria) -> Fase 2 (diseno) -> Fase 3
(esta seccion). Ver `AUDITORIA_FASE1_SHOP_PDP_REINGENIERIA_2026-08-04.md` y
`DISENO_FASE2_SHOP_CONTENIDO_PDP_2026-08-05.md` en la raiz del repo para el detalle completo del
razonamiento. Resumen: se pidio un sistema de "15 bloques de contenido" para la PDP; la auditoria
encontro que 9 de los 15 ya existian como los modelos de la seccion 13. Por eso esta fase NO crea
un CMS de bloques que duplique esos modelos — agrega solo una capa de orquestacion (orden +
visibilidad) mas los 2-3 bloques que genuinamente faltaban.

### 14.1 Modelos nuevos — viven en `shared/models.py`, NO en `shop/models.py`

`ContentBlockConfig` y `CatalogRelation` son genericos (via `ContentType` + `object_uuid`, nunca
`GenericForeignKey` — ver docstring de `shared/models.py` sobre por que) para que Renting/
Technical Services puedan sumarse despues sin duplicar el modelo. En esta fase solo se usan
Shop-a-Shop; el contrato admin (`dashboard/api/content_blocks_views.py`) los expone con `product`
como parametro, ocultando el `content_type` generico al consumidor de la API.

- `ContentBlockConfig`: orden + visibilidad de los 15 bloques. **Sin fila para un bloque = visible
  con el orden por defecto** (`ContentBlockConfig.DEFAULT_ORDER`) — los productos existentes antes
  de esta fase no requirieron backfill.
- `CatalogRelation`: un solo modelo para "productos compatibles"/"accesorios recomendados"/
  "productos relacionados" (`relation_type`), no tres modelos.

Service layer: `shared/services/content_blocks.py`
(`ContentBlockConfigSelector`/`Commands`, `CatalogRelationSelector`/`Commands`).

### 14.2 Los 2 bloques de texto nuevos — campos directos en `Product`

`Product.scope` (Alcance) y `Product.warranty` (Garantia) — `TextField(blank=True)`, mismo patron
que `description`. No son modelos hijos porque son texto unico, no listas.

### 14.3 Exposicion publica — mismo endpoint, sin endpoints nuevos

`ProductDetailSerializer` (`shop/api/serializers.py`) gana, de forma aditiva:
`warranty`, `scope`, `content_blocks` (los 15 bloques ya resueltos: `block_type`/`display_order`/
`is_visible`), `related_products`, `compatible_products`, `accessories` (cada uno una lista de
`ProductSerializer`, resuelta via `CatalogRelationSelector.get_related_objects`). Todo viaja en la
misma respuesta de `GET /shop/products/{uuid}/detail/` — ningun campo existente cambio de forma.

### 14.4 Admin — `dashboard/api/content_blocks_views.py`

Dos ViewSets nuevos, registrados en `dashboard/api/urls.py`:

```
GET  /api/v1/dashboard/product-content-blocks/?product=<uuid>       15 bloques resueltos
POST /api/v1/dashboard/product-content-blocks/reorder/               body: product, ordered_block_types
POST /api/v1/dashboard/product-content-blocks/set-visibility/        body: product, block_type, is_visible

GET    /api/v1/dashboard/product-relations/?product=<uuid>&relation_type=X
POST   /api/v1/dashboard/product-relations/                          body: product, relation_type, related_product
DELETE /api/v1/dashboard/product-relations/<uuid>/
POST   /api/v1/dashboard/product-relations/reorder/                  body: product, relation_type, ordered_uuids
```

Permisos: `IsAdminUser`, igual que el resto del catalogo enriquecido (seccion 13). Un producto no
puede relacionarse consigo mismo (validado en la vista).

**Pendiente (Fase 4, frontend, no implementado en esta pasada):** pestana "Contenido del
Producto" en `ProductForm.vue` (coexiste con las 9 pestanas existentes de la seccion 13, no las
reemplaza — enlaza a ellas para el contenido real, solo controla orden/visibilidad + edita
scope/warranty/relaciones inline) y el registry bloque->componente en `ShopDetailContent.vue`
(reemplaza el orden hardcodeado del template; conecta `PublicDetailRelated.vue`, hoy sin uso).
Ver `DISENO_FASE2_SHOP_CONTENIDO_PDP_2026-08-05.md` §5-6 para el diseno completo de esa parte.
