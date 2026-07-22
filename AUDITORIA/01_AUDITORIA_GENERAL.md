# 01 — AUDITORÍA GENERAL
**Proyecto:** Sintel E-Commerce REST  
**Fecha:** 2026-07-16  
**Referencia:** `Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md` (v8, 2026-07-09)  
**Alcance:** Backend Django 5.2 (20 apps) + Frontend Vue 3 + AI Engine FastAPI

---

## Resumen Ejecutivo

La auditoría abarcó 5.749 archivos Python, 279 componentes Vue, 13 stores Pinia, 20 apps Django y la totalidad del AI Engine. La arquitectura general es sólida — el Service Layer Pattern (Commands/Selectors) está implementado consistentemente en el 85% de las apps — pero se identificaron **4 hallazgos críticos de seguridad**, **25 hallazgos de alta prioridad** y **40 hallazgos de prioridad media** que requieren atención antes de la siguiente iteración de producción.

---

## Métricas Globales

| Dimensión | Valor |
|---|---|
| Apps Django auditadas | 20 |
| Clases Commands | 93 |
| Clases Selectors | 82 |
| Clases Orchestrators (BFF) | 12 |
| ViewSets / APIViews | 165 |
| Decoradores `@transaction.atomic` | 323 |
| Componentes Vue | 280 |
| Stores Pinia | 13 archivos |
| Composables | 18 |
| Endpoints AllowAny detectados | ~45 |
| Endpoints protegidos con IsAdminUser (custom) | 79 |
| Instancias Django IsAdminUser (débil, sólo is_staff) | **2** (inventory) |
| Endpoints con file upload sin validación | **3** |
| N+1 confirmados en serializers | 5 |
| Componentes Vue muertos (sin importadores) | 4 |
| Violaciones Service Layer en ViewSets | 14 archivos |

---

## Hallazgos Críticos (resumen)

| ID | Descripción | App | Riesgo |
|---|---|---|---|
| SEC-C1 | `inventory/api/views.py` usa Django `IsAdminUser` (solo `is_staff`) en vez del custom | inventory | Escalación de privilegio |
| SEC-C2 | `integrity_signature` expuesta en respuesta de la API de pagos | payment | Bypass de verificación Wompi |
| SEC-C3 | `/api/schema/` y `/api/docs/` accesibles por cualquier usuario autenticado | ecommerce | Fuga de contrato API |
| ARCH-C1 | `core/services/selectors.py` contiene Commands (escrituras) en archivo de lectura | core | Inconsistencia arquitectónica, escrituras sin `@transaction.atomic` |

---

## Hallazgos de Alta Prioridad (resumen)

| ID | Área | Descripción |
|---|---|---|
| SEC-H1 | Seguridad | Admin login sin rate limiting |
| SEC-H2 | Seguridad | Quotations: file upload sin validación para usuarios anónimos |
| SEC-H3 | Seguridad | SuccessCase upload sin verificación de magic bytes |
| SEC-H4 | Seguridad | Operations `upload_document` sin validación |
| SEC-H5 | Seguridad | `/api/v1/internal/ai/*` accesible externamente (nginx no bloquea la ruta) |
| SEC-H6 | Seguridad | Cambio de contraseña no invalida tokens JWT existentes |
| SEC-H7 | Seguridad | Inventory list/retrieve accesible por cualquier usuario autenticado |
| ARCH-H1 | Arquitectura | `users/services/commands.py`: todos los métodos de escritura sin `@transaction.atomic` |
| ARCH-H2 | Arquitectura | `payment/online/services/commands.py`: `initialize_transaction` sin `@transaction.atomic` |
| ARCH-H3 | Arquitectura | `dashboard/api/views.py`: 6 operaciones ORM directas en el ViewSet |
| ARCH-H4 | Arquitectura | `inventory/api/views.py`: `StockRecord` creado directamente en ViewSet |
| ARCH-H5 | Arquitectura | `cart/api/views.py:125`: `item.delete()` físico bypasea `CartCommands.remove_item()` |
| ARCH-H6 | Arquitectura | `payment/cards/views.py`: CRUD completo de `TokenizedCard` en ViewSet sin Commands |
| ARCH-H7 | Arquitectura | `dashboard/services/admin_orchestrators.py:906-1038`: ORM directo en Orchestrator de métricas |
| DB-H1 | Base de datos | `RentalRequest` tiene 50 campos — split urgente |
| DB-H2 | Base de datos | `ServiceReview` sin `unique_together` — permite reseñas duplicadas |
| DB-H3 | Base de datos | `StockRecord.item_variant` GenericForeignKey permanentemente roto |
| DB-H4 | Base de datos | `Quotation.status` sin `db_index` — campo filtrado frecuentemente |
| FE-H1 | Frontend | Conflicto de ruta: `/panel/ordenes/renting` inaccesible (shadowed por `:uuid`) |
| FE-H2 | Frontend | `apps/customer/main.js`: entrada muerta, monta en elemento DOM inexistente |
| FE-H3 | Frontend | 3 mega-stores de más de 400 líneas con 9+ dominios de responsabilidad |
| FE-H4 | Frontend | `alert('Global Debug Triggered')` en `AppShell.vue:48` |
| FE-H5 | Frontend | Servicios API casi inexistentes: 193 llamadas Axios directas sin capa de abstracción |
| FE-H6 | Frontend | `RentalBookingWizard.vue` minificado — archivo fuente ilegible |

---

## Estado de Cumplimiento por Área

| Área | Estado | Cobertura |
|---|---|---|
| Service Layer Pattern (Commands/Selectors) | Parcial | 85% conforme |
| `@transaction.atomic` en Commands | Parcial | 93% conforme |
| Soft-delete obligatorio | Parcial | 88% conforme |
| IsAdminUser custom (no rest_framework) | Casi completo | 97% conforme (2 excepciones) |
| NotificationCommands (no ws_notify directo) | Completo | 100% conforme |
| ProfileResolver (no getattr directo) | Parcial | 2 violaciones detectadas |
| Nginx bloqueo de rutas /internal/ | No implementado | 0% |
| File upload validation (magic bytes) | Parcial | 70% conforme |
| Rate limiting en endpoints sensibles | Parcial | Admin login sin protección |

---

## Documentos Generados

| # | Documento | Contenido |
|---|---|---|
| 01 | `01_AUDITORIA_GENERAL.md` | Este documento — resumen ejecutivo |
| 02 | `02_DEUDA_TECNICA.md` | Catálogo priorizado de deuda técnica |
| 03 | `03_DUPLICIDAD_CODIGO.md` | Duplicaciones en backend y frontend |
| 04 | `04_OPTIMIZACION_BD.md` | Modelos, índices, constraints, N+1 |
| 05 | `05_RENDIMIENTO.md` | N+1, queries lentas, bundle frontend |
| 06 | `06_SEGURIDAD.md` | Hallazgos de seguridad detallados |
| 07 | `07_FRONTEND.md` | Auditoría Vue, Pinia, router |
| 08 | `08_BACKEND.md` | Auditoría Service Layer, DDD |
| 09 | `09_API.md` | Endpoints, permisos, contratos REST |
| 10 | `10_PLAN_REFACTORIZACION.md` | Hoja de ruta priorizada |
| 11 | `11_QUICK_WINS.md` | Cambios de alto impacto / bajo riesgo |
| 12 | `12_CHECKLIST_IMPLEMENTACION.md` | Checklist de verificación |
