# Guia: Productos, Categorias y Marcas — Arquitectura actual (Vue 3 SPA)

> Actualizado 2026-06-11. Versión anterior describía HTMX + Django SSR — obsoleta.

---

## Dependencias de modelos

```
Product (requiere Category, opcional Brand)
    ├── category → Category  [REQUERIDO — SlugRelatedField uuid]
    └── brand    → Brand     [OPCIONAL  — SlugRelatedField uuid]

ProductVariant (pertenece a Product)
    └── product → Product
```

Orden correcto para crear un producto:
1. Crear Categoria (si no existe)
2. Crear Marca (opcional)
3. Crear Producto — elige Categoria y Marca en el select del form

---

## Endpoints reales (2026-06)

### Lectura (public ReadOnly — sin auth)

| Recurso | Endpoint |
|---|---|
| Listar productos | `GET /api/v1/shop/products/` |
| Listar categorias | `GET /api/v1/shop/categories/` |
| Listar marcas | `GET /api/v1/shop/brands/` |
| Listar impuestos | `GET /api/v1/shop/taxes/` |
| Variantes de producto | `GET /api/v1/shop/variants/?product={uuid}` |

### Escritura (admin — requiere JWT con is_staff + role=ADMIN)

| Operacion | Endpoint |
|---|---|
| Crear producto | `POST /api/v1/dashboard/products/` |
| Editar producto | `PATCH /api/v1/dashboard/products/{id}/` |
| Eliminar producto | `DELETE /api/v1/dashboard/products/{id}/` |
| Crear variante | `POST /api/v1/dashboard/products/{id}/variants/create/` |
| Editar variante | `PATCH /api/v1/dashboard/products/{id}/variants/{vid}/` |
| Eliminar variante | `DELETE /api/v1/dashboard/products/{id}/variants/{vid}/delete/` |
| Crear categoria | `POST /api/v1/dashboard/categories/` |
| Editar categoria | `PATCH /api/v1/dashboard/categories/{id}/` |
| Eliminar categoria | `DELETE /api/v1/dashboard/categories/{id}/` |
| Crear marca | `POST /api/v1/dashboard/brands/` |
| Editar marca | `PATCH /api/v1/dashboard/brands/{id}/` |
| Eliminar marca | `DELETE /api/v1/dashboard/brands/{id}/` |
| Crear impuesto | `POST /api/v1/dashboard/taxes/` |
| Editar impuesto | `PATCH /api/v1/dashboard/taxes/{id}/` |
| Eliminar impuesto | `DELETE /api/v1/dashboard/taxes/{id}/` |

---

## Payload ProductInputSerializer

```json
{
  "name": "Laptop XPS 15",
  "category": "uuid-de-la-categoria",
  "brand": "uuid-de-la-marca-o-null",
  "condition": "new",
  "description": "...",
  "is_active": true,
  "is_featured": false,
  "price": "1299.99",
  "sku": "LAPTOP-001",
  "meta_title": "Laptop XPS 15 | Sintel",
  "meta_description": "..."
}
```

Notas clave:
- `category` y `brand` reciben **uuid string** (no PK entero) — son `SlugRelatedField(slug_field='uuid')`
- `price` y `sku` solo en modo create (crean la variante default)
- En PATCH solo se envian los campos a modificar

---

## Payload ProductVariantInputSerializer

```json
{
  "sku": "LAPTOP-001-BLUE",
  "price": "1299.99",
  "discounted_price": "1099.99",
  "stock": 10,
  "is_default": false,
  "attributes": { "color": "Azul", "RAM": "16GB" },
  "discount_start_date": "2026-06-01T00:00:00",
  "discount_end_date": "2026-06-30T23:59:59"
}
```

El campo `effective_price` en la respuesta aplica la logica de descuento temporal
(solo activo si `now` esta dentro de `[discount_start_date, discount_end_date]`).

---

## Soft-delete

- Producto: `is_active=False` + `is_deleted=True` (ambos requeridos)
- Categoria: `is_active=False` + `is_deleted=True`
- Marca: `is_active=False` + `is_deleted=True`
- El admin lista con `is_deleted=False` — nunca ve eliminados
- El DELETE al dashboard BFF ejecuta el soft-delete via `delete_product/category/brand` command

---

## Rutas del panel admin (Vue Router)

| URL | Vista | Accion |
|---|---|---|
| `/panel/productos` | ProductList.vue | Lista + offcanvas crear/editar |
| `/panel/categorias` | CategoryList.vue | Lista + offcanvas crear/editar |
| `/panel/marcas` | BrandList.vue | Lista + offcanvas crear/editar |
| `/panel/impuestos` | TaxList.vue | Lista + offcanvas crear/editar |

---

## Archivos frontend relevantes

```
src/modules/shop/
├── ProductList.vue       — Tabla productos + SintelOffcanvas
├── ProductForm.vue       — Form 3 tabs: General / SEO / Variantes
├── CategoryList.vue      — Tabla categorias
├── CategoryForm.vue      — Form 2 tabs: General / SEO
├── BrandList.vue         — Tabla marcas
├── BrandForm.vue         — Form simple: nombre + is_active
├── TaxList.vue           — Tabla impuestos
└── TaxForm.vue           — Form: nombre + tipo + valor + is_active
```

---

## Archivos backend relevantes

```
shop/
├── models.py             — Category, Brand, Product, ProductVariant, Tax
├── api/views.py          — ReadOnlyModelViewSet para todo (publico)
├── api/serializers.py    — ProductSerializer + Input serializers
└── services/
    ├── commands.py       — ProductCommands, CategoryCommands, BrandCommands, TaxCommands
    ├── selectors.py      — ProductSelector, CategorySelector
    └── pricing_service.py — PricingService.calculate_variant_price() con logica temporal

dashboard/
├── api/views.py          — AdminProductViewSet, AdminCategoryViewSet, AdminBrandViewSet
├── api/urls.py           — router: products/, categories/, brands/, taxes/
└── services/admin_orchestrators.py — ShopAdminOrchestrator
```
