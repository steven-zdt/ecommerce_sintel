# ARQUITECTURA COMPLETA - MÓDULO QUOTES

## 📋 Descripción General

El módulo **Quotes** cubre dos flujos distintos que conviven en el mismo
modelo `Quotation`:

1. **Flujo catálogo/personalizado (legado)**: un asesor arma una cotización
   directamente desde el panel admin agregando productos del catálogo
   (`shop.ProductVariant`), servicios técnicos (`technical_services.ServiceVariant`)
   o líneas personalizadas, con precios inmediatos.
2. **Constructor de Cuestionarios Técnicos (flujo principal, `/cotizar`)**:
   el administrador diseña **Plantillas** de captura de requerimiento
   (sin precios). Un cliente **autenticado** responde el cuestionario de una
   plantilla publicada y el sistema crea una **Solicitud de Cotización**
   (`Quotation` en estado `RECIBIDA`, sin precios ni cálculos). Un asesor
   comercial revisa esa solicitud, le agrega productos/servicios con precio
   y la avanza por un flujo de estados hasta enviarla al cliente.

**Separación de conceptos clave (pedida explícitamente por el negocio):**

- **Plantilla** (`QuoteTemplate`) ≠ Solicitud ≠ Cotización. Una plantilla es
  un modelo de captura de información, no un presupuesto.
- **Solicitud de Cotización**: resultado de que un cliente complete una
  plantilla. Solo contiene respuestas — nunca precios, productos ni
  cálculos.
- **Cotización**: la elabora después un asesor comercial usando la
  información capturada en la solicitud, con las herramientas del flujo
  catálogo/personalizado ya existentes (`add-item`, `add-service`).

**Jerarquía real de taxonomía de plantillas** (no catálogos sueltos):

```
Tipo de Servicio
   └─ Categoría          (pertenece a un Tipo de Servicio)
        └─ Subcategoría  (pertenece a esa Categoría)
             └─ Tipo de Instalación   (opciones propias de esa Subcategoría,
                                        ej. Altura doble, Confinamiento)
```

**Módulos de una plantilla**: toda plantilla se configura con tres módulos
segmentados — **Equipos**, **Materiales**, **Mano de Obra** — cada uno un
contenedor independiente de preguntas dinámicas (26 tipos de dato soportados)
que el administrador define y el cliente responde.

**Conceptos clave:**
- **Snapshot pattern**: en el flujo catálogo/personalizado, `QuotationItem`/
  `QuotationService`/`QuotationMaterial` capturan precios inmutables al crear.
- **Sin motor de cálculo**: el motor de reglas y cálculo automático de mano
  de obra que existió brevemente en esta app fue **eliminado por decisión
  explícita del negocio** — el cliente nunca ve precios ni estimaciones.
- **Modelo genérico + discriminador `kind`/`module_type`**: en vez de
  triplicar modelos casi idénticos, `QuoteTemplateModule` (Equipos/
  Materiales/Mano de Obra) y `QuoteTemplateAttribute` (Tipo de Servicio/
  Instalación/Sistema) usan un solo modelo con un campo discriminador —
  mismo patrón repetido dos veces en esta app.
- **Auditoría append-only**: `QuotationTimeline` registra cada cambio de
  estado de una solicitud (mismo patrón que `technical_services.OrderServiceTimeline`).
- **Soft delete**: todos los modelos heredan de `SintelBaseModel`
  (`uuid`, `created_at`, `updated_at`, `is_deleted`).
- **Service Layer**: Commands (escritura) + Selectors (lectura read-only),
  sin ORM directo en las vistas ni en el BFF admin (`dashboard/`).

---

## 📁 Estructura de Directorios

```
quotes/
├── __init__.py
├── apps.py
├── models.py                        # Todos los modelos (ver sección Modelos)
├── admin.py
├── urls.py
│
├── api/
│   ├── views.py                     # QuotationViewSet, QuoteTemplateCategoryViewSet,
│   │                                 # QuoteTemplateSubcategoryViewSet, QuoteTemplateViewSet
│   ├── serializers.py               # Output + Input serializers, ~25 clases
│   └── urls.py                      # Router público: quotations/, quote-template-categories/,
│                                     # quote-template-subcategories/, quote-templates/
│
├── services/
│   ├── __init__.py                  # Exports de Commands + Selectors + PDFService
│   ├── commands.py                  # QuotationBuilder, QuotationReviewCommands,
│   │                                 # *Commands por cada entidad de plantilla
│   ├── selectors.py                 # *Selector por cada entidad, read-only
│   └── pdf_service.py               # PDFService.generate_quotation_pdf() (ReportLab)
│                                     # [2026-07-12] titulo del PDF ya no hardcodea "SINTEL" --
│                                     # lee organization.Company.trade_name (OrganizationSelector),
│                                     # ver MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md
│
└── migrations/
    ├── 0001_initial.py … 0009_...   # Flujo catálogo/personalizado original
    ├── 0010…0014                    # Fase CPQ inicial (plantillas, preguntas, allow_other)
    ├── 0015_rename_equipment_to_module.py   # QuoteTemplateEquipment -> QuoteTemplateModule
    ├── 0016_subcategory_and_question_fields.py
    ├── 0017_remove_calc_engine_models.py    # Elimina QuoteRule* y QuoteTemplateMaterial
    ├── 0018_quotation_status_rework.py      # 10 estados nuevos + remap de datos
    ├── 0019_quotationtimeline.py
    ├── 0020_alter_quotation_template_and_more.py
    ├── 0021_quotetemplateattribute_and_more.py   # Catálogo Tipo Servicio/Instalación/Sistema
    └── 0022_remove_quotetemplate_service_type_and_more.py  # Jerarquía real (service_type derivado)
```

**Nota histórica**: `quotes/services/rule_engine.py` y `quotes/services/labor_engine.py`
existieron en una fase intermedia de este proyecto (motor de reglas +
cálculo automático de mano de obra) y **fueron eliminados por completo** —
no reintroducir sin pedido explícito del negocio.

---

## 🏗️ Modelos de Datos

### Taxonomía de plantillas

```python
class QuoteTemplateAttribute(SintelBaseModel):
    """Catalogo generico: Tipo de Servicio / Tipo de Instalacion / Tipo de Sistema."""
    kind = CharField(choices=['SERVICE_TYPE', 'INSTALLATION_TYPE', 'SYSTEM_TYPE'])
    name = CharField(max_length=100)
    slug = SlugField()  # unique_together (kind, slug)
    subcategory = FK('QuoteTemplateSubcategory', null=True, blank=True, on_delete=CASCADE)
    # ^ solo se usa cuando kind=INSTALLATION_TYPE: a que subcategoria pertenece
    icon, description, display_order, is_active

class QuoteTemplateCategory(SintelBaseModel):
    name = CharField(unique=True)
    slug = SlugField(unique=True)
    service_type = FK(QuoteTemplateAttribute, null=True, blank=True, on_delete=SET_NULL,
                       limit_choices_to={'kind': 'SERVICE_TYPE'})
    icon, description, display_order, is_active

class QuoteTemplateSubcategory(SintelBaseModel):
    category = FK(QuoteTemplateCategory, on_delete=CASCADE, related_name='subcategories')
    name = CharField()
    slug = SlugField()  # unique_together (category, slug)
    icon, description, display_order, is_active

class QuoteEquipmentType(SintelBaseModel):
    """Catalogo reutilizable de tipos de equipo (Camara IP, NVR, Panel, Sensor...).
    Solo se usa dentro de modulos EQUIPMENT."""
    name, slug, icon, description, display_order, is_active
```

### Plantilla y sus módulos

```python
class QuoteTemplate(SintelBaseModel):
    category = FK(QuoteTemplateCategory, null=True, blank=True, on_delete=SET_NULL)
    subcategory = FK(QuoteTemplateSubcategory, null=True, blank=True, on_delete=SET_NULL)
    # service_type NO es un campo propio — se deriva de category.service_type
    installation_type = FK(QuoteTemplateAttribute, null=True, blank=True, on_delete=SET_NULL,
                            limit_choices_to={'kind': 'INSTALLATION_TYPE'})
    system_type = FK(QuoteTemplateAttribute, null=True, blank=True, on_delete=SET_NULL,
                      limit_choices_to={'kind': 'SYSTEM_TYPE'})
    name = CharField()
    slug = SlugField(unique=True)
    code = CharField(unique=True, null=True)      # autogenerado si no se manda, ej. "CCTV-001"
    description, service_type_free_text=None (no existe, ver arriba)
    version = PositiveIntegerField(default=1)
    is_published = BooleanField(default=False)     # solo publicadas se ven en /cotizar
    display_order, is_active

class QuoteTemplateModule(SintelBaseModel):
    """Equipos / Materiales / Mano de Obra — mismo modelo, module_type distinto."""
    template = FK(QuoteTemplate, on_delete=CASCADE, related_name='modules')
    module_type = CharField(choices=['EQUIPMENT', 'MATERIALS', 'LABOR'])
    equipment_type = FK(QuoteEquipmentType, null=True, blank=True)  # solo si module_type=EQUIPMENT
    name, description = CharField(), TextField()
    unit, min_quantity, max_quantity  # solo tienen sentido para EQUIPMENT
    is_required, display_order, is_active

class QuoteQuestion(SintelBaseModel):
    module = FK(QuoteTemplateModule, on_delete=CASCADE, related_name='questions')
    key = SlugField()  # unique_together (module, key), autogenerado desde label
    question_type = CharField(choices=[26 tipos, ver abajo])
    label, description, help_text, placeholder
    is_required, is_visible, is_active
    default_value, unit, group
    min_value, max_value, validation_regex
    table_columns = JSONField(default=list)   # solo para question_type=TABLE
    allow_other = BooleanField(default=False) # agrega opcion "Otro" en SELECT/RADIO
    display_order

class QuoteQuestionOption(SintelBaseModel):
    question = FK(QuoteQuestion, on_delete=CASCADE, related_name='options')
    label, value, display_order, is_active
```

**26 tipos de pregunta soportados** (`QuoteQuestion.QUESTION_TYPE_CHOICES`):
`TEXT, TEXTAREA, NUMBER, DECIMAL, CURRENCY, BOOLEAN, DATE, TIME, SELECT,
MULTISELECT, RADIO, CHECKBOX, IMAGE, FILE, SIGNATURE, GPS, ADDRESS, EMAIL,
PHONE, NIT, CC, COLOR, SLIDER, TABLE, DYNAMIC_LIST, AUTOCOMPLETE`.

### Solicitud de Cotización / Cotización (`Quotation`)

```python
class Quotation(SintelBaseModel):
    STATUS_CHOICES = (
        'BORRADOR', 'RECIBIDA', 'EN_REVISION', 'PENDIENTE_INFORMACION',
        'COTIZADA', 'ENVIADA', 'ACEPTADA', 'RECHAZADA', 'VENCIDA', 'CANCELADA',
    )
    status = CharField(choices=STATUS_CHOICES, default='BORRADOR')

    # Flujo catalogo/personalizado (legado, sin cambios)
    subtotal_products, subtotal_services, subtotal_rentals, total_amount
    is_custom = BooleanField(default=False)
    notes = TextField(blank=True)
    user = FK(AUTH_USER_MODEL, null=True, blank=True, related_name='quotations')

    # Cuestionario tecnico
    template = FK(QuoteTemplate, null=True, blank=True, on_delete=SET_NULL, related_name='quotations')
    answers = JSONField(default=dict)  # {"<module_uuid>": {"<question_key>": valor}}

    # Datos del destinatario (propio usuario o tercero con NIT/CC)
    client_name, client_email, valid_until
    company, document_type[NIT|CC], document_number, phone
    city, department, address, gps_location, project_name

class QuotationTimeline(SintelBaseModel):
    """Historial append-only de cambios de estado."""
    quotation = FK(Quotation, on_delete=CASCADE, related_name='timeline_events')
    status = CharField(choices=Quotation.STATUS_CHOICES)
    notes = TextField(blank=True)
    changed_by = FK(AUTH_USER_MODEL, null=True, blank=True)

class QuotationAttachment(SintelBaseModel):
    quotation = FK(Quotation, on_delete=CASCADE, related_name='attachments')
    file = ImageField()
    note = CharField(blank=True)  # "<module_uuid>__<question_key>" para respuestas tipo archivo
```

### Ítems del flujo catálogo/personalizado (legado, sin cambios)

`QuotationItem` (snapshot de `shop.ProductVariant` o `QuoteProductVariant`),
`QuotationService` (snapshot de `technical_services.ServiceVariant` o
servicio personalizado), `QuotationMaterial` (snapshot de material dentro
de un servicio), `QuotationRentalItem` (snapshot de `renting.EquipmentVariant`),
`QuotationItemCostSnapshot` (breakdown de costos adicionales aplicados a un
item), `QuoteProduct`/`QuoteProductVariant` (productos custom fuera del
catálogo). Todos con el mismo Snapshot Pattern documentado en la versión
anterior de este archivo — no se tocaron en esta refactorización.

---

## 🏗️ Diagrama: ciclo de vida completo

```
ADMINISTRADOR (/panel/cotizaciones)
   │
   ├─ Catálogos: crea Tipo de Servicio → Categoría (con ese tipo) →
   │  Subcategoría → Tipo de Instalación (scoped a esa subcategoría) →
   │  Tipo de Sistema → Tipo de Equipo
   │
   ├─ Plantillas: crea Plantilla (Categoría + Subcategoría; Tipo de
   │  Servicio se hereda; código autogenerado) → configura sus 3 módulos
   │  (Equipos/Materiales/Mano de Obra) con preguntas dinámicas →
   │  Vista previa (sin cálculo, solo layout) → Publica
   │
   ▼
CLIENTE (/cotizar — requiere login)
   │
   ├─ Paso 0 Destinatario: "Para mí" (autocompleta desde su perfil,
   │  email readonly) o "Para un tercero" (NIT empresa / CC persona natural)
   ├─ Paso 1 Plantilla: Categoría → Subcategoría → Plantilla (drill-down)
   ├─ Pasos 2-4: Equipos → Materiales → Mano de Obra (preguntas dinámicas,
   │  sin precios visibles en ningún momento)
   ├─ Paso 5 Resumen: recap de solo lectura → "Enviar solicitud"
   │
   ▼
POST quotes/quotations/from-template/  (IsAuthenticated)
   │  Valida: destinatario con documento (NIT/CC) obligatorio,
   │  Tipo de Instalación debe pertenecer a la Subcategoría elegida
   ▼
Quotation(status=RECIBIDA) + QuotationTimeline inicial
   │
   ▼
ASESOR COMERCIAL (panel admin → RequestViewer.vue)
   │  Ve respuestas agrupadas por módulo, historial de estados
   ├─ change-status → EN_REVISION / PENDIENTE_INFORMACION
   ├─ add-item / add-service → agrega precios reales (reusa el motor
   │  de precios del flujo catálogo/personalizado)
   ├─ change-status → COTIZADA → ENVIADA
   │
   ▼
download_pdf (AllowAny): sin items aún → PDF "Requerimiento del Cliente"
                          con items/servicios → PDF de cotización con precios
```

---

## 🌐 API pública (`quotes/api/`, prefijo `/api/v1/quotes/`)

| Endpoint | Método | Permiso | Propósito |
|---|---|---|---|
| `quote-template-categories/` | GET | AllowAny | Listado de categorías |
| `quote-template-subcategories/?category=<uuid>` | GET | AllowAny | Subcategorías de una categoría |
| `quote-templates/` | GET | AllowAny | Listado liviano (solo publicadas y activas) |
| `quote-templates/<uuid>/` | GET | AllowAny | Árbol completo: módulos → preguntas → opciones |
| `quotations/` | GET/POST/PATCH/DELETE | IsAuthenticated | Flujo catálogo/personalizado (legado) |
| `quotations/from-template/` | POST | **IsAuthenticated** | Crea la Solicitud de Cotización — exige `document_type`/`document_number` |
| `quotations/<uuid>/send/` | POST | IsAuthenticated | Marca ENVIADA y dispara email async |
| `quotations/<uuid>/add_attachment/` | POST | IsAuthenticated | Adjuntos manuales |
| `quotations/<uuid>/download_pdf/` | GET | AllowAny | PDF (requerimiento o cotizado, según tenga items) |

El cliente **no envia** `installation_type`/`subcategory` en `from-template`
— hereda ambos del `template` elegido. La jerarquia se garantiza antes, en
`QuoteTemplateInputSerializer.validate()` (API admin, `dashboard/`): al
crear/editar una plantilla, rechaza (400) si el `installation_type` no
pertenece a la `subcategory` seleccionada. Es una validacion de
**configuracion** (tiempo de admin), no de **envio** (tiempo de cliente) —
backend como fuente de verdad igual se cumple, solo que en el momento en
que se define la plantilla, no en el momento en que el cliente la responde.

Ademas, `from-template` solo acepta plantillas `is_published=True` **y**
`is_active=True` (queryset del campo `template` en
`QuotationFromTemplateInputSerializer`) — un cliente autenticado no puede
crear una solicitud contra un borrador ni contra una plantilla desactivada,
aunque conozca su UUID (corregido 2026-07-22, hallazgo QA E2E HG-01).

## 🌐 API admin (`dashboard/api/`, prefijo `/api/v1/dashboard/`)

Todas con `permission_classes=[IsAuthenticated, IsAdminUser]`, patrón
`viewsets.ViewSet` con métodos explícitos delegando a
`dashboard/services/admin_orchestrators.py::QuoteTemplateAdminOrchestrator`
/ `QuotationAdminOrchestrator` (sin ORM directo en la vista):

`quote-template-categories/`, `quote-template-subcategories/?category=`,
`quote-template-attributes/?kind=&subcategory=`, `quote-templates/`,
`quote-equipment-types/`, `quote-template-modules/?template=&module_type=`
(+ `/duplicate/`, `/reorder/`), `quote-questions/?module=`,
`quote-question-options/?question=`, `quotations/` (list/create/retrieve/
partial_update + `/change-status/`, `/add-item/`, `/add-service/`).

---

## 🖥️ Frontend

### Admin — `/panel/cotizaciones` (`frontend/src/modules/quotes/`)

`QuoteStudioView.vue` — 3 pestañas principales: **Solicitudes**
(`QuotationList.vue`, abre `RequestViewer.vue` si la fila tiene plantilla o
`QuotationDetail.vue` si es legado), **Plantillas** (`QuoteTemplateList.vue`
+ `QuoteTemplateForm.vue`), **Catálogos** (sub-pestañas en el orden de la
jerarquía: Tipo de Servicio → Categorías → Subcategorías → Tipo de
Instalación → Tipo de Sistema → Tipo de Equipo, usando
`QuoteAttributeList.vue` genérico + `QuoteTemplateCategoryList.vue` +
`QuoteTemplateSubcategoryList.vue` + `QuoteEquipmentTypeList.vue`).

`QuoteTemplateBuilder.vue` (ruta `/panel/cotizaciones/plantillas/:uuid`) —
4 pestañas: **Equipos** / **Materiales** / **Mano de Obra**
(`QuoteModuleQuestionsPanel.vue` genérico + 3 wrappers finos
`EquipmentQuestionsPanel.vue`/`MaterialQuestionsPanel.vue`/
`LaborQuestionsPanel.vue`, con `QuoteQuestionForm.vue` para el CRUD de
preguntas) y **Vista previa** (`PreviewTemplate.vue`, sin cálculo).

`RequestViewer.vue` — panel de revisión del asesor: datos del destinatario,
respuestas agrupadas por módulo, `QuotationTimeline`, cambio de estado,
formulario para agregar producto/servicio con precio, botón PDF.

Store único: `frontend/src/store/quotesAdmin.js` (Pinia).

### Cliente — `/cotizar` (`frontend/src/views/customer/quotes/`)

Ruta con `meta: { requiresAuth: true }`. `QuoteWizardView.vue` orquesta 6
pasos vía `composables/useQuoteWizard.js`:

0. `ApplicantStep.vue` ("Destinatario") — toggle Para mí (autocompleta
   desde `GET auth/profile/`, email readonly) / Para un tercero (NIT o CC
   manual).
1. `TemplateSelectStep.vue` — drill-down Categoría → Subcategoría →
   Plantilla (avanza automático al elegir tarjeta, sin botón Continuar).
2-4. `EquipmentQuestionsStep.vue` / `MaterialQuestionsStep.vue` /
   `LaborQuestionsStep.vue` — filtran `template.modules` por `module_type`
   y renderizan con `DynamicQuestionField.vue` (26 tipos).
5. `QuoteSummaryStep.vue` — recap de solo lectura, sin precios, botón
   "Enviar solicitud" → pantalla de éxito sin descarga de PDF (aún no hay
   precio).

`DynamicQuestionField.vue` es compartido entre el wizard cliente y
`PreviewTemplate.vue` del admin — un solo mapeo tipo→input, sin duplicar
lógica.

---

## 🏗️ Patrones de Diseño Utilizados

1. **Service Layer**: Commands (`services/commands.py`) para escritura,
   Selectors (`services/selectors.py`) para lectura — sin ORM directo en
   vistas ni en `dashboard/api/views.py`.
2. **Modelo genérico + discriminador**: `QuoteTemplateModule.module_type` y
   `QuoteTemplateAttribute.kind` — un modelo, varios "tipos" lógicos, para
   no triplicar CRUD/serializers/commands.
3. **Snapshot Pattern**: intacto en el flujo catálogo/personalizado
   (`QuotationItem.unit_price`, `QuotationService.labor_cost`, etc.).
4. **Auditoría append-only**: `QuotationTimeline`, un registro nuevo por
   cambio de estado, nunca se edita uno existente.
5. **Backend como fuente de verdad**: el cliente en `/cotizar` nunca ve
   precios; toda validación de integridad (destinatario obligatorio,
   Instalación debe pertenecer a la Subcategoría) se re-valida en el
   serializer del backend, no solo en el frontend.
6. **Soft delete**: `is_deleted` heredado de `SintelBaseModel` en todos los
   modelos.
7. **Transacciones atómicas**: `@transaction.atomic` en todos los Commands
   que escriben más de una tabla.

---

## 🔐 Seguridad

- `/cotizar` (frontend) exige sesión iniciada (`meta: requiresAuth`).
- `POST quotations/from-template/` exige `IsAuthenticated` en el backend
  (defensa en profundidad — no basta con el guard del frontend).
- `document_type`/`document_number` son **obligatorios** en el serializer
  de creación — ninguna solicitud se crea sin destinatario identificado.
- `download_pdf` es `AllowAny` (UUID como capability token, mismo patrón
  usado en otros flujos de pago/confirmación del proyecto).
- Todas las rutas admin (`dashboard/`) exigen `IsAuthenticated` + `IsAdminUser`.

---

## 🚀 Fuera de alcance / decisiones explícitas del negocio

- **No hay motor de cálculo automático de precios.** Existió (`QuoteRuleEngine` +
  `LaborCalculationEngine`) y fue eliminado a pedido explícito (migración
  `0017_remove_calc_engine_models.py`) — no reintroducir sin que el usuario lo
  pida de nuevo. **[Corregido 2026-08-05, auditoría transversal]** esto NO
  incluye `services/labor_conditions_evaluator.py::LaborConditionsEvaluator`
  — un evaluador distinto y más chico, agregado despues (Fase 10, plan
  "Simplificación Inteligente", 2026-07-23), que NO calcula precio: solo
  deriva de `installation_height` una bandera informativa
  (`work_at_height`) para que el asesor la vea en `QuotationSerializer.
  get_labor_analysis()` (`api/serializers.py`) y en `RequestViewer.vue`
  (frontend). Se recalcula en cada lectura, nunca se persiste. Sigue activo
  y en uso — no es código muerto, esta sección no lo mencionaba.
- **Tipo de Sistema** sigue siendo un catálogo plano, no forma parte de la
  jerarquía Tipo de Servicio → Categoría → Subcategoría → Instalación.
- No hay máquina de estados estricta para `Quotation.status` (transiciones
  libres, igual que `Order`/`RentalRequest` en el resto del proyecto).
- No hay reordenamiento drag-and-drop (se usan botones ↑/↓) — `vuedraggable`
  no está instalado en el proyecto.

---

## 📝 Resumen de la Arquitectura

| Aspecto | Detalles |
|---|---|
| **Patrón principal** | Service Layer + modelo genérico con discriminador (`kind`/`module_type`) |
| **Dos flujos** | Catálogo/personalizado (legado, con precios inmediatos) + Constructor de Cuestionarios Técnicos (principal, sin precios para el cliente) |
| **Jerarquía de taxonomía** | Tipo de Servicio → Categoría → Subcategoría → Tipo de Instalación |
| **Módulos de plantilla** | Equipos / Materiales / Mano de Obra — mismo modelo `QuoteTemplateModule` |
| **Tipos de pregunta** | 26 (`QuoteQuestion.QUESTION_TYPE_CHOICES`) |
| **Estados de Quotation** | 10: BORRADOR, RECIBIDA, EN_REVISION, PENDIENTE_INFORMACION, COTIZADA, ENVIADA, ACEPTADA, RECHAZADA, VENCIDA, CANCELADA |
| **Auditoría** | `QuotationTimeline`, append-only |
| **Auth** | `/cotizar` requiere login; `from-template` exige `IsAuthenticated` + documento obligatorio |
| **PDF** | ReportLab, rama "requerimiento" (sin precios) o rama "cotizado" (con precios), según tenga items |
| **Frontend admin** | `QuoteStudioView` (Solicitudes/Plantillas/Catálogos) + `QuoteTemplateBuilder` (Equipos/Materiales/Mano de Obra/Vista previa) + `RequestViewer` |
| **Frontend cliente** | `/cotizar`, 6 pasos: Destinatario → Plantilla → Equipos → Materiales → Mano de Obra → Resumen |

---

**Última actualización:** 2026-08-05 (corrección puntual sobre `LaborConditionsEvaluator`,
auditoría transversal — el resto del documento no se re-verificó línea por línea en esta pasada;
el cuerpo describe funcionalidad de julio/2026 sin que se haya confirmado que siga vigente en su
totalidad. Fecha anterior: 2026-07-02, ya inconsistente entonces con las migraciones 0018-0022
descritas más arriba en este mismo documento.)
