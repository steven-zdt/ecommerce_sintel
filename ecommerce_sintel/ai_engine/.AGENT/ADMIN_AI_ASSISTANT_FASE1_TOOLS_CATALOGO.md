# Admin AI Assistant -- FASE 1 + FASE 2: Catalogo de Tools y clasificacion de riesgo
## Vertical piloto: Catalogo (Products / Categories / Brands / Taxes, app `shop`)

Fecha: 2026-09-16
Alcance: SOLO esta vertical (recomendada como piloto por el propio plan). No se definen
Tools para ninguno de los otros 18 dominios de la matriz de Fase 0.
Metodo: lectura directa de `shop/services/selectors.py`, `shop/services/commands.py`,
`dashboard/services/admin_orchestrators.py` (`ShopAdminOrchestrator`, wrapper delgado 1:1
sobre los Selectors/Commands reales -- confirmado, no agrega logica propia) y
`dashboard/api/views.py` (l.235-450+) + `shop/api/serializers.py` para los payloads reales.

No existe accion `publish` separada en ningun endpoint de esta vertical: `is_active` es un
campo mas de `ProductInputSerializer` / `CategoryInputSerializer` / `BrandInputSerializer` /
`TaxInputSerializer`, aceptado por el mismo `partial_update`/PATCH que cualquier otro campo.
Esto obliga a una decision de diseno explicita (ver seccion "Decisiones delicadas" abajo):
la Tool layer, no la API, es quien separa "editar contenido" de "publicar".

## Niveles de riesgo (segun el plan)

0 = lectura directa | 1 = borrador sin publicar | 2 = mutacion auditada |
3 = publicacion / cambio de alto impacto, confirmacion humana obligatoria |
4 = accion sensible (delete explicito), controles superiores obligatorios

## Catalogo de Tools

### Product

| Tool | Selector/Command real | Input real | Output | Riesgo | HITL |
|---|---|---|---|---|---|
| `catalog.product.list` | `ShopAdminOrchestrator.list_products` -> `ProductSelector.list_all_for_admin` | filtros opcionales: `search`, `is_active`, `is_featured` | lista paginada `ProductSerializer` | 0 | No |
| `catalog.product.get` | `ShopAdminOrchestrator.get_product` -> `ProductSelector.get_by_uuid` | `uuid` | `ProductSerializer` (detalle completo) | 0 | No |
| `catalog.product.create_draft` | `ShopAdminOrchestrator.create_product` -> `ProductCommands.create_product` | `name`, `category` (uuid), `price`, `condition`, `short_description`, `description`, `video_url`, `scope`, `warranty`, `brand` (uuid, opc.), `is_featured`, `meta_title`, `meta_description`. **`vendor` lo inyecta el contexto de sesion (admin actual), NUNCA lo rellena el LLM.** | `Product` creado (uuid) | 1, **con 2 overrides obligatorios de la Tool sobre el default del serializer** (ver Decision 1 y 2 abajo) | No (pero ver overrides) |
| `catalog.product.update_draft` | `ShopAdminOrchestrator.update_product` -> `ProductCommands.update_product` | subconjunto de `PRODUCT_ALLOWED_FIELDS` (`name`, `short_description`, `description`, `video_url`, `scope`, `warranty`, `condition`, `is_featured`, `category`, `brand`, `meta_title`, `meta_description`) + opcionalmente `price`/`discounted_price`/`stock` de la variante default. **Excluye `is_active` explicitamente** (va por la Tool siguiente) | `Product` actualizado | 2 | No |
| `catalog.product.set_published_state` | Mismo `ShopAdminOrchestrator.update_product`/`ProductCommands.update_product`, pero la Tool solo permite el payload `{is_active: bool}` | `is_active` (bool) | `Product` actualizado | **3** | **Si, siempre** |
| `catalog.product.delete` | `ShopAdminOrchestrator.delete_product` -> `ProductCommands.delete_product` (soft-delete: `is_active=False` + `is_deleted=True`) | `uuid` | 204 | 4 | Si, siempre |
| `catalog.product.list_variants` | `ShopAdminOrchestrator.list_variants` -> `ProductVariantSelector.list_for_product` | `product_uuid` | lista `ProductVariantSerializer` | 0 | No |
| `catalog.product.create_variant` | `ShopAdminOrchestrator.create_variant` -> `ProductVariantCommands.create_variant` | `price`, `discounted_price`, `is_default`, `stock`, `attributes`, dimensiones/peso | `ProductVariant` creado | 2 (no hay estado "borrador" de variante -- si el producto padre ya esta publicado, la variante es visible de inmediato) | No, pero requiere que `catalog.product.get` confirme el estado de publicacion del padre antes de ejecutarla |
| `catalog.product.update_variant` | `ShopAdminOrchestrator.update_variant` -> `ProductVariantCommands.update_variant` | `price`, `discounted_price`, `is_default`, `stock`, `attributes`, fechas de descuento, dimensiones | `ProductVariant` actualizado | 2 (incluye cambio de precio -- el plan lo tipifica como Nivel 2 explicitamente) | No |
| `catalog.product.delete_variant` | `ShopAdminOrchestrator.delete_variant` -> `ProductVariantCommands.delete_variant` (soft-delete) | `variant_uuid` | 204 | 4 | Si |
| `catalog.product.add_image` | `ProductImageCommands.add_image` | `image` (binario), `alt_text`, `is_primary` | `ProductImageSerializer` | 2 | No |
| `catalog.product.delete_image` | `ProductImageCommands.delete_image` (hard delete, no soft-delete -- unico caso de la vertical) | `image_uuid` | 204 | 4 | Si |
| `catalog.product.set_primary_image` | `ProductImageCommands.set_primary_image` | `image_uuid` | `ProductImageSerializer` | 2 | No |

### Category / Brand / Tax (mismo patron entre si)

| Tool | Selector/Command real | Input real | Riesgo | HITL |
|---|---|---|---|---|
| `catalog.category.list` / `catalog.brand.list` / `catalog.tax.list` | `*Selector.list_all_for_admin` (`TaxSelector.list_all` en el caso de Tax) | filtros minimos | 0 | No |
| `catalog.category.get` / `catalog.brand.get` / `catalog.tax.get` | `*Selector.get_by_uuid` | `uuid` | 0 | No |
| `catalog.category.create_draft` | `CategoryCommands.create_category` | `name`, `description`, `parent` (uuid, opc.), `image`, `meta_title`, `meta_description` | 1 (mismo override de `is_active` que Product, ver Decision 1) | No |
| `catalog.brand.create_draft` | `BrandCommands.create_brand` | `name`, `logo` | 1 (idem) | No |
| `catalog.tax.create` | `TaxCommands.create_tax` | `name`, `tax_type`, `value` | **2 directo, sin nivel "borrador"** -- ver Decision 3 | No |
| `catalog.category.update` / `catalog.brand.update` | `*Commands.update_*` | campos de negocio, **excluye `is_active`** | 2 | No |
| `catalog.category.set_published_state` / `catalog.brand.set_published_state` | mismo Command, payload restringido a `{is_active}` | `is_active` | 3 | Si |
| `catalog.tax.update` | `TaxCommands.update_tax` | `name`, `tax_type`, `value`, `is_active` (aqui SI se deja junto, ver Decision 3) | **3** (no 2) | **Si** |
| `catalog.category.delete` / `catalog.brand.delete` / `catalog.tax.delete` | `*Commands.delete_*` (soft-delete) | `uuid` | 4 | Si |

## Decisiones delicadas (la parte que el usuario pidio justificar explicitamente)

**Decision 1 -- por que `create_draft` no es realmente "borrador" sin un override de la Tool.**
`ProductInputSerializer`/`CategoryInputSerializer`/`BrandInputSerializer` ponen
`is_active` con `default=True`. Si la Tool `catalog.*.create_draft` reenviara el payload
del LLM tal cual, un producto "en borrador" quedaria publicado de inmediato salvo que el
LLM recuerde poner `is_active=False` explicitamente -- inaceptable para un principio
draft-first. **Regla obligatoria de la Tool (no de la API):** `catalog.*.create_draft`
SIEMPRE fuerza `is_active=False` en el payload que arma antes de llamar al Command,
sin importar lo que pida el usuario en lenguaje natural. Para publicar, el flujo
correcto es: `create_draft` (is_active=False forzado) -> ... -> `set_published_state`
(Nivel 3, HITL). Esto es lo que separa create_draft (Nivel 1) de update_draft/update
(Nivel 2) de set_published_state (Nivel 3), aunque las tres puedan pegarle al mismo
Command (`update_product`) por debajo.

**Decision 2 -- `create_draft` de Product cruza silenciosamente al dominio Inventory.**
`ProductCommands.create_product` no solo crea el `Product`: crea tambien la
`ProductVariant` default y, si `stock > 0`, llama a `_sync_variant_stock` ->
`InventoryCommands.register_entry`, que escribe un movimiento de inventario real y
auditado. La matriz de Fase 0 trata `Inventory` como dominio propio de riesgo Alto con
su propio permiso fuera del BFF -- pero aqui se le puede escribir de rebote desde una
Tool de Catalogo Nivel 1. **Regla obligatoria de la Tool:** `catalog.product.create_draft`
fuerza tambien `stock=0` (ignora cualquier stock inicial que pida el usuario en lenguaje
natural). Cargar stock real es una operacion aparte, explicita, vía
`catalog.product.update_draft` con `stock` (Nivel 2, auditada) -- nunca agrupada dentro
de la creacion del borrador. Sin este override, un Nivel 1 "sin publicar" terminaria
escribiendo en un dominio Alto sin que el usuario lo pidiera explicitamente.

**Decision 3 -- Tax no tiene, ni deberia tener, un nivel "borrador".**
A diferencia de Product/Category/Brand, un `Tax` no es contenido de catalogo que un
cliente ve directamente -- es un parametro que alimenta el calculo de precio de TODOS
los productos que lo referencian (`PricingService`). No existe un estado intermedio
razonable ("impuesto en borrador"): o el impuesto existe con un `value` correcto, o no
existe. Por eso `catalog.tax.create` es Nivel 2 directo (no Nivel 1), y
`catalog.tax.update` se clasifica **Nivel 3 con HITL obligatorio** (mas estricto que
`catalog.category.update`/`catalog.brand.update`, que son Nivel 2) porque cambiar
`value` de un impuesto existente recalcula el precio final de todo el catalogo asociado
de forma retroactiva e inmediata -- el mismo criterio de blast-radius que justifica que
`set_published_state` sea Nivel 3, aplicado aqui a un campo de negocio en vez de a un
flag de visibilidad.

**Nota sobre Nivel 4 (deletes):** el plan agrupa todo `delete` bajo un mismo Nivel 4
generico junto con operaciones financieras y de usuarios. Todos los deletes de esta
vertical son soft-delete reversible (excepto `catalog.product.delete_image`, que es
DELETE fisico real -- unico caso duro de la vertical). Se respeta la clasificacion Nivel
4 del plan tal cual para las 5 Tools de delete de este documento, pero se deja anotado
que su severidad real es menor que un delete de Usuario o una operacion financiera
(Fase 0, filas Users/Security) -- una futura Fase 2 global podria subdividir Nivel 4 en
4a (soft-delete reversible) / 4b (irreversible o fuera de este dominio) si hace falta
diferenciar controles.
