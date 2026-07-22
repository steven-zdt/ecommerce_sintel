# 02 — DEUDA TÉCNICA
**Fecha:** 2026-07-16  
**Clasificación por impacto y esfuerzo**

---

## Deuda Técnica Crítica (bloquea seguridad o correctitud)

| ID | Descripción | App | Esfuerzo |
|---|---|---|---|
| DT-C1 | `inventory/api/views.py` usa Django `IsAdminUser` (is_staff) en vez del custom (is_staff+superuser) | inventory | 15 min — 2 líneas |
| DT-C2 | `integrity_signature` expuesta en respuesta API de pagos | payment | 30 min — serializer + 1 línea view |
| DT-C3 | `/api/schema/` y `/api/docs/` accesibles sin restricción de rol | ecommerce | 15 min — 2 líneas |
| DT-C4 | `AdminLoginView` sin rate limiting (brute force en superuser) | users | 30 min — throttle_classes |
| DT-C5 | `/api/v1/internal/ai/*` no bloqueado en nginx — accesible externamente | nginx | 15 min — 3 líneas nginx |
| DT-C6 | Quotations: file upload sin validación para usuarios anónimos | quotes | 2h — validate_file + tests |
| DT-C7 | Operations `upload_document` sin validación de archivo | operations | 1h |
| DT-C8 | `StockRecord.item_variant` GenericForeignKey permanentemente roto | inventory | 3h — eliminar accessor |
| DT-C9 | Inventory list/retrieve accesible por cualquier usuario autenticado | inventory | 15 min |

---

## Deuda Técnica Alta (correctitud arquitectónica)

| ID | Descripción | App | Esfuerzo |
|---|---|---|---|
| DT-H1 | `core/services/selectors.py` contiene Commands — mezcla escritura/lectura, sin `@transaction.atomic` | core | 2h — split en commands.py |
| DT-H2 | `users/services/commands.py` cero `@transaction.atomic` en todos los métodos de escritura | users | 1h |
| DT-H3 | `payment/online/services/commands.py`: `initialize_transaction` sin `@transaction.atomic` | payment | 30 min |
| DT-H4 | Otras Commands sin `@transaction.atomic` (marketing, notifications, support) | varios | 1h total |
| DT-H5 | `dashboard/api/views.py`: 6+ operaciones ORM directas (image mgmt, quotation.save()) | dashboard | 4h — ProductImageCommands |
| DT-H6 | `inventory/api/views.py`: `StockRecord.objects.create()` directo en ViewSet | inventory | 2h — InventoryCommands.create_stock_record() |
| DT-H7 | `payment/cards/views.py`: CRUD completo de TokenizedCard en ViewSet sin Commands | payment | 2h — PaymentCardCommands |
| DT-H8 | `dashboard/services/admin_orchestrators.py:906`: AdminMetricsOrchestrator con ORM directo | dashboard | 2h — delegar a Selectors |
| DT-H9 | Deletes físicos en modelos soft-deletable (7 instancias en 4 apps) | varios | 2h |
| DT-H10 | `ServiceReview` sin `unique_together` — permite reseñas duplicadas | technical_services | 30 min + migración |
| DT-H11 | `Quotation.status` sin `db_index` — table-scan en filtros del CPQ | quotes | 15 min + migración |
| DT-H12 | `UserProfile.document` sin unicidad por `(document_type, document)` | accounts | 30 min + migración |
| DT-H13 | `RentalRequest` 50 campos — full-row load innecesario en listas | renting | 8h — split 1:1 |
| DT-H14 | Cambio de contraseña no invalida tokens JWT existentes | accounts | 1h |
| DT-H15 | N+1 en `CartSerializer.get_total` (1 Tax query por ítem) | cart | 2h |
| DT-H16 | N+1 en `UserProfile.total_services_completed` (COUNT por perfil en listas) | accounts | 2h — annotation |
| DT-H17 | Sin lazy loading de rutas en el router (bundle inicial contiene todo el admin) | frontend | 3h |
| DT-H18 | Conflicto de ruta: `/panel/ordenes/renting` inaccesible | frontend | 5 min |
| DT-H19 | `apps/customer/main.js` entrada muerta — monta en DOM inexistente | frontend | 15 min — eliminar |
| DT-H20 | `alert('Global Debug Triggered')` en `AppShell.vue:48` — producción | frontend | 5 min — eliminar |
| DT-H21 | 3 mega-stores Pinia (>400 líneas, 9+ dominios) sin split | frontend | 16h — split por dominio |
| DT-H22 | `RentalBookingWizard.vue` minificado — código fuente ilegible | frontend | 2h — restaurar fuente |
| DT-H23 | WhatsApp webhook sin verificación de firma `X-Hub-Signature-256` | notifications | 2h |

---

## Deuda Técnica Media (mantenibilidad)

| ID | Descripción | Esfuerzo |
|---|---|---|
| DT-M1 | ProfileResolver violations (2 instancias `getattr(user, 'profile', None)`) | 30 min |
| DT-M2 | ORM directo en `get_queryset()` de múltiples ViewSets (accounts, quotes, shop, payment/nequi) | 4h |
| DT-M3 | `notifications/api/views.py:80` write ORM directo en ViewSet | 30 min |
| DT-M4 | `cart/api/views.py:176` `WishlistItem.objects.get_or_create()` en ViewSet | 30 min |
| DT-M5 | `payment/online/api/views.py:75,118,137`: `TransactionEvent.objects.create()` en views | 1h |
| DT-M6 | `operations/api/views.py`: múltiples ORM directos en lógica de negocio | 3h |
| DT-M7 | 6 índices de BD faltantes | 1h — 6 migraciones |
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
| DT-M22 | Access token lifetime de 60 minutos (debería ser 15) | 5 min |
| DT-M23 | `UserDetailSerializer` expone `AdminVerificationDetailSerializer` a usuarios normales | 1h |

---

## Deuda Técnica Baja (mejoras)

| ID | Descripción | Esfuerzo |
|---|---|---|
| DT-L1 | `useFormValidation.js` específico de campaña con nombre genérico | 1h |
| DT-L2 | `useRentalsStore` 14 líneas innecesariamente como store Pinia | 30 min |
| DT-L3 | `useAvailabilityStore`: dos actions duplicadas (`check` vs `fetchAvailability`) | 30 min |
| DT-L4 | `FilterSidebar.vue` sin importadores (posiblemente muerto) | 15 min |
| DT-L5 | `src/shared/` directorio vacío | 5 min |
| DT-L6 | 12 rutas hijas de `/mi-cuenta` repiten `meta: { requiresAuth: true }` | 15 min |
| DT-L7 | `HomeConfigView.vue` (2.705L) y `ModuleBuilderModal.vue` (1.588L) — god-components | 20h |
| DT-L8 | FSM de Operaciones triplicado sin clase base compartida | 12h |
| DT-L9 | Serializers de imagen duplicados por app (shop/renting/services) | 2h |
| DT-L10 | Sin catch-all admin 404 en el router | 30 min |
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
