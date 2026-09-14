# Sprint 6 — Evaluación + ejecución parcial, 2026-08-05

**Estado: la propuesta de Review (§1.3) fue aprobada y ejecutada el mismo día -- ver
"Ejecución" al final del documento. `technical_services` en sub-paquetes (§2) sigue sin
ejecutar.** El usuario pidió
explícitamente evaluar Sprint 6 del roadmap de la
[auditoría transversal](INFORME_AUDITORIA_TRANSVERSAL_2026-08-05.md) sin ejecutarlo — este
documento es el resultado de esa evaluación (2 agentes de investigación en paralelo, solo
lectura) más el análisis y la propuesta concreta. Sirve como base para una decisión de
producto posterior; no autoriza ejecución por sí mismo.

---

## 1. Unificar el modelo Review (4→1)

### 1.1 Hallazgo principal: el patrón `ContentBlockConfig` NO es el mejor ajuste aquí

El roadmap original proponía "unificar via `ContentType`, mismo patrón que `ContentBlockConfig`".
Tras investigar los 4 modelos a fondo, ese patrón es el ajuste equivocado para este caso
específico — y el ajuste correcto ya existe en el proyecto, usado en Sprint 2 para un problema
estructuralmente análogo (`AbstractCostRule`/`AbstractCostAssignment`). Razón:

- `ContentBlockConfig`/`CatalogRelation` funcionan bien con `ContentType`+`uuid` porque son
  **capas de orquestación** (orden/visibilidad) que no necesitan agregación pesada ni conservan
  el contenido real — el contenido sigue viviendo en los modelos ya existentes.
- `Review` es distinto: **es el único almacén del dato** (rating+comentario), y 2 de los 4
  dominios ya hacen **agregación a nivel de base de datos** sobre la relación inversa
  (`Avg('reviews__rating')` en Shop; una composición de 5 `Avg()` en Accounts/Contractor). Migrar
  a `ContentType`+`object_uuid` (obligatorio sin `GenericForeignKey`, regla ya establecida en el
  proyecto) **rompe esa agregación por FK inversa** — pasaría a requerir filtrar por
  `content_type`+`object_uuid` en cada query, un cambio de forma de consulta real, no cosmético,
  y pierde los accesores hoy usados activamente (`product.reviews.all()`,
  `equipment.reviews.all()`, `service.reviews.all()`, `contractor.contractor_reviews.all()` — los
  4 en uso real, no hipotético, ver §1.3).

**Comparación con el problema ya resuelto en Sprint 2:** `RentalCostRule`/`ProductCostRule`/
`ServiceCostRule` tenían la misma tensión (campos comunes + reglas de negocio/`context` distintos
por dominio) y se resolvió con una clase base abstracta (`shared.models.AbstractCostRule`), NO
con un modelo concreto único vía `ContentType` — cada dominio conserva su propio modelo (su
propia tabla, su propio FK directo, sus propias reglas), solo se factoriza la definición de
campos/comportamiento común. Ese es el patrón que de verdad aplica aquí.

### 1.2 Los 4 modelos NO son igual de unificables — `ContractorReview` es un caso aparte

| | ProductReview | EquipmentReview | ServiceReview | ContractorReview |
|---|---|---|---|---|
| Entidad calificada | Producto (catálogo) | Equipo (catálogo) | Servicio (catálogo) | **Persona** (`UserProfile`) |
| Forma del rating | 1 campo `rating` (1-5) | 1 campo `rating` (1-5) | 1 campo `rating` (1-5) | **5 campos** (calidad/puntualidad/profesionalismo/comunicación/cumplimiento) |
| `comment` | Obligatorio | Obligatorio | Obligatorio | Opcional |
| Validadores DB en rating | Sí (`MinValueValidator`/`MaxValueValidator`) | Sí | Sí | **No** (solo validación en Commands) |
| Duplicado (mismo autor, misma entidad) | Rechaza (400) | Rechaza (400) | Rechaza (400) | **Upsert** (`get_or_create` + actualiza) |
| Gate de elegibilidad | Ninguno | Debe tener alquiler `FINISHED` | Debe tener operación `CLOSED` | Ninguno (solo bloquea auto-reseña) |
| `uuid` expuesto en el serializer | Sí | Sí | Sí | **No** (usa `id`) |

`ContractorReview` no es "el mismo concepto con un FK distinto" — califica una **persona** en 5
dimensiones profesionales independientes, no un ítem de catálogo en una sola escala. Forzarlo
dentro del mismo modelo que los otros 3 exigiría o bien (a) un campo `rating` único que no
representa lo que hoy captura, o (b) un `JSONField` de ratings flexible que pierde los
validadores de rango a nivel de BD y complica cualquier agregación futura. **Recomendación:
excluir `ContractorReview` de la unificación** — es un caso genuinamente distinto, no
duplicación.

### 1.3 Propuesta concreta (para aprobación futura, no ejecutada)

**Alcance: solo los 3 reviews de catálogo** (Product/Equipment/Service), vía
`shared.models.AbstractReview` — mismo mecanismo que `AbstractCostRule`:

```python
class AbstractReview(SintelBaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.user_id} -> {self.rating}"
```

Cada dominio conserva su propio modelo concreto con su propio FK a la entidad, su propio
`related_name='reviews'` (sin cambios -- todos los accesores hoy en uso siguen funcionando
igual: `product.reviews.all()`, `Avg('reviews__rating')`, `Prefetch('reviews', ...)`), su propio
`unique_together`, y su propia regla de elegibilidad en el Commands correspondiente (el gate de
"debe haber terminado el alquiler/servicio" de Equipment/Service NO se toca ni se unifica --
sigue viviendo en cada `Commands.create_review()` como hoy). `is_verified_purchase` (Shop, campo
hoy muerto -- nunca se setea `True` en ningún lugar del código) se queda como campo propio de
`ProductReview`, no pasa a la base abstracta.

**Lo que esto NO resuelve** (y por qué no importa para el objetivo real): las 3 clases concretas
seguirían siendo 3 tablas con 3 Selectors/Commands casi idénticos (igual que
`RentalCostRule`/`ProductCostRule`/`ServiceCostRule` siguen siendo 3 tablas hoy tras Sprint 2) --
el ahorro es en la definición de campos/validación repetida (~15 líneas por modelo), no en el
número de tablas ni en unificar los endpoints. Si el objetivo real es "un solo endpoint de
reviews para las 3", eso es un problema distinto (unificación de API, no de modelo) y no está
cubierto por esta propuesta -- el roadmap original tampoco lo pedía explícitamente, solo decía
"unificar el modelo".

**Hallazgos colaterales encontrados durante la investigación** (no bloquean nada, pero vale la
pena registrarlos):

- `frontend/src/views/customer/detail/components/PublicDetailReviews.vue` es un componente
  huérfano (grep confirma: sin ninguna referencia en el resto del código), con un comentario
  literal `// TODO: Implementar endpoint de POST review` -- candidato a limpieza directa,
  independiente de esta propuesta.
- El frontend de reviews está en 3 patrones distintos hoy: `ProductDetailView.vue` tiene su
  propio bloque de reviews a medida (no usa el componente compartido), Renting/Services sí
  comparten `BaseReviews.vue`, y Contractor tiene su propio formulario de 5 dimensiones. Unificar
  el modelo backend no unifica esto solo -- sería trabajo de frontend aparte, ya cubierto en
  espíritu por el mismo Sprint 5 que se acaba de completar (aunque no se incluyó porque
  `ProductDetailView.vue`'s bloque de reviews no fue identificado como duplicado exacto en esa
  pasada).
- `helpful_count` en el DTO de reviews de Renting (`ReviewsSummaryDTO`) está hardcodeado a `0` --
  no es un campo real, es una aspiración sin implementar. No se toca aquí, solo se deja
  documentado por si alguien lo asume real más adelante.

### 1.4 Riesgo si se ejecuta

Bajo-medio, y sin período de coexistencia necesario si se sigue el patrón abstracto (a
diferencia de la propuesta original vía `ContentType`, que sí exigiría migrar datos entre tablas
y coexistencia de 2 endpoints por dominio durante la transición). Con el patrón abstracto: la
migración es aditiva/estructural (mover definiciones de campo a una clase base), Django genera
`makemigrations` sin cambios de esquema reales si los campos resultantes son idénticos a los
actuales -- mismo resultado ya verificado empíricamente en Sprint 2 (`AbstractCostRule`: 0
migraciones nuevas en los 3 dominios). Los endpoints públicos (`GET/POST .../reviews/`,
`.../review/`) no cambian de forma en absoluto.

---

## 2. Sub-paquetes internos de `technical_services`

### 2.1 Hallazgo principal: el problema está en la capa de servicios, no en el esquema de BD

La historia de migraciones (30 migraciones, `0001`→`0032`) muestra una separación limpia por FK
entre los 4 dominios propuestos:

- **Scheduling** (`WorkingSchedule`/`WorkingException`, migración `0025`) tiene **cero FK** hacia
  operaciones o pricing -- solo FK a `AUTH_USER_MODEL`.
- **Catálogo enriquecido** (7 modelos agregados en `0031`-`0032`) tiene **cero FK** fuera de
  catálogo -- todos apuntan solo a `TechnicalService`.
- **Paquetes** (`ServicePackage`+hijos, `0027`) FK limpio solo a `TechnicalService`/`ServicePackage`.
- El único acoplamiento real a nivel de esquema es `ServiceOperation.availability_slot` →
  `accounts.ProfessionalAvailability` (app externa, ni siquiera hacia el propio scheduling interno
  de `technical_services`).

**El enredo real vive en `technical_services/services/selectors.py` (439 líneas) y
`services/commands.py` (894 líneas)** -- ambos mezclan las 4 categorías en una sola clase/archivo
(ej. `ServiceSelector.get_variant_quotation()` es un método de cálculo de precio completo viviendo
dentro de un selector nominalmente "de catálogo"; `ServiceCommands.request_service()` toca las 4
categorías más `accounts`/`orders`/`notifications` en un solo método). Esto confirma la
sospecha original de la auditoría, pero el detalle importa para dimensionar el esfuerzo real: **no
es solo mover archivos, es refactorizar 2 archivos grandes que mezclan responsabilidades a nivel
de método, no solo de import.**

### 2.2 Inventario (34 modelos, `models.py` de 1083 líneas, sin paquete `models/` aún)

| Categoría | Modelos | Cantidad |
|---|---|---|
| Catálogo | `ServiceCategory`, `ServiceLevel`, `TechnicalService`, `ServiceVariant`, `ServiceImage`, `ServiceReview`, `ServiceFAQ`, `ServiceMarketing`, `ServiceIncludedItem`, `ServiceExcludedItem`, `ServiceRequirement`, `ServiceSpecificationGroup`, `ServiceSpecification`, `ServiceDocument`, `ServiceVideo`, `ServiceProcessStep` | 16 |
| Pricing | `ServiceConfiguration`, `ServiceCostRule`, `ServiceCostAssignment`, `ServicePriceHistory` | 4 |
| Scheduling | `ServiceBooking`, `WorkingSchedule`, `WorkingException` | 3 |
| Operaciones (FSM) | `ServiceOperation`, `ServiceOperationEvent`, `ServiceAttachment` | 3 |
| Paquetes (dominio propio) | `ServicePackage`, `PackageIncludedItem`, `PackageAdditionalCost`, `ServiceRequestPackage`, `ServiceRequestAdditionalCost` | 5 |
| Sin encaje limpio (ver abajo) | `ServiceMaterial`, `OrderServiceDetail`, `OrderServiceTimeline` | 3 |

**Los 3 "sin encaje limpio" necesitan una decisión explícita antes de mover nada:**
- `ServiceMaterial` -- forma de catálogo (fila hija de `ServiceVariant`) pero existe solo para
  alimentar el cálculo de costo de materiales (`material_cost` en pricing). Candidato más
  probable: catálogo (es donde vive su FK), consumido por pricing (igual que hoy).
- `OrderServiceDetail`/`OrderServiceTimeline` -- snapshot comercial de una orden pagada, con
  campos de agenda (`booked_slot_id`) y un timeline pre-FSM que se superpone conceptualmente con
  `ServiceOperationEvent`. Son más viejos que el FSM (`ServiceOperation`, migración `0023`) --
  probablemente vestigios de una fase anterior a la introducción del FSM. Antes de mover estos 2
  a cualquier sub-paquete, vale la pena investigar aparte si `OrderServiceTimeline` sigue
  cumpliendo una función que `ServiceOperationEvent` no cubra ya, o si es codigo parcialmente
  redundante -- esa es una pregunta de negocio/arquitectura distinta a la reorganización de
  archivos, y no se responde en esta evaluación.

### 2.3 Superficie externa (18 apps/módulos externos importan de `technical_services`)

La mayoría importa `technical_services.models` directo (sobre todo `ServiceVariant`/
`TechnicalService`/`ServiceCategory`, los modelos de catálogo más referenciados -- `cart`,
`orders`, `marketing`, `quotes` todos tienen FK o referencian `ServiceVariant`) o pasa por el
barril `technical_services/services/__init__.py` (`from technical_services.services import
ServiceSelector`, 8+ call sites). Unos pocos hacen import profundo directo a submódulos
específicos (`services.pricing`, `services.catalog`, `services.selectors`, `services.summary`,
`services.commands`) -- esos sí necesitarían actualizar su ruta de import si el archivo destino
cambia de ubicación.

**Implicación práctica:** si el reordenamiento preserva el barril (`services/__init__.py`
sigue re-exportando todo, solo cambia DE DÓNDE lo importa internamente), la mayoría de los 18
callers externos no necesita ningún cambio. Solo los imports profundos (`services.pricing`,
`services.catalog`, etc. -- confirmados ya "limpios" de una sola categoría, ver abajo) necesitan
actualizarse, y son pocos.

### 2.4 Qué ya está limpio vs. qué requiere refactor real

**Ya son de una sola categoría (mover de archivo sin tocar lógica):**
`services/pricing.py`, `services/catalog.py`, `services/marketing.py` (catálogo),
`services/calculator.py` -- estos 4 se pueden trasladar a sus sub-paquetes destino como
`mv` conceptual, sin reescribir nada.

**Mezclan categorías, requieren separar métodos (no solo mover el archivo):**
`services/selectors.py` (catálogo + pricing + scheduling en una sola clase/archivo),
`services/commands.py` (las 4 categorías, es el archivo más grande y más mezclado -- 894
líneas), `services/summary.py` (catálogo + scheduling, pequeño). `services/technician_availability.py`
y `services/calendar.py` (scheduling) leen `ServiceOperation` (operaciones) directamente y una
función privada compartida (`_visit_window`) vive dentro de `services/operations.py` -- esa
dependencia cruzada scheduling→operations es real y tendría que resolverse (ej. moviendo
`_visit_window` a un módulo neutral) antes de separar limpiamente esos 2 paquetes.

### 2.5 Estimación de esfuerzo (sin ejecutar)

**Alto, tal como decía el roadmap original, confirmado ahora con evidencia en vez de estimación
genérica:**
1. Convertir `models.py` en paquete `models/` (catalog.py/pricing.py/scheduling.py/
   operations.py/packages.py) -- mecánico, bajo riesgo, mismo patrón ya usado por `renting/models/`
   en este mismo proyecto.
2. Decidir el encaje de los 3 modelos sin categoría clara (`ServiceMaterial`,
   `OrderServiceDetail`, `OrderServiceTimeline`) -- requiere una conversación de arquitectura
   aparte, no es mecánico.
3. Separar `services/selectors.py` y `services/commands.py` en sus categorías -- **el grueso real
   del esfuerzo**, es refactor de lógica (extraer métodos, no solo archivos), del mismo tipo (pero
   mayor escala) que el trabajo ya hecho en Sprint 3 sobre `quotes/services/commands.py`.
4. Resolver la dependencia cruzada scheduling↔operations (`_visit_window`).
5. Actualizar los pocos imports profundos externos identificados en §2.3.
6. Suite de tests ya existe parcialmente separada por categoría (`tests_operations.py`,
   `tests_packages.py`, `tests_technician_availability.py` ya son archivos propios) -- reduce el
   riesgo de regresión silenciosa, pero `tests.py` (918 líneas) sigue siendo genérico y cubre
   catálogo+pricing+legacy mezclado.

**No urgente** (coincide con la conclusión original del roadmap): es un problema de
mantenibilidad a largo plazo, no un riesgo de datos ni de contrato público -- ningún endpoint ni
modelo cambia de comportamiento, solo la organización interna de archivos Python.

---

## 3. Recomendación

Ninguna de las 2 piezas de Sprint 6 se ejecutó en esta pasada (el usuario pidió explícitamente
solo evaluar). Si se decide avanzar más adelante:

- **Review**: ejecutar la versión acotada (§1.3, solo Product/Equipment/Service vía
  `AbstractReview`, excluyendo `ContractorReview`) es de esfuerzo bajo y riesgo bajo-medio --
  comparable a Sprint 2. Se puede aprobar como un sprint independiente sin esperar a decidir sobre
  `technical_services`.
- **`technical_services`**: requiere primero una decisión de negocio sobre los 3 modelos sin
  encaje claro (§2.2) antes de poder dimensionar el esfuerzo final con precisión, y el trabajo
  real (separar `selectors.py`/`commands.py`) es sustancialmente mayor que "mover archivos" --
  encaja mejor como su propio sprint dedicado, no como continuación directa de este roadmap.

---

## 4. Ejecución (§1.3) — 2026-08-05

Usuario aprobó explícitamente ejecutar la propuesta acotada de §1.3 el mismo día de la
evaluación. Ejecutado completo:

- ✅ **`shared.models.AbstractReview`** (nuevo) -- `user`/`rating` (con
  `MinValueValidator`/`MaxValueValidator`)/`comment`, mismo mecanismo que `AbstractCostRule`
  (Sprint 2). `ProductReview`/`EquipmentReview`/`ServiceReview` heredan de ella; cada una
  conserva su propio FK a la entidad (`related_name='reviews'`, sin cambios), su propio
  `unique_together`, su propio `Meta.ordering` (solo `EquipmentReview` lo tenía), y sus campos
  propios (`ProductReview.is_verified_purchase`). `user` se redeclara en cada subclase para
  preservar su `related_name` específico (`reviews`/`equipment_reviews`/`service_reviews` --
  distintos por dominio, ya documentado en §1.3). `ContractorReview` NO se tocó, tal como
  recomendaba la evaluación.
- ✅ **Verificación**: `manage.py check` limpio, `makemigrations --check` sin cambios (0
  migraciones, confirmado -- mismo resultado que `AbstractCostRule` en Sprint 2). Verificado
  manualmente en shell para los 3 modelos (creación, `entidad.reviews.all()`,
  `Avg('rating')`, presenter de Renting) -- todo idéntico al comportamiento pre-refactor.
  Suites: `shop`+`technical_services` 144/144, `renting.tests_catalog` 15/15 (incluye
  `EquipmentReviewFlowTestCase`, el flujo HTTP completo end-to-end).
- ⚠️ **Hallazgo colateral real, no causado por este cambio**: al correr
  `renting.tests_presenters` se encontraron 9 fallos (3 failures + 6 errors) previamente
  enmascarados por el bug de `vendor_id` ya corregido por separado (sesión de background
  aparte) -- incluye un `EquipmentReview.objects.create(..., is_active=True)` que **nunca fue
  un campo válido** en ese modelo, ni antes ni después de este cambio (confirmado
  verificando manualmente que la lógica de reviews funciona correctamente sin ese kwarg
  inválido). Reportado aparte como tarea de background (`task_0898a71a`), no se tocó aquí --
  fuera de alcance de esta unificación.

**No ejecutado:** `technical_services` en sub-paquetes (§2) -- sigue a la espera de la
decisión de negocio sobre los 3 modelos sin encaje claro, tal como recomendaba §3.
