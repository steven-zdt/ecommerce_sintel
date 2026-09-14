# Auditoria Frontend/Backend de Servicios (technical_services) -- 2026-08-14

FASE 0 del plan "Rediseno ServiceForm + Content/Media". Auditoria real de
codigo (no de documentacion) sobre los archivos listados por el plan. Cero
cambios de codigo en esta fase -- solo lectura y verificacion.

## Resolucion de la discrepancia de documentacion (pedida explicitamente)

El numero de pestanas de `ServiceForm.vue` esta desactualizado/fragmentado en
**3 lugares distintos**, ninguno con el numero real actual:

| Fuente | Fecha archivo | Dice | Estado real |
|---|---|---|---|
| `frontend/.AGENT/doc/ARQUITECTURA_COMPLETAFRONEND.md` L95 | 2026-08-05 | "ServiceForm (7 tabs)" | Snapshot PRE reingenieria SDP |
| `technical_services/.AGENT/docs/ARQUITECTURA_COMPLETA_SERVICES.md` L2140 | 2026-08-13 | "gano una 5a pestana Paquetes" | Nota historica de cuando solo habia 5 |
| `technical_services/CLAUDE.md` | -- | "tiene 7 tabs (...)" en una linea, pero mas abajo documenta correctamente "gano 8 tabs" adicionales de la SDP | 7+8=15 es correcto pero no esta consolidado en un solo numero |

**Numero real verificado en codigo (`ServiceForm.vue`, lineas 18-98):
15 pestanas** -- 1 siempre visible (General) + 14 solo-EDIT (Imagen,
Variantes, Costos, Paquetes, FAQ, Marketing, Incluye, No incluye,
Requisitos, Ficha tecnica, Documentacion, Videos, Proceso, Contenido del
Servicio).

Criterio de resolucion pedido por el usuario: la arquitectura **frontend**
(estructura visual del form) se toma como mas reciente/autoritativa para la
ESTRUCTURA, pero en la practica ninguno de los 3 docs tenia el numero
correcto -- se corrigen los 3 en este mismo incremento (ver seccion final).

## Archivos auditados

### `ServiceForm.vue` (shell, 15 tabs)
Orquesta `form`/`initVar` (estado del tab General) + monta permanentemente
(via `v-show`, no `v-if`) casi todos los sub-tabs de EDIT, lo que dispara
sus `onMounted()` (fetchVariants, fetchPackages, etc.) apenas se abre el
formulario en modo edicion, independientemente de que pestana este activa.
Confirma el hallazgo de FASE 10 del plan: **ninguna pestana usa lazy-loading
real (`v-if`)**, todas montan de entrada salvo Imagen/Variantes/Costos/
Marketing/Contenido que llevan `:key` para forzar remount al cambiar de
item -- pero el montaje inicial sigue siendo eager.

### `GeneralTab.vue`
Campos: Nombre*, Descripcion*, Categoria, Nivel, Activo/Destacado/Comprable,
SEO (meta_title/meta_description/meta_keywords, solo EDIT), Variante
inicial (solo CREATE). Tras las correcciones de esta misma sesion (ver
`MEMORY.md`/transcript): Alcance/Garantia/Cobertura y el editor duplicado de
Variante principal en EDIT ya se eliminaron de aqui.

### `ServiceList.vue` -- **hallazgo nuevo, no corregido aun**
La tabla de listado tiene edicion inline propia (`InlineTextEditor`/
`InlineSelectEditor`/`InlineSwitch`) para: `name`, `description`,
`category`, `level`, `is_active`, `is_featured`, `is_purchasable`, y para la
variante default: `fixed_price`, `estimated_hours`, `complexity_factor`.
**Todos estos campos son tambien editables desde `ServiceForm.vue`** (tab
General, y para los de variante tambien desde `VariantsTab.vue`) -- una
redundancia de 2-3 vias no detectada hasta esta auditoria. Ver matriz FASE 1
para la clasificacion propuesta (no se toca en este incremento).

### `technicalServicesAdmin/services.js` (store)
CRUD de Service/Image/Variant, patron BFF limpio (`Vue -> store -> dashboard
BFF`, cero ORM directo). `uploadImage()` ya tiene el override explicito de
`Content-Type: multipart/form-data` que pide FASE 5 del plan -- **ya
resuelto, no requiere trabajo adicional** salvo extender el payload cuando
se agreguen caption/description/display_order (FASE 4).

### `ServiceDetailView.vue` -- **no existe, confirmado de nuevo**
Ya documentado como codigo muerto eliminado el 2026-08-05
(`technical_services/CLAUDE.md`, nota "[CORREGIDO 2026-08-05]"). El archivo
real es `frontend/src/views/customer/detail/ServiceDetailContent.vue`.

### `components/services/detail/*`
Solo existe **1 archivo real**: `ServiceProfessionals.vue`. Los componentes
que el plan de FASE 7 menciona (`ServiceGallery`, `ServiceFeatureList`,
`ServiceScopeList`, `ServiceSpecificationTable`, `ServiceFAQAccordion`,
`ServiceReviews`) **no existen como archivos separados** -- fueron
generalizados a componentes compartidos (`BaseGallery`, `BaseAccordion`,
`BaseReviews` en `components/base/`, reusados tambien por Shop/Renting)
durante la reingenieria SDP del 2026-08-05. El plan de FASE 7 debe
reformularse contra esta arquitectura real, no contra la asumida.

### `dashboard/api/views.py` / `admin_orchestrators.py` (recorte Services)
`AdminServiceViewSet` expone `add_image`/`delete_image`/`set_primary_image`/
`duplicate` sobre `ServiceAdminOrchestrator`. Patron BFF respetado. Hallazgo
menor: `duplicate()` (linea ~1166) copia `name/description/category/level/
is_active/is_featured/is_purchasable` + la variante default, pero **no**
copia `scope/warranty/coverage_notes` ni los campos SEO -- gap menor, fuera
del alcance de este plan pero anotado para referencia futura.

### `technical_services/models.py`
- `TechnicalService`: `vendor, category, level, name, slug, description,
  scope, warranty, coverage_notes, is_active, is_featured, is_purchasable,
  meta_title, meta_description, meta_keywords, og_image`.
- `ServiceVariant`: `service, sku, estimated_hours, complexity_factor,
  fixed_price, pricing_strategy, min_duration, max_duration,
  simultaneous_capacity, is_default, is_active, pricing_source,
  manual_unit_price, manual_project_price` (los ultimos 3, Manual Pricing
  Engine, campana previa de esta misma sesion).
- `ServiceImage`: **solo** `service, variant(opcional), image, alt_text,
  is_primary`. Confirma la brecha que pide cerrar FASE 4 del plan: no tiene
  `caption`, `description` ni `display_order`. `shop.ProductImage` (el
  "espejo" habitual) tampoco los tiene -- usa `image_type` (Principal/
  Galeria/Detalle/Ejemplo) en su lugar, un enfoque distinto. Cualquier
  implementacion de FASE 4 sera, por tanto, genuinamente nueva (no una
  replica de un patron ya existente en otro modulo).

### `selectors.py` / `commands.py` / `serializers.py`
Ya documentados en profundidad por la campana "Manual Pricing Engine"
(misma sesion, ver `MANUAL_PRICING_FASE*.md`) -- `ServiceSelector.
get_variant_quotation()`, `ServiceCommands.request_service()`,
`ServicePricingCommands`, `OrderPricingCommands` no cambiaron desde
entonces y no se re-auditan linea por linea aqui.

## Confirmacion positiva: separacion CATALOGO vs OPERACION ya existe

El plan pide explicitamente verificar que "tecnico asignado, agenda,
operacion, desplazamiento, estado operativo" no esten mezclados con la
creacion del catalogo. **Verificado: no lo estan.** Ninguna de las 15
pestanas de `ServiceForm.vue` toca `ServiceOperation` ni conceptos
operativos -- ese dominio vive 100% separado en
`technical_services/services/operations.py` +
`/panel/servicios/operaciones` (`ServiceOperationBoard.vue`), ya auditado en
la campana "Manual Pricing Engine" FASE 16-19 de esta misma sesion. "Proceso
del servicio" (`ServiceProcessStep`, tab "Proceso") podria sonar operativo
por el nombre pero es contenido comercial (pasos que ve el cliente en la
pagina publica), no estado operativo real -- no viola el principio.

## No auditado en profundidad en este incremento

- `ServiceRequestWizard.vue` -- confirmado por `CLAUDE.md` que tiene sidebar
  de resumen (`ServiceRequestSummary.vue`) y usa `CheckoutStepper.vue`
  compartido; no se releyo linea por linea (sin cambios reportados desde su
  ultima auditoria, 2026-07-18).
- Testing de performance/responsive/comprehension de usuario (FASE 11-13 del
  plan) -- requieren medicion real con herramientas de profiling y/o
  usuarios reales, fuera del alcance de una auditoria de codigo.

## Siguiente paso

FASE 1 del plan: matriz de campos con clasificacion KEEP/MERGE/MOVE/HIDE/
REMOVE/NEW. Ver `SERVICES_FIELD_MATRIX_2026-08-14.md`. Ningun campo se
elimina en este incremento (instruccion explicita del plan: "No borrar
todavia").
