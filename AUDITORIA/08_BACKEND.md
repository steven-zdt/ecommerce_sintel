# 08 — BACKEND (Arquitectura y DDD)
**Fecha:** 2026-07-16  
**Referencia:** Service Layer Pattern definido en `IMPLEMENTATION_SUMMARY.md` §Service Layer

> **Sincronizado 2026-07-27** contra `01_AUDITORIA_GENERAL.md` §2-3: **ARCH-C1 y los 9 ARCH-H
> están todos ✅ Resueltos.** MEDIA PRIORIDAD (ARCH-M1-M7) no re-verificada individualmente.

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
**Estado: ✅ RESUELTO** — `core/services/commands.py` creado, `selectors.py` ya solo exporta `HomeConfigSelector`. Nota: un hallazgo real durante SPRINT 1 encontró ~21 imports lazy en `dashboard/api/views.py` que seguían apuntando al `selectors.py` viejo tras el split — corregido, ver checklist 12.
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
**Estado: ✅ RESUELTO** — 5 decoradores presentes.
**Archivo:** `users/services/commands.py`

Ningún método de escritura tiene el decorador:
- `UserCommands.change_password` (L20): `user.save()`
- `VerificationCommands.request_email_verification` (L33): invalidate old + create new — sin transacción, un fallo a mitad deja al usuario sin código válido
- `VerificationCommands.resend_email_verification` (L107): mismo patrón
- `UserAuditCommands.log` (L177): `UserAuditLog.objects.create()`

### ARCH-H2 — `payment/online/services/commands.py`: `initialize_transaction` sin `@transaction.atomic`
**Estado: ✅ RESUELTO CON DISEÑO MÁS FINO** — el atómico cubre creación+firma; la llamada a Wompi corre deliberadamente fuera para que un registro `ERROR` de auditoría sobreviva un fallo de red sin perder el registro (bug real corregido en el camino: el atómico original envolvía TODO, así que un `WompiApiError` deshacía también el propio registro de error).
**Archivo:** `payment/online/services/commands.py:32`

Crea `Transaction` y luego salva `integrity_signature` en un segundo write. Si el segundo falla, queda una `Transaction` sin firma válida. `handle_status_change` (L156) y `PaymentCommands.confirm_payment` (L256) también carecen del decorador.

### ARCH-H3 — Otras Commands sin `@transaction.atomic`
**Estado: ✅ RESUELTO** (SPRINT 1) — marketing/notifications/support todos decorados.
| Archivo | Métodos sin decorator |
|---|---|
| `marketing/services/commands.py` | `dispatch` (L15), `send_now` (L40) |
| `notifications/services/commands.py` | `update_template` (L160) |
| `support/services/commands.py` | `get_or_create_room` (L8), `mark_messages_read` (L38) |

### ARCH-H4 — ORM directo en `dashboard/api/views.py`
**Estado: ✅ RESUELTO** (SPRINT 3) — `ProductImageCommands` creado y conectado; `quotation.save()` delega a `QuotationAdminOrchestrator.partial_update()`.
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
**Estado: ✅ RESUELTO** (SPRINT 3) — `InventoryCommands.create_stock_record()` creado y usado.
**Archivo:** `inventory/api/views.py:81-100`

`StockRecord.objects.create(...)` llamado directamente en la action `create` del ViewSet. No existe `InventoryCommands.create_stock_record()`. La creación del registro salta completamente la capa de Commands.

### ARCH-H6 — `dashboard/services/admin_orchestrators.py:906-1038`: `AdminMetricsOrchestrator` usa ORM directamente
**Estado: ✅ RESUELTO** — delega en `OrderSelector`/`UserSelector`/`ProductSelector`.
Queries directas sobre `Order`, `User`, `Product`, `UserProfile`, `RentalRequest`. Debe delegar a `OrderSelector`, `UserSelector`, `ProductSelector`, `RentingSelector`.

### ARCH-H7 — `payment/cards/views.py`: CRUD completo en ViewSet sin Commands
**Estado: ✅ RESUELTO** — `PaymentCardCommands` (`save_card`/`remove_card`/`set_default_card`) creado y conectado.
**Archivo:** `payment/cards/views.py:49, 55, 59`

`TokenizedCard.objects.filter().exists()`, `.exists()`, `.create()` en el ViewSet. La lógica de "primera tarjeta = default" y el guard de race condition están en la vista. No existe `PaymentCardCommands`.

### ARCH-H8 — Delete físico en modelos soft-deletable
**Estado: ✅ RESUELTO** (SPRINT 3) — todas las instancias listadas confirmadas con soft-delete real. Hallazgo real: `CartCommands.remove_item()` existía con una firma distinta y CERO callers; la vista hacía el soft-delete inline. Re-firmado y conectado.
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
**Estado: ✅ RESUELTO** — ambas instancias usan `ProfileResolver.resolve()`/`.get_profile()`.
| Archivo | Línea | Patrón |
|---|---|---|
| `accounts/services/commands.py` | 381 | `getattr(user, 'profile', None)` en Command |
| `accounts/api/serializers.py` | 213 | `getattr(obj.reviewer, 'profile', None)` en Serializer |

---

## MEDIA PRIORIDAD

> **Estado (2026-07-30): ✅ Los 7 items MEDIA (ARCH-M1 a M7) resueltos.** 4 ya estaban resueltos
> por sesiones previas (M3, M4, M5, M6 — el doc nunca se sincronizó); los otros se corrigieron
> esta sesión. Detalle completo en `project_sintel_auditoria_enterprise_remediation.md`. Verificado
> con `manage.py check` limpio, `py_compile` en todos los archivos tocados, y suites de test en
> verde en accounts/quotes/shop/technical_services/payment/operations/notifications/cart/kyc/orders
> (12 apps). `accounts/api/views.py` confirmado en 0 sitios ORM directos (solo queda un
> `.objects.none()` de stub para swagger, no una violación real).

### ARCH-M1 — ORM en ViewSets de lectura (get_queryset)
Las siguientes apps usan ORM directo en `get_queryset()` en lugar de Selectors:
- `accounts/api/views.py` (líneas 315, 428, 447, 464, 485, 506, 525, 550, 588, 593) — ✅ Resuelto: `ContractorCVSelector`/`ContractorProfileSelector`/`AvailabilitySelector.list_all()` (nuevos)
- `quotes/api/views.py:49` — `Quotation.objects.filter(user=self.request.user, is_deleted=False)` — ✅ Resuelto: `QuotationSelector.list_for_user()`/`.none()` (nuevo)
- `shop/api/views.py:141, 159` — `ProductVariant.objects.get()` en retrieve actions — ✅ Resuelto: `ProductVariantSelector.get_by_uuid()` (ya existía)
- `technical_services/api/views.py:83, 131` — `ServiceVariant.objects.get()` en view actions — ✅ Resuelto: `ServiceVariantSelector.get_by_uuid()` (ya existía)
- `payment/nequi/api/views.py:32` — `Order.objects.get()` en ViewSet — ✅ Resuelto: `OrderSelector.get_by_uuid()` (ya existía)
- `renting/api/views.py:713-718` — fallback en `EquipmentBlockViewSet.get_queryset()` — ✅ Resuelto: `EquipmentBlockSelector.list_all()` (nuevo)

### ARCH-M2 — `operations/api/views.py`: múltiples ORM directos en lógica de negocio
✅ Resuelto — `OperationStaffSelector` (nuevo) + `DispatcherSelector.get_by_uuid()` (nuevo). 0 ORM directo restante.
- Líneas 180, 201, 209, 222: queries directas a `TechnicianProfile`, `UserProfile`, `DispatcherProfile` en action `available_staff`
- Líneas 316, 328, 337: `User.objects.get()` y `DispatcherProfile.objects.get()` en create/update/destroy

### ARCH-M3 — `notifications/api/views.py:80`: write directo en ViewSet
**Estado: ✅ Ya resuelto por una sesión previa (2026-07-30, verificado no re-hecho)** — `NotificationPreferenceCommands.set_preference()` ya existe (`@staticmethod` + `@transaction.atomic`), el ViewSet ya lo llama.

### ARCH-M4 — `cart/api/views.py:176`: `WishlistItem.objects.get_or_create()` en ViewSet
**Estado: ✅ Ya resuelto por una sesión previa** — implementado como `WishlistCommands.add_to_wishlist()` (clase dedicada en vez de `CartCommands` como sugería el doc original), ya conectado.

### ARCH-M5 — `payment/online/api/views.py:75, 118, 137`: `TransactionEvent.objects.create()` en views
**Estado: ✅ Ya resuelto por una sesión previa** — las 3 instancias en `_sync_wompi_status` ya pasan por `WompiCommands.record_sync_event()`.

### ARCH-M6 — `users/api/views.py:141`: `user.delete()` físico en ViewSet
**Estado: ✅ Ya resuelto por una sesión previa, y de forma MEJOR que lo que pedía este doc** — `UserCommands.erase_user()` existe, pero en vez del DELETE físico que este hallazgo pedía encapsular, es un **soft-delete** (`is_deleted=True`). Motivo documentado en el propio código: un hard delete choca con `on_delete=PROTECT` dos saltos mas abajo en el grafo de borrado (`RentalOperation` protege `RentalRequest`) y causaba un `ProtectedError`/500 real en produccion/dev. El doc original pedía envolver el DELETE fisico, no eliminarlo — la sesión previa correctamente identificó que el propio DELETE fisico era el bug real y lo reemplazó, superando el alcance literal del hallazgo.

### ARCH-M7 — `quotes/api/views.py:155`: `QuotationAttachment.objects.create()` en ViewSet
✅ Resuelto — `QuotationCommands.add_attachment()`.

---

## Lo que está bien (no reportar de nuevo)

- Cero imports de `rest_framework.permissions.IsAdminUser` — migración completa al custom
- Cero llamadas `ws_notify` directas — todo pasa por `NotificationCommands.dispatch_notification()`
- Signals (`core/signals.py`, `technical_services/signals.py`) son solo invalidación de cache, sin side-effects de negocio
- KYC, renting, orders, shop Commands bien decorados con `@transaction.atomic`
- Dashboard BFF correcto para los dominios principales (products, variants, categories, rentals, services, quotes)
