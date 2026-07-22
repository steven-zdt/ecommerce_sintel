# 08 — BACKEND (Arquitectura y DDD)
**Fecha:** 2026-07-16  
**Referencia:** Service Layer Pattern definido en `IMPLEMENTATION_SUMMARY.md` §Service Layer

---

## Reglas arquitectónicas del proyecto

1. ViewSets llaman SOLO Commands (escritura) y Selectors (lectura) — nunca ORM directo
2. Commands: métodos estáticos, siempre `@transaction.atomic`
3. Selectors: métodos estáticos, sin efectos secundarios
4. Soft-delete obligatorio: `is_active=False` + `is_deleted=True` — nunca `DELETE` físico
5. `IsAdminUser` siempre de `users.api.permissions`
6. Notificaciones via `NotificationCommands.dispatch_notification()` — nunca `ws_notify` directo
7. `ProfileResolver` en vez de `getattr(user, 'profile', None)`

---

## CRÍTICO

### ARCH-C1 — `core/services/selectors.py` contiene Commands (writes) mezclados con Selectors
**Archivo:** `core/services/selectors.py` (642 líneas)

El archivo está nombrado `selectors.py` pero contiene 8 clases de Commands con operaciones de escritura:
`HomeConfigCommands`, `HomeCardGroupCommands`, `HomeCardCommands`, `NavbarLinkCommands`, `FooterGroupCommands`, `FooterCommands`, `FooterCTACommands`, `BrandSliderCommands`.

**Problema adicional:** Los métodos de escritura no tienen `@transaction.atomic`:
- `HomeConfigCommands.create_banner` (línea 51)
- `HomeConfigCommands.update_banner` (línea 63)
- `HomeConfigCommands.update_module_config` (línea 87)
- `HomeConfigCommands.create_module` (línea 102)
- `HomeConfigCommands.delete_module` (línea 121)
- `NavbarLinkCommands.create/update/delete` (líneas 367-384)

**Fix:** Crear `core/services/commands.py` con todas las clases Commands y dejar en `selectors.py` solo las clases de lectura. Agregar `@transaction.atomic` a todos los métodos de escritura.

---

## ALTA PRIORIDAD

### ARCH-H1 — `users/services/commands.py`: cero `@transaction.atomic`
**Archivo:** `users/services/commands.py`

Ningún método de escritura tiene el decorador:
- `UserCommands.change_password` (L20): `user.save()`
- `VerificationCommands.request_email_verification` (L33): invalidate old + create new — sin transacción, un fallo a mitad deja al usuario sin código válido
- `VerificationCommands.resend_email_verification` (L107): mismo patrón
- `UserAuditCommands.log` (L177): `UserAuditLog.objects.create()`

### ARCH-H2 — `payment/online/services/commands.py`: `initialize_transaction` sin `@transaction.atomic`
**Archivo:** `payment/online/services/commands.py:32`

Crea `Transaction` y luego salva `integrity_signature` en un segundo write. Si el segundo falla, queda una `Transaction` sin firma válida. `handle_status_change` (L156) y `PaymentCommands.confirm_payment` (L256) también carecen del decorador.

### ARCH-H3 — Otras Commands sin `@transaction.atomic`
| Archivo | Métodos sin decorator |
|---|---|
| `marketing/services/commands.py` | `dispatch` (L15), `send_now` (L40) |
| `notifications/services/commands.py` | `update_template` (L160) |
| `support/services/commands.py` | `get_or_create_room` (L8), `mark_messages_read` (L38) |

### ARCH-H4 — ORM directo en `dashboard/api/views.py`
**Archivo:** `dashboard/api/views.py`

| Línea(s) | Violación |
|---|---|
| 239-240 | `ProductImage.objects.filter().update()` + `.create()` en `add_image` |
| 253-256 | `ProductImage.objects.get()` + `img.delete()` en `delete_image` |
| 264-267 | `.get()`, `.filter().update()`, `img.save()` en `set_primary_image` |
| 627 | `quotation.save()` en `partial_update` — bypasea `QuotationAdminOrchestrator` |
| 1271, 1344, 1416 | `ProductVariant/EquipmentVariant/ServiceVariant.objects.get()` en views |
| 1566 | `HomeModuleConfig.objects.filter(...).exists()` en view |
| 1816, 1846 | `SocialLink.objects.filter(...)` en dos actions |

**Fix:** `ProductImageCommands` con `add_image`, `delete_image`, `set_primary_image` en `shop/services/commands.py`. Mover quotation update a `QuotationAdminOrchestrator`.

### ARCH-H5 — ORM directo en `inventory/api/views.py`
**Archivo:** `inventory/api/views.py:81-100`

`StockRecord.objects.create(...)` llamado directamente en la action `create` del ViewSet. No existe `InventoryCommands.create_stock_record()`. La creación del registro salta completamente la capa de Commands.

### ARCH-H6 — `dashboard/services/admin_orchestrators.py:906-1038`: `AdminMetricsOrchestrator` usa ORM directamente
Queries directas sobre `Order`, `User`, `Product`, `UserProfile`, `RentalRequest`. Debe delegar a `OrderSelector`, `UserSelector`, `ProductSelector`, `RentingSelector`.

### ARCH-H7 — `payment/cards/views.py`: CRUD completo en ViewSet sin Commands
**Archivo:** `payment/cards/views.py:49, 55, 59`

`TokenizedCard.objects.filter().exists()`, `.exists()`, `.create()` en el ViewSet. La lógica de "primera tarjeta = default" y el guard de race condition están en la vista. No existe `PaymentCardCommands`.

### ARCH-H8 — Delete físico en modelos soft-deletable
| Archivo | Línea | Modelo |
|---|---|---|
| `cart/api/views.py` | 125 | `CartItem.delete()` — bypasea `CartCommands.remove_item()` |
| `technical_services/services/commands.py` | 361 | `ServiceLevel.delete()` |
| `technical_services/services/commands.py` | 386 | `ServiceImage.delete()` |
| `technical_services/services/commands.py` | 571 | `ServiceMaterial.delete()` |
| `renting/services/commands.py` | 1023 | `EquipmentLogisticsConfig.objects.filter().delete()` (bulk) |
| `cart/services/commands.py` | 67, 81, 86 | `CartItem` (3 instancias) |
| `orders/services/commands.py` | 141 | `CartItem` post-checkout |

### ARCH-H9 — Violaciones de ProfileResolver
| Archivo | Línea | Patrón |
|---|---|---|
| `accounts/services/commands.py` | 381 | `getattr(user, 'profile', None)` en Command |
| `accounts/api/serializers.py` | 213 | `getattr(obj.reviewer, 'profile', None)` en Serializer |

---

## MEDIA PRIORIDAD

### ARCH-M1 — ORM en ViewSets de lectura (get_queryset)
Las siguientes apps usan ORM directo en `get_queryset()` en lugar de Selectors:
- `accounts/api/views.py` (líneas 315, 428, 447, 464, 485, 506, 525, 550, 588, 593)
- `quotes/api/views.py:49` — `Quotation.objects.filter(user=self.request.user, is_deleted=False)`
- `shop/api/views.py:141, 159` — `ProductVariant.objects.get()` en retrieve actions
- `technical_services/api/views.py:83, 131` — `ServiceVariant.objects.get()` en view actions
- `payment/nequi/api/views.py:32` — `Order.objects.get()` en ViewSet
- `renting/api/views.py:713-718` — fallback en `EquipmentBlockViewSet.get_queryset()`

### ARCH-M2 — `operations/api/views.py`: múltiples ORM directos en lógica de negocio
- Líneas 180, 201, 209, 222: queries directas a `TechnicianProfile`, `UserProfile`, `DispatcherProfile` en action `available_staff`
- Líneas 316, 328, 337: `User.objects.get()` y `DispatcherProfile.objects.get()` en create/update/destroy

### ARCH-M3 — `notifications/api/views.py:80`: write directo en ViewSet
`UserNotificationPreference.objects.update_or_create(...)` sin Commands wrapper, sin `@transaction.atomic`.

### ARCH-M4 — `cart/api/views.py:176`: `WishlistItem.objects.get_or_create()` en ViewSet
Write directo. No existe `CartCommands.add_to_wishlist()`.

### ARCH-M5 — `payment/online/api/views.py:75, 118, 137`: `TransactionEvent.objects.create()` en views
Tres instancias en helper `_sync_wompi_status`. Los eventos de transacción son escrituras que deben ir en Commands.

### ARCH-M6 — `users/api/views.py:141`: `user.delete()` físico en ViewSet
Intencional (GDPR erase), pero debe encapsularse en `UserCommands.erase_user()` para mantener el patrón.

### ARCH-M7 — `quotes/api/views.py:155`: `QuotationAttachment.objects.create()` en ViewSet
Debe ir en `QuotationCommands.add_attachment()`.

---

## Lo que está bien (no reportar de nuevo)

- Cero imports de `rest_framework.permissions.IsAdminUser` — migración completa al custom
- Cero llamadas `ws_notify` directas — todo pasa por `NotificationCommands.dispatch_notification()`
- Signals (`core/signals.py`, `technical_services/signals.py`) son solo invalidación de cache, sin side-effects de negocio
- KYC, renting, orders, shop Commands bien decorados con `@transaction.atomic`
- Dashboard BFF correcto para los dominios principales (products, variants, categories, rentals, services, quotes)
