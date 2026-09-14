# 02 — DEUDA TÉCNICA
**Fecha:** 2026-07-16
**Clasificación por impacto y esfuerzo**

> **Sincronizado 2026-07-27** contra `01_AUDITORIA_GENERAL.md` (§2-4, §7) y
> `12_CHECKLIST_IMPLEMENTACION.md`: todos los items Crítica y Alta quedaron anotados con su estado
> real verificado. Los items Media y Baja (secciones más abajo) **no se re-verificaron en esta
> pasada** — tratarlos como snapshot de 2026-07-16 hasta una nueva auditoría puntual.

---

## Deuda Técnica Crítica (bloquea seguridad o correctitud)

| ID | Descripción | App | Esfuerzo | Estado (2026-07-27) |
|---|---|---|---|---|
| DT-C1 | `inventory/api/views.py` usa Django `IsAdminUser` (is_staff) en vez del custom (is_staff+superuser) | inventory | 15 min — 2 líneas | ✅ Resuelto (SEC-C1) |
| DT-C2 | `integrity_signature` expuesta en respuesta API de pagos | payment | 30 min — serializer + 1 línea view | ✅ Resuelto con matiz (SEC-C2) — ya no en respuestas de solo-lectura; sigue en `initialize()` a propósito, es funcionalmente necesaria ahí |
| DT-C3 | `/api/schema/` y `/api/docs/` accesibles sin restricción de rol | ecommerce | 15 min — 2 líneas | ✅ Resuelto (SEC-C3) |
| DT-C4 | `AdminLoginView` sin rate limiting (brute force en superuser) | users | 30 min — throttle_classes | ✅ Resuelto (SEC-H1) |
| DT-C5 | `/api/v1/internal/ai/*` no bloqueado en nginx — accesible externamente | nginx | 15 min — 3 líneas nginx | ✅ Resuelto (SEC-H5), verificado en vivo contra producción |
| DT-C6 | Quotations: file upload sin validación para usuarios anónimos | quotes | 2h — validate_file + tests | ✅ Resuelto (SEC-H2 + Q-01/Q-02, Auditoría Enterprise) |
| DT-C7 | Operations `upload_document` sin validación de archivo | operations | 1h | ✅ Resuelto (SEC-H4) |
| DT-C8 | `StockRecord.item_variant` GenericForeignKey permanentemente roto | inventory | 3h — eliminar accessor | ✅ Resuelto (documentado + mitigado, DB-C1) — 0 callers directos del GFK roto |
| DT-C9 | Inventory list/retrieve accesible por cualquier usuario autenticado | inventory | 15 min | ✅ Resuelto (SEC-H7) |

---

## Deuda Técnica Alta (correctitud arquitectónica)

| ID | Descripción | App | Esfuerzo | Estado (2026-07-27) |
|---|---|---|---|---|
| DT-H1 | `core/services/selectors.py` contiene Commands — mezcla escritura/lectura, sin `@transaction.atomic` | core | 2h — split en commands.py | ✅ Resuelto (ARCH-C1) |
| DT-H2 | `users/services/commands.py` cero `@transaction.atomic` en todos los métodos de escritura | users | 1h | ✅ Resuelto (ARCH-H1) |
| DT-H3 | `payment/online/services/commands.py`: `initialize_transaction` sin `@transaction.atomic` | payment | 30 min | ✅ Resuelto con diseño más fino (ARCH-H2) — atómico cubre creación+firma, llamada a Wompi corre fuera a propósito |
| DT-H4 | Otras Commands sin `@transaction.atomic` (marketing, notifications, support) | varios | 1h total | ✅ Resuelto (SPRINT 1, checklist 12) |
| DT-H5 | `dashboard/api/views.py`: 6+ operaciones ORM directas (image mgmt, quotation.save()) | dashboard | 4h — ProductImageCommands | ✅ Resuelto (ARCH-H3) |
| DT-H6 | `inventory/api/views.py`: `StockRecord.objects.create()` directo en ViewSet | inventory | 2h — InventoryCommands.create_stock_record() | ✅ Resuelto (ARCH-H4) |
| DT-H7 | `payment/cards/views.py`: CRUD completo de TokenizedCard en ViewSet sin Commands | payment | 2h — PaymentCardCommands | ✅ Resuelto (ARCH-H6) |
| DT-H8 | `dashboard/services/admin_orchestrators.py:906`: AdminMetricsOrchestrator con ORM directo | dashboard | 2h — delegar a Selectors | ✅ Resuelto (ARCH-H7) |
| DT-H9 | Deletes físicos en modelos soft-deletable (7 instancias en 4 apps) | varios | 2h | ✅ Resuelto (ARCH-H5 + SPRINT 3, incluye el hallazgo real de `CartCommands.remove_item()` sin callers) |
| DT-H10 | `ServiceReview` sin `unique_together` — permite reseñas duplicadas | technical_services | 30 min + migración | ✅ Resuelto (DB-H2) |
| DT-H11 | `Quotation.status` sin `db_index` — table-scan en filtros del CPQ | quotes | 15 min + migración | ✅ Resuelto (DB-H4) |
| DT-H12 | `UserProfile.document` sin unicidad por `(document_type, document)` | accounts | 30 min + migración | ✅ Resuelto (SPRINT 2) — con un bug real corregido en el camino: la condición inicial no excluía `document=''`, ver hallazgos de checklist 12 |
| DT-H13 | `RentalRequest` 50 campos — full-row load innecesario en listas | renting | 8h — split 1:1 | ✅ Resuelto 2026-07-27 (DB-H1) — split en 4 sub-modelos + migración final 0036 que faltaba (ver doc 01 §7.2, incluyó un incidente crítico nuevo: `NameError` que tumbaba todo el backend) |
| DT-H14 | Cambio de contraseña no invalida tokens JWT existentes | accounts | 1h | ✅ Resuelto y verificado 2026-07-27 (SEC-H6), 3/3 tests en vivo |
| DT-H15 | N+1 en `CartSerializer.get_total` (1 Tax query por ítem) | cart | 2h | ✅ Resuelto (SPRINT 2) |
| DT-H16 | N+1 en `UserProfile.total_services_completed` (COUNT por perfil en listas) | accounts | 2h — annotation | ✅ Resuelto (SPRINT 2) — con un `AttributeError` real corregido (property sin setter) |
| DT-H17 | Sin lazy loading de rutas en el router (bundle inicial contiene todo el admin) | frontend | 3h | ✅ Resuelto (SPRINT 4) |
| DT-H18 | Conflicto de ruta: `/panel/ordenes/renting` inaccesible | frontend | 5 min | ✅ Resuelto (FE-H1) |
| DT-H19 | `apps/customer/main.js` entrada muerta — monta en DOM inexistente | frontend | 15 min — eliminar | ✅ Resuelto (FE-H2) |
| DT-H20 | `alert('Global Debug Triggered')` en `AppShell.vue:48` — producción | frontend | 5 min — eliminar | ✅ Resuelto (FE-H4) |
| DT-H21 | 3 mega-stores Pinia (>400 líneas, 9+ dominios) sin split | frontend | 16h — split por dominio | ✅ Resuelto 2026-07-27 (FE-H3) — más migración completa de los 40 módulos admin restantes a Pinia (doc 01 §7.7-§7.21) |
| DT-H22 | `RentalBookingWizard.vue` minificado — código fuente ilegible | frontend | 2h — restaurar fuente | ✅ Resuelto (FE-H6) |
| DT-H23 | WhatsApp webhook sin verificación de firma `X-Hub-Signature-256` | notifications | 2h | ✅ Resuelto (N-01, Auditoría Enterprise) |

---

## Deuda Técnica Media (mantenibilidad)

| ID | Descripción | Esfuerzo |
|---|---|---|
| DT-M1 | ProfileResolver violations (2 instancias `getattr(user, 'profile', None)`) | ✅ Resuelto (ARCH-H9, doc 08) |
| DT-M2 | ORM directo en `get_queryset()` de múltiples ViewSets (accounts, quotes, shop, payment/nequi) | ✅ Resuelto 2026-07-30 (ARCH-M1, doc 08) |
| DT-M3 | `notifications/api/views.py:80` write ORM directo en ViewSet | ✅ Resuelto (ARCH-M3, doc 08) |
| DT-M4 | `cart/api/views.py:176` `WishlistItem.objects.get_or_create()` en ViewSet | ✅ Resuelto (ARCH-M4, doc 08) |
| DT-M5 | `payment/online/api/views.py:75,118,137`: `TransactionEvent.objects.create()` en views | ✅ Resuelto (ARCH-M5, doc 08) |
| DT-M6 | `operations/api/views.py`: múltiples ORM directos en lógica de negocio | ✅ Resuelto 2026-07-30 (ARCH-M2, doc 08) |
| DT-M7 | 6 índices de BD faltantes | ✅ Resuelto 2026-07-30 (DB-M1, doc 04) — solo 2 faltaban realmente |
| DT-M8 | N+1 en `ShipmentOrderSummarySerializer` y `FlashOfferCardSerializer` | 2h |
| DT-M9 | `FooterGroupSerializer.get_links_count` N+1 sin prefetch | 30 min |
| DT-M10 | Servicios API ausentes en frontend: 193 llamadas Axios directas | 12h |
| DT-M11 | 7 Timeline components duplicados | 4h — StatusTimeline base |
| DT-M12 | 4 Operation Boards duplicados | 6h — BaseOperationBoard |
| DT-M13 | `useQuoteWizard` y `useCatalogQuoteWizard` sin base compartida | 3h |
| DT-M14 | `_log_ai_action()` helper definido en múltiples archivos internal_ai.py | 30 min |
| DT-M15 | Patrones de error handling inconsistentes en frontend (5 patrones distintos) | 8h — estandarizar |
| DT-M16 | Patrones de loading state inconsistentes (3 patrones distintos) | 4h |
| DT-M17 | Colombia locations data duplicada | 15 min |
| DT-M18 | Cadenas de migración largas en 4 apps (23-28 migraciones) | 8h — squash |
| DT-M19 | `AdminContractorSerializer` dispara queries extra sin select_related apropiado | 1h |
| DT-M20 | `TechnicalServiceSerializer`: `get_calculated_price` y `get_price_info` duplican cálculo | 3h |
| DT-M21 | `SuccessCase` upload sin magic bytes check | 30 min |
| DT-M22 | Access token lifetime de 60 minutos (debería ser 15) | ✅ Resuelto y desplegado a producción (QW-17, ver `11_QUICK_WINS.md`) |
| DT-M23 | `UserDetailSerializer` expone `AdminVerificationDetailSerializer` a usuarios normales | ✅ Resuelto 2026-07-30 (SEC-M6, doc 06) — confirmado explotable (fuga real de `actor_email` de staff) |

---

## Deuda Técnica Baja (mejoras)

| ID | Descripción | Esfuerzo |
|---|---|---|
| DT-L1 | `useFormValidation.js` específico de campaña con nombre genérico | 1h |
| DT-L2 | `useRentalsStore` 14 líneas innecesariamente como store Pinia | 30 min |
| DT-L3 | `useAvailabilityStore`: dos actions duplicadas (`check` vs `fetchAvailability`) | 30 min |
| DT-L4 | `FilterSidebar.vue` sin importadores (posiblemente muerto) | ✅ Resuelto/moot 2026-07-30 — el archivo ya no existe en el árbol actual |
| DT-L5 | `src/shared/` directorio vacío | 5 min |
| DT-L6 | 12 rutas hijas de `/mi-cuenta` repiten `meta: { requiresAuth: true }` | 15 min |
| DT-L7 | `HomeConfigView.vue` (2.705L) y `ModuleBuilderModal.vue` (1.588L) — god-components | 20h |
| DT-L8 | FSM de Operaciones triplicado sin clase base compartida | 12h |
| DT-L9 | Serializers de imagen duplicados por app (shop/renting/services) | 2h |
| DT-L10 | Sin catch-all admin 404 en el router | ✅ Resuelto 2026-07-30 — catch-all ahora distingue `/panel/*` (→ `/panel/dashboard`, cae a `/panel/login` si no autenticado) de rutas públicas (→ `/`), verificado en vivo |
| DT-L11 | `Quotation.answers` JSONField — impide queries analíticas | 16h |
| DT-L12 | `OrderServiceDetail.contact_person` JSONField — datos estructurados sin normalizar | 4h |

---

## Resumen por Esfuerzo

| Categoría | Items | Esfuerzo Total Estimado |
|---|---|---|
| Crítica | 9 | ~10h |
| Alta | 23 | ~65h |
| Media | 23 | ~55h |
| Baja | 12 | ~57h |
| **TOTAL** | **67** | **~187h** |

**Nota:** Las estimaciones asumen un desarrollador senior familiarizado con el proyecto. No incluyen tiempo de testing ni revisión de código.

**Nota 2026-07-27:** de los 32 items Crítica+Alta (9+23), **los 32 están resueltos** según la
verificación cruzada de esta pasada. Los 46 items Media+Baja (23+12 según la tabla original — la
suma de la fila "Media" cuenta 23) no fueron re-verificados; su esfuerzo estimado (~112h) sigue siendo
la única cifra de referencia disponible hasta una nueva auditoría puntual de esas prioridades.
