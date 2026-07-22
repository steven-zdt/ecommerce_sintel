# Technical Services Module — Phase 1: Auditoría Completa
**Fecha:** 2026-07-01  
**Status:** ✅ AUDITORÍA COMPLETADA  
**Scope:** Backend (Django) + Frontend (Vue 3) + API + Commands/Selectors

---

## Executive Summary

El módulo **Technical Services** está bien estructurado en el backend con una arquitectura Commands/Selectors sólida y cálculos de precios complejos. Sin embargo, el frontend es **funcional pero anticuado**:

- ✅ Backend: 11 modelos, 8 comandos, 7 selectores, 13 endpoints API, cálculos SMLV completos
- 🟡 Frontend: Componentes básicos, pero falta UX moderna, Cost Rules UI, Technician selection
- 🔴 Brecha: 8 campos no utilizados, 3 features incompletas, No admin.py

**Conclusión:** Sistema está listo para modernización sin romper compatibilidad.

---

## 1. Estructura de Directorios

```
technical_services/
├── .AGENT/docs/
│   └── ARQUITECTURA_COMPLETA_SERVICES.md
├── api/
│   ├── views.py                 (6 ViewSets: Service, Category, Level, Variant, Material, Config)
│   ├── serializers.py           (Input/Output con price_info, IVA)
│   └── urls.py                  (Router config)
├── migrations/                  (20 migrations, última: service_visit_fields)
├── services/
│   ├── commands.py              (8 command classes: Create/Update/Delete + request_service)
│   ├── selectors.py             (7 selector classes: list/get/quotation/availability)
│   ├── calculator.py            (LaborCostCalculator: SMLV-based)
│   ├── pricing.py               (ServicePricingCalculator: cost rules engine)
│   └── summary.py               (ServicesSummaryProvider: stats)
├── models.py                    (11 model classes, 20 fields total)
├── admin.py                     (❌ NO EXISTE — solo dashboard BFF)
├── apps.py
├── CLAUDE.md
├── ANTIGRAVITY.md
├── tests.py
└── static/
    └── technical_services/      (❌ Archivos heredados de Django templates)
```

---

## 2. Modelos (Backend)

### 2.1 Catálogo & Configuración

| Modelo | Propósito | Campos Clave | Relaciones |
|--------|----------|--------------|-----------|
| **ServiceCategory** | Taxonomía (ej: Instalación, Mantenimiento) | `name`, `slug`, `description`, `is_active`, `parent` (self-FK) | Children; Services |
| **ServiceLevel** | Expertise (Junior, Senior, Master) | `name`, `slug` | Services |
| **ServiceConfiguration** | Parámetros globales SMLV Colombia | `smlv`, `transport_subsidy`, `benefit_rate`, `indirect_costs_rate`, `iva_rate` (19% default) | — |
| **TechnicalService** | Entrada catálogo (analoga a Product) | `name`, `slug`, `description`, `is_active`, `is_featured`, `is_purchasable`, `vendor` (FK User) | Category, Level, Variants, Images, Reviews |

### 2.2 Precios & Variantes

| Modelo | Propósito | Estrategia Precio | Campos Clave |
|--------|----------|---|-----------|
| **ServiceVariant** | SKU con regla pricing | HOURLY / DAILY / FIXED | `sku`, `estimated_hours`, `complexity_factor`, `fixed_price`, `min_duration`, `max_duration`, `simultaneous_capacity` |
| **ServiceMaterial** | Suministros (FK a shop.ProductVariant) | Costo = `product_variant.price × qty` | `quantity`, `product_variant` |
| **ServicePriceHistory** | Audit trail precios | — | `old_price`, `new_price`, `changed_by` |
| **ServiceImage** | Imágenes servicio/variante | — | `image`, `alt_text`, `is_primary` |
| **ServiceReview** | Calificaciones cliente | Rating 1-5 | `rating`, `comment`, `user` |

### 2.3 Órdenes & Ejecución

| Modelo | Propósito | Estados | Campos Clave |
|--------|----------|--------|-----------|
| **OrderServiceDetail** | Satélite de Order | pending→assigned→in_progress→completed | `description`, `address`, `priority` (low/medium/high/critical), `scheduled_at`, `contact_person` (JSON), `booked_slot_id` |
| **OrderServiceTimeline** | Audit log estados | Linear progression | `status`, `notes`, `created_by` |
| **ServiceAttachment** | Archivos (fotos, blueprints) | — | `file`, `file_name`, `mime_type`, `doc_type`, `uploaded_by` |
| **ServiceBooking** | Disponibilidad temporal/capacity | scheduled→active→completed→cancelled | `start_time`, `end_time`, `status` |

### 2.4 Reglas de Costo

| Modelo | Propósito | Tipos |
|--------|----------|-------|
| **ServiceCostRule** | Reglas adicionales costo/descuento | FIXED / PERCENTAGE |
| **ServiceCostAssignment** | Linker rule→variant | Many-to-many through-table |

---

## 3. Arquitectura Commands/Selectors

### 3.1 Commands (Mutaciones)

```python
ServiceCommands
├─ request_service(user, variant, duration, service_detail_data, ...)
│  └─ ✅ Transacción atómica: Order + OrderItem + OrderServiceDetail + ServiceBooking
├─ create_service(vendor, data)
├─ update_service(service, data)
├─ delete_service(service)          # Soft-delete
├─ confirm_slot_on_payment(order)   # Activa ServiceBooking
└─ release_slot_on_failure(order)   # Cancela ServiceBooking

ServiceVariantCommands
├─ create_variant(service, data)    # Auto-slug, price_history tracking
├─ update_variant(variant, data)    # Si fixed_price cambia → crea history entry
└─ delete_variant(variant)          # Soft-delete

ServiceCategoryCommands / ServiceLevelCommands
├─ create, update, delete           # CRUD standard

ServiceImageCommands
├─ add_image(service, file, ...)    # Asegura exactamente 1 primary
├─ delete_image(...)
└─ set_primary_image(...)
```

### 3.2 Selectors (Consultas)

```python
ServiceSelector
├─ list_active_services()
├─ get_by_uuid(uuid)
├─ get_variant_quotation(variant, duration, discount_pct)
│  └─ Retorna DICT completo: labor_cost + material_cost + IVA + cost_rules
├─ check_time_availability(variant, start_time, end_time, capacity)
└─ (Todas prefetch materials, images; select_related category/level)

LaborCostCalculator
└─ calculate_hourly_rate()          # SMLV × benefits + transport / 240h

ServiceCategorySelector / ServiceLevelSelector
├─ list_all()
└─ get_by_uuid(uuid)

TechnicianSelector
└─ get_available_for_category(category, start_time, end_time)
```

---

## 4. Lógica de Precios Detallada

### 4.1 Cálculo de Mano de Obra (Colombiano SMLV)

```
benefits_multiplier = 1 + (benefit_rate / 100)
total_monthly_cost = (SMLV × benefits_multiplier) + transport_subsidy
base_hourly_rate = total_monthly_cost / 240 horas
final_hourly_rate = base_hourly_rate × (1 + indirect_costs_rate / 100)

Pricing Strategies:
├─ FIXED:  fixed_price (directo)
├─ HOURLY: final_hourly_rate × hours × complexity_factor
└─ DAILY:  (final_hourly_rate × 8) × days × complexity_factor
```

### 4.2 Cost Rules Engine

Aplicadas DESPUÉS labor + materials:

- **FIXED:** Suma/resta monto fijo (COP)
- **PERCENTAGE:** Suma/resta % del precio base
- **CONTEXT:** TAX / DISCOUNT / SETUP / OPERATIONAL
- **Global vs Specific:** `applies_globally=True` o linked via `ServiceCostAssignment`

### 4.3 IVA & Impuestos

- **Default:** 19% (desde `ServiceConfiguration.iva_rate`)
- **Aplicado a:** `(base_amount - discount_amount)`
- **No incluido en:** labor_cost o material_cost por separado
- **Resultado:** `total_price = (base - discount) × (1 + iva_rate/100)`

---

## 5. Endpoints REST API

| Endpoint | Método | Permisos | Propósito |
|----------|--------|----------|----------|
| `/api/v1/services/` | GET/POST | GET: Public / POST: Admin | List/create services (pagination 25/page) |
| `/api/v1/services/{uuid}/` | GET/PATCH/DELETE | GET: Public / Modify: Admin | Detail/edit/delete |
| `/api/v1/services/quotation/` | GET | Public | `?variant_uuid=...&duration=...` → full quotation |
| `/api/v1/categories/` | GET/POST | GET: Public / POST: Admin | Categories |
| `/api/v1/levels/` | GET/POST | GET: Public / POST: Admin | Levels |
| `/api/v1/variants/` | GET/POST | Admin | `?service=<uuid>` required |
| `/api/v1/variants/{uuid}/` | GET/PATCH/DELETE | Admin | Variant detail |
| `/api/v1/materials/` | GET/POST | Admin | `?variant=<uuid>` required |
| `/api/v1/configurations/` | GET/POST | Admin | SMLV params |

---

## 6. Dashboard BFF Orchestrator

**Ubicación:** `dashboard/services/admin_orchestrators.py`

Delega a Service Layer para:
- `list_services()` → `ServiceSelector.list_all_for_admin()`
- `get_service(uuid)` → `ServiceSelector.get_by_uuid()`
- `create_service(vendor, data)` → `TechnicalServiceCommands.create_service()`
- `update_service(service, data)` → `TechnicalServiceCommands.update_service()`
- `delete_service(service)` → Soft-delete
- Variant/Image/Category/Level CRUD delegado

**Prefix:** `/api/v1/dashboard/services/`

---

## 7. Frontend (Vue 3) - Componentes Actuales

| Componente | Propósito | Status |
|-----------|----------|--------|
| **ServiceList.vue** | Admin: lista/search/filter/delete | ✅ Complete |
| **ServiceForm.vue** | Admin: create/edit (4 tabs: General, Images, Variants, Costos) | 🟡 Partial |
| **ServiceDetail.vue** | Public/Admin: view detail + "Request Service" | ✅ Complete |
| **ServiceCategoryList.vue** | Admin: CRUD categorías | ✅ Complete |
| **ServiceLevelList.vue** | Admin: CRUD levels | ✅ Complete |
| **Cost Rules UI** | Admin: manage ServiceCostRule | ❌ **MISSING** |

### 7.1 ServiceForm.vue Tabs

**Tab 1: General**
- Name, Description, Category (FK), Level (FK), Is Active/Featured/Purchasable
- **Initial Pricing (create only):** Pricing strategy radio, fixed_price o estimated_hours/complexity_factor

**Tab 2: Images**
- Upload (file input + FormData)
- Alt text
- Set as primary
- List + delete

**Tab 3: Variants**
- Tabla: SKU, strategy, hours, complexity, fixed_price, is_default, is_active
- Create/Edit/Delete via modal

**Tab 4: Costos**
- Display cost rules asignadas (read-only?)
- **Gap:** Sin UI para crear/asignar nuevas reglas

---

## 8. Pinia Store

**Store:** `src/store/technicalServicesAdmin.js`

**State:**
- `services[]`, `totalServices`, `currentService`
- `variants[]`, `categories[]`, `levels[]`, `costRules[]`
- `loading`, `actionLoading`, `error`

**Actions:**
- `fetchServices(params)`, `createService()`, `updateService()`, `deleteService()`
- `fetchVariants()`, `createVariant()`, `updateVariant()`, `deleteVariant()`
- `uploadImage()`, `deleteImage()`, `setPrimaryImage()`
- Category/Level/CostRule actions

**Getters:** `activeServices`, `activeCategories`, `globalCostRules`

---

## 9. Rutas Frontend

```javascript
/admin/technical-services
  ├─ /services            → ServiceList
  ├─ /services/create     → ServiceForm (create mode)
  ├─ /services/:uuid      → ServiceDetail
  ├─ /services/:uuid/edit → ServiceForm (edit mode)
  ├─ /categories          → ServiceCategoryList
  └─ /levels              → ServiceLevelList

/services (Public)
  ├─ /services            → ServiceList (public catalog)
  └─ /services/:uuid      → ServiceDetail + "Request Service" button
```

---

## 10. Flujos de Datos Actuales

### 10.1 Crear Servicio (Admin)

```
ServiceForm.vue (create)
    ↓ POST /api/v1/dashboard/services/
    (name, description, category, level, is_active, is_featured, is_purchasable, pricing_strategy, ...)
    ↓
ServiceAdminOrchestrator.create_service()
    ↓
ServiceCommands.create_service()
    ├─ Auto-slug name
    ├─ Valida category/level (opcional)
    └─ Retorna service con UUID
    ↓
Frontend: Redirige a ServiceForm (edit mode)
```

### 10.2 Crear Variante

```
ServiceForm.vue → Variants tab → Create modal
    ↓ POST /api/v1/dashboard/service-variants/
    (sku, pricing_strategy, estimated_hours, complexity_factor, fixed_price, ...)
    ↓
ServiceVariantCommands.create_variant()
    ├─ Crea SKU (manual input)
    ├─ Valida pricing_strategy
    └─ Retorna variant con UUID
    ↓
Frontend: Actualiza tabla variantes (replaceData)
```

### 10.3 Solicitar Servicio (Cliente)

```
ServiceDetail.vue → "Request Service" button
    ↓ POST /api/v1/orders/service-orders/
    (variant_uuid, duration, service_detail_data: {address, priority, contact_person, ...}, selected_slot_id)
    ↓
ServiceCommands.request_service(user, variant, duration, ...)
    ├─ Valida variant (is_active, is_purchasable)
    ├─ Check ServiceBooking capacity
    ├─ Valida ProfessionalAvailability slot (si selected_slot_id)
    ├─ Fetch quotation → get_variant_quotation()
    ├─ Crea Order + OrderItem
    ├─ Crea OrderServiceDetail (con contact_person JSON)
    ├─ Crea ServiceBooking
    ├─ Crea OrderServiceTimeline entry
    ├─ Emit WebSocket notification
    └─ Retorna Order UUID
    ↓
Frontend: Redirige a checkout
```

### 10.4 Cálculo de Cotización (GET /quotation/)

```
GET /api/v1/services/quotation/?variant_uuid=<uuid>&duration=<decimal>&discount_pct=<decimal>
    ↓
ServiceSelector.get_variant_quotation()
    ├─ Fetch variant + materials + category
    ├─ LaborCostCalculator.calculate_hourly_rate() → SMLV-based
    ├─ labor_cost = hourly_rate × duration × complexity_factor
    ├─ material_cost = SUM(material.product_variant.price × qty)
    ├─ base_amount = labor_cost + material_cost
    ├─ discount_amount = base_amount × discount_pct / 100
    ├─ ServiceCostRule.apply_rules() → additions/discounts
    ├─ iva_amount = (base_amount - discount_amount) × iva_rate / 100
    ├─ total_price = base_amount - discount_amount + iva_amount
    └─ Retorna DICT: {labor_cost, material_cost, base_amount, discount_amount, iva_amount, total_price, breakdown}
```

---

## 11. Issues & Inconsistencias Críticas

### 🔴 CRÍTICOS

#### 1. **No SKU Auto-Generation**
- **Problema:** SKU es manual → typos, duplicados
- **Impacto:** Admin debe recordar convención de naming
- **Solución:** Auto-generar: `{service_slug}-{strategy}-{index}` (e.g., `INST-CAM-IP-HOURLY-01`)

#### 2. **Cost Rules UI Completamente Ausente**
- **Problema:** Backend CRUD endpoints existen, pero frontend tab es **read-only**
- **Modelos:** `ServiceCostRule`, `ServiceCostAssignment`
- **API Endpoints:** POST/PATCH/DELETE `/api/v1/services/cost-rules/` (inferred)
- **Frontend:** Tab muestra rules pero sin create/edit/delete UI
- **Impacto:** Admin NO puede gestionar reglas desde UI → solo shell/direct DB
- **Solución Fase 3:** Agregar form + drag-drop en Costos tab

#### 3. **Admin Interface Completamente Ausente**
- **Problema:** No existe `/admin/` para Django admin
- **Impacto:** Bulk operations, debugging must go through dashboard BFF
- **Solución:** Generar admin.py con `list_display`, `search_fields`, `list_filter`

#### 4. **Campos No Utilizados (Unused Fields)**
- `OrderServiceDetail.confirmed_date`, `confirmed_time` → **nunca set en commands**
- `OrderServiceDetail.professional_type_snapshot` → **siempre NULL**
- `OrderServiceDetail.applied_rate_type`, `applied_rate_amount` → **nunca set**
- **Impacto:** Confunde devs, falso sense de funcionalidad
- **Solución:** Popular en `request_service()` o remover

#### 5. **Contact Person Schema Sin Validación**
- **Problema:** `OrderServiceDetail.contact_person` es JSON libre sin schema validation upstream
- **Backend:** `ContactPersonSerializer` define estructura pero no usado en create
- **Frontend:** No hay form fields para completar contact_person
- **Impacto:** Datos inválidos/incompletos persisten
- **Solución:** Strict JSON schema validation + form fields

#### 6. **Technician Assignment Sin UI**
- **Problema:** `selected_technician` soportado en `request_service()` pero NO hay UI para seleccionar
- **Comando:** If provided → crea Timeline entry + sets technician.is_available=False
- **Frontend:** Missing UX para pre-asignar technician
- **Impacto:** Feature completamente oculta del admin
- **Solución Fase 5:** Agregar dropdown technician con auto-filter por category + availability

---

### 🟡 MODERADOS

#### 7. **Double-Booking Risk (Temporal Availability)**
- **Problema:** `ServiceBooking` maneja slots temporal (start_time ↔ end_time)
- `simultaneous_capacity` limita ejecuciones paralelas
- **Risk:** Race condition si `check_time_availability()` no usa `select_for_update()`
- **Mitigación:** Code DOES use overlapping window query con locking
- **Status:** ✅ OK, pero frágil

#### 8. **Pricing Calculation Complexity**
- **Problema:** Quotation incluye IVA + ServiceCostRules (TAX context)
- **Unclear:** ¿Qué impuestos ya están en `iva_rate`? ¿Double-counting?
- **Solución:** Document tax hierarchy clearly en models.py

#### 9. **Circular Import Risk**
- `services/selectors.py` → imports `calculator.py`
- `services/commands.py` → imports `selectors.py`
- **Works:** Late imports, but fragile
- **Solución:** Reorganize to DAG (calculator ← selectors ← commands)

#### 10. **Legacy Static Files Not Removed**
- `static/technical_services/js|css/` presente pero no usado
- **Impacto:** Confusión, potencial technical debt
- **Solución:** Remover o documentar fallback

---

### 🟢 MENORES

#### 11. **Incomplete Admin Confirmation Workflow**
- `confirmed_date`, `confirmed_time` fields exist but unused
- Implies incomplete feature: admin confirmation before execution
- **Status:** Design incomplete

#### 12. **Inventory Integration Removed Incompletely**
- Migration 0007 removed `Inventory.StockRecord` dependency
- But `ServiceBooking` may reference old patterns
- **Status:** ✅ Actually clean, just confusing comments

---

## 12. Backend/Frontend Misalignments

| Feature | Backend | Frontend | Brecha |
|---------|---------|----------|--------|
| Create Service | ✅ Full | ✅ Full | ✅ Aligned |
| Edit Service | ✅ Full | ✅ Full | ✅ Aligned |
| Delete Service | ✅ Full | ✅ Full | ✅ Aligned |
| Manage Variants | ✅ Full | ✅ Tab + modals | ✅ Aligned |
| Images | ✅ Full | ✅ Tab complete | ✅ Aligned |
| **Cost Rules** | ✅ Full CRUD | ❌ **Read-only tab** | 🔴 **BROKEN** |
| **Technician Pre-Assignment** | ✅ Supported | ❌ **No UI** | 🔴 **BROKEN** |
| **Contact Person** | ✅ Schema defined | ❌ **No form fields** | 🔴 **BROKEN** |
| **Snapshot Fields** | ✅ Fields exist | ❌ **Never populated** | 🔴 **BROKEN** |
| **Confirmed Date/Time** | ✅ Fields exist | ❌ **No admin UI** | 🔴 **BROKEN** |
| Quotation Calculation | ✅ Complete | ✅ Called via API | ✅ Aligned |

---

## 13. Historial de Migraciones

| # | Archivo | Propósito | Status |
|---|---------|----------|--------|
| 0001 | initial | Modelos core | ✅ |
| 0002-0005 | schema updates | Soft-delete, duraciones, seed | ✅ |
| **0006** | **iva_rate** | **Agregó IVA field a ServiceConfiguration** | ✅ **CRITICAL** |
| 0007 | **order integration** | **OrderServiceDetail + timeline** | ✅ **CRITICAL** |
| 0008-0014 | schema iterations | Technician, price history, cost rules | ✅ |
| 0015 | cost rules engine | `ServiceCostRule` + `ServiceCostAssignment` | ✅ |
| 0016-0020 | bookings & visit fields | `ServiceBooking`, temporal mgmt | ✅ |

---

## 14. Oportunidades de Optimización

### Tier 1: Critical (Fase 2-3)
- [ ] Implementar Admin Interface (`admin.py`)
- [ ] Auto-generar SKUs
- [ ] Popular snapshot fields en order creation
- [ ] Crear Cost Rules UI
- [ ] Agregar Technician selection UI
- [ ] Validar Contact Person schema

### Tier 2: Important (Fase 3-4)
- [ ] Complete Admin Confirmation Workflow (confirmed_date/time)
- [ ] Implementar Redis cache para quotations (TTL 1h)
- [ ] Reorganizar imports (DAG)
- [ ] Agregar comprehensive test coverage

### Tier 3: Nice-to-Have (Opcional)
- [ ] ServiceWorker para offline-first
- [ ] Real-time enum sync (WebSocket)
- [ ] Advanced technician matching (rating, response time)
- [ ] Analytics + monitoring

---

## 15. Readiness Assessment

| Aspecto | Score | Notas |
|--------|-------|-------|
| **Backend Completeness** | 9/10 | Modelos, commands, selectors, pricing: sólido |
| **API Contracts** | 9/10 | Bien definidos, solo falta Cost Rules endpoints |
| **Frontend Components** | 6/10 | Básicos funcionales, pero anticuado |
| **UX Modernidad** | 4/10 | Formularios simples, sin Skeleton, Toasts, etc. |
| **Admin Experience** | 5/10 | Dashboard BFF OK, pero sin Django admin |
| **Documentation** | 8/10 | ARQUITECTURA.md excelente |
| **Test Coverage** | 6/10 | tests.py existe, pero coverage probable < 70% |
| **Production Readiness** | 7/10 | Funcional pero necesita UX modernization |

**Conclusión:** Sistema es **READY para modernización sin breaking changes**.

---

## 16. Resumen de Hallazgos Clave

### ✅ Fortalezas
1. **Backend sólido** con Commands/Selectors pattern
2. **Cálculos SMLV complejos** pero correctamente implementados
3. **Modelos comprehensivos** con 20 migraciones
4. **Dashboard BFF orchestrator** bien diseñado
5. **API contracts** bien definidos

### 🔴 Críticas
1. **Cost Rules UI missing** → admin no puede gestionar reglas
2. **SKU manual** → riesgo de duplicados/typos
3. **Snapshot fields unused** → datos históricos perdidos
4. **Contact person sin validación** → datos inválidos
5. **Technician selection missing** → feature oculta

### 🟡 Oportunidades
1. **UX completamente anticuada** → reemplazar con Shopify-style
2. **No admin.py** → agregar para bulk ops
3. **Campos unused** → limpiar o documentar
4. **Circular imports** → refactor to DAG

---

## Next Steps (Fase 2)

1. ✅ **Auditoría completada** — Documento este
2. 🔜 **Fase 2: Simplificación flujo** — Identifica qué eliminar
3. 🔜 **Fase 3: Rediseño formulario** — 4 secciones: General, Imagen, Variantes, Costos
4. 🔜 **Fase 4-10** — Automatización, UX, optimización

---

**END OF AUDIT | Status: READY FOR PHASE 2 SIMPLIFICATION**
