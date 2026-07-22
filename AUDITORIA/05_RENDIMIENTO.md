# 05 — RENDIMIENTO
**Fecha:** 2026-07-16

---

## N+1 Confirmados (Backend)

### N+1-1 — `CartSerializer.get_total`: 1 query Tax por ítem de carrito
**Archivo:** `cart/api/serializers.py:114-121`  
**Severidad:** Alta — cada ítem dispara `Tax.objects.filter(is_active=True)`  
**Impacto medido:** Carrito con 10 ítems = 10 queries idénticas de Tax

```python
# ACTUAL (N+1):
for item in obj.items.all():
    price = CartItemSerializer(item).data  # llama TaxSelector.list_active() por item

# CORRECTO: pre-calcular taxes una vez
active_taxes = TaxSelector.list_active()
total = sum(
    PricingService.calculate_final_price(item.variant, taxes=active_taxes) * item.quantity
    for item in obj.items.all()
)
```

### N+1-2 — `FlashOfferCardSerializer.get_item_thumbnail`: 1-2 queries por oferta
**Archivo:** `core/api/serializers.py:101-115`  
**Severidad:** Media (la home-feed tiene cache de 5 min — el costo es por ventana de cache)  
`MarketingSelector.list_active_flash_offers()` no prefetch images. El `.filter(is_primary=True)` en el serializer ignora cualquier cache de prefetch.

```python
# FIX en selector: agregar prefetch
.prefetch_related(
    'variant__product__images',
    'service_variant__service__images',
    'equipment_variant__equipment__images'
)
# FIX en serializer: filtrar en Python sobre .all()
imgs = obj.variant.product.images.all()
primary = next((i for i in imgs if i.is_primary), next(iter(imgs), None))
```

### N+1-3 — `UserProfile.total_services_completed`: COUNT por perfil en listas de admin
**Archivo:** `accounts/models.py:92-95`  
**Severidad:** Alta — lista de contratistas con N perfiles = N+1 queries COUNT  
Ver fix de anotación en `04_OPTIMIZACION_BD.md`.

### N+1-4 — `ShipmentOrderSummarySerializer.get_items_count`: COUNT bypasea prefetch
**Archivo:** `orders/api/serializers.py:130`  
**Severidad:** Alta — panel de operaciones de envío  
Fix: reemplazar `.filter().count()` con `sum(1 for i in obj.items.all() if i.variant_id)`.

### N+1-5 — `FooterGroupSerializer.get_links_count`: COUNT por grupo sin prefetch
**Archivo:** `core/api/serializers.py:440`  
**Severidad:** Baja (footer es poco frecuente)  
Fix: `prefetch_related('links')` en selector + filtro en Python.

---

## N+1 Ya Corregidos (no reportar de nuevo)

Los siguientes ya fueron corregidos en la auditoría de 2026-07-03:
- `OrderSelector.list_for_user()`: pasó de 19 a 3 queries (select_related + prefetch)
- `TechnicalServiceSerializer.get_variants()`: `.filter()` reemplazado por `.all()` sobre prefetch
- `FeaturedProductCardSerializer.get_thumbnail`: usa `obj.images.all()` (no `.filter()`)
- `FeaturedEquipmentCardSerializer.get_thumbnail`: ídem
- `FeaturedServiceCardSerializer.get_thumbnail`: ídem

---

## Queries Lentas por Falta de Índices

Ver lista completa en `04_OPTIMIZACION_BD.md` §DB-M1. Los más impactantes:

| Campo | Tabla | Filtro frecuente en |
|---|---|---|
| `Quotation.status` | `quotes_quotation` | Panel admin, CPQ workflow |
| `EquipmentVariant.is_active` | `renting_equipmentvariant` | Catálogo público (JOIN frecuente) |
| `OperationAssignment.status` | `operations_operationassignment` | Panel de operaciones |

---

## Rendimiento de Serializers

### Serializer lento: `TechnicalServiceSerializer` (benchmark: 31→23 queries por 2 servicios)
Parcialmente corregido en 2026-07-03. Problema pendiente: `get_calculated_price()` y `get_price_info()` en `ServiceVariantSerializer` llaman por separado a `ServiceSelector.get_variant_quotation(obj)`, duplicando todo el cálculo de precio por variante. Requiere refactor de diseño: calcular una vez y pasar al serializer como contexto.

### Serializer con TextFields innecesarios: `Equipment.list_all_for_admin`
Carga `description`, `meta_description`, `meta_keywords` en listados donde solo se usan `name`, `slug`, `is_active`. Agregar `.defer()`.

---

## Rendimiento Frontend

### Bundle sin lazy loading de rutas
**Archivo:** `src/apps/admin/router.js`  
Ninguna de las 60+ rutas del panel admin usa `() => import(...)` (lazy import). Todos los componentes se cargan en el bundle inicial. El tiempo de carga inicial del panel admin incluye todos los boards de operaciones, el constructor visual de home, los módulos de marketing, etc.

```javascript
// ACTUAL:
import HomeConfigView from '../../modules/core/HomeConfigView.vue'
{ path: 'home-config', component: HomeConfigView }

// CORRECTO:
{ path: 'home-config', component: () => import('../../modules/core/HomeConfigView.vue') }
```

### Componentes masivos que deberían dividirse

| Componente | Líneas | Problema |
|---|---|---|
| `HomeConfigView.vue` | 2.705 | "God component" — editor, preview, config, modal en uno |
| `ModuleBuilderModal.vue` | 1.588 | Lógica de 18 tipos de layout en un único modal |
| `rentingAdmin.js` (store) | 557 | 9 dominios de estado — cada action recarga el store entero |
| `quotesAdmin.js` (store) | 557 | Templates + quotations en un store — template build reload afecta quotation views |

### Re-renders innecesarios en mega-stores
Las tres stores de admin (`rentingAdmin`, `quotesAdmin`, `technicalServicesAdmin`) tienen un único flag `loading` por store. Una acción de carga de categorías (`loadCategories`) pone `this.loading = true`, lo que hace que TODO el template que observe `store.loading` re-renderice, incluyendo listas de equipos, variants, etc.

---

## Caché (estado actual)

| Capa | Implementado | Notas |
|---|---|---|
| `GET /api/v1/core/home-feed/` | Sí — 5 min Redis cache | Correcto |
| `LaborCostCalculator.get_active_config()` | Sí — 5 min + signal invalidation | Correcto (desde 2026-07-03) |
| Selectors de catálogo público | No | `ProductSelector.list_active()` sin cache |
| `FlashOfferSelector.list_active()` | No | Llamado por la home-feed (que sí tiene cache) pero también por endpoints directos |
| Django REST Framework throttling | Parcial | Solo en auth, no en endpoints de lista pesados |

**Recomendación:** Agregar `@method_decorator(cache_page(60 * 5))` o cache a nivel de Selector para los catálogos públicos (`/api/v1/shop/products/`, `/api/v1/renting/equipment/`, `/api/v1/services/`).

---

## Celery / Background Tasks

Tareas identificadas:
- `ai_proactive_room_message_task` — mensajes proactivos del AI Engine
- `process_whatsapp_inbound_task` — procesamiento de WhatsApp inbound
- Tareas de marketing (`send_now` en `marketing/tasks.py`)
- Generación PDF de cotizaciones

No se detectaron tareas que ejecuten shell commands o manipulación de archivos sin sanitización. Las tareas de WhatsApp reciben `wa_id` y `text` del webhook — si el webhook no verifica firma (ver `06_SEGURIDAD.md` SEC-M5), estas tareas podrían procesarse con input arbitrario.
