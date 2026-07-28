# 10 — PLAN DE REFACTORIZACIÓN
**Fecha:** 2026-07-16  
**Estrategia:** Iteraciones de bajo riesgo, prioridad por impacto en seguridad → correctitud → rendimiento → mantenibilidad

> ✅ **COMPLETADO — sincronizado 2026-07-27.** Iteraciones 1-5 ejecutadas en su totalidad (ver
> `12_CHECKLIST_IMPLEMENTACION.md` SPRINT 0-4 y `01_AUDITORIA_GENERAL.md` §2-3/§7). De Iteración 6
> (largo plazo): 6.1 (split `RentalRequest`) ✅ resuelto 2026-07-27; 6.2 (`BaseOperationFSM`) y 6.3
> (squash de migraciones) siguen abiertas, sin urgencia; 6.4 (descomponer `HomeConfigView.vue`) es
> hoy el único ítem abierto de toda la punch list de deuda técnica, diferido a propósito a su propia
> sesión — ver `01_AUDITORIA_GENERAL.md` §6 punto 5 y §7.21.

---

## Principios de la Refactorización

1. **Una cosa a la vez** — un PR por hallazgo (no mega-PRs)
2. **Test antes de refactorizar** — si el código a modificar no tiene tests, escribirlos primero
3. **No cambiar contratos API** — las refactorizaciones son internas; los endpoints no cambian
4. **Migraciones en PRs separados** — no mezclar cambios de schema con lógica
5. **Sin regresiones de fases anteriores** — los bugs corregidos en 2026-07-03 (N+1 orders, COD, inventory stubs) no deben reaparecer

---

## ITERACIÓN 1 — Seguridad Crítica (1-2 días)

**Objetivo:** Cerrar los 4 hallazgos críticos de seguridad antes del próximo despliegue.

### 1.1 — Fix inventory permissions (15 min)
- `inventory/api/views.py:41, 145`: reemplazar `permissions.IsAdminUser` con `users.api.permissions.IsAdminUser`
- Test: verificar que `is_staff=True, is_superuser=False` recibe 403

### 1.2 — Remover integrity_signature de respuestas (30 min)
- `payment/online/api/serializers.py`: remover del fields list
- `payment/online/api/views.py:335`: remover de la respuesta manual
- Test: confirmar que la respuesta de `confirmation` no incluye el campo

### 1.3 — Bloquear /internal/ en nginx (15 min)
- `nginx-common.conf`: agregar `location /api/v1/internal/ { deny all; return 403; }`
- Test: curl externo a `/api/v1/internal/ai/orders/` debe retornar 403

### 1.4 — Rate limiting en AdminLoginView (30 min)
- `users/api/admin_auth.py`: agregar `throttle_classes`, `throttle_scope = 'admin_login'`
- `settings/base.py`: agregar `'admin_login': '5/hour'` a `DEFAULT_THROTTLE_RATES`

### 1.5 — Restricción de schema/docs + inventory list (30 min)
- `ecommerce/urls.py`: `permission_classes=[IsAdminUser]` en SpectacularAPIView/SwaggerView
- `inventory/api/views.py:42`: cambiar `IsAuthenticated` a `IsAdminUser` para list/retrieve

---

## ITERACIÓN 2 — Bugs Funcionales (2-3 días)

### 2.1 — Fix router Vue: ruta renting-operations (5 min)
Reordenar rutas en `router.js` — estática antes que dinámica.

### 2.2 — Eliminar debug code frontend (15 min)
Quitar `alert()` de `AppShell.vue:48`.

### 2.3 — `@transaction.atomic` en Commands críticos (4h)
Orden de prioridad:
1. `users/services/commands.py` — todos los métodos de escritura
2. `payment/online/services/commands.py` — `initialize_transaction`
3. `support/services/commands.py` — `get_or_create_room`, `mark_messages_read`
4. `marketing/services/commands.py` — `dispatch`, `send_now`
5. `notifications/services/commands.py` — `update_template`

### 2.4 — Crear `core/services/commands.py` (3h)
Mover `HomeConfigCommands`, `NavbarLinkCommands` y demás classes Commands desde `selectors.py` a `commands.py`. Agregar `@transaction.atomic` a todos los métodos de escritura. Actualizar imports en `core/api/internal_ai.py` y `dashboard/api/views.py`.

### 2.5 — Fix file upload validation (3h)
- `quotes/services/commands.py`: agregar `validate_file()` con restricciones
- `operations/services/commands.py:426-443`: agregar `validate_file()`
- `accounts/services/commands.py:733`: agregar `magic_bytes_check=True`

---

## ITERACIÓN 3 — Base de Datos (1 semana)

### 3.1 — Constraints e índices faltantes (2h, 7 migraciones)
Orden por impacto:
1. `ServiceReview.Meta.unique_together = ('user', 'service')` + migración
2. `Quotation.status`: `db_index=True` + migración
3. `EquipmentVariant.is_active`: `db_index=True` + migración
4. `OperationAssignment.status`: `db_index=True` + migración
5. `EmailVerificationCode`: index compuesto `(email, is_used)` + migración
6. `UserProfile.document`: `UniqueConstraint(fields=['document_type', 'document'], condition=Q(document__isnull=False))` + migración
7. `ServiceVariant.is_active`: `db_index=True` + migración

Ejecutar cada migración individualmente y verificar con `EXPLAIN ANALYZE` que el índice se usa.

### 3.2 — Refactorizar StockRecord GenericForeignKey (4h)
Opción recomendada: eliminar el accessor `GenericForeignKey` y documentar que la resolución es manual. Alternativa: 3 FKs concretas opcionales (`product_variant`, `equipment_variant`, `service_variant`).

### 3.3 — Fix N+1 en serializers (4h)
Por prioridad:
1. `CartSerializer.get_total` — pre-calcular taxes antes del loop
2. `ShipmentOrderSummarySerializer.get_items_count` — Python filter sobre prefetch
3. `FlashOfferCardSerializer.get_item_thumbnail` — prefetch images en selector
4. `FooterGroupSerializer.get_links_count` — prefetch links + Python filter
5. `UserProfile.total_services_completed` — annotation en Selector

---

## ITERACIÓN 4 — Service Layer (2 semanas)

### 4.1 — `ProductImageCommands` en shop (4h)
Crear `ProductImageCommands.add_image()`, `delete_image()`, `set_primary_image()` en `shop/services/commands.py`. Actualizar `dashboard/api/views.py:239-267` para usar estos Commands. Agregar tests.

### 4.2 — `PaymentCardCommands` (2h)
Extraer lógica de `payment/cards/views.py` a `payment/cards/services/commands.py`. Incluir lógica de "primera tarjeta = default" y guard de race condition.

### 4.3 — `InventoryCommands.create_stock_record()` (2h)
Extraer la lógica de `inventory/api/views.py:81-100` a un Command. ViewSet solo llama el Command.

### 4.4 — `AdminMetricsOrchestrator` — delegar a Selectors (3h)
Reemplazar queries ORM directas en `admin_orchestrators.py:906-1038` con llamadas a `OrderSelector`, `UserSelector`, `ProductSelector`, `RentingSelector`.

### 4.5 — `QuotationAdminOrchestrator.partial_update()` (1h)
Extraer `quotation.save()` de `dashboard/api/views.py:627` a `QuotationCommands.update()`.

### 4.6 — Fix soft-delete (7 instancias de .delete() físico) (3h)
Reemplazar `.delete()` por `obj.is_deleted = True; obj.is_active = False; obj.save()` o crear `Commands.soft_delete()` genérico.

### 4.7 — Fix ProfileResolver violations (30 min)
- `accounts/services/commands.py:381`: `ProfileResolver.resolve(user)`
- `accounts/api/serializers.py:213`: `ProfileResolver.get_profile(obj.reviewer)`

### 4.8 — `NotificationPreferenceCommands` (1h)
Extraer `UserNotificationPreference.objects.update_or_create()` de `notifications/api/views.py:80`.

### 4.9 — `CartCommands.add_to_wishlist()` (30 min)
Extraer `WishlistItem.objects.get_or_create()` de `cart/api/views.py:176`.

---

## ITERACIÓN 5 — Frontend (2-3 semanas)

### 5.1 — Lazy loading de rutas (3h)
Envolver todos los componentes del router en `() => import(...)` para code-splitting.

### 5.2 — Split mega-stores (8h por store, 24h total)
Comenzar con `rentingAdmin.js`:
```
rentingEquipmentStore.js  — Equipment + Variants
rentingCatalogStore.js    — Categories + Brands + Labor  
rentalRequestStore.js     — RentalRequests + Blocks
rentalLogisticsStore.js   — CostRules + Logistics
```

### 5.3 — Capa de servicios API (12h)
Crear `services/{domain}/` para cada módulo (shop, quotes, technical_services, operations, marketing, orders). Migrar las 193 llamadas Axios directas.

### 5.4 — `StatusTimeline.vue` unificado (4h)
Componente base con interface normalizada `{ id, timestamp, status, label, icon, description }`. Cada timeline de dominio mapea sus datos a esta interface.

### 5.5 — `BaseOperationBoard.vue` (6h)
Componente base para los 4 boards Kanban. Props/slots para customización de acciones por dominio.

### 5.6 — Estandarizar error handling (8h)
Definir un patrón único (toast para acciones, inline para formularios) y aplicarlo consistentemente. Crear `useErrorHandler()` composable.

### 5.7 — Restaurar `RentalBookingWizard.vue` (2h)
Obtener la versión no minificada y hacer commit del código fuente.

---

## ITERACIÓN 6 — Refactorizaciones a Largo Plazo

### 6.1 — Split `RentalRequest` en 3 modelos 1:1 (8h)
Alta complejidad — requiere migración de datos y actualización de serializers/Commands.

### 6.2 — `BaseOperationFSM` compartido (12h)
Refactorizar `RentalOperation`, `ServiceOperation`, y `Shipment FSM` para heredar de una clase base.

### 6.3 — Squash de migraciones (8h)
4 apps con 23-28 migraciones (technical_services, core, quotes, renting).

### 6.4 — Descomponer god-components del home builder (20h)
`HomeConfigView.vue` y `ModuleBuilderModal.vue` en sub-componentes por panel.

---

## Métricas de Éxito

| Métrica | Estado 2026-07-16 | Objetivo | Estado 2026-07-27 |
|---|---|---|---|
| Hallazgos críticos de seguridad | 4 | 0 | ✅ 0 |
| ViewSets con ORM directo | 14 | <3 (casos edge documentados) | ✅ Resuelto (ARCH-C1/H1-H9, checklist SPRINT 3) |
| Commands sin `@transaction.atomic` | 15 métodos | 0 | ✅ 0 |
| N+1 confirmados en serializers | 5 | 0 | ✅ 0 (SPRINT 2) |
| Rutas Vue con lazy loading | 0% | 100% | ✅ 100% (SPRINT 4) |
| Stores Pinia > 300 líneas | 3 | 0 | ✅ 0 — los 3 originales divididos + 40 módulos admin restantes migrados a Pinia (2026-07-27) |
| Componentes Vue muertos | 4+ | 0 | ✅ 0 (SPRINT 4 + purga de doc 13, 2026-07-23) |
| Endpoints admin sin rate limiting | 1 | 0 | ✅ 0 |
| Archivos internal_ai accesibles externamente | Todos | 0 (bloqueados por nginx) | ✅ 0, verificado en vivo contra producción |
