# PLAN — Auditoría Arquitectónica Transversal Enterprise Sintel ERP

**Guía única del proceso**, mismo formato que `shop/.AGENT/docs/UI_MÓDULO_SHOP.MD` y
`technical_services/.AGENT/docs/UI_MODULO_SERVICES.md`: el brief original
(`core/.AGENT/docs/auditori_responsabilidades_tranversal.md`, 14 fases) se preserva íntegro más
abajo, con el estado real anotado fase por fase.

**Diferencia clave con las 2 campañas anteriores:** este brief es explícitamente **de solo
auditoría** — "El objetivo NO es desarrollar nuevas funcionalidades" / "No realizar ninguna
modificación hasta finalizar el análisis". No se escribe código en este plan. El entregable es el
Informe Ejecutivo (Fase 14).

**Alcance:** 10 módulos nombrados explícitamente — Core, Renting, Organization, Frontend, Shop,
Services, Accounts, Payments, Notifications, Quotes. Fuente de verdad: los documentos
`ARQUITECTURA_COMPLETA_*.md` de cada módulo (ya son la fuente única de verdad establecida en este
proyecto, ver `CLAUDE.md` raíz — no se re-audita código línea por línea salvo para verificar un
hallazgo puntual de desactualización, mismo criterio ya usado en las 2 campañas anteriores donde
se detectaron docs desactualizados).

**Método de ejecución:** dado el volumen (~9500 líneas de documentación entre los 10 módulos),
Shop/Renting/Services/Frontend se auditan directamente (ya conocidos en profundidad por trabajo
reciente en esta misma sesión, incluyendo hallazgos de código muerto y docs desactualizados no
mencionados aquí de nuevo). Core/Organization/Accounts/Payments/Notifications/Quotes se auditan
vía agentes de exploración en paralelo, cada uno reportando los mismos 8 lentes (Fases 1-8) en
formato denso y estructurado para síntesis central.

---

## Estado general

| Fase | Título | Estado |
|---|---|---|
| 0 | Grafo arquitectónico | ✅ Completa |
| 1 | Auditoría de responsabilidades | ✅ Completa — 10/10 módulos |
| 2 | Inventario del dominio | ✅ Completa — 10/10 módulos |
| 3 | Auditoría de modelos | ✅ Completa — 10/10 módulos |
| 4 | Auditoría de services | ✅ Completa — 10/10 módulos |
| 5 | Auditoría de APIs | ✅ Completa — 10/10 módulos |
| 6 | Auditoría del frontend | ✅ Completa |
| 7 | Auditoría de dependencias | ✅ Completa — 10/10 módulos |
| 8 | Auditoría documental | ✅ Completa — 10/10 módulos (100% con hallazgos, ver Informe §12) |
| 9 | Propuesta de refactorización | ✅ Completa |
| 10 | Plan de implementación (roadmap) | ✅ Completa — 6 sprints |
| 11 | Matriz de impacto | ✅ Completa (integrada en Informe §14, por sprint) |
| 12 | Validación de compatibilidad | ✅ Completa — checklist en Informe §17 |
| 13 | Métricas de reducción | ✅ Completa — estimación con evidencia, ver Informe |
| 14 | Informe ejecutivo | ✅ Completa — [`INFORME_AUDITORIA_TRANSVERSAL_2026-08-05.md`](INFORME_AUDITORIA_TRANSVERSAL_2026-08-05.md) |

## Ejecución Sprint 1 (Limpieza documental) — 2026-08-05

El usuario aprobó implícitamente avanzar tras entregar el informe ("continua"). Se ejecutó
**solo la porción de corrección factual concreta** del Sprint 1 (hallazgos con evidencia
file:line ya identificados en la auditoría) — no la reorganización estructural completa
(separar referencia/changelog en 2 archivos por módulo), que queda pendiente por ser más
subjetiva y de mayor esfuerzo:

- ✅ **Quotes**: corregido el alcance de "motor eliminado por completo" — `LaborConditionsEvaluator`
  (Fase 10, 2026-07-23) es una feature distinta y activa, no el motor de precios removido. Fecha
  de "última actualización" corregida.
- ✅ **Notifications**: tabla de plantillas 13→18 slugs (agregados los 5 de `kyc`, ausentes).
  Documentadas 2 tareas Celery que ya existían en código (`send_sms_notification_task`,
  `send_whatsapp_agent_reply_task`) y no estaban en ningún lado del doc — corregida además la
  afirmación de que SMS estaba "fuera de esta entrega" (la infraestructura de código ya existe).
- ✅ **Core**: eliminadas 2 referencias a serializers que ya no existen
  (`CompanyContactInfoInputSerializer`/`SiteBrandConfigInputSerializer`, migrados a
  `organization`). Conteo de modelos 10→12 corregido en 2 lugares (incluye verificación real de
  cobertura de `signals.py`, que sí cubre los 12).
- ✅ **Renting**: corregido el hallazgo más grande de todo el audit — `RentalRequest` documentado
  con nota explícita de que el modelo real se normalizó en 4 tablas hijas (migraciones 0033-0037)
  vía fachada de propiedades. Corregido el árbol de directorios (bloque `api/` duplicado,
  `models.py` como archivo único cuando es un paquete de 11 módulos) y documentados 4 archivos
  que no aparecían en ningún lado del doc (`services/dtos.py`, `services/presenters.py`,
  `api/internal_ai.py`, `api/operation_serializers.py`). Mismo fix replicado en `renting/CLAUDE.md`.

**Actualización 2026-08-05 (tras confirmación del usuario de continuar con "Accounts/Payment"):**

- ✅ **Accounts**: extraída la sección completa "## Auditoria y Correcciones" (líneas 518-754,
  ~237 líneas, 5 entradas fechadas 2026-06 a 2026-07-09) a un archivo nuevo,
  [`accounts/.AGENT/docs/CHANGELOG_ACCOUNTS.md`](../../../accounts/.AGENT/docs/CHANGELOG_ACCOUNTS.md).
  El doc principal quedó con una nota-puntero de 6 líneas en su lugar. La sección "Política de
  arquitectura de perfiles (2026-07-05 — inmutable)", que sigue justo después y también tiene
  fecha, se dejó intacta en el doc principal — no es changelog, es la regla vigente (señal
  explícita: el propio título dice "inmutable"). Extracción mecánica limpia porque era un único
  bloque contiguo, puramente narrativo/histórico, sin mezclarse con contenido de referencia activo.

- ⚠️ **Payment: evaluado y NO restructurado — hallazgo distinto al esperado.** Se inspeccionaron
  los 7 puntos "Bug corregido"/"corregido" señalados en la auditoría (líneas ~433, 461, 533, 644,
  662, 1002-1026 de `ARQUITECTURA_COMPLETA_PAYMENT.md`). A diferencia de Accounts, **no son un
  bloque narrativo separable**: son blockquotes cortos intercalados dentro de la explicación
  técnica de POR QUÉ el código actual tiene la forma que tiene (ej. §5.1 explica por qué
  `_sync_wompi_status()` usa `wompi_id_hint` citando el bug que lo motivó; §10.6 narra 2 bugs como
  parte de la fase ADR-001 que está describiendo). Sacarlos requeriría reescribir la prosa técnica
  de referencia (no un corte-y-pega) y arriesga perder contexto del que depende la explicación
  vigente — eso excede "limpieza documental de bajo riesgo" y entra en territorio editorial. Se
  decidió NO forzar el mismo patrón mecánico que Accounts sin ese riesgo. Payment queda con su
  estructura actual; si se quiere igual una reorganización, necesita una pasada de reescritura
  deliberada (separar "qué es cierto hoy" de "por qué se llegó aquí" sin perder ninguna de las dos),
  no una extracción de bloque.

Sprints 3-6 (código, no documentación) siguen sin ejecutar — requieren aprobación explícita
antes de tocar modelos/servicios/endpoints reales, tal como pide el brief.

## Ejecución Sprint 2 (Modelos abstractos compartidos) — 2026-08-05

Usuario eligió explícitamente "Sprint 2" entre las 4 opciones de código de bajo/medio riesgo
ofrecidas. Ejecutado completo:

- ✅ **`shared.models.SingletonMixin`** (nuevo) — consolida el `save()` de 3 lineas que existía
  por separado en `organization.SingletonMixin` (original), `core.FooterCTAConfig.save()`,
  `payment.PaymentFeatureFlags.save()`, y estaba completamente AUSENTE en
  `core.AboutUsConfig`/`BrandSliderConfig` (usaban "get-or-create sin lock", con riesgo real de
  2 filas activas en escritura concurrente). **Hallazgo durante la ejecución:** el roadmap decía
  "adoptar `organization.SingletonMixin`", pero `organization.CLAUDE.md` prohibe explícitamente
  que otras apps importen sus modelos (regla SSoT), y `payment.models.PaymentFeatureFlags` ya
  documentaba por qué evitaba ese import cruzado a propósito. Se resolvió moviendo el mixin a
  `shared` (lugar ya establecido para mixins genéricos, mismo criterio que `ContentBlockConfig`)
  en vez de violar esa regla — `organization.models.SingletonMixin` ahora reexporta desde ahí.
  Adoptado en los 4 modelos objetivo (`FooterCTAConfig`, `AboutUsConfig`, `BrandSliderConfig`,
  `PaymentFeatureFlags`). `AboutUsConfig`/`BrandSliderConfig` ganaron un campo `is_active` nuevo
  (migración aditiva `core/migrations/0027_...`, aplicada) — cierra el hueco de carrera real
  que tenían.
- ✅ **`shared.models.AbstractCostRule`/`AbstractCostAssignment`** (nuevo) — consolida
  `name`/`description`/`cost_type`/`value`/`is_active`/`TYPE_FIXED`/`TYPE_PERCENTAGE`/`__str__`,
  que eran idénticos byte a byte en `RentalCostRule`/`ProductCostRule`/`ServiceCostRule`.
  Deliberadamente NO se tocó `context` (taxonomía de `CONTEXT_CHOICES` distinta por app -- Renting
  tiene DEPOSIT/INSURANCE/SURCHARGE que Shop/Services no tienen) ni `applies_globally` (Renting lo
  eliminó a propósito en la migración `0027_remove_applies_globally...`, Shop/Services lo
  conservan) -- unificar cualquiera de los dos habría sido un cambio de regla de negocio, no de
  arquitectura, fuera del alcance de este sprint.
- ✅ **Migraciones**: el refactor de `SingletonMixin`/`CostRule` en shared/organization/payment/
  renting/shop/technical_services generó **0 migraciones** (`makemigrations --dry-run` confirmó
  "No changes detected" antes del fix de Core) -- la herencia abstracta no cambia el esquema
  cuando el conjunto de campos resultante es igual. Solo `core` generó una migración real
  (aditiva, 2 columnas `is_active` nuevas), aplicada sin incidentes.
- ✅ **Verificación**: `manage.py check` limpio; `makemigrations --check` sin cambios pendientes
  en todo el proyecto; suites de `shared`/`organization`/`core`/`payment`/`renting`/`shop`/
  `technical_services` corridas (376+118 tests). 21 errores totales, **los 21 preexistentes y
  no relacionados**: 20 en `renting/tests_presenters.py` (fixture rota, `Equipment.objects.create()`
  sin el FK obligatorio `vendor`, nada que ver con CostRule) + 1 en `core/tests/
  test_models_and_signals.py` (`ModuleNotFoundError: pytest`, dependencia no instalada en el
  contenedor). Ninguno de los 2 toca código de este sprint -- confirmado leyendo ambos archivos
  (no se tocaron en este sprint) y corriendo cada suite por separado para aislar la causa. El
  hallazgo de `vendor` se reportó aparte (tarea en background, fuera de este plan). Comportamiento
  de singleton de los 3 modelos de Core y de la herencia de `AbstractCostRule` en las 3 apps
  verificado manualmente via `manage.py shell` (toggle correcto, `applies_globally` presente solo
  donde corresponde).

## Ejecución Sprint 3 (Refactor Services) — 2026-08-05

Usuario eligió explícitamente "Sprint 3" entre las opciones ofrecidas (Sprint 4/5/"ninguno"
también disponibles). Ejecutado completo, los 3 archivos del roadmap:

- ✅ **`quotes/services/commands.py`** (747→~730 líneas, pero el ahorro real es de
  duplicación, no de líneas) — se agregaron 3 helpers de módulo (`_create`/`_update`/
  `_soft_delete`, mismo criterio que `shop/services/catalog.py`) y se refactorizaron los
  create/update/delete genéricos de `QuoteTemplateCategoryCommands`,
  `QuoteTemplateSubcategoryCommands`, `QuoteTemplateAttributeCommands`,
  `QuoteEquipmentTypeCommands`, y las partes genéricas de `QuoteTemplateCommands`/
  `QuoteTemplateModuleCommands`/`QuoteQuestionCommands`/`QuoteQuestionOptionCommands` (8
  clases en total) para usarlos -- la lógica con reglas propias (generación de código,
  clonado profundo, reordenamiento por vecino) no se tocó. **Hallazgo de paso:**
  `QuoteQuestionOptionCommands.create_option` tenía un parámetro `option` nunca usado
  (verificado con grep que ningún caller lo pasaba) -- se retiró junto con el refactor.
- ✅ **`accounts/services/commands.py`** (1176→937 líneas) — se extrajo
  `AvailabilityCommands` (agenda de disponibilidad de profesionales, dominio sin relación
  con la lógica de identidad/auth del resto del archivo) a un archivo nuevo,
  `accounts/services/availability_commands.py`. `CustomerPasswordResetCommands` se quedó en
  `commands.py` a propósito -- depende directo de
  `AccountCommands._blacklist_all_refresh_tokens`, es parte del mismo dominio de auth.
  `commands.py` reexporta `AvailabilityCommands` para que los ~10 call sites existentes
  (`accounts/tasks.py`, `accounts/api/views.py`, `technical_services/services/*.py`) seguían
  funcionando sin tocarlos.
- ✅ **`payment/online/api/views.py`** (756→~340 líneas) — split en 3 archivos exactamente
  como pedía el roadmap ("ViewSet / sync / HMAC"): `_sync_wompi_status` → `sync.py`,
  `_verify_wompi_event_signature` → `signature.py`, `WompiPaymentViewSet` +
  `_build_rental_confirmation`/`_is_nequi_configured` se quedan en `views.py`. Reexportadas
  ambas funciones desde `views.py` para no romper los call sites externos (`payment/tasks.py`,
  `payment/api/views.py`, `dashboard/services/admin_orchestrators.py`).
- ✅ **Verificación**: `manage.py check` limpio, `makemigrations --check` sin cambios (0
  esperado -- Sprint 3 es reorganización de código, no de modelos). Suites completas:
  `quotes` (8/8), `dashboard`+`accounts` corridos juntos (133/133, logs confirman
  `accounts.services.availability_commands` funcionando en runtime real), `payment` (75/75
  tras un fix real necesario: 10 tests mockeaban `payment.online.api.views.http_requests.get`
  -- el path del mock tenía que actualizarse a `payment.online.api.sync.http_requests.get`
  porque el símbolo se movió; sin este fix los tests fallaban con `AttributeError` genuino,
  no con un falso positivo).

## Ejecución Sprint 4 (Refactor API — orquestadores admin) — 2026-08-05

Usuario eligió "Sprint 4" (riesgo medio) entre Sprint 4/5/"ninguno" ofrecidas. Ejecutado
completo -- los 4 orquestadores admin de catálogo hijo (Shop/Renting/Services/Packages) +
sus 4 ViewSets base:

- ✅ **Capa de servicio** (`dashboard/services/admin_orchestrators.py`, 1425→~1150 líneas):
  nueva `_GenericCatalogChildOrchestrator` (8 classmethods: `list_for_parent`/`get`/`create`/
  `update`/`delete`/`toggle_active`/`duplicate`/`reorder`) que reemplaza los 4 bloques
  idénticos (~40 líneas c/u) de `ProductCatalogChildOrchestrator`/`RentingCatalogChildOrchestrator`/
  `ServiceCatalogChildOrchestrator`/`ServicePackageChildOrchestrator`, ahora reducidos a 2
  líneas de configuración cada uno (`REGISTRY`/`PARENT_KWARG`). El nombre del metodo del
  Selector (`list_for_product`/`list_for_equipment`/etc, definido en cada `catalog.py` de
  cada app) NO se unificó -- fuera de alcance de este sprint -- se resuelve dinámicamente
  via `getattr(selector, f'list_for_{PARENT_KWARG}')`.
- ✅ **Hallazgo real corregido de paso**: `ServicePackageChildOrchestrator.duplicate()` no
  tenía el guard `hasattr(commands, 'duplicate')` que los otros 3 sí tenían (habría lanzado
  `AttributeError` en vez de un `ValueError` legible si algún recurso de Package no
  soportara duplicar) -- confirmado inofensivo unificar (ambos recursos de Package sí
  soportan duplicar hoy) y corregido con la unificación.
- ✅ **Capa de ViewSet** (nuevo `dashboard/api/catalog_child_views.py`,
  `GenericCatalogChildViewSet`) — reemplaza las 4 bases casi-idénticas
  (`ProductCatalogChildViewSet`/`EquipmentCatalogChildViewSet`/`ServiceCatalogChildViewSet`/
  `PackageChildViewSet`, ~65 líneas c/u) por 4 configuraciones de ~8 líneas
  (`orchestrator_class`/`parent_field`/`get_parent()`). Las subclases concretas de cada
  recurso (`AdminProductFeatureViewSet`, etc. — 25+ clases en total) NO se tocaron, siguen
  heredando de la misma clase base por nombre en su mismo archivo. `AdminServicePackageViewSet`
  (el ViewSet del propio ServicePackage, no uno de sus hijos) quedó fuera del alcance a
  propósito -- no es parte de los "4 orquestadores de catálogo hijo".
- ✅ **Verificación**: `manage.py check` limpio, `makemigrations --check` sin cambios (0
  esperado). Suites: `dashboard` 52/52, `shop`+`technical_services` limpias, `renting` con
  los mismos 20 errores preexistentes ya reportados (fixture de `vendor` en
  `tests_presenters.py`, nada que ver con este sprint). Además, un smoke test end-to-end
  real via `APITestCase` (creado, corrido y luego eliminado) contra los 4 dominios --
  create/list/toggle-active/duplicate/reorder/delete, los 6 verbos del contrato REST
  compartido, sobre HTTP real -- confirmó que la unificación no rompió ningún endpoint.

## Ejecución Sprint 5 (Refactor Frontend) — 2026-08-05

Usuario confirmó continuar tras Sprint 4; único sprint de bajo riesgo restante era Sprint 5
(Sprint 6 requiere decisión de producto aparte, no se ofrece como continuación directa).
Ejecutado completo -- los 3 pares de managers Vue de catálogo con duplicación real
(Specifications/Documents/Videos, cada uno con copia byte-idéntica en shop/renting/
technical_services):

- ✅ **`SpecificationsManager.vue`** y **`VideosManager.vue`** -- confirmado que las 3 copias
  eran idénticas salvo placeholders/endpoints/nombre de prop (mismo hallazgo que ya hizo el
  agente de Renting en la auditoría original). Generalizadas con prop `entity-type`
  (`'product'|'equipment'|'service'`) + `ENTITY_CONFIG`, mismo patrón que
  `ContentBlocksTab.vue` (el precedente ya sentado en esta sesión). Viven en
  `shop/catalog/` (mismo criterio que `ContentBlocksTab.vue` vive en `shop/product-form/`
  pese a ser genérico) -- Renting/Services las importan cruzado.
- ✅ **`DocumentsManager.vue`** -- **no era pura duplicación cosmética**: Renting agrega
  3 tipos de documento (`PLANO`/`FIRMWARE`/`DRIVER`) que Shop/Services no tienen, y
  Services **no tiene los campos `version`/`language` en absoluto** (`ServiceDocument` no
  los expone, a diferencia de `ProductDocument`/`RentalDocument`). Se modeló con
  `hasVersionLanguage: bool` + `documentTypes: [...]` por entidad en vez de asumir un
  shape compartido -- confirmado con diff línea a línea antes de generalizar, no por
  suposición.
- ✅ **`ProcessStepsManager.vue`** (Technical Services) -- **deliberadamente NO generalizado**:
  es un concepto exclusivo de Services (paso a paso del servicio), sin equivalente en
  Shop/Renting hoy. Documentado explícitamente en el código (comentario en `ServiceForm.vue`)
  para que quede claro que es una decisión, no un descuido.
- ✅ **6 archivos eliminados** (las copias de renting/technical_services), **3 archivos
  generalizados** en su lugar, **3 formularios actualizados**
  (`ProductForm.vue`/`RentingForm.vue`/`ServiceForm.vue`) para pasar `entity-type`+`entity-uuid`.
- ✅ **Verificación**: `npx vite build` limpio (un fix real necesario en el camino: el
  validador de `defineProps` no puede referenciar una constante del module scope por como
  Vue compila `<script setup>` -- se cambió a un array literal inline, igual que ya hacía
  `ContentBlocksTab.vue`). Verificado en navegador real contra datos de producción de
  desarrollo: los 3 dominios (Product/Equipment/Service) muestran sus placeholders/tipos de
  documento/campos version-language correctos; creación real de un grupo de especificaciones
  (POST 201 + refetch) confirmada contra `un pc` (Shop) y limpiada después. 0 errores de
  consola en los 3 formularios. **Efecto secundario detectado y corregido durante la
  verificación**: un intento manual anterior (Sprint 4, antes de cambiar a `APITestCase`)
  había dejado un producto/categoría/2 usuarios de prueba (`S4 Product`, `S4Cat`,
  `sprint4_admin@test.com`, `sprint4_vendor@test.com`) en la base de datos de desarrollo real
  -- detectado al ver el dato en la lista de productos del panel, limpiado antes de cerrar
  este sprint.

## Evaluación Sprint 6 (sin ejecutar) — 2026-08-05

Usuario eligió explícitamente "solo evaluar, no ejecutar" para Sprint 6. Investigado con 2
agentes en paralelo (solo lectura) + análisis propio -- resultado completo en
[`PLAN_SPRINT6_EVALUACION_2026-08-05.md`](PLAN_SPRINT6_EVALUACION_2026-08-05.md). Resumen de
los 2 hallazgos principales (el detalle completo, con evidencia file:line, está en ese
documento):

- **Review (4→1):** el patrón propuesto originalmente (`ContentType`, como `ContentBlockConfig`)
  NO es el mejor ajuste -- rompe la agregación por FK inversa que 2 de los 4 dominios ya usan
  (`Avg('reviews__rating')`) y pierde accesores hoy en uso real (`product.reviews.all()`, etc.).
  El patrón correcto ya existe en el proyecto: clase base abstracta (`shared.models.AbstractReview`),
  mismo mecanismo que `AbstractCostRule` (Sprint 2) para el mismo tipo de tensión. Además,
  `ContractorReview` no es el mismo concepto que los otros 3 (califica una persona en 5
  dimensiones, no un ítem de catálogo en una escala) -- se recomienda excluirlo de cualquier
  unificación futura, no forzarlo.
- **`technical_services` en sub-paquetes:** confirmado con evidencia de migraciones que el
  acoplamiento real NO está en el esquema de BD (scheduling/catálogo-enriquecido/paquetes ya
  tienen FK limpios por categoría) sino en la capa de servicios (`selectors.py`/`commands.py`
  mezclan las 4 categorías a nivel de método, no solo de import) -- el esfuerzo real es
  refactorizar esos 2 archivos (~1300 líneas combinadas), no mover archivos. 3 modelos
  (`ServiceMaterial`, `OrderServiceDetail`, `OrderServiceTimeline`) no tienen encaje limpio y
  necesitan una decisión de negocio aparte antes de poder dimensionar el esfuerzo con precisión.

**No ejecutado.** Ambos hallazgos quedan documentados como propuesta para una decisión de
producto posterior -- Review (versión acotada, sin Contractor) es de esfuerzo bajo si se
aprueba; `technical_services` requiere su propio sprint dedicado dado el esfuerzo real
identificado.

## Cierre del roadmap — 2026-08-05

Los 6 sprints del roadmap de refactorización quedaron resueltos: Sprints 1-5 ejecutados y
verificados completos, Sprint 6 evaluado (no ejecutado, a la espera de decisión de producto).
La auditoría transversal que originó todo este plan queda formalmente cerrada.

## Cierre — 2026-08-05

Auditoría completa. **0 cambios de código en este plan** (cumple el principio obligatorio del
brief — es auditoría, no implementación). Método: 4 agentes de exploración en paralelo
(Core+Organization, Accounts+Payment, Notifications+Quotes, Renting) + auditoría directa de
Shop/Technical Services/Frontend desde conocimiento verificado en esta sesión. Los 10 módulos
mostraron hallazgos con evidencia real (no suposiciones, cumpliendo el criterio de aceptación del
brief). El hallazgo más consistente: documentación desactualizada o con changelog mezclado en el
100% de los módulos auditados. El hallazgo más accionable: 3 patrones (Review, CostRule/
Assignment, singleton-config, orquestador admin de catálogo hijo) reimplementados 2-4 veces entre
módulos hermanos sin abstracción compartida, con un roadmap de 6 sprints propuesto (ninguno
ejecutado — quedan a la espera de aprobación explícita antes de tocar código, tal como pide el
brief).

(Se actualiza a ✅ a medida que cada fase se completa; las Fases 0-8 son investigación y se
consolidan directamente en el Informe Ejecutivo junto con 9-13, no como documentos separados —
el brief no pide un artefacto por fase, pide el informe final de Fase 14 con las 17 secciones.)

---

## Brief original (verbatim, con estado anotado)

> Ver `core/.AGENT/docs/auditori_responsabilidades_tranversal.md` para el texto íntegro. Este plan
> no lo duplica — lo ejecuta. El resultado se entrega en
> `core/.AGENT/docs/INFORME_AUDITORIA_TRANSVERSAL_2026-08-05.md` (Fase 14) siguiendo exactamente
> las 17 secciones pedidas.

## Principios obligatorios — checklist de cumplimiento (se valida en Fase 12)

- [ ] No modificar procesos / casos de uso / UX / contratos REST / eventos / reglas de negocio / flujos
- [ ] Cada recomendación respaldada por evidencia en la documentación analizada (no suposiciones)
- [ ] 0 cambios de código en este plan (es auditoría, no implementación)
