# Fase 2 — Frontend Refactorization Plan
## Consolidate ServiceForm.vue from 6 tabs → 4 tabs

**Date:** July 1, 2026  
**Status:** READY FOR IMPLEMENTATION  
**Complexity:** HIGH (600+ lines file)  
**Estimated Time:** 2-3 hours

---

## Overview

**Current State:** ServiceForm.vue has 6+ tabs (General, Images, Variants, Materials, Costos, etc.)  
**Target State:** 4 consolidated tabs (General, Imagen, Variantes, Costos)  
**Goal:** Reduce UI complexity, remove duplicate material/image fields, enable smart cost calculation

---

## Tab Consolidation Strategy

### TAB 1: General (Create/Edit Mode)
**Components:**
- ✅ Name (text, required)
- ✅ Description (textarea, required)
- ✅ Category (FK dropdown, optional)
- ✅ Level (FK dropdown, optional)
- ✅ Is Active (toggle)
- ✅ Is Featured (toggle)
- ✅ Is Purchasable (toggle)
- ❌ REMOVE: Vendor (set auto to current user in backend)
- ❌ REMOVE: Slug (auto-generated in backend)
- ⚠️ ONLY CREATE MODE: Initial Pricing (pricing_strategy radio + fields)
- ⚠️ ONLY CREATE MODE: Initial SKU (text input → now hidden, auto-generated)

**Changes:**
- Keep all current functionality
- Hide "SKU" input field (auto-generated from backend)
- Display: "SKU will be auto-generated" helper text
- Min/max duration fields → move to "Advanced" collapsible

### TAB 2: Imagen (Edit Mode Only)
**Current Location:** Separate Images tab  
**New:** Consolidated in TAB2  
**Components:**
- Upload zone (drag-drop, click to select)
- Pending file preview + alt text input + set-as-primary toggle
- Image gallery (current uploaded images)
- Primary image badge
- Delete button per image
- Empty state

**Changes:**
- Same functionality, just consolidated
- No new features needed

### TAB 3: Variantes (Edit Mode Only)
**Current Location:** Separate Variants tab  
**New:** Consolidated in TAB3 with inline materials  
**Components:**
- Header: "Variantes (inline table with quick-edit)"
- Create Variant button → opens modal
- Variants table (inline quick-edit style)
  - Columns: SKU (read-only), Strategy, Price/Hours, Complexity, is_default, is_active
  - Actions: Edit, Duplicate, Delete inline buttons
  - Inline editing on click

**Inline Material Management (NEW):**
- Per-variant expandable section "Materiales"
- Material list (read-only display)
- "+ Add Material" button → inline modal

**Changes:**
- Move materials from separate tab into variants
- Use inline quick-edit instead of full modal
- Drag-drop reorder (future enhancement)
- "Price History" action button per variant

### TAB 4: Costos (Edit Mode Only)
**Current Location:** Read-only cost rules display  
**New:** Smart auto-calculated panel  
**Components:**
- Use `CostCalculationPanel.vue` component
- Display: labor cost, materials, IVA, rules breakdown, total
- "Edit Global Rules" button → opens admin panel (separate feature)

**Changes:**
- Replace static rule list with smart calculation
- Auto-refresh on variant selection
- Show complete cost breakdown with examples
- Enable transparency for admins

---

## Implementation Steps

### Step 1: Create New Refactored ServiceForm.vue
**Task:** Rewrite ServiceForm.vue with 4-tab structure  
**File Size Estimate:** 500-600 lines (vs 700+ current)  
**Key Changes:**
- Remove duplicate material/image handling  
- Consolidate tab switching logic  
- Import `CostCalculationPanel.vue`  
- Import inline quick-edit components  
- Remove old materials/images sub-components

**Estimated Duration:** 90 minutes

### Step 2: Create Inline Variant Quick-Edit Component
**File:** `VariantQuickEditTable.vue`  
**Purpose:** Tabulator-like table with inline editing  
**Features:**
- Read-only display of variants
- Click-to-edit rows
- Inline save/cancel (blur events)
- Optimistic UI updates
- Undo/redo capability (optional)

**Estimated Duration:** 60 minutes

### Step 3: Create Material Management Modal
**File:** `AddMaterialModal.vue`  
**Purpose:** Inline modal for adding materials to variant  
**Features:**
- Product variant searchable dropdown
- Quantity input
- [Add] button with loading state
- Error handling

**Estimated Duration:** 30 minutes

### Step 4: Update API Serializers
**Files:** `technical_services/api/serializers.py`  
**Changes:**
- Make `sku` field optional in `ServiceVariantSerializer`
- Update create_variant validation
- Document auto-generation behavior

**Estimated Duration:** 15 minutes

### Step 5: Integration Testing
**Scenarios:**
- Create service with auto-generated variant SKU
- Edit variant inline (quick-edit)
- Add material to variant
- View cost calculation in Costos tab
- Verify 4 tabs consolidated correctly

**Estimated Duration:** 30 minutes

---

## File Changes Summary

### Files to Modify
| File | Changes | Impact | Time |
|------|---------|--------|------|
| `frontend/src/modules/technical_services/ServiceForm.vue` | Complete refactor to 4 tabs | HIGH | 90 min |
| `frontend/src/modules/technical_services/VariantQuickEditTable.vue` | NEW component | MEDIUM | 60 min |
| `frontend/src/modules/technical_services/AddMaterialModal.vue` | NEW component | LOW | 30 min |
| `frontend/src/modules/technical_services/CostCalculationPanel.vue` | Already created (Phase 2) | — | — |
| `technical_services/api/serializers.py` | Make SKU optional | LOW | 15 min |

### Files No Changes Needed
- ✅ ServiceList.vue (works with unchanged models)
- ✅ ServiceDetail.vue (works with unchanged models)
- ✅ Store (pinia store remains compatible)
- ✅ Models (no schema changes)
- ✅ API endpoints (no breaking changes)

---

## Risk Assessment

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| Breaking existing service creation | Low | Extensive testing, backward compatible |
| Form state management complexity | Medium | Use Vue refs carefully, separate concerns |
| Performance regression with inline edit | Low | Use debouncing, optimistic updates |
| UX confusion (fewer tabs) | Low | Clear labeling, helper tooltips |
| API compatibility | Very Low | No API changes, only internal form logic |

---

## Validation Checklist

- [ ] Backend: SKU auto-generation works (test with API)
- [ ] Backend: Snapshot fields populate correctly
- [ ] Frontend: Create service with < 2 minutes
- [ ] Frontend: Edit variant inline without page reload
- [ ] Frontend: Add material to variant works
- [ ] Frontend: Cost calculation panel displays correctly
- [ ] Frontend: All 4 tabs accessible and functional
- [ ] Build: `npm run build` succeeds with no errors
- [ ] Browser: No console errors or warnings
- [ ] E2E: Full create → edit → order flow works

---

## Post-Implementation Tasks (Fase 3+)

- [ ] Add drag-drop image reordering
- [ ] Implement variant duplication UI
- [ ] Add inline SKU edit with override option
- [ ] Create Cost Rules management UI
- [ ] Add Technician selection dropdown
- [ ] Implement Contact Person validation
- [ ] Add Skeleton loading states
- [ ] Add Toast notifications for saves
- [ ] Performance profiling & optimization

---

## Estimated Total Timeline

- **Step 1 (Form refactor):** 90 min
- **Step 2 (Variant table):** 60 min
- **Step 3 (Material modal):** 30 min
- **Step 4 (API update):** 15 min
- **Step 5 (Testing):** 30 min
- **Buffer (10%):** 25 min

**Total: ~250 minutes (4-4.5 hours)**

---

## Notes for Implementation

### Gotchas to Watch For
1. **Image upload async:** Currently uses Pinia store mutations. Ensure loading states stay in sync.
2. **Variant deletion:** Soft-delete with `is_deleted` field. Verify filter logic in variants list.
3. **SKU display:** Show as read-only with helper "Auto-generated" on create.
4. **Materials quantity:** Use decimal field (not int) to allow partial quantities.
5. **Tab switching:** Clear unsaved changes warning before leaving tabs.

### Vue 3 Composition API Patterns
- Use `ref()` for local form state (not reactive)
- Use `computed()` for derived data (tab badges count, etc.)
- Use `watch()` for auto-refresh cost panel on variant change
- Use `provide/inject` for parent-child communication (optional)

### Testing Strategy
- Unit: Test SKU generation logic in isolation
- Integration: Test form submit with API mock
- E2E: Test complete flow from create to order

---

## Success Criteria

✅ **Metric: Time to Create Service**  
- Current: ~300 seconds (5 min)
- Target: < 90 seconds (1.5 min)
- Success: 70% reduction

✅ **Metric: Tab Count**  
- Current: 6+ tabs
- Target: 4 tabs
- Success: Simplified UI

✅ **Metric: Field Count Visible**  
- Current: 15+ fields per tab
- Target: 6-8 fields per tab
- Success: Less overwhelmed admin

✅ **Metric: Breaking Changes**  
- Current: None planned
- Target: 0 breaking changes
- Success: Backward compatible

---

**READY FOR IMPLEMENTATION** ✅

Estimated start: **Next session**  
Expected completion: **Same day** (4-5 hours)

