# 03 — DUPLICIDAD DE CÓDIGO
**Fecha:** 2026-07-16

---

## Backend — Lógica Duplicada

### DUP-B1 — `BrandList` y `CategoryList` duplicados entre `shop` y `renting`
| Componente Backend | shop | renting |
|---|---|---|
| Commands | `BrandCommands`, `CategoryCommands` | `RentingBrandCommands`, `RentingCategoryCommands` |
| Selectors | `BrandSelector`, `CategorySelector` | `RentingSelector.list_brands()`, `list_categories()` |
| ViewSets | `AdminBrandViewSet`, `AdminCategoryViewSet` | `AdminRentingBrandViewSet`, `AdminRentingCategoryViewSet` |

El patrón CRUD es idéntico (name, slug, image, is_active, soft-delete). La diferencia es solo el modelo destino. Oportunidad de una implementación genérica `BaseCatalogCommands` / `BaseCatalogSelector`, pero el beneficio real es bajo porque los modelos son distintos y hay contexto de negocio en cada uno.

### DUP-B2 — FSM de Operaciones post-pago triplicado
Tres FSMs (RentalOperation, ServiceOperation, Shipment FSM) implementan el mismo patrón:
- Estado inicial "READY_FOR_*"
- Transiciones de estado con Commands específicos
- Timeline append-only
- Notificaciones por transición
- Asignación de dispatcher (DispatcherProfile)
- Incidencias

La estructura es idéntica, solo el modelo de datos varía. No hay una clase base `BaseOperationFSM` compartida — cada FSM reimplementa la misma estructura de transiciones y validaciones.

**Recomendación:** Crear una capa `operations/services/base_fsm.py` con la lógica de transición reutilizable que cada módulo herede. Esto evitará que futuros cambios (e.g., agregar un estado de "PAUSED") requieran modificar 3 archivos distintos.

### DUP-B3 — Serializers de imagen duplicados por app
`ProductImageSerializer` (shop), `EquipmentImageSerializer` (renting), y equivalentes en `technical_services` tienen exactamente la misma estructura: `uuid`, `image`, `alt_text`, `is_primary`, `order`. No hay un `BaseMediaSerializer` compartido.

### DUP-B4 — Lógica de validación de Stock duplicada
`CartCommands._check_availability()` y `OrderCommands.create_from_cart()` ambas validan disponibilidad de stock. La validación real delega a `InventorySelector.get_current_stock()`, pero el código de validación (comparar con cantidad, generar mensaje de error) se repite.

### DUP-B5 — `_log_ai_action()` helper definido en múltiples archivos
La función helper `_log_ai_action(request, tool, metadata)` que llama `SecurityCommands.log_event(SecurityEvent.AI_ACTION_EXECUTED, ...)` está definida en:
- `renting/api/internal_ai.py`
- `core/api/internal_ai.py`
- `ecommerce/internal_ai_urls.py` (posiblemente)

Debería estar en un solo lugar, por ejemplo `ecommerce/internal_ai_utils.py`, e importarse.

---

## Frontend — Componentes Duplicados

### DUP-F1 — `EquipmentGallery` con dos implementaciones distintas
| Versión A | `components/customer/renting/EquipmentGallery.vue` |
| Versión B | `components/renting/detail/EquipmentGallery.vue` |

A: galería minificada/simplificada. B: galería completa con alt text, type badges, placeholder handling. Debería haber una sola implementación parametrizable.

### DUP-F2 — `BrandList` y `CategoryList` duplicados entre shop y renting (frontend)
| Entidad | shop | renting |
|---|---|---|
| BrandList | `modules/shop/BrandList.vue` (258L, con bulk-delete + CSV export) | `modules/renting/RentingBrandList.vue` (120L, subset) |
| CategoryList | `modules/shop/CategoryList.vue` (190L) | `modules/renting/RentingCategoryList.vue` (126L) |

La funcionalidad de renting es un subconjunto de shop. Un `BaseCatalogList.vue` parametrizable podría unificar ambos.

### DUP-F3 — 7 componentes Timeline con lógica de render idéntica
Ver `07_FRONTEND.md` FE-M4. Todos renderizan listas de eventos con timestamp, ícono y estado. Solo varía el modelo de datos.

### DUP-F4 — 4 Operation Boards con estructura Kanban idéntica
`operations/OperationBoard.vue`, `orders/ShopOperationBoard.vue`, `renting/RentalOperationBoard.vue`, `technical_services/ServiceOperationBoard.vue`. Misma estructura visual, diferentes endpoints y estados. Un `BaseOperationBoard.vue` con slots para las acciones de dominio eliminaría la duplicación.

### DUP-F5 — Cost Rules implementado en 3 lugares
1. `components/shared/CostRulesView.vue` — muerto, 12KB
2. `modules/renting/panels/CostRulesPanel.vue` — activo
3. Inline en `modules/shop/ProductForm.vue` — forma parte del formulario de producto

### DUP-F6 — Colombia locations data duplicada
- Fuente canónica: `src/data/colombiaLocations.js`
- Copia inline: `components/customer/checkout/ColombianAddressForm.vue:228`

### DUP-F7 — Wizards de cotización paralelos sin código compartido
`useQuoteWizard.js` y `useCatalogQuoteWizard.js` implementan el mismo wizard multi-paso (applicant, steps, localStorage, submit, error handling) para dos flujos distintos. Compartir `useWizardBase(steps, storageKey)`.

### DUP-F8 — Patrones de validación de formularios repetidos en ~10 componentes
No hay un sistema de validación compartido (el `useFormValidation.js` existente es específico de campañas). Cada formulario implementa su propia lógica de `required` / `email regex` / `minLength`.

---

## Duplicación entre Módulos de Negocio

### Patrón "catálogo + variantes + precio" (shop, renting, technical_services)
Los tres dominios implementan de forma independiente:
- Modelo base con variantes
- Sistema de precios con reglas dinámicas (`CostRule`)
- Selector de variantes con precios
- Serializer de breakdown de precios

**Impacto:** Un bug en la lógica de pricing debe corregirse en 3 lugares. Un cambio de UI en el display de precios requiere actualizar 3 serializers/componentes.

### Patrón "asignación de técnico/dispatcher"
Tanto `technical_services.ServiceAssignmentCommands` como `renting.RentalOperationCommands` asignan a `DispatcherProfile`. El código de validación "¿está disponible? ¿tiene el perfil correcto?" está duplicado.

---

## Recomendaciones

| Prioridad | Acción |
|---|---|
| Alta | Crear `BaseOperationFSM` en `operations/services/` — unifica transiciones FSM |
| Alta | Crear `BaseOperationBoard.vue` — unifica los 4 boards Kanban |
| Alta | Unificar los 7 Timeline components en `StatusTimeline.vue` parametrizable |
| Media | Mover `_log_ai_action()` a `ecommerce/internal_ai_utils.py` |
| Media | `BaseCatalogList.vue` para shop/renting brand+category |
| Media | `useWizardBase.js` compartido para los dos wizards de cotización |
| Media | `BaseMediaSerializer` para image serializers de shop/renting/services |
| Baja | Eliminar copia inline de Colombia locations |
| Baja | Eliminar `CostRulesView.vue` (muerto) |
