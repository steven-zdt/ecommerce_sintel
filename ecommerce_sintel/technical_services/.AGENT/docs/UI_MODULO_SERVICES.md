# REGISTRO DE IMPLEMENTACIÓN — Reingeniería UX/UI del módulo Technical Services (SDP)

**Este documento es la guía única del proceso**, mismo formato que
[`shop/.AGENT/docs/UI_MÓDULO_SHOP.MD`](../../../shop/.AGENT/docs/UI_MÓDULO_SHOP.MD). El brief
original vive en [`technical_services/.AGENT/REINGENIERÍAUX_UI.md`](../REINGENIERÍAUX_UI.md)
(25 fases, "Enterprise Service Detail Experience") — no se reescribió, este documento lo
referencia y anota el estado real fase por fase.

**Documento relacionado:** [`ARQUITECTURA_COMPLETA_SERVICES.md`](ARQUITECTURA_COMPLETA_SERVICES.md)
y `technical_services/CLAUDE.md` (corregidos el 2026-08-05 — tenían afirmaciones desactualizadas
sobre componentes que nunca existieron, ver Fase 1 abajo).

---

## Contexto — por qué este plan difiere del de Shop

Este plan se ejecutó inmediatamente después de terminar la reingeniería equivalente de Shop
(`shop/.AGENT/docs/UI_MÓDULO_SHOP.MD`), reutilizando toda la infraestructura genérica ya construida
ahí (`shared.models.ContentBlockConfig`/`CatalogRelation`) — exactamente el escenario para el que
se diseñó esa infraestructura (Regla del brief de Shop: "reutilizada por Renting y Technical
Services" en fases futuras).

**Hallazgo central de la auditoría previa a este plan** (2 agentes en paralelo + verificación
directa — uno de los agentes exploró por error una copia vieja del repo en `D:\`, sus hallazgos
sobre `shared/` fueron descartados y re-verificados a mano contra el código real): a diferencia de
Shop (9 de 15 bloques ya tenían modelo real), en Technical Services **el catálogo enriquecido
nunca se había construido** — la página pública de detalle renderizaba casi todo con
`SERVICE_FALLBACK`, un objeto de datos **inventados** dentro del `.vue`, nunca conectados a ningún
modelo. Solo Galería, Paquetes, FAQ, Profesionales y Reseñas eran reales. También se confirmó que
`technical_services/CLAUDE.md` tenía afirmaciones desactualizadas (describía componentes —
`ServiceGallery`, `ServiceFAQAccordion`, `ServiceReviews` — que nunca existieron en el código
real).

---

## Estado general (2026-08-05)

| Fase del brief | Título | Estado | Resumen de una línea |
|---|---|---|---|
| 1 | Auditoría Arquitectónica | ✅ Completa | 2 agentes + verificación directa; corrigió afirmaciones desactualizadas de CLAUDE.md |
| 2 | Auditoría UX | ✅ Completa | Confirmó que la mayoría de secciones públicas eran `SERVICE_FALLBACK` (datos inventados) |
| 3 | Nueva arquitectura de información | ✅ Completa | 19 bloques (no 23 literales, ver nota de alcance) vía `ContentBlockConfig.SERVICE_DEFAULT_ORDER` -- **[CORREGIDO 2026-08-14]: hoy son 18**, se quito `support` en la auditoria FASE 7 del plan "Rediseno ServiceForm + Content/Media" por no tener backing data ni render en `ServiceDetailContent.vue` |
| 4 | Diseño del CMS | ⚠️ Misma desviación que Shop | Orquestación de orden/visibilidad, no un builder de HTML libre |
| 5 | Constructor de bloques | ⚠️ Parcial — ver nota de alcance | 7 modelos nuevos reales; "Personalizado" no implementado |
| 6-9 | Alcance/Beneficios/Incluye/No incluye | ✅ Completos (versión simplificada) | Reuso del patrón de campos ya usado por Shop |
| 10 | Proceso del servicio | ✅ Completa | `ServiceProcessStep` — único modelo sin equivalente en Shop/Renting |
| 11 | Materiales utilizados | ✅ Completa | `ServiceMaterial` ya existía (motor de costos); expuesto al cliente por primera vez |
| 12 | Cobertura | ✅ Completa (versión simplificada) | `TechnicalService.coverage_notes`, campo de texto |
| 13 | Instalación | ✅ Ya existía (reusado) | `ServiceRequirement` cubre "requisitos previos" |
| 14 | Soporte | ❌ No implementado | Sin modelo — ver "Decisiones pendientes" |
| 15 | Técnicos especializados | ✅ Ya existía (reusado) | `ServiceProfessionals.vue`, funcionando desde antes de esta fase |
| 16 | Ficha técnica | ✅ Completa | `ServiceSpecificationGroup`/`ServiceSpecification`, sin tablas HTML |
| 17 | Documentación | ✅ Completa | `ServiceDocument` — nuevo, espejo de `ProductDocument` |
| 18 | Videos | ✅ Completa | `ServiceVideo` — nuevo, espejo de `ProductVideo` |
| 19 | FAQ | ✅ Ya existía (reusado) | `ServiceFAQ`, funcionando desde 2026-07-17 |
| 20 | Servicios relacionados | ✅ Completa | `CatalogRelation` (relation_type=related/compatible) |
| 21 | Productos relacionados | ✅ Completa | `CatalogRelation` cruzado a `shop.Product` — primer uso real de esa capacidad |
| 22 | Responsive | ✅ Completa | Verificado en vivo (desktop/tablet/mobile) |
| 23 | Accesibilidad | ❌ No auditado en esta pasada | Ver "Decisiones pendientes" |
| 24 | Rendimiento | ⚠️ Parcial | Mismo estado que Shop (lazy images + code splitting; Intersection Observer/Lighthouse no medidos) |
| 25 | Auditoría final | ✅ Completa | Ver sección al final |

**Nota de alcance (léase antes de las fases 5-14):** igual que en Shop, se aplicó la Regla del
brief "antes de crear cualquier modelo, comprobar si ya existe una estructura equivalente" —
Beneficios reusa `ServiceMarketing.quick_benefits` (ya existía) en vez de crear un modelo nuevo;
Soporte no tiene ningún dato real detrás (ni en el modelo viejo ni en el nuevo catálogo) y se dejó
sin implementar en vez de inventar contenido; Personalizado/Casos de éxito se retiraron sin
reemplazo (`SERVICE_FALLBACK.caso de exito` era 100% inventado, se documenta como decisión
explícita, no como omisión).

---

## Backend implementado

**Modelos nuevos** (`technical_services/models.py`, migración `0032`, espejo exacto de
`shop.Product*`/`renting.Rental*`): `ServiceIncludedItem`, `ServiceExcludedItem`,
`ServiceRequirement`, `ServiceSpecificationGroup`/`ServiceSpecification`, `ServiceDocument`,
`ServiceVideo`, `ServiceProcessStep` (único genuinamente nuevo, sin equivalente a mirrorear) +
`TechnicalService.scope`/`warranty`/`coverage_notes` (campos de texto).

**Service layer:** `technical_services/services/catalog.py` (nuevo), mismo patrón factorizado
(`_reorder`/`_toggle_active`/`_soft_delete`/`_duplicate`) que `shop/services/catalog.py`.

**Reutilización de infraestructura genérica (sin cambios a los modelos):**
`shared.models.ContentBlockConfig`/`CatalogRelation` se registraron para un segundo
`content_type` (`TechnicalService`). Único cambio real a `shared/`:
- `ContentBlockConfig.BLOCK_TYPE_CHOICES` se extendió con 5 tipos propios de servicios
  (`coverage`, `process`, `materials`, `technicians`, `recommended_products`) — migración
  `shared.0002` (solo metadata de `choices`, sin impacto en datos).
- `ContentBlockConfig.SERVICE_DEFAULT_ORDER` (nuevo, 19 bloques) convive con
  `ContentBlockConfig.DEFAULT_ORDER` (Shop, 15 bloques) — verificado que ambos catálogos funcionan
  de forma independiente sobre el mismo modelo compartido.
- `ContentBlockConfigSelector.resolve_for()`/`Commands.set_visibility()` ganaron un parámetro
  opcional `default_order` (default = el de Shop, para no romper su call site original).

**Serializer:** `TechnicalServiceDetailSerializer(TechnicalServiceSerializer)` (nuevo, mismo
patrón de herencia que `ProductDetailSerializer`) — expone el catálogo enriquecido +
`content_blocks` + `related_services`/`compatible_services` (otro `TechnicalService`) +
`recommended_products` (cruza a `shop.Product` vía `CatalogRelation`, sin que el modelo dependa de
lógica de Shop — mismo nivel de acoplamiento que ya existía en `ServiceMaterial.product_variant`).
Conectado al endpoint ya existente `GET services/services/{uuid}/detail/` (antes usaba el
serializer liviano). `servicesService.detail()` (frontend) actualizado para apuntar ahí.

**Admin:** `dashboard/api/services_catalog_views.py` (nuevo, espejo de `shop_catalog_views.py`) +
`ServiceCatalogChildOrchestrator`/`_SERVICE_CATALOG_CHILD_REGISTRY` en `admin_orchestrators.py` +
2 ViewSets nuevos en `content_blocks_views.py` (`AdminServiceContentBlockViewSet`,
`AdminServiceRelationViewSet` — este último soporta relacionar con otro servicio O con un producto
de Shop vía `related_entity_type`).

**Tests:** `technical_services/test_content_blocks.py` (nuevo, 11 tests) — orden por defecto de
19 bloques, reorder/visibilidad con tipos de bloque propios de servicios, relación cruzada real a
`shop.Product`, exposición en el endpoint público, permisos admin. Suite completa de
`technical_services` (pre-existente) corrida sin regresiones.

## Frontend implementado

**Admin (`ServiceForm.vue`):** 8 pestañas nuevas (7 tabs → 15). Incluye/No incluye/Requisitos
reusan `CatalogListManager.vue` (de Renting, ya generalizado con `parent-key`, ahora también con
`parent-key="service"`). Ficha técnica/Documentación/Videos/Proceso: 4 managers nuevos y
dedicados en `modules/technical_services/catalog/` (mismo patrón que los de Shop). "Contenido del
Servicio" reusa `ContentBlocksTab.vue` de Shop — **generalizado** con prop `entity-type`
(`'product'|'service'`), no duplicado; cada `entityType` tiene su propia config de endpoints,
bloques con pestaña propia (para el link "Editar") y tipos de relación.

**Público (`ServiceDetailContent.vue`):** reescrito — `SERVICE_FALLBACK` eliminado por completo.
Todas las secciones que antes mostraban datos inventados ahora leen el catálogo real, envueltas en
la misma orquestación `content_blocks` que Shop (`blockVisible`/`blockStyle`). Reutiliza
componentes ya genéricos: `DescriptionSection`/`ItemCard` (de Shop), `EquipmentIncludedList`/
`ExcludedList`/`RequirementList`/`SpecificationTable`/`VideoGallery`/`ManualList`/`DocumentList`/
`DownloadSection` (de Renting, ya compartidos con Shop). "Proceso" y "Materiales" son las únicas
secciones con markup genuinamente nuevo (sin componente reusable con esa forma de dato).

**Código muerto eliminado:** `components/services/detail/ServiceFeatureList.vue`,
`ServiceScopeList.vue`, `ServiceSpecificationTable.vue` (solo renderizaban `SERVICE_FALLBACK`,
sin otro consumidor) y `views/customer/services/ServiceDetailView.vue` (huérfano, ninguna ruta lo
usaba — confirmado por grep antes de borrar).

---

## Auditoría final (Fase 25)

> **Estado: ✅ COMPLETA**

- `manage.py check` — limpio (mismo warning preexistente de `cart.Cart.user`, ajeno).
- `manage.py test technical_services.test_content_blocks` — 11/11 OK.
- `manage.py test technical_services` (suite completa preexistente) — sin regresiones.
- `manage.py test shared shop` — 30/30 OK (confirma que la generalización de `ContentBlockConfig`
  no rompió el comportamiento ya establecido de Shop).
- `npx vite build` — limpio, sin warnings nuevos.
- No rompe: Commands/Selectors/Pricing Engine/ServiceOperation/Marketplace/Scheduler/DTO — cero
  archivos de `services/pricing.py`, `services/operations.py`, `services/technician_availability.py`
  tocados. `ServiceMaterial`/`ServiceFAQ`/`ServiceMarketing` reusados sin cambios de contrato.

---

## REGLAS OBLIGATORIAS — checklist de cumplimiento

Mismas 7 reglas que el brief de Shop (no están numeradas explícitamente en
`REINGENIERÍAUX_UI.md`, pero la sección "PRINCIPIOS" es equivalente):

1. No modificar Commands/Selectors/Service Layer/API/Endpoints/DTO/Serializer/Workflow
   Operativo/Sistema de Cotización/Sistema de Operaciones/Asignación de Técnicos/Sistema de
   Pagos/Scheduler/Disponibilidad/Marketplace/Pricing Engine. → ✅ (ver Auditoría final)
2. No crear código duplicado. → ✅ (`ContentBlockConfig`/`CatalogRelation` reusados sin cambios
   de modelo; `CatalogListManager.vue`/`ContentBlocksTab.vue` generalizados, no copiados)
3. Reutilizar infraestructura existente. → ✅
4. Mantener compatibilidad hacia atrás. → ✅ (migraciones 100% aditivas; `resolve_for()`/
   `set_visibility()` con parámetro opcional, call site de Shop sin cambios)

## ENTREGABLES — checklist

- [x] Auditoría completa del módulo (2 agentes + verificación directa, con hallazgo de agente
      explorando ruta incorrecta documentado y corregido)
- [x] Mapa de componentes reales vs. documentados (corrigió `technical_services/CLAUDE.md`)
- [x] Arquitectura objetivo (este documento + reutilización de `shared/`)
- [x] Checklist técnico (tabla de 25 fases arriba)
- [ ] Plan de pruebas formal como documento independiente (existen tests automatizados +
      verificación manual, no un plan previo a la ejecución — mismo estado que Shop)
- [x] Validación final de que el módulo mantiene la arquitectura Enterprise y reutiliza la misma
      infraestructura de contenido de Shop (era el objetivo explícito de la Regla 6 del brief de
      Shop — cumplido: es literalmente el mismo `ContentBlockConfig`/`CatalogRelation`, sin
      duplicar el modelo)

---

## Decisiones pendientes (requieren definición de producto, no técnica)

1. **Soporte (Fase 14 del brief):** canales/horario/SLA/mantenimiento no tienen ningún modelo
   detrás, ni antes ni después de esta reingeniería. El bloque `support` existe en la orquestación
   (`ContentBlockConfig`) pero nunca tendrá contenido hasta que se decida construir el modelo.
2. **Accesibilidad (Fase 23):** no se auditó ARIA/contraste/navegación por teclado en esta pasada.
3. **Intersection Observer + Lighthouse (Fase 24):** mismo estado que Shop — no implementado/no
   medido, razón documentada en `shop/.AGENT/docs/UI_MÓDULO_SHOP.MD` (lazy nativo del navegador
   cubre el mismo objetivo práctico sin código a medida).
4. **Bloque "Personalizado" / Casos de éxito:** sin estructura de datos clara, se retiraron sin
   reemplazo (Casos de éxito) o nunca se implementaron (Personalizado) — mismo criterio que Shop
   con "Lista"/"Bloque personalizado".

---

## Cierre — 2026-08-05

Implementación cerrada en este punto. Verificación final antes del cierre:
`manage.py check` limpio, `manage.py test technical_services` 133/133,
`manage.py test technical_services.test_content_blocks` 11/11,
`manage.py test shared shop` 30/30 (confirma que generalizar `ContentBlockConfig` para un
segundo `content_type` no rompió el comportamiento ya establecido de Shop), `npx vite build`
limpio. Verificado en navegador contra datos reales: página pública sin errores de consola
(degrada correctamente a vacío donde no hay contenido cargado), y flujo admin completo probado
de punta a punta (pestaña "Contenido del Servicio" — 19 bloques listados, relación
servicio-a-servicio creada vía búsqueda real, `POST` → 201, reflejada en la UI al instante). Los
4 puntos de "Decisiones pendientes" arriba son las únicas piezas del brief original de 25 fases
que no se implementaron, y las 4 requieren una decisión de producto (no técnica) antes de tocar
código. Hasta que se resuelvan, el estado de este documento es el estado final de la
reingeniería SDP de Technical Services.
