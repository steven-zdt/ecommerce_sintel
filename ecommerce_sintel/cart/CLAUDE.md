# App: cart — Instrucciones IA

## Nota (2026-07-03)

No existe `ecommerce_sintel/cart/.AGENT/docs/ARQUITECTURA_COMPLETA_CART.md` (referenciado desde el
`CLAUDE.md` raiz pero nunca creado). Este archivo es la unica fuente de contexto real para esta
app hasta que se cree ese documento.

## Responsabilidad de esta app

Carrito de compras por usuario. Gestión de ítems (agregar, actualizar cantidad, eliminar).
El carrito se vacía automáticamente al crear una orden en `orders`.

## Archivos clave

| Archivo | Propósito |
|---------|-----------|
| `models.py` | `Cart` (FK a User con `unique=True`, un carrito por usuario garantizado en BD), `CartItem` (FK a `Cart` + dos FK nullable `variant`/`service_variant`, exactamente una de las dos) |
| `api/views.py` | CartViewSet: get_or_create cart, add_item, update_item, remove_item, clear |
| `api/serializers.py` | CartSerializer, CartItemSerializer, CartItemInputSerializer |
| `services/commands.py` | CartCommands: add_item(), update_item_quantity(), remove_item(), clear_cart(), checkout_cart() |
| `services/selectors.py` | CartSelector: get_for_user(), get_by_guest_id(), get_cart_queryset() |

## Patrones obligatorios en esta app

- Un carrito por usuario, garantizado con `unique=True` en `Cart.user` (migration `0005`, Fase 6
  auditoria de BD 2026-07-03) — antes solo lo garantizaba `get_or_create()` de aplicacion, vulnerable
  a condicion de carrera.
- `CartItem` usa **dos ForeignKey nullable** (`variant`, `service_variant`), **no**
  `GenericForeignKey` — exactamente una debe estar establecida, forzado con `CheckConstraint`
  (`cart_cartitem_exactly_one_target`) y con un `UniqueConstraint` parcial por cada FK
  (`cart_cartitem_unique_variant_per_cart` / `..._service_variant_per_cart`), todos en migration
  `0005`. `CartCommands.add_item()` captura `IntegrityError` de esas constraints y fusiona la
  cantidad en la fila existente en vez de fallar.
- Validar stock disponible antes de agregar: `InventorySelector.get_current_stock(variant)` (NO
  existe `InventorySelector.is_available()`).
- Owner validation: `cart.user == request.user`
- El carrito NO se elimina al hacer orden — solo se vacían los ítems (`CartCommands.clear_cart()`)
- `Cart.guest_id` existe en el modelo y `CartSelector.get_by_guest_id()` lo usa, pero **ningun
  endpoint de `api/views.py` lo expone actualmente** — es una funcionalidad de carrito-invitado
  incompleta/no conectada, no un bug activo.

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
