# Fase 2 — Simplificación del Flujo
**Basado en:** Auditoría Fase 1  
**Objetivo:** Eliminar complejidad innecesaria para que crear un servicio tome < 2 minutos  
**Status:** Ready to Implement

---

## Resumen de Simplificaciones

| Área | Actual | Objetivo | Simplificación |
|------|--------|----------|----------------|
| **SKU** | Manual (texto) | Auto-generado | `{service_slug}-{strategy}-{complexity}-{index}` |
| **Campos Técnicos** | Todos visibles | Ocultos por default | Contact person, snapshot fields → hidden until needed |
| **Variantes** | Tab modal complejo | Inline quick-edit | Tabla editable, botones flotantes |
| **Costos** | Read-only | Smart panel | Cálculo automático en tiempo real |
| **Validaciones** | Múltiples passes | Single pass | Una sola vez al save |
| **Pasos** | 6+ (General → Images → Variants → Materials → Rules → Costos) | 4 (General → Imagen → Variantes → Costos) | Consolidar materials en variant |
| **Admin Interface** | None (solo dashboard BFF) | Django admin | Bulk operations, debugging |

---

## 1. Campos Técnicos a OCULTAR

### En ServiceForm.vue → General Tab

**Mostrar siempre:**
- ✅ Name
- ✅ Category
- ✅ Level
- ✅ Description
- ✅ Is Featured
- ✅ Is Purchasable
- ✅ Is Active

**Ocultar por default (collapsible "Advanced" section):**
- ❌ Vendor (auto-set a current user)
- ❌ Slug (auto-generated from name)
- ❌ Created at / Updated at (display only, not editable)
- ❌ UUID (display only)

**En Variant Tab:**
- ❌ is_deleted (soft-delete handled backend)
- ❌ min_duration / max_duration (advanced, collapsible)
- ❌ simultaneous_capacity (capacity mgmt, collapsible)

---

## 2. SKU Auto-Generation

### Backend Implementation (ServiceVariant Create)

```python
# services/commands.py
ServiceVariantCommands.create_variant(service, pricing_strategy, estimated_hours, complexity_factor, fixed_price, ...)
    ├─ IF sku is None or empty:
    │   ├─ Generar: f"{service.slug}-{pricing_strategy.lower()}-{complexity_factor_code}-{variant_count+1:02d}"
    │   │   Ejemplo: "inst-cam-ip-hourly-std-01", "inst-cam-ip-daily-adv-02"
    │   └─ Validar no exista duplicado
    └─ Else: usar sku proporcionado (allow override)
```

### Frontend Change (ServiceForm.vue → Variants Tab)

**Antes:** Manual SKU input field

**Después:** 
- SKU auto-populated, **read-only by default**
- Opción "Edit SKU" button → pequeño modal si admin quiere override
- Display: `SKU: {sku} (auto-generated)`

### Complexity Factor Codes

```python
complexity_factor ↔ code_mapping
1.0                ↔ STD (Standard)
1.25               ↔ INT (Intermediate)  
1.5                ↔ ADV (Advanced)
2.0                ↔ EXP (Expert)
```

---

## 3. Contact Person & Snapshot Fields

### Backend: No cambios (ya está)

Campos existen pero nunca son editados en form. Solo poblados on order creation via `request_service()`.

### Frontend: No mostrar en ServiceForm

**Justificación:** Contact person es del ORDEN (customer data), no del SERVICIO (catalog entry).

**Location correcto:** Debe estar en Order Request Form (flow de customer), no en Service admin form.

### Snapshot Fields: Popular automáticamente

**En `request_service()`:**
```python
if selected_technician:
    order_service_detail.professional_type_snapshot = selected_technician.profile.professional_type

# Siempre capturar quotation al momento
quotation = get_variant_quotation(variant, duration, discount_pct)
order_service_detail.applied_rate_type = quotation['pricing_strategy']
order_service_detail.applied_rate_amount = quotation['labor_cost']
```

---

## 4. Consolidación: Materials → Variant

### Problema Actual

- ServiceVariant tiene fields de pricing
- Pero materials se crean por separado en tab diferente
- Requires 2 requests (create variant, then add materials)

### Solución

**Mantener arquitectura actual** (materials son separate model), pero:

**Frontend Change:**
- Mostrar materials como **inline section** en Variants Tab
- Al crear/editar variante: mostrar lista de materials
- "Add Material" button → pequeño modal inline
- Materials guardados atomically en submit

**Backend:** Sin cambios. Materials siguen siendo FK a ProductVariant.

---

## 5. Costos Panel → Smart Calculation

### Actual

**Costos Tab:** Display read-only rules asignadas al service.

**Problema:**
- No muestra cálculo final
- No muestra labor cost + material cost
- No está claro qué reglas aplican

### Nuevo

**Smart Panel:** Muestra en tiempo real

```
┌─────────────────────────────────────────┐
│ COSTOS CALCULADOS (Example)             │
├─────────────────────────────────────────┤
│                                         │
│ Mano de Obra (HOURLY)                   │
│   Base hourly rate: $52,500 COP         │
│   Duration: 2 hours                     │
│   Complexity: Standard (1.0x)           │
│   → Labor Cost: $105,000 COP            │
│                                         │
│ Materiales                              │
│   Cable Cat6 × 50m: $85,000 COP        │
│   Conectores × 10: $15,000 COP         │
│   → Material Cost: $100,000 COP        │
│                                         │
│ Subtotal: $205,000 COP                 │
│ Descuento (5%): -$10,250 COP           │
│ IVA (19%): +$36,937.50 COP             │
│ ─────────────────────────────────────  │
│ TOTAL ESTIMADO: $231,687.50 COP        │
│                                         │
│ [Aplicar Cost Rules...] (admin button) │
└─────────────────────────────────────────┘
```

### Implementation

**Backend:** Ya existe `ServiceSelector.get_variant_quotation()`

**Frontend:**
- Component: `CostCalculationPanel.vue`
- Props: `variant`, `selectedDuration`, `discount`
- Fetch on mount/change: `GET /api/v1/services/quotation/?variant_uuid=...&duration=...`
- Display breakdown (labor, materials, taxes, rules)

**UX:**
- Read-only por default
- Toggle "View Rules" → expandable list
- Button "Edit Rules" → delegue a Cost Rules Admin panel (separate feature)

---

## 6. Tabla de Variantes → Inline Quick-Edit

### Actual

- Tabla list-only
- Create/Edit via modal con full form
- Cada cambio requiere reload

### Nuevo (Shopify-style)

```
┌────────────────┬──────────┬─────────────┬────────────────┬──────────┐
│ SKU            │ Strategy │ Hours/Days  │ Complexity     │ Price    │
├────────────────┼──────────┼─────────────┼────────────────┼──────────┤
│ INST-CAM-..01  │ HOURLY   │ 2.0  [edit] │ Standard [edit]│ $105k    │
│ INST-CAM-..02  │ DAILY    │ 1.0  [edit] │ Advanced [edit]│ $420k    │
│ INST-CAM-..03  │ FIXED    │ —           │ —              │ $800k    │
└────────────────┴──────────┴─────────────┴────────────────┴──────────┘

[+ Add Variant]  [Duplicate]  [Manage Materials]  [Price History]
```

### Implementation

**Frontend:**
- Inline editing en celdas (click para editar)
- Inline dropdowns para strategy/complexity
- Save on blur o [Save] button
- Loading spinner durante save
- Error toast si falla

**Backend:** Sin cambios. PATCH /variants/{uuid}/ ya existe.

---

## 7. Materials Management

### Actual

- Separate materials tab
- CRUD via modal
- FK a shop.ProductVariant (requires product lookup)

### Nuevo

**Inline en Variants Tab:**

```
Variant: INST-CAM-..01 (HOURLY, 2h, $105k)
  Materials:
  ┌──────────────────────────────┬───┬──────────┐
  │ Product                      │ Qty│ Subtotal │
  ├──────────────────────────────┼───┼──────────┤
  │ Cable Cat6 × 50m [remove]    │ 1 │ $85,000  │
  │ Conectores RJ45 [remove]     │ 10│ $15,000  │
  └──────────────────────────────┴───┴──────────┘
  
  [+ Add Material]  Cost: $100,000 COP
```

**Modal inline** (when click "Add Material"):
- Dropdown: buscar productos (searchable, autocomplete)
- Quantity field
- [Add] button

**Backend:** Sin cambios. POST /materials/ con variant_id + product_variant_id.

---

## 8. Cost Rules Management

### Actual

- Costos tab muestra rules assigned to service
- No UI para manage

### Nuevo (Fase 3 separada)

- Separate admin panel: `/admin/cost-rules`
- No mostrar en ServiceForm (es config global, no per-service)
- BUT: en Costos tab → button "[Edit Global Rules]" → abre modal en otra ventana

**No incluir en Fase 2.** Dejar para Fase 3 como enhancement.

---

## 9. Form Validation Simplification

### Actual

- Validación per-field en blur
- Validación full form on submit
- Multiple error messages

### Nuevo

- **Real-time validation** solo en fields críticos (name, category)
- **Full validation only on submit**
- **Inline errors** (no separate error section)
- **Single error toast** si múltiples errores

---

## 10. Admin.py Implementation

**Create:** `/technical_services/admin.py`

```python
from django.contrib import admin
from .models import (
    TechnicalService, ServiceVariant, ServiceCategory,
    ServiceLevel, ServiceImage, ServiceMaterial, ...
)

@admin.register(TechnicalService)
class TechnicalServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'level', 'is_active', 'is_featured', 'vendor')
    search_fields = ('name', 'slug', 'description')
    list_filter = ('is_active', 'is_featured', 'is_purchasable', 'category', 'level')
    readonly_fields = ('slug', 'created_at', 'updated_at', 'uuid')
    fieldsets = (
        ('General', {'fields': ('name', 'slug', 'description', 'vendor', 'is_active')}),
        ('Visibility', {'fields': ('is_featured', 'is_purchasable')}),
        ('Classification', {'fields': ('category', 'level')}),
        ('Metadata', {'fields': ('uuid', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

@admin.register(ServiceVariant)
class ServiceVariantAdmin(admin.ModelAdmin):
    list_display = ('sku', 'service', 'pricing_strategy', 'fixed_price', 'is_active')
    search_fields = ('sku', 'service__name')
    list_filter = ('pricing_strategy', 'is_active', 'service')
    readonly_fields = ('created_at', 'updated_at', 'uuid')

# ... similar for Category, Level, Image, Material, Config
```

---

## 11. Cambios de Rutas Frontend

### Actualizar `/admin/technical-services`

```javascript
// routes/admin.js
{
  path: 'technical-services',
  component: TechnicalServicesLayout,
  children: [
    { path: 'services', component: ServiceList },
    { path: 'services/create', component: ServiceForm, meta: { mode: 'create' } },
    { path: 'services/:uuid', component: ServiceDetail },
    { path: 'services/:uuid/edit', component: ServiceForm, meta: { mode: 'edit' } },
    { path: 'categories', component: ServiceCategoryList },
    { path: 'levels', component: ServiceLevelList },
    // ❌ Remover: materials tab (ahora inline)
    // ❌ Remover: images tab separada (inline en general)
  ]
}
```

---

## 12. Simplificación de Componentes

### Consolidar:

- **Images Tab** → Inline en General tab (thumbnail gallery)
- **Materials Tab** → Inline en Variants tab (per-variant)
- **Costos Tab** → Smart panel con read-only calculation

### Resultado:

**ServiceForm.vue = 4 tabs ONLY:**
1. **General** (name, category, level, description, featured, active, purchasable, images inline)
2. **Imagen** (upload gallery, reorder, set primary)
3. **Variantes** (inline table + quick-edit + materials per variant)
4. **Costos** (smart calculation panel + global rules button)

---

## 13. UX Improvements (Quick Wins)

| Mejora | Effort | Impact | Phase |
|--------|--------|--------|-------|
| Skeleton loading on tab change | 15 min | High | 2 |
| Unsaved changes warning | 10 min | High | 2 |
| Inline error messages (toast) | 20 min | High | 2 |
| Undo/Redo para edits | 30 min | Medium | 3 |
| Keyboard shortcuts (Ctrl+S save) | 15 min | Low | 3 |
| Dark mode toggle | 20 min | Low | 3 |

---

## 14. Implementación Order (Recommended)

### Week 1 (Fase 2)
- [ ] Implement admin.py
- [ ] Auto-generate SKUs
- [ ] Consolidate materials into variants tab
- [ ] Implement Smart Costos Panel
- [ ] Refactor form to 4 tabs

### Week 2 (Fase 3)
- [ ] Inline quick-edit table for variants
- [ ] Drag-drop images reorder
- [ ] Real-time validation
- [ ] Technician selection UI (preparar para Week 3)

### Week 3+ (Fase 4-6)
- [ ] Auto-populate snapshots on order creation
- [ ] Contact person form validation + UI
- [ ] Cost Rules management UI
- [ ] Advanced UX (Skeleton, Toasts, etc.)

---

## 15. Testing Strategy (Fase 2)

### Unit Tests (Backend)
- [ ] SKU auto-generation logic
- [ ] Quotation calculation with rules
- [ ] Snapshot field population

### Integration Tests (API)
- [ ] Create service → auto-generates SKU + default variant
- [ ] Update variant → saves atomically
- [ ] GET /quotation/ with all parameters

### E2E Tests (Frontend + Backend)
- [ ] Create complete service in < 2 minutes
- [ ] Edit variant without reload
- [ ] Verify admin.py bulk operations work

---

## 16. Breaking Changes? (Risk Assessment)

✅ **NO BREAKING CHANGES**

- Admin.py addition: backward compatible
- SKU auto-generation: can be overridden if needed
- Form consolidation: same fields, just reorganized
- Smart Costos panel: read-only, no data mutation

**API Compatibility:**
- All endpoints unchanged
- Responses unchanged
- Only internal form flow simplified

---

## Summary: Fase 2 Goals

✅ **Reducir pasos**: 6+ → 4 tabs  
✅ **Reducir clics**: Eliminar sub-tabs (materials, images)  
✅ **Reducir validaciones**: Merge into single pass  
✅ **Auto-generar SKU**: No manual entry  
✅ **Add admin.py**: Bulk ops support  
✅ **Smart Costos**: Real-time calculation  

**Target:** Crear servicio en < 90 segundos (vs ~300s actualmente)

---

**READY FOR PHASE 2 IMPLEMENTATION**
