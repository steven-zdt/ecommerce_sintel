# Matriz de campos -- ServiceForm.vue (FASE 1)

Clasificacion por campo segun el plan: **KEEP** (se queda donde esta),
**MERGE** (fusionar con otro editor del mismo campo), **MOVE** (cambiar de
pestana/lugar), **HIDE** (ocultar del flujo de creacion, dejar solo en
edicion), **REMOVE** (eliminar duplicado, ya resuelto o propuesto), **NEW**
(no existe todavia, hay que crearlo). Ningun cambio de codigo se aplica en
este incremento -- ver `SERVICES_FRONTEND_AUDIT_2026-08-14.md` FASE 0.

| Campo | Fuente (modelo.campo) | Tab actual | Obligatorio | Redundante | Customer visible | API | Destino visual (publico) | Clasificacion |
|---|---|---|---|---|---|---|---|---|
| name | TechnicalService.name | General + **ServiceList.vue inline** | Si | Si (2 vias) | Si | dashboard/services/ | Hero / titulo | **MERGE** -- decidir cual de las 2 vias es la fuente unica |
| description | TechnicalService.description | General + **ServiceList.vue inline** | Si | Si (2 vias) | Si | dashboard/services/ | Hero / descripcion | **MERGE** |
| category | TechnicalService.category | General + **ServiceList.vue inline** | No | Si (2 vias) | Si (filtro) | dashboard/services/ | Breadcrumb/filtro | **MERGE** |
| level | TechnicalService.level | General + **ServiceList.vue inline** | No | Si (2 vias) | Si (filtro) | dashboard/services/ | Badge nivel | **MERGE** |
| is_active | TechnicalService.is_active | General + **ServiceList.vue inline** | No | Si (2 vias) | Indirecto (visibilidad) | dashboard/services/ | -- | **MERGE** |
| is_featured | TechnicalService.is_featured | General + **ServiceList.vue inline** | No | Si (2 vias) | Si (destacados) | dashboard/services/ | Badge/listado home | **MERGE** |
| is_purchasable | TechnicalService.is_purchasable | General + **ServiceList.vue inline** | No | Si (2 vias) | Indirecto (CTA) | dashboard/services/ | CTA habilitado/no | **MERGE** |
| scope | TechnicalService.scope | ContentBlocksTab (unico, EDIT) | No | No (ya resuelto hoy) | Si | dashboard/services/ | Seccion "Alcance" | KEEP |
| warranty | TechnicalService.warranty | ContentBlocksTab (unico, EDIT) | No | No (ya resuelto hoy) | Si | dashboard/services/ | Seccion "Garantia" | KEEP |
| coverage_notes | TechnicalService.coverage_notes | ContentBlocksTab (unico, EDIT) | No | No (ya resuelto hoy) | Si | dashboard/services/ | Seccion "Cobertura" | KEEP |
| meta_title/description/keywords | TechnicalService.meta_* | General > SEO (EDIT) | No | No | Si (indirecto, SEO) | dashboard/services/ | `<head>` | KEEP |
| og_image | TechnicalService.og_image | **ninguno** | No | No aplica | Si (indirecto, share) | dashboard/services/ (campo existe, sin UI) | `<meta og:image>` | **NEW** (gap conocido, documentado como deliberado en 2026-07-18) |
| Variante inicial (pricing_strategy/fixed_price/estimated_hours/complexity_factor) | ServiceVariant.* | General (solo CREATE, unico) | Si | No | Si | dashboard/services/ (`initial_variant`) | Precio mostrado | KEEP |
| pricing_strategy/fixed_price/estimated_hours/complexity_factor/min_duration/max_duration/simultaneous_capacity (variante existente) | ServiceVariant.* | VariantsTab (unico tras fix de hoy) + **ServiceList.vue inline (fixed_price/estimated_hours/complexity_factor)** | Si | Si (parcial, 2 vias) | Si | dashboard/service-variants/ | Precio/variantes | **MERGE** (para los 3 campos que ServiceList.vue tambien edita) |
| pricing_source/manual_unit_price/manual_project_price | ServiceVariant.* | CostosTab > PricingSourceCard (unico) | No | No | Si | dashboard/service-variants/{uuid}/set-pricing/ | Precio mostrado | KEEP |
| ServiceImage (image/alt_text/is_primary) | ServiceImage.* | ImagesTab (unico) | Recomendado | No | Si | dashboard/services/{uuid}/add_image/ | Galeria | KEEP (base) |
| ServiceImage.caption | -- no existe -- | -- | No | No aplica | Si (propuesto) | -- | Pie de imagen en galeria | **NEW** (FASE 4) |
| ServiceImage.description | -- no existe -- | -- | No | No aplica | Si (propuesto) | -- | Texto ampliado por imagen | **NEW** (FASE 4) |
| ServiceImage.display_order | -- no existe -- | -- | No | No aplica | Si (propuesto, orden real) | -- | Orden de galeria | **NEW** (FASE 4) |
| ServicePackage/PackageIncludedItem/PackageAdditionalCost | modelos propios | Paquetes (unico) | No | No | Si | dashboard/service-packages/ | Seccion "Paquetes" | KEEP |
| ServiceFAQ | modelo propio | FAQ (unico) | No | No | Si | dashboard/service-faqs/ | Seccion "FAQ" | KEEP |
| ServiceMarketing.* | modelo propio | Marketing (unico) | No | No | Si (parcial, copy) | dashboard/services/{uuid}/marketing/ | Badges/mensajes promo | KEEP |
| ServiceIncludedItem/ExcludedItem/Requirement | modelos propios | Incluye/No incluye/Requisitos (unico c/u) | No | No | Si | dashboard/service-*-items/ | Secciones "Incluye"/"No incluye"/"Requisitos" | KEEP |
| ServiceSpecificationGroup/Specification | modelos propios | Ficha tecnica (unico) | No | No | Si | dashboard/service-specification*/ | Tabla especificaciones | KEEP |
| ServiceDocument/ServiceVideo | modelos propios | Documentacion/Videos (unico c/u) | No | No | Si | dashboard/service-documents/, -videos/ | Secciones respectivas | KEEP |
| ServiceProcessStep | modelo propio | Proceso (unico) | No | No | Si | dashboard/service-process-steps/ | Seccion "Proceso del servicio" | KEEP (no operativo, ver auditoria) |
| ContentBlockConfig (orden/visibilidad) + CatalogRelation | modelos compartidos | Contenido del Servicio (unico) | No | No | Si (orden real de la pagina) | dashboard/service-content-blocks/, -relations/ | Orquesta el orden de TODAS las secciones de arriba | KEEP |

## Resumen por categoria del plan (CORE/COMMERCIAL/CONTENT/MEDIA/MARKETING/OPERATIONS)

- **CORE** (name/description/category/level/toggles): 7 campos, **todos
  MERGE** -- unica categoria con redundancia real detectada (tabla vs
  formulario).
- **COMMERCIAL** (variante): redundancia parcial (3 campos de la variante
  default tambien editables desde la tabla) + 3 campos NEW pendientes de
  imagen no son comerciales, van en MEDIA.
- **CONTENT** (scope/warranty/coverage/incluye/no-incluye/requisitos/ficha
  tecnica/proceso/documentos/videos): sin redundancia, ya con un editor
  unico cada uno tras las correcciones de esta sesion.
- **MEDIA** (ServiceImage): base KEEP, 3 campos NEW (caption/description/
  display_order) pendientes de FASE 4.
- **MARKETING** (ServiceMarketing + SEO): sin redundancia; `og_image` NEW
  pendiente (gap conocido, no urgente).
- **OPERATIONS**: **confirmado que no hay nada operativo mezclado** en
  `ServiceForm.vue` -- ver seccion correspondiente de la auditoria FASE 0.

## Decision pendiente para MERGE (CORE + los 3 campos de variante)

El plan no especifica cual de las 2 vias (tabla `ServiceList.vue` vs.
formulario `ServiceForm.vue`) debe ganar. Recomendacion tecnica (no
aplicada, pendiente de tu confirmacion antes de tocar codigo): mantener la
edicion inline de `ServiceList.vue` para cambios rapidos de un solo campo
(patron ya usado en Shop/Renting, UX valida y deliberada) y dejar el
formulario como la vista completa/estructurada -- no son verdaderamente
"redundantes" en el sentido de UI duplicada confusa (como si eran Alcance/
Garantia/Variante principal), sino 2 flujos de edicion con proposito
distinto: edicion rapida en tabla vs. edicion completa en formulario. Este
patron ya existe igual en `ProductList.vue`/`RentingList.vue` sin que se
haya reportado como problema -- por eso se marca MERGE (revisar) y no
REMOVE directo, a diferencia de los casos ya resueltos hoy que si eran
duplicados accidentales sin proposito distinto.
