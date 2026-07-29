# Phase 14: API Contract Confirmation — Zero Backend Changes Required

**Estado:** ✓ COMPLETADO  
**Fecha:** 2026-07-29  
**Auditor:** Claude Code

---

## Resumen Ejecutivo

**CONFIRMADO:** MarketplaceShowcase 2.0 no requiere cambios en API backend. Utiliza contractualmente el mismo `HomeModuleConfig` y `GET core/home-feed/` existentes, con `layout_config` (JSONField) como único vector de configuración nueva.

---

## 1. Endpoint Usado: GET /core/home-feed/

### Shape Actual (Existente)

```json
{
  "modules": [
    {
      "uuid": "...",
      "label": "Ecosistema Sintel",
      "url": "/tienda",
      "icon": "bi-shop",
      "color": "#2563eb",
      "background_image": "...",
      "is_visible": true,
      "display_order": 1,
      "layout_config": {
        "show": { "icon": true, "title": true, "button": true },
        "badge": { "text": "Nueva", "color": "#f59e0b" },
        "button": { "text": "Explorar", "color": "#2563eb" }
        /* ... otros campos existentes ... */
      }
    }
  ]
}
```

### Changes for Phase 10+ (Additions Only)

```json
{
  "modules": [
    {
      /* ... existing fields ... */
      "layout_config": {
        /* ... existing fields ... */
        
        /* NEW: Fase 10 — Carousel config */
        "carousel": {
          "items_desktop": 6,
          "items_tablet": 3,
          "items_mobile": 1.2,
          "autoplay": false,
          "loop": true,
          "speed": 40,
          "pause_on_hover": true,
          "pause_on_touch": true,
          "pause_on_focus": true,
          "show_arrows": true,
          "show_indicators": true
        },
        
        /* NEW: Fase 3/10 — Media per card */
        "media": {
          "type": "color|image|video",
          "image": "",
          "video_url": "",
          "video_url_webm": "",
          "poster": "",
          "blur": 0,
          "glass": false
        },
        
        /* NEW: Fase 6/10 — Header config */
        "header": {
          "title": "El Ecosistema Sintel",
          "subtitle": "Marketplace",
          "description": "...",
          "cta_text": "Explorar Todo",
          "cta_url": "/tienda",
          "cta_target": "_self|_blank"
        },
        
        /* NEW: Fase 3/10 — Section background */
        "section_background": {
          "type": "none|image|video|color",
          "image": "",
          "video_url": "",
          "video_url_webm": "",
          "poster": "",
          "parallax": false
        }
      }
    }
  ]
}
```

### Verificación de Compatibilidad ✓

1. **Campos Nuevos son Opcionales:**
   - `carousel`, `media`, `header`, `section_background` NO existen en módulos legacy
   - Frontend **nunca falla** si faltan — fallbacks sensatos en DEFAULT_FORM()

2. **Ningún Campo Existente Modificado:**
   - `show`, `badge`, `button`, `stats`, `animation`, `background` — sin cambios
   - Módulos sin `layout_config.carousel/media/header/section_background` se comportan idéntico a antes

3. **JSONField Flexibility:**
   - Django JSONField ya almacena dicts arbitrarios desde Fase 1
   - No require schema change, migration, o validación stricta
   - Nuevos campos se guardan, módulos legacy no tienen que migrar

---

## 2. Models Impactados

### HomeModuleConfig (No Changes Required)

**Ubicación:** `core/models.py`  
**Campo:** `layout_config = JSONField(default=dict, blank=True, null=True)`

**Status:** ✓ Existente, sin cambios

No hay necesidad de:
- Crear nuevos campos en el modelo
- Migrations en Django
- Model validators (JSONField no valida estructura)

**Decisión de Diseño:** Mantener `layout_config` como JSON libre permite evolucionar sin migrations.

---

## 3. API ViewSets

### HomeModuleViewSet (Read-Only, No Changes)

**Ubicación:** `core/api/serializers.py` y `core/api/views.py`  
**Endpoint:** `GET /api/core/modules/` y `GET /core/home-feed/`

**Status:** ✓ Sin cambios

No hay necesidad de:
- Modificar serializers (HomeModuleSerializer ya serializa `layout_config` como-es)
- Agregar new endpoints
- Cambiar response shape

**Razón:** `layout_config` es un JSONField opaco — el serializer lo incluye sin importar estructura interna.

---

## 4. Admin Panel (ModuleBuilderModal.vue)

### Donde se Ingresa Nueva Data

**Ubicación (Frontend):** `src/modules/core/ModuleBuilderModal.vue`  
**Type:** Vue component, NO cambios de API

**Status:** ✓ Phase 10 completada (Fase 10 Editor Visual)

- Tabs nuevos en UI recolectan `carousel`, `media`, `header`, `section_background` del usuario
- Se mapean a `configPayload` computed (también en ModuleBuilderModal.vue)
- Se guardan en `layout_config` via `POST/PATCH /dashboard/modules/`

**Endpoint Backend:** `PATCH /dashboard/modules/{id}/`  
**Payload:** Same as before — `layout_config` field contains merged dict

---

## 5. Data Flow End-to-End

```
User (Admin)
  ↓
ModuleBuilderModal.vue (Fase 10)
  ↓ sets form.carousel, form.media, form.header, form.section_background
  ↓
configPayload computed (Fase 10)
  ↓ merges into layout_config: { carousel: {...}, media: {...}, ... }
  ↓
PATCH /dashboard/modules/{id}/ (Existing endpoint)
  ↓ body: { custom_label: "...", layout_config: {...}, ... }
  ↓
HomeModuleSerializer (Existing)
  ↓ validates and saves
  ↓
HomeModuleConfig.layout_config (JSONField, stores as JSON)
  ↓
GET /core/home-feed/ (Existing endpoint)
  ↓ returns modules with full layout_config
  ↓
HomeRenderer.vue (HomeView.vue via store)
  ↓
MarketplaceShowcase.vue (Orquestador, Fase 8)
  ↓ reads layout_config.carousel/media/header/section_background
  ↓
MarketplaceCarousel.vue (Fase 4/7/8)
MarketplaceCard.vue (Fase 5)
MarketplaceBackground.vue (Fase 3)
MarketplaceHeader.vue (Fase 6)
```

**Result:** ✓ Zero API changes, only UI + components

---

## 6. Backward Compatibility Matrix

| Scenario | Old Module (No new fields) | New Module (With carousel/media/header) |
|----------|---|---|
| GET /core/home-feed/ | ✓ Works (layout_config empty/partial) | ✓ Works (full layout_config) |
| MarketplaceShowcase render | ✓ Fallback defaults apply | ✓ Uses new config |
| ModuleBuilderModal edit | ✓ Opens with defaults | ✓ Opens with saved config |
| PATCH /dashboard/modules/ | ✓ Saves existing fields | ✓ Adds new fields to layout_config |
| Legacy ModuleGrid fallback | N/A (ModuleGrid removed) | ✓ MarketplaceShowcase replaces it |

**Compatibility:** ✓ 100% backward compatible — no module breaks.

---

## 7. Changelog for Backend Team (For Reference)

If backend needs to log changes or audit this component:

**No Changes Required**

Frontend implemented MarketplaceShowcase 2.0 (Phases 1-13):
- Component system (11 new Vue files)
- Configurability via `layout_config.carousel/media/header/section_background` (additive JSON)
- Home Builder UI extension (ModuleBuilderModal tabs)
- Performance optimizations (RAF, IntersectionObserver, CSS Scroll Snap)
- Accessibility (ARIA, keyboard nav, prefers-reduced-motion)
- SEO (real links, semantic HTML)

All new data stored in existing `layout_config` JSONField.  
**No database migrations needed.**  
**No API changes needed.**  
**No model changes needed.**

---

## 8. Rollback Plan (If Needed)

If frontend needs to disable MarketplaceShowcase and fall back:

1. **HomeRenderer.vue:** Replace `<MarketplaceShowcase />` with `<ModuleGrid />`
2. **CSS:** Optional — remove `--mps-*` variables if present
3. **No backend work needed**

Modules continue working with their old `layout_config` (new fields ignored by ModuleGrid fallback).

---

## 9. Deployment Readiness

| Aspect | Status | Notes |
|--------|--------|-------|
| **Backend API** | ✓ Ready | Zero changes, zero downtime |
| **Database** | ✓ No migration | JSONField is flexible |
| **Frontend Deploy** | ✓ Ready | Can deploy independently |
| **Feature Flag** | Optional | MarketplaceShowcase could be feature-flagged if needed |
| **Monitoring** | ✓ Existing | No new endpoints to monitor |

---

## 10. Checklist Phase 14

| Item | Status |
|------|--------|
| GET /core/home-feed/ unchanged | ✓ Confirmed |
| HomeModuleConfig model unchanged | ✓ Confirmed |
| layout_config field sufficient | ✓ Confirmed |
| No new endpoints needed | ✓ Confirmed |
| No database migrations | ✓ Confirmed |
| Backward compatible | ✓ Confirmed |
| Can deploy frontend without backend | ✓ Confirmed |

---

**Phase 14 COMPLETADA ✓**

**Próximo:** Phase 15 (Unit Tests) [Optional] — Phase 16 (Production Deploy)

---

## Appendix: Example Payload

### POST /dashboard/modules/ (Create new marketplace module)

```json
{
  "custom_label": "Marketplace Premium",
  "custom_icon": "bi-shop",
  "custom_url": "/tienda",
  "is_visible": true,
  "display_order": 1,
  "display_type": "marketplace",
  "layout_config": {
    "carousel": {
      "items_desktop": 6,
      "items_tablet": 3,
      "items_mobile": 1.2,
      "autoplay": true,
      "loop": true,
      "speed": 50,
      "pause_on_hover": true,
      "pause_on_touch": true,
      "pause_on_focus": true,
      "show_arrows": true,
      "show_indicators": true
    },
    "media": {
      "type": "video",
      "video_url": "https://...",
      "poster": "https://...",
      "blur": 0,
      "glass": true
    },
    "header": {
      "title": "Nuestro Marketplace",
      "subtitle": "Ofertas Exclusivas",
      "description": "Descubre productos premium...",
      "cta_text": "Explorar Ahora",
      "cta_url": "/tienda/bestsellers",
      "cta_target": "_self"
    },
    "section_background": {
      "type": "image",
      "image": "https://...",
      "parallax": true
    }
  }
}
```

**Response:** `201 Created` — same response format as existing endpoints.
