# ARQUITECTURA COMPLETA - MODULO RENTING

## Descripcion General

> **[AUDITADO 2026-07-23]** Esta pasada verifico el modulo completo contra `models.py`,
> `api/views.py`, `api/urls.py`, `services/` y el frontend real, y encontro un desfase grande:
> el documento no habia sido releido a fondo desde 2026-07-07/2026-07-14 pese a que el modulo
> gano un "Catalogo Enriquecido de Equipment" completo (11 modelos nuevos, migracion `0022`,
> 2026-07-16), una modalidad comercial nueva (Renting vs. Comodato, 2026-07-22), y un rediseno
> del wizard de reserva (renombrado, de 7 a 4 pasos visibles). Ver notas `[AUDITADO 2026-07-23]`
> en cada seccion afectada.

El modulo **Renting** gestiona el catalogo de equipos para alquiler y el ciclo completo de una
solicitud de renta: desde la seleccion del equipo hasta el pago via Wompi (o, desde 2026-07-22,
sin pago si la modalidad es Comodato).

**Responsabilidades principales:**
- Catalogo de equipos (Equipment, EquipmentVariant, categorias, marcas, imagenes, resenas)
- **Catalogo enriquecido de Equipment (2026-07-16):** 11 modelos administrables (incluye,
  no incluye, caracteristicas, especificaciones tecnicas, requisitos, servicios incluidos/
  opcionales, FAQ, videos, documentos descargables) — ver seccion dedicada abajo.
- **Marketing y modalidad comercial (2026-07-16/2026-07-22):** `EquipmentMarketing` (precio
  promocional, etiquetas, mensajes de conversion), `EquipmentCommercialConfig`/
  `EquipmentCommercialOption` (Renting vs. Comodato, plazos en meses).
- Configuracion de costos logisticos por equipo (EquipmentLogisticsConfig)
- Wizard de reserva de 4 pasos visibles (`RentalBookingWizard.vue`, antes `RentalRequestWizard.vue`
  con 7 pasos — ver seccion "Wizard Frontend")
- Calendario de disponibilidad por fechas (RentalPeriod) + bloqueos manuales (EquipmentBlock)
- Verificacion de disponibilidad en tiempo real (check-availability/availability/calendar/timeline)
- Calculo de costos: base + logistica + IVA (Comodato: base_cost siempre 0)
- Pago hibrido Tarjeta(API)/Widget/Nequi/COD/Comodato(sin costo) via `process-payment/`
  (`initialize-payment/` **eliminado 2026-07-23**, ver seccion API Endpoints)
- Estadisticas para marketing (RentingSummaryProvider, pull-based)

**Desacoplamiento de Inventory:**
El modulo NO depende de `InventorySelector` ni `StockRecord`. La disponibilidad se verifica
contra `RentalPeriod` (calendario propio). El campo `EquipmentVariant.stock` es el stock
fisico total; la disponibilidad real = `stock - unidades ocupadas en periodos activos`.

---

## Estructura de Directorios

```
renting/
├── models.py                  # Todos los modelos del dominio
├── urls.py                    # Router raiz del modulo
├── tasks.py                   # Celery beat: expire_abandoned_pending_payment_requests
│
├── api/
│   ├── views.py               # ViewSets con logica de permisos y acciones
│   ├── serializers.py         # Serializers de entrada/salida
│   └── urls.py                # Router REST
│
├── api/
│   ├── views.py               # ViewSets con logica de permisos y acciones
│   ├── operation_views.py     # RentalOperationViewSet (ciclo operativo post-pago)
│   ├── serializers.py         # Serializers de entrada/salida
│   └── urls.py                # Router REST
│
├── services/
│   ├── __init__.py            # Exports publicos (1199 lineas commands.py, 657 catalog.py -- 2026-07-23)
│   ├── commands.py            # Escritura atomica (Commands) -- RentingCommands, EquipmentCommands,
│   │                          #   EquipmentVariantCommands, EquipmentReviewCommands, EquipmentBlockCommands,
│   │                          #   EquipmentReturnInspectionCommands, RentingCategoryCommands,
│   │                          #   RentingBrandCommands, RentalLaborCommands, RentalRequestCommands,
│   │                          #   EquipmentLogisticsConfigCommands, EquipmentCommercialConfigCommands,
│   │                          #   EquipmentCommercialOptionCommands, EquipmentMarketingCommands
│   ├── selectors.py           # Lectura optimizada (Selectors)
│   ├── catalog.py             # [NUEVO 2026-07-16] Selector+Commands de los 11 modelos del catalogo
│   │                          #   enriquecido (Included/Excluded/Feature/SpecificationGroup/
│   │                          #   Specification/Requirement/ServiceIncluded/OptionalService/FAQ/
│   │                          #   Video/Document) + EquipmentImage
│   ├── availability.py        # AvailabilityEngine (is_available/find_next_available_slot/generate_schedule)
│   ├── operations.py          # [NUEVO 2026-07-07] RentalOperationCommands/RentalOperationSelector
│   ├── display.py             # Vocabulario de estados visibles
│   ├── pricing.py             # RentalPricingCalculator (tax rate) + RentalCostRuleSelector/Commands
│   └── summary.py             # RentingSummaryProvider (pull-based stats)
│
├── tests.py                   # Tests de negocio (concurrencia, lifecycle, permisos)
├── tests_availability.py      # Tests unitarios de AvailabilityEngine
├── tests_endpoints.py         # Tests de API (availability/calendar/timeline + acciones admin)
│
└── migrations/
    ├── 0001_initial.py .. 0021_equipmentreturninspection.py  # Ver tabla completa abajo
    ├── 0022_catalog_detail_models.py    # [2026-07-16] 11 modelos de catalogo enriquecido + SEO en Equipment
    ├── 0023-0029                        # Ajustes menores + EquipmentMarketing + periodic task de vencimientos
    ├── 0030_rentalperiod_commercial_type_and_more.py  # [2026-07-22] commercial_type en RentalRequest/RentalPeriod
    ├── 0031_seed_comodato_notification_templates.py
    └── 0032_alter_rentalrequest_payment_method.py     # PAYMENT_COMODATO agregado a choices
```

Ver "Migraciones Aplicadas" abajo para la tabla completa (32 migraciones a la fecha).

---

## Modelos

### RentingCategory

```python
class RentingCategory(SintelBaseModel):
    parent      = ForeignKey('self', null=True, blank=True, related_name='children')
    name        = CharField(max_length=100, unique=True)
    slug        = SlugField(unique=True, db_index=True)
    description = TextField(blank=True)
    is_active   = BooleanField(default=True)
```

Taxonomia jerarquica. `parent` permite subcategorias anidadas.

---

### RentingBrand

```python
class RentingBrand(SintelBaseModel):
    name = CharField(max_length=100, unique=True)
    slug = SlugField(unique=True, db_index=True)
```

---

### Equipment

```python
class Equipment(SintelBaseModel):
    vendor      = ForeignKey(AUTH_USER_MODEL, related_name='equipment_offered')
    category    = ForeignKey(RentingCategory, related_name='equipments')
    brand       = ForeignKey(RentingBrand, null=True, blank=True)
    name        = CharField(max_length=255)
    slug        = SlugField(unique=True, db_index=True)
    description = TextField(blank=True)
    is_active   = BooleanField(default=True)
    is_featured = BooleanField(default=False)
```

Registro maestro. `is_featured` lo incluye en el home feed publico.

---

### EquipmentVariant

```python
class EquipmentVariant(SintelBaseModel):
    equipment              = ForeignKey(Equipment, related_name='variants')
    sku                    = CharField(max_length=100, unique=True, db_index=True)
    rental_price_per_day   = DecimalField(null=True, blank=True)
    rental_price_per_hour  = DecimalField(null=True, blank=True)
    stock                  = PositiveIntegerField(default=0)
    is_active              = BooleanField(default=True)
```

- `stock`: unidades fisicas totales disponibles.
- Un equipo puede tener precio por dia, por hora, o ambos.
- La disponibilidad REAL en una fecha = `stock - ocupadas en RentalPeriod`.

---

### EquipmentImage y EquipmentReview

```python
class EquipmentImage(SintelBaseModel):
    equipment  = ForeignKey(Equipment, related_name='images')
    image      = ImageField(upload_to='renting/')
    alt_text   = CharField(max_length=255, blank=True, null=True)
    is_primary = BooleanField(default=False)
    image_type = CharField(choices=PRINCIPAL|GALERIA|DETALLE|INSTALACION|VISTA_360|PLANO|EJEMPLO,
                            default=GALERIA, db_index=True)  # extendido 2026-07-16
    position   = PositiveIntegerField(default=0)

class EquipmentReview(SintelBaseModel):
    user      = ForeignKey(AUTH_USER_MODEL, related_name='equipment_reviews')
    equipment = ForeignKey(Equipment, related_name='reviews')
    rating    = PositiveSmallIntegerField(validators=[1..5])
    comment   = TextField()
    class Meta:
        unique_together = ('user', 'equipment')
```

`EquipmentReviewCommands.create_review()` es el unico Command que valida el guard real
("solo quien alquilo y ya devolvio el equipo puede reseñar") — el modelo solo garantiza
1 reseña por usuario/equipo en BD. Endpoints publicos: `GET /equipment/{uuid}/reviews/`
(lista) y `POST /equipment/{uuid}/review/` (`IsAuthenticated`).

---

### Catalogo Enriquecido de Equipment (2026-07-16, migracion `0022_catalog_detail_models`)

**Regla arquitectonica vigente (ver `renting/CLAUDE.md`): `Equipment` es el aggregate root,
`EquipmentVariant` es SOLO inventario/precio (`sku`, `rental_price_per_day`,
`rental_price_per_hour`, `stock`, `is_active`).** Todo el contenido descriptivo vive
exclusivamente en `Equipment`, vía 11 modelos hijos nuevos que reemplazan lo que antes
hubieran sido `TextField`/JSON libres — mismo nivel de detalle administrable que `shop`.
Los 11 comparten el mismo patron: `equipment` (FK, `related_name` entre parentesis),
`position` (orden manual) e `is_active` (activar/desactivar sin borrar — el borrado real
usa `is_deleted` de `SintelBaseModel`).

| Modelo | `related_name` | Campos propios | Proposito |
|---|---|---|---|
| `RentalIncludedItem` | `included_items` | `title, description, icon` | Que incluye el alquiler |
| `RentalExcludedItem` | `excluded_items` | `title, description, icon` | Que NO incluye el alquiler |
| `RentalFeature` | `features` | `title, value, icon` | Caracteristica destacada (ej. "Potencia: 20T") |
| `RentalSpecificationGroup` | `specification_groups` | `name` | Agrupador de ficha tecnica (ej. "Motor") |
| `RentalSpecification` | `specifications` | `group` (FK), `name, value` | Fila de ficha tecnica (denormaliza `equipment` ademas de `group`, mismo patron que `RentalSpecificationGroup.equipment`, para listar sin join) |
| `RentalRequirement` | `requirements` | `title, description` | Requisito para poder rentar (ej. acceso vehicular) |
| `RentalServiceIncluded` | `services_included` | `title, description, icon` | Servicio ya incluido en el precio |
| `RentalOptionalService` | `optional_services` | `title, description, price, icon` | Servicio adicional de costo extra (catalogo informativo — distinto de `RentalLabor`, que es mano de obra generica reutilizable entre equipos) |
| `RentalFAQ` | `faqs` | `question, answer` | Pregunta frecuente del detalle publico |
| `RentalVideo` | `videos` | `title, source_type (YOUTUBE\|VIMEO\|MP4), video_url, video_file, thumbnail` | Video del equipo |
| `RentalDocument` | `documents` | `title, description, document_type (9 opciones), version, language, file, cover_image, downloads, is_public` | Documento descargable (manual/ficha tecnica/certificado/etc.) — `is_public=False` lo oculta del cliente |

**SEO** (`meta_title`, `meta_description`, `meta_keywords`, `og_image`) tambien se agrego en
esta migracion, pero como campos directos de `Equipment` (no un modelo aparte) — espejo de
`shop.Product`. El JSON-LD (`schema.org`) NO se persiste: se genera en serializer/frontend a
partir de estos campos.

Administracion: 12 endpoints en `/api/v1/dashboard/` (11 modelos + `equipment-images/`), todos
`EquipmentCatalogChildViewSet` (`dashboard/api/renting_catalog_views.py`), filtrados por
`?equipment=<uuid>` — ver tabla completa en "API Endpoints".

---

### EquipmentLogisticsConfig

```python
class EquipmentLogisticsConfig(SintelBaseModel):
    equipment         = OneToOneField(Equipment, related_name='logistics_config')
    delivery_cost     = DecimalField(null=True, blank=True)  # Costo de entrega
    pickup_cost       = DecimalField(null=True, blank=True)  # Costo de recogida
    installation_cost = DecimalField(null=True, blank=True)
    calibration_cost  = DecimalField(null=True, blank=True)
    training_cost     = DecimalField(null=True, blank=True)
    startup_cost      = DecimalField(null=True, blank=True)
    notes             = TextField(blank=True)
```

Configurada por el admin. Los costos se leen automaticamente en `create_request()`;
el usuario del wizard NO los ingresa manualmente.

Agrupacion en la vista:
- **Transporte** = `delivery_cost + pickup_cost`
- **Puesta en marcha** = `installation_cost + calibration_cost + training_cost + startup_cost`

Admin: `GET/PUT/DELETE /api/v1/dashboard/equipment/{uuid}/logistics/`
(`EquipmentLogisticsConfigCommands.upsert()`/`.delete()`).

---

### EquipmentCommercialConfig, EquipmentCommercialOption y EquipmentMarketing (2026-07-16/2026-07-22)

Tres configuraciones OneToOne/1-a-muchos adicionales de `Equipment`, mismo patron que
`EquipmentLogisticsConfig` (upsert via Commands, sin tocar `Equipment`/`EquipmentVariant`):

```python
class EquipmentCommercialConfig(SintelBaseModel):
    """Que modalidades comerciales admite este Equipment."""
    equipment         = OneToOneField(Equipment, related_name='commercial_config')
    renting_enabled   = BooleanField(default=True)   # default reproduce el comportamiento
    comodato_enabled  = BooleanField(default=False)  # previo a que esta config existiera
    comodato_notes    = TextField(blank=True)

class EquipmentCommercialOption(SintelBaseModel):
    """Plazos configurables (hoy solo Comodato los usa)."""
    equipment    = ForeignKey(Equipment, related_name='commercial_options')
    modality     = CharField(choices=RENTAL|COMODATO, default=COMODATO)
    term_months  = PositiveSmallIntegerField(choices=[6,12,18,24,36])
    is_enabled   = BooleanField(default=True)
    class Meta:
        constraints = [UniqueConstraint(fields=['equipment','modality','term_months'])]

class EquipmentMarketing(SintelBaseModel):
    """Presentacion comercial/visual publica -- NO info tecnica/inventario/logistica."""
    equipment = OneToOneField(Equipment, related_name='marketing')
    reference_price, promo_price, show_discount_percentage   # precio comercial
    tags                       = JSONField(default=list)      # codigos de 9 TAG_CHOICES (OFERTA, NUEVO, ...)
    main_message, featured_benefit, trust_message,
    urgency_message, social_proof_message                     # mensajes de conversion (texto libre)
    purchase_price_reference, financial_message                # comparativa comprar vs alquilar
    use_cases                 = JSONField(default=list)        # ["Eventos", "Construccion", ...]
    cta_label                                                   # texto del boton principal
    promo_banner_message
    quick_benefits             = JSONField(default=list)        # [{"icon": "bi-truck", "label": "..."}]
```

- `EquipmentCommercialConfig` es el gate real de Comodato: `renting_enabled`/`comodato_enabled`
  deciden si el wizard ofrece esa modalidad para ese equipo especifico (default = solo Renting,
  igual que todo equipo anterior a esta feature).
- SEO (`meta_title` etc.) NO se duplica en `EquipmentMarketing` — ya vive en `Equipment` desde
  la migracion `0022`, se reutiliza tal cual.
- Sin herencia/plantillas/config compartida entre equipos en ninguno de los 3 modelos — mismo
  principio que `RentalCostRule` (ver seccion dedicada abajo).

Admin (acciones custom de `AdminEquipmentViewSet` en `dashboard/api/views.py`, no ViewSets
propios):

| Endpoint | Metodos | Command |
|---|---|---|
| `/api/v1/dashboard/equipment/{uuid}/marketing/` | GET, PUT, DELETE | `EquipmentMarketingCommands.upsert()`/`.delete()` |
| `/api/v1/dashboard/equipment/{uuid}/commercial-config/` | GET, PUT, DELETE | `EquipmentCommercialConfigCommands.upsert()`/`.delete()` |
| `/api/v1/dashboard/equipment/{uuid}/commercial-options/` | GET, POST | `RentingAdminOrchestrator.list_commercial_options()`/`.upsert_commercial_option()` |
| `/api/v1/dashboard/equipment/{uuid}/commercial-options/{option_uuid}/delete/` | DELETE | `RentingAdminOrchestrator.delete_commercial_option()` |

---

### RentalRequest

```python
class RentalRequest(SintelBaseModel):
    # Ciclo de vida
    STATUS_DRAFT              = 'draft'               # sin uso (reservado)
    STATUS_PENDING_VALIDATION = 'pending_validation'   # COD esperando aprobacion admin
    STATUS_PENDING_PAYMENT    = 'pending_payment'      # NUNCA bloquea agenda
    STATUS_PAID               = 'paid'                 # Wompi/Nequi aprobado -> bloquea
    STATUS_CONFIRMED          = 'confirmed'            # COD aprobado por admin -> bloquea
    STATUS_IN_OPERATION       = 'in_operation'          # equipo entregado
    STATUS_FINISHED           = 'finished'
    STATUS_CANCELLED          = 'cancelled'
    STATUS_PAYMENT_CONFLICT   = 'payment_conflict'      # perdio la carrera de disponibilidad

    # Modalidad comercial [AGREGADO 2026-07-22, migracion 0030] -- distinto de rental_mode
    # (dias/horas, eje de pricing). commercial_type es "que tipo de contrato es esto":
    COMMERCIAL_RENTAL   = 'RENTAL'    # paga de inmediato (Wompi/Nequi/COD) -- default, preserva
    COMMERCIAL_COMODATO = 'COMODATO'  # comportamiento previo a esta feature

    user               = ForeignKey(AUTH_USER_MODEL)
    equipment_variant  = ForeignKey(EquipmentVariant, on_delete=PROTECT)
    status             = CharField(max_length=30, default=STATUS_PENDING_PAYMENT, db_index=True)
    commercial_type    = CharField(choices=RENTAL|COMODATO, default=RENTAL, db_index=True)
    priority           = CharField(choices=LOW|HIGH, default=LOW, db_index=True)  # min_days: LOW=7, HIGH=3
    refund_required    = BooleanField(default=False, db_index=True)   # True si se cobro y perdio la carrera
    admin_notes        = TextField(blank=True)          # interno, no se expone al cliente
    delivery_time      = TimeField(null=True, blank=True)  # modo horas
    pickup_time        = TimeField(null=True, blank=True)  # modo horas

    # Paso 2 - Lugar
    location_address    = CharField(max_length=500)
    location_city       = CharField(max_length=100)
    location_department = CharField(max_length=100)
    location_coordinates = CharField(max_length=100, blank=True)
    project_type        = CharField(max_length=255, blank=True)
    access_conditions   = TextField(blank=True)
    location_notes      = TextField(blank=True)

    # Paso 3 - Responsable
    contact_full_name = CharField(max_length=255)
    contact_doc_type  = CharField(max_length=10)   # CC, NIT, CE, PP
    contact_doc_number = CharField(max_length=50)
    contact_email     = EmailField()
    contact_phone     = CharField(max_length=30)
    contact_company   = CharField(max_length=255, blank=True)
    contact_position  = CharField(max_length=255, blank=True)

    # Paso 4 - Configuracion
    start_date        = DateField()
    end_date          = DateField()
    quantity          = PositiveIntegerField(default=1)
    estimated_hours   = DecimalField(null=True, blank=True)
    rental_mode       = CharField(max_length=10)  # 'days' | 'hours'
    operational_notes = TextField(blank=True)

    # Paso 5 - Contrato
    terms_accepted    = BooleanField(default=False)
    terms_accepted_at = DateTimeField(null=True, blank=True)

    # Costos (llenados por commands.py desde EquipmentLogisticsConfig -- Comodato: igual que Renting)
    delivery_cost      = DecimalField(default=0)
    pickup_cost        = DecimalField(default=0)
    distance_km        = DecimalField(null=True, blank=True)
    installation_cost  = DecimalField(default=0)
    calibration_cost   = DecimalField(default=0)
    training_cost      = DecimalField(default=0)
    startup_cost       = DecimalField(default=0)
    labor_items        = ManyToManyField(RentalLabor, blank=True)

    # Totales calculados
    total_rental_days  = PositiveIntegerField(null=True, blank=True)
    base_cost          = DecimalField(null=True, blank=True)  # Comodato: siempre 0
    labor_total        = DecimalField(default=0)
    transport_total    = DecimalField(default=0)
    setup_total        = DecimalField(default=0)
    tax_amount         = DecimalField(default=0)
    grand_total        = DecimalField(null=True, blank=True)

    # Metodo de pago [AGREGADO, migracion 0032] -- WOMPI/NEQUI/COD/COMODATO (sin costo)
    payment_method = CharField(choices=WOMPI|NEQUI|COD|COMODATO, default=WOMPI)

    # Pago Wompi
    wompi_reference      = CharField(max_length=255, blank=True)
    wompi_transaction_id = CharField(max_length=255, blank=True)
    payment_status       = CharField(max_length=50, blank=True)
    paid_at              = DateTimeField(null=True, blank=True)
```

Creado al confirmar el wizard. Status inicial: `pending_payment` para Renting, **directo a
`pending_validation` para Comodato** (sin pasarela que inicializar — ver seccion "Modalidad
Comercial" abajo). `pending_payment` NUNCA bloquea el calendario (ver "Prevencion de Doble
Reserva" abajo, reescrita en la Fase 1 del Plan Maestro de Renting, 2026-07-07).

**`labor_total`/`labor_items`** existen en el modelo desde antes pero **[VERIFICADO
2026-07-23] no se usan en el calculo actual de `create_request()`** (que no los lee de
`validated_data`) ni se seleccionan en el wizard actual (`RentalBookingWizard.vue`) —
quedan como campos vigentes en BD sin consumidor activo hoy, no como error.

---

### RentalProjectAttachment

```python
class RentalProjectAttachment(SintelBaseModel):
    rental_request = ForeignKey(RentalRequest, related_name='project_attachments')
    file           = FileField(upload_to='renting/project_attachments/%Y/%m/')
    original_name  = CharField(max_length=255, blank=True)
    content_type   = CharField(max_length=100, blank=True)
    uploaded_by    = ForeignKey(AUTH_USER_MODEL, null=True, on_delete=SET_NULL)
```

Fotos/documentos de reconocimiento del proyecto aportados por el cliente (paso "Lugar" del
wizard, ver seccion Frontend). Hasta 10 archivos por solicitud
(`RentalRequestCommands.add_project_attachments()`), endpoint
`POST /rental-requests/{uuid}/attachments/`.

---

### RentalPeriod

```python
class RentalPeriod(SintelBaseModel):
    STATUS_SCHEDULED = 'scheduled'
    STATUS_ACTIVE    = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    rental_request    = ForeignKey(RentalRequest, related_name='periods')
    equipment_variant = ForeignKey(EquipmentVariant, related_name='rental_periods')
    start_date        = DateField(db_index=True)
    end_date          = DateField(db_index=True)
    start_time        = TimeField(null=True, blank=True)   # modo horas
    end_time          = TimeField(null=True, blank=True)   # modo horas
    rental_mode       = CharField(max_length=10, default='days')  # denormalizado de la request
    quantity          = PositiveIntegerField(default=1)
    status            = CharField(max_length=20, default=STATUS_SCHEDULED)

    class Meta:
        indexes = [
            Index(fields=['start_date', 'end_date']),
            Index(fields=['equipment_variant', 'status']),
            Index(fields=['equipment_variant', 'start_date', 'end_date'], name='renting_period_var_range_idx'),
        ]
```

**Ya NO se crea junto con `RentalRequest`** (Fase 1 del Plan Maestro, 2026-07-07). Se crea
recien en `RentalRequestCommands.confirm_payment()` (pago Wompi/Nequi aprobado) o en
`approve_manual_validation()` (COD aprobado por un admin) -- los dos unicos puntos
autoritativos de lock+disponibilidad. `STATUS_ACTIVE` se alcanza via `activate_period()`
("marcar entregado") y `STATUS_COMPLETED` via `complete_period()` ("marcar recogido").
Cuando se cancela la solicitud (o falla el pago online), el periodo pasa a `cancelled`,
liberando la disponibilidad.

---

### EquipmentBlock

```python
class EquipmentBlock(SintelBaseModel):
    equipment_variant = ForeignKey(EquipmentVariant, related_name='blocks')
    block_type        = CharField(choices=MAINTENANCE|DAMAGE|INVENTORY|OTHER, default=MAINTENANCE)
    start_date        = DateField()
    end_date          = DateField()
    quantity          = PositiveIntegerField(default=1)
    status            = CharField(choices=active|released, default=active)
    reason            = TextField()
    created_by        = ForeignKey(AUTH_USER_MODEL, null=True, on_delete=SET_NULL)
    released_by       = ForeignKey(AUTH_USER_MODEL, null=True, on_delete=SET_NULL)
    released_at       = DateTimeField(null=True)
    release_reason    = TextField(blank=True)
```

Bloqueo manual de una `EquipmentVariant` por mantenimiento, daño o conteo de
inventario — **no** está atado a ninguna `RentalRequest`. Agregado 2026-07-14 como
complemento aditivo al motor de disponibilidad existente (no reemplaza nada de
`AvailabilityEngine`/`RentalRequestCommands`, que ya estaban en producción). Es un
override admin: `EquipmentBlockCommands.create_block()` NO valida contra
`AvailabilityEngine.is_available()` (un equipo puede necesitar bloquearse aunque ya
esté rentado, ej. se dañó en campo). Una sola fila cubre todo el ciclo de vida
(creación + liberación) como historial auditable — mismo patrón liviano que
`RentalPeriod`, sin tabla de eventos aparte.

---

### EquipmentReturnInspection

```python
class EquipmentReturnInspection(SintelBaseModel):
    rental_request        = OneToOneField(RentalRequest, related_name='return_inspection')
    has_damage             = BooleanField(default=False)
    condition_notes         = TextField(blank=True)
    missing_accessories     = TextField(blank=True)
    inspected_by            = ForeignKey(AUTH_USER_MODEL, null=True, on_delete=SET_NULL)
    resulting_block          = ForeignKey(EquipmentBlock, null=True, on_delete=SET_NULL)
```

Inspeccion de devolucion (2026-07-14). Registro **opcional/aparte**: NO gatea
`RentalRequestCommands.complete_period()` (mark-returned) -- decision explicita del
usuario, para no arriesgar el flujo de finalizacion ya en produccion. Solo se
permite crear una sobre una `RentalRequest` ya en `STATUS_FINISHED` (una por
solicitud, `OneToOneField`). Si `has_damage=True`,
`EquipmentReturnInspectionCommands.create_inspection()` crea automaticamente un
`EquipmentBlock` (`TYPE_DAMAGE`, horizonte de 365 dias) sobre la variante --
tambien decision explicita del usuario, conecta esta feature con
`EquipmentBlock` (ver arriba). El bloqueo queda activo hasta que un admin lo
libere manualmente tras reparar el equipo; el `end_date` exacto no importa
mientras sea lo bastante lejano.

---

### RentalOperation y RentalOperationEvent (2026-07-07)

```python
class RentalOperation(SintelBaseModel):
    """Ciclo operativo exclusivo de una RentalRequest aprobada. 10 estados."""
    rental_request = OneToOneField(RentalRequest, on_delete=PROTECT, related_name='rental_operation')
    status = CharField(choices=[READY_FOR_SCHEDULING, SCHEDULED, TRANSPORT_ASSIGNED,
                                 READY_FOR_DELIVERY, DELIVERED, IN_OPERATION,
                                 READY_FOR_PICKUP, PICKED_UP, RETURN_INSPECTION, COMPLETED],
                        default=READY_FOR_SCHEDULING, db_index=True)
    assigned_dispatcher = ForeignKey('operations.DispatcherProfile', null=True, on_delete=SET_NULL)
    assigned_vehicle, delivery_date/time, pickup_date/time, estimated_duration_minutes, route, notes
    priority = CharField(choices=RentalRequest.PRIORITY_CHOICES, default=LOW)
    has_incident = BooleanField(default=False)
    incident_notes = TextField(blank=True)

class RentalOperationEvent(SintelBaseModel):
    operation   = ForeignKey(RentalOperation, related_name='timeline')
    event_type  = CharField(max_length=50, db_index=True)
    description = TextField(blank=True)
    actor       = ForeignKey(AUTH_USER_MODEL, null=True, on_delete=SET_NULL)
    metadata    = JSONField(default=dict)
```

FSM post-pago separada de `RentalRequest` (dominio comercial). Se crea automaticamente en
`READY_FOR_SCHEDULING` desde `confirm_payment()`/`approve_manual_validation()`. Detalle
completo (endpoints, `dashboard_metrics()`, incidencias, emails de ciclo de vida) en la
seccion "Operaciones de Renting" mas abajo (Pendiente/Roadmap) — no se repite aqui.

---

### RentalCostRule

```python
class RentalCostRule(SintelBaseModel):
    name            = CharField(max_length=150)
    cost_type       = CharField(max_length=10)   # 'FIXED' | 'PERCENTAGE'
    context         = CharField(max_length=20)   # 'TAX' | 'DISCOUNT' | 'DEPOSIT' | 'INSURANCE' | 'SURCHARGE'
    value           = DecimalField(max_digits=12, decimal_places=4)
    is_active       = BooleanField(default=True)
```

**Correccion arquitectonica definitiva (2026-07-17, migracion 0027):** se elimino el campo
`applies_globally`. NO existen reglas globales/heredadas/compartidas entre equipos en Renting
-- cada `RentalCostRule` pertenece exclusivamente al `Equipment` donde el admin la creo, via su
asignacion explicita (`RentalCostAssignment`) a una `EquipmentVariant` de ESE equipo. Antes de
este cambio, una regla con `applies_globally=True` se aplicaba automaticamente a TODOS los
equipos del sistema sin asignacion explicita, y ademas el endpoint de listado
(`AdminRentalCostRuleViewSet.list()`) devolvia el catalogo completo de reglas sin filtrar por
equipo -- esto causaba que un equipo recien creado mostrara "N reglas definidas" heredadas de
otros equipos (bug real reportado y corregido). Ahora:

- `RentalCostRuleSelector.list_for_equipment(equipment)` es la UNICA forma de listar reglas --
  siempre filtra por `RentalCostAssignment.variant__equipment=equipment`.
- `RentalCostRuleCommands.create_rule_for_equipment(equipment, ...)` es el UNICO punto de
  creacion desde el panel: crea la regla Y la asigna de inmediato a la variante principal de
  ESE equipo, sin ventana donde la regla exista "suelta"/sin dueno.
- `RentalPricingCalculator.get_tax_rate(variant)`/`calculate_breakdown(variant, ...)` solo leen
  reglas asignadas a ESA variante especifica -- nunca de otra variante ni de un catalogo global.
  Si la variante no tiene ninguna regla TAX propia, se usa `FALLBACK_TAX_RATE = 19%` (constante
  de codigo, no un dato tomado de otro equipo).
- Un nuevo equipo, recien creado, siempre arranca con 0 reglas de costo.

`RentalCostAssignment` (rule + variant, unique_together) sigue siendo la unica forma de vincular
una regla a una variante. **"Costos" (este modelo) y "Logistica" (`EquipmentLogisticsConfig`, ver
arriba) son dos conceptos distintos que comparten nombre por accidente, no el mismo dato
duplicado:**

- **Logistica** (`EquipmentLogisticsConfig`, FK a `Equipment`) = costos operativos FIJOS del
  equipo (delivery/pickup/install/calibration/training/startup) -- son iguales sin importar
  que variante/SKU se reserve, por eso viven en Equipment.
- **Costos** (`RentalCostRule`/`RentalCostAssignment`, FK a `EquipmentVariant`) = reglas de
  PRECIO (IVA, descuento, deposito, seguro, recargo) que se calculan sobre el subtotal ya
  armado (`RentalPricingCalculator.calculate_breakdown()`). Estas SI pueden variar por variante
  dentro del mismo Equipment (ej. un "Seguro premium" solo asignado a la variante mas costosa) --
  por eso se asignan a `EquipmentVariant`, no a `Equipment`. Nunca a otro Equipment.

---

### RentalLabor

```python
class RentalLabor(SintelBaseModel):
    name          = CharField(max_length=255)
    description   = TextField(blank=True)
    price_per_hour = DecimalField(max_digits=12, decimal_places=2)
    is_active     = BooleanField(default=True)
```

Mano de obra disponible (referencia de catalogo; ya no se selecciona en el wizard).

---

## Calculo de Costos

```
base_cost      = price_per_day * total_days * quantity
                 O price_per_hour * estimated_hours * quantity

transport_total = delivery_cost + pickup_cost           (de EquipmentLogisticsConfig)
setup_total     = installation_cost + calibration_cost
                + training_cost + startup_cost           (de EquipmentLogisticsConfig)

subtotal        = base_cost + transport_total + setup_total
tax_rate        = RentalPricingCalculator.get_tax_rate(variant)  # default 19%
tax_amount      = subtotal * tax_rate
grand_total     = subtotal + tax_amount
```

El calculo ocurre en `RentalRequestCommands.create_request()` y se persiste en `RentalRequest`.
El frontend replica el calculo en tiempo real con los mismos campos de `logistics_config`
que vienen en la respuesta de `GET /renting/equipment/{uuid}/`.

**Comodato (ver seccion siguiente): `base_cost` queda fijo en `0`** — el resto del calculo
(logistica/impuestos) se aplica identico, sin rama especial fuera de ese único `if`.

---

## Modalidad Comercial: Renting vs. Comodato (2026-07-22)

**Nuevo eje del negocio, independiente de `rental_mode` (dias/horas, que sigue siendo el eje
de *pricing*).** `RentalRequest.commercial_type` define "que tipo de contrato es esto":

| | `RENTAL` (default) | `COMODATO` |
|---|---|---|
| Cobra tarifa por dia/hora | Si (`base_cost` calculado normal) | **No** — `base_cost` siempre `0` |
| Metodos de pago | WOMPI / NEQUI / COD | Ninguno — `payment_method` se fija en `COMODATO` |
| Estado inicial tras `create_request()` | `pending_payment` | **`pending_validation`** directo (salta el paso de pago por completo) |
| Pasa por `process_payment_selection()` | Si | **No** — nunca llega ahi |
| Notificacion al crear | Ninguna (regla PaymentResult) | `rental_comodato_review_pending`, solo a `admin_notifications`, nunca al cliente (misma regla PaymentResult, sin excepcion real) |
| Habilitado por equipo | Siempre (no requiere config) | Solo si `EquipmentCommercialConfig.comodato_enabled=True` para ESE equipo |
| Plazos disponibles | N/A | `EquipmentCommercialOption` (6/12/18/24/36 meses) configurados por el admin para ese equipo |

**Por que existe `payment_method=COMODATO` si Comodato no paga:** sin ese valor explicito, el
campo se quedaba en el default del modelo (`WOMPI`) para una solicitud que jamas paso por
ninguna pasarela — bug real encontrado en el smoke test del 2026-07-22 (el `Order` resultante,
via `OrderCommands.create_from_rental()`, quedaba marcado `payment_method='WOMPI'` sin que
hubiera pago real involucrado). `create_request()` fija ambos campos (`commercial_type` y
`payment_method`) en el mismo `RentalRequest.objects.create()`, antes de que exista ninguna
oportunidad de que queden en su default incorrecto.

**A partir de `pending_validation`, el resto del flujo es identico al de COD:** un admin
aprueba/rechaza desde `/panel/renta/solicitudes` (`approve/`/`reject/`), y `approve_manual_validation()`
(el mismo Command que usa COD) crea el `RentalPeriod` con lock+disponibilidad. No hay ninguna
rama especial de Comodato despues de este punto — toda la maquinaria de operaciones
(`RentalOperation`, `Order`+`OrderItem`, notificaciones) es la misma que para cualquier
`RentalRequest` aprobada.

`RentalPeriod.commercial_type` (denormalizado desde `RentalRequest` al crear el periodo, mismo
motivo que `rental_mode`/`quantity` ya denormalizados ahi) permite que `AvailabilityEngine` y
los endpoints `calendar/`/`timeline/` etiqueten cada bloqueo como Renting o Comodato sin join
adicional al padre — es un hot-path.

---

## Algoritmo de Disponibilidad (AvailabilityEngine)

`renting/services/availability.py`. Reemplaza el algoritmo binario original;
`RentingSelector.check_availability()` es ahora un wrapper delgado sobre
`AvailabilityEngine.is_available()` en modo dias (se mantiene por compatibilidad con sus
3 llamadores existentes).

```python
# AvailabilityEngine.is_available(variant_id, start_date, end_date, quantity,
#                                  rental_mode='days', start_time=None, end_time=None,
#                                  exclude_period_id=None)

stock_total = EquipmentVariant.objects.only('stock').get(id=variant_id).stock
if stock_total < quantity:
    return False

# Prefiltro en BD inclusivo (start_date<=end_requested, end_date>=start_requested):
# mas ancho que el original para no excluir por error dos reservas por horas el mismo dia.
candidates = RentalPeriod.objects.filter(
    equipment_variant_id=variant_id,
    status__in=['scheduled', 'active'],
    start_date__lte=end_date,
    end_date__gte=start_date,
)

# Test exacto en Python, normalizando cada candidato a un intervalo datetime:
#   modo dias:  (start_date 00:00, end_date 00:00)      -- end_date exclusivo (checkout)
#   modo horas: (start_date+start_time, end_date+end_time)
# Solapamiento: existing.start_dt < new.end_dt AND existing.end_dt > new.start_dt
occupied = sum(p.quantity for p in candidates if _overlaps(p, start_date, end_date, ...))
return (stock_total - occupied) >= quantity
```

Metodos adicionales:
- `find_next_available_slot(variant_id, start_date, ...)`: barrido dia a dia (horizonte
  configurable, default 90 dias) devolviendo `{'date', 'time'}` del primer hueco libre.
- `generate_schedule(variant_id, range_start, range_end, statuses=None, include_blocks=True)`:
  lista de periodos que se solapan con el rango. `statuses=None` -> solo bloqueantes
  (scheduled/active, para calendar); pasar los 4 estados para el timeline (historial).

**EquipmentBlock (2026-07-14)**: `is_available()` y `generate_schedule()` tambien
consultan `EquipmentBlock` (status=`active`) y suman su `quantity` a `occupied`, con
la misma normalizacion `_period_range()` (siempre modo dias). `generate_schedule()`
mapea cada bloqueo a la MISMA forma de dict que un `RentalPeriod` (`status='blocked'`,
o `'block_released'` cuando el caller pide historial completo con los 4 estados de
`RentalPeriod`), sin exponer `reason`/`created_by` — los endpoints `calendar`/
`timeline`/`availability` son `AllowAny`. `find_next_available_slot()` no cambio:
ya delega en `is_available()`.

Se llama en:
- `RentalRequestInputSerializer.validate()` (retorna 400 si no hay disponibilidad, best-effort).
- `RentalRequestCommands.create_request()` (best-effort, ya NO bloquea con lock -- ver
  "Prevencion de Doble Reserva").
- `RentalRequestCommands.confirm_payment()` y `approve_manual_validation()` (autoritativo,
  con `select_for_update()` sobre la variante).
- El wizard lo llama en `goStep5()` via `GET .../check-availability/` antes de avanzar al paso 5.
- Los endpoints `availability/`, `calendar/` y `timeline/` (ver API Endpoints).

---

## API Endpoints

### EquipmentViewSet — `/api/v1/renting/equipment/`

| Metodo | URL | Permiso | Descripcion |
|--------|-----|---------|-------------|
| GET | `/equipment/` | AllowAny | Lista equipos activos con stock |
| GET | `/equipment/{uuid}/` | AllowAny | Detalle con variantes, imagenes, logistics_config |
| POST | `/equipment/` | IsAdminUser | Crear equipo |
| PATCH | `/equipment/{uuid}/` | IsAdminUser | Editar equipo |
| DELETE | `/equipment/{uuid}/` | IsAdminUser | Borrado logico |
| GET | `/equipment/{uuid}/check-availability/` | AllowAny | Verificar disponibilidad por fechas (legacy, compatible) |
| GET | `/equipment/{uuid}/availability/` | AllowAny | Sucesor de check-availability, mismo payload |
| GET | `/equipment/{uuid}/calendar/` | AllowAny | Calendario dia a dia (unidades libres por dia) |
| GET | `/equipment/{uuid}/timeline/` | AllowAny | Historial completo de periodos (4 estados), sin PII |
| POST | `/equipment/{uuid}/documents/{document_uuid}/register-download/` | AllowAny | **[AGREGADO 2026-07-23]** Registra descarga (`downloads += 1`) y retorna la URL absoluta del archivo — solo `RentalDocument` publico/activo |
| GET | `/equipment/{uuid}/reviews/` | AllowAny | **[AGREGADO 2026-07-23]** Lista reseñas publicadas del equipo |
| POST | `/equipment/{uuid}/review/` | IsAuthenticated | **[AGREGADO 2026-07-23]** Crea una reseña — solo quien alquilo y devolvio el equipo, 1 por usuario/equipo |

**check-availability / availability query params:**
```
variant=<uuid>&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&quantity=1&rental_mode=days
```
**Respuesta (check-availability y availability comparten forma; check-availability
mantiene start_date/end_date como los strings originales del query, availability los
retorna como date):**
```json
{
  "available": false,
  "variant_uuid": "3ae2cde7-...",
  "start_date": "2026-07-01",
  "end_date": "2026-07-05",
  "quantity": 1,
  "rental_mode": "days",
  "next_available_date": "2026-07-06",
  "next_available_time": null,
  "occupied_slots": [
    {"start_date": "2026-07-01", "end_date": "2026-07-05", "start_time": null, "end_time": null,
     "rental_mode": "days", "quantity": 1, "status": "scheduled"}
  ]
}
```

**calendar query params:** `variant=<uuid>&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
**Respuesta:** `{ variant_uuid, range_start, range_end, stock, days: [{date, available_units, status, hour_bookings}] }`
`status` por dia: `available` | `booked` | `full`.

**timeline query params:** `variant=<uuid>&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
**Respuesta:** `{ variant_uuid, range_start, range_end, periods: [...] }` -- incluye los 4
estados de `RentalPeriod` (scheduled/active/completed/cancelled) para heatmap/barras,
sin datos del cliente.

---

### RentalRequestViewSet — `/api/v1/renting/rental-requests/`

| Metodo | URL | Permiso | Descripcion |
|--------|-----|---------|-------------|
| POST | `/rental-requests/` | IsBuyerOrAdmin | Crear solicitud (equivalente backend de los pasos 1-4 del wizard) |
| GET | `/rental-requests/` | IsBuyerOrAdmin | Listar solicitudes del usuario (admin ve todas) |
| GET | `/rental-requests/{uuid}/` | IsBuyerOrAdmin | Detalle |
| POST | `/rental-requests/{uuid}/attachments/` | IsBuyerOrAdmin | **[AGREGADO 2026-07-23]** Adjunta hasta 10 fotos/documentos de reconocimiento del proyecto (`RentalProjectAttachment`) |
| POST | `/rental-requests/{uuid}/cancel/` | IsBuyerOrAdmin | Cancelar (libera RentalPeriod si existia) |
| POST | `/rental-requests/{uuid}/process-payment/` | IsBuyerOrAdmin | Seleccionar metodo de pago (WOMPI/NEQUI/COD) y continuar el flujo — ver "Integracion con Wompi" |
| ~~POST `/rental-requests/{uuid}/initialize-payment/`~~ | — | **[ELIMINADO 2026-07-23, auditoria SSoT de Payment, hallazgo H-01]** Recalculaba la firma de integridad con su propia copia de `hashlib.sha256`, duplicando `_compute_integrity_signature()` de `payment/online/services/commands.py`, sin ningun consumidor real en frontend ni backend. El camino vigente y unico es `process-payment/`. Si aparece una referencia a este endpoint en otro documento, esta desactualizada. |
| POST | `/rental-requests/{uuid}/approve/` | IsAdminUser | Aprueba COD/Comodato `pending_validation` -> `confirmed` (crea RentalPeriod) |
| POST | `/rental-requests/{uuid}/reject/` | IsAdminUser | Rechaza COD/Comodato `pending_validation` -> `cancelled` |
| POST | `/rental-requests/{uuid}/mark-delivered/` | IsAdminUser | paid/confirmed -> in_operation (periodo scheduled -> active) |
| POST | `/rental-requests/{uuid}/mark-returned/` | IsAdminUser | in_operation -> finished (periodo active -> completed) |
| POST | `/rental-requests/{uuid}/release-period/` | IsAdminUser | Libera la agenda sin cancelar la solicitud (override admin) |
| POST | `/rental-requests/{uuid}/extend/` | IsAdminUser | Extiende `end_date` si hay disponibilidad (2026-07-14, ver "Extension de renta") |
| POST | `/rental-requests/{uuid}/return-inspection/` | IsAdminUser | Registra inspeccion de devolucion (2026-07-14, opcional/aparte, solo si `status=finished`) |

`RentalRequestViewSet` soporta filtros `?status=...&payment_method=...&refund_required=true&commercial_type=...`
via `DjangoFilterBackend` (`filterset_fields`) — **[CORREGIDO 2026-07-23]** el permiso real de
todo el ViewSet es `IsBuyerOrAdmin` (`users.api.permissions`), no `IsAuthenticated` generico
como decian versiones previas.

**process-payment — kill-switches (2026-07-22, generalizacion del ADR-001 de `payment`):**
para `payment_method=WOMPI`, el backend valida `PaymentFeatureFlags.get_active()` ANTES de
delegar: rechaza con 403 si `card_token` viene presente pero `card_api_flow_enabled=False`, o
si `card_token` esta ausente (Widget) pero `widget_flow_enabled=False`. Simetrico al frontend
(que oculta el sub-metodo deshabilitado), no solo una validacion de UI.

**POST /rental-requests/ — payload:**
```json
{
  "equipment_variant": "<variant-uuid>",
  "commercial_type": "RENTAL",
  "location_address": "Calle 100 #15-20",
  "location_city": "Bogota",
  "location_department": "Cundinamarca",
  "contact_full_name": "Juan Perez",
  "contact_doc_type": "CC",
  "contact_doc_number": "12345678",
  "contact_email": "juan@empresa.com",
  "contact_phone": "3001234567",
  "start_date": "2026-07-01",
  "end_date": "2026-07-05",
  "quantity": 1,
  "rental_mode": "days",
  "priority": "LOW",
  "terms_accepted": true
}
```

`commercial_type` y `priority` son opcionales (default `RENTAL`/`LOW`) — **[AGREGADOS
2026-07-23]** no estaban en la version previa de este payload de ejemplo.

**Respuesta 201 (campos relevantes):**
```json
{
  "uuid": "...",
  "status": "pending_payment",
  "commercial_type": "RENTAL",
  "payment_method": "WOMPI",
  "base_cost": "1000000.00",
  "transport_total": "22000.00",
  "setup_total": "0.00",
  "tax_amount": "194180.00",
  "grand_total": "1216180.00"
}
```

Si `commercial_type=COMODATO`: `status` viene `pending_validation` directo, `payment_method`
viene `COMODATO`, `base_cost` viene `0.00`.

**Regla critica DRF para acciones custom:**
`process-payment`, `attachments` y `cancel` son metodos `@action` y deben vivir dentro de
`RentalRequestViewSet`, que es la clase registrada en `DefaultRouter`. No ubicarlos dentro de
`RentalRequestListCreateAPIView`: Django compila, pero el router no registra la ruta y el
frontend recibira 404.

---

### Otros ViewSets

| ViewSet | URL prefix | Acciones admin | Acciones publicas |
|---------|-----------|----------------|-------------------|
| EquipmentVariantViewSet | `/variants/?equipment=<uuid>` | — | `list` unicamente |
| RentingCategoryViewSet | `/categories/` | — | `ReadOnlyModelViewSet`: list, retrieve |
| RentingBrandViewSet | `/brands/` | — | `ReadOnlyModelViewSet`: list, retrieve |
| RentalLaborViewSet | `/labor/` | — | `ReadOnlyModelViewSet`: list, retrieve |

**[CORREGIDO 2026-07-23]** Los 4 ViewSets de arriba son de **solo lectura** en `renting/api/` —
ninguno tiene `create`/`partial_update`/`destroy` (versiones previas de este documento decian
"CRUD completo" para Category/Brand/Labor, lo cual era incorrecto). El CRUD real de variantes,
categorias, marcas y mano de obra vive todo en `dashboard/api/` (`AdminEquipmentViewSet` para
variantes vía `/api/v1/dashboard/equipment/{uuid}/variants/`+`variants/create`+`variants/{pk}`;
`AdminRentingCategoryViewSet`/`AdminRentingBrandViewSet`/`AdminRentalLaborViewSet` para el
resto), consistente con la regla del proyecto "lectura publica en `<app>/`, escritura en
`dashboard/`".

---

### EquipmentBlockViewSet — `/api/v1/renting/equipment-blocks/` (2026-07-14)

Admin-only (sin lectura publica — es informacion operativa interna, el `reason` no
debe filtrarse). Sigue la misma excepcion documentada que `RentalRequestViewSet`:
pega directo a `renting/` (no a `dashboard/`) porque el permiso es por-accion.

| Metodo | URL | Permiso | Descripcion |
|--------|-----|---------|-------------|
| GET | `/equipment-blocks/?variant=<uuid>` | IsAdminUser | Lista bloqueos de una variante |
| GET | `/equipment-blocks/?equipment=<uuid>` | IsAdminUser | Lista bloqueos de todas las variantes de un equipo |
| GET | `/equipment-blocks/?status=active\|released&block_type=...` | IsAdminUser | Filtros adicionales |
| POST | `/equipment-blocks/` | IsAdminUser | Crea un bloqueo (`EquipmentBlockCommands.create_block`) |
| POST | `/equipment-blocks/{uuid}/release/` | IsAdminUser | Libera un bloqueo (`EquipmentBlockCommands.release_block`) |

**POST /equipment-blocks/ — payload:**
```json
{
  "equipment_variant": "<variant-uuid>",
  "block_type": "MAINTENANCE",
  "start_date": "2026-08-01",
  "end_date": "2026-08-05",
  "quantity": 1,
  "reason": "Mantenimiento preventivo"
}
```

---

### Endpoints admin del Catalogo Enriquecido y Marketing (2026-07-16, `/api/v1/dashboard/`)

**[AGREGADO 2026-07-23, no capturado en ninguna version previa de este documento.]** A
diferencia del resto de `renting`, estos 12 recursos viven **directamente** en `dashboard/api/`
(`dashboard/api/renting_catalog_views.py`, patron `EquipmentCatalogChildViewSet`), CRUD
completo `IsAdminUser`, todos filtrados por `?equipment=<uuid>`:

| Endpoint | Modelo |
|---|---|
| `/api/v1/dashboard/equipment-images/` | `EquipmentImage` |
| `/api/v1/dashboard/rental-included-items/` | `RentalIncludedItem` |
| `/api/v1/dashboard/rental-excluded-items/` | `RentalExcludedItem` |
| `/api/v1/dashboard/rental-features/` | `RentalFeature` |
| `/api/v1/dashboard/rental-specification-groups/` | `RentalSpecificationGroup` |
| `/api/v1/dashboard/rental-specifications/` | `RentalSpecification` |
| `/api/v1/dashboard/rental-requirements/` | `RentalRequirement` |
| `/api/v1/dashboard/rental-services-included/` | `RentalServiceIncluded` |
| `/api/v1/dashboard/rental-optional-services/` | `RentalOptionalService` |
| `/api/v1/dashboard/rental-faqs/` | `RentalFAQ` |
| `/api/v1/dashboard/rental-videos/` | `RentalVideo` |
| `/api/v1/dashboard/rental-documents/` | `RentalDocument` |

Los endpoints de `marketing/`, `commercial-config/` y `commercial-options/` (acciones custom
de `AdminEquipmentViewSet`, no ViewSets propios) ya estan documentados en la seccion
"EquipmentCommercialConfig, EquipmentCommercialOption y EquipmentMarketing" (Modelos, arriba)
— no se repiten aqui.

---

## Services

### RentingSelector — Lectura

```python
class RentingSelector:
    list_all_for_admin()          # Equipment con logistics_config, variants, images
    list_available_equipment()    # Solo activos con variants.stock > 0 (DISTINCT)
    list_featured()               # is_featured=True para home feed
    get_by_uuid(uuid)             # Detalle con logistics_config, variants, images, reviews
    check_availability(variant_id, start_date, end_date, quantity=1)  # bool -- wrapper sobre AvailabilityEngine.is_available()
    list_categories()             # [AGREGADO 2026-07-23] solo is_active -- usado por RentingCategoryViewSet
    list_brands()                 # [AGREGADO 2026-07-23] usado por RentingBrandViewSet
    list_rental_labor()           # [AGREGADO 2026-07-23] solo is_active -- usado por RentalLaborViewSet

class EquipmentVariantSelector:
    list_for_equipment(equipment_uuid)
    get_by_uuid(variant_uuid)

class RentalRequestSelector:
    list_for_user(user)
    list_all_for_admin()
    get_by_uuid_for_user(uuid, user)
    get_by_uuid_for_admin(uuid)
```

Selectors adicionales exportados desde `services/selectors.py`: `EquipmentBlockSelector` (ver
seccion dedicada abajo), `EquipmentReturnInspectionSelector` (ver modelo arriba),
`EquipmentReviewSelector.list_for_equipment(equipment_uuid)` **[AGREGADO 2026-07-23]**,
`EquipmentCommercialOptionSelector` **[AGREGADO 2026-07-23]** (usado por
`RentingAdminOrchestrator.list_commercial_options()`).

---

### RentalRequestCommands — Escritura Atomica

```python
class RentalRequestCommands:

    @staticmethod
    @transaction.atomic
    def create_request(user, validated_data) -> RentalRequest:
        """
        1. Verifica disponibilidad (best-effort, fail-fast de UX -- YA NO toma lock).
        2. Calcula base_cost segun rental_mode (days/hours) -- COMODATO: base_cost=0 siempre.
        3. Lee costos de EquipmentLogisticsConfig (delivery, pickup, install, etc.) -- igual
           para ambas modalidades comerciales.
        4. Calcula subtotal, tax_amount, grand_total.
        5. Crea RentalRequest: status=pending_payment (RENTAL) o pending_validation (COMODATO,
           salta el pago por completo -- ver seccion "Modalidad Comercial"). Fija commercial_type
           y payment_method (COMODATO usa PAYMENT_COMODATO, nunca el default WOMPI).
        6. COMODATO: notifica solo a admin_notifications (rental_comodato_review_pending) --
           regla PaymentResult, nunca al cliente en esta funcion.
        NO crea RentalPeriod: pending_payment/pending_validation nunca bloquean agenda.

        [CORREGIDO 2026-07-23] Esta funcion NO notifica al usuario via WebSocket en ningun
        caso (versiones previas de este documento lo afirmaban para el flujo general) -- la
        unica notificacion que dispara es la de admin, y solo para COMODATO.
        """

    @staticmethod
    @transaction.atomic
    def process_payment_selection(rental_request, payment_method, extra_data=None) -> dict:
        """
        [AGREGADO 2026-07-23, no capturado en ninguna version previa] Reemplaza lo que el
        endpoint `process-payment/` describia inline -- la logica real vive aqui. Exige
        status=pending_payment (lanza ValueError si no). Fija `rental_request.payment_method`
        de inmediato (antes de resolver cada rama), luego:
          - COD: pending_payment -> pending_validation, notifica admin_notifications
            (rental_cod_review_pending). No bloquea agenda todavia.
          - NEQUI: exige phone_number, delega a NequiCommands.initialize_rental_transaction().
          - WOMPI (default): delega a WompiCommands.initialize_transaction(rental_request,
            card_token=...) -- MISMA infraestructura de Transaction que ordenes de tienda/
            servicios (SSoT de payment, no una copia propia de renting). Si card_token viene
            presente, la transaccion se crea sincrona en Wompi (sin widget); si no, retorna
            los datos para abrir el Widget completo. Guarda wompi_reference = str(Transaction.uuid).
        """

    @staticmethod
    def add_project_attachments(rental_request, files, uploaded_by=None) -> list:
        """
        [AGREGADO 2026-07-23, no capturado en ninguna version previa] Crea hasta 10
        `RentalProjectAttachment` (limite validado aqui, no en el serializer) para una
        RentalRequest ya existente. Usado por el paso "Lugar del proyecto" del wizard
        (subida ocurre DESPUES de crear la solicitud, no antes).
        """

    @staticmethod
    @transaction.atomic
    def confirm_payment(rental_request) -> None:
        """
        Punto autoritativo de lock+disponibilidad para Wompi/Nequi aprobados.
        select_for_update(variant) + AvailabilityEngine.is_available(); si hay cupo,
        crea el RentalPeriod (scheduled) y pasa a status=paid; si no, llama
        _flag_payment_conflict(refund_required=True) -> status=payment_conflict.
        Idempotente sobre cualquier estado ya resuelto (paid/confirmed/in_operation/
        finished/cancelled/payment_conflict).
        """

    @staticmethod
    @transaction.atomic
    def approve_manual_validation(rental_request, admin_user=None) -> RentalRequest:
        """
        Punto autoritativo de lock+disponibilidad para COD (admin aprueba desde el
        panel). Mismo patron que confirm_payment pero refund_required=False (no se
        cobro nada). pending_validation -> confirmed (+ RentalPeriod scheduled) o
        -> payment_conflict si perdio la carrera.
        """

    @staticmethod
    @transaction.atomic
    def reject_request(rental_request, admin_user=None, reason='') -> RentalRequest:
        """Rechaza COD pending_validation -> cancelled. No existe RentalPeriod aun."""

    @staticmethod
    @transaction.atomic
    def activate_period(rental_request) -> RentalRequest:
        """'Marcar entregado': paid/confirmed -> in_operation, RentalPeriod scheduled -> active."""

    @staticmethod
    @transaction.atomic
    def release_period(rental_request, admin_user=None, reason='') -> RentalRequest:
        """Override admin: libera la agenda (periodo -> cancelled) sin tocar RentalRequest.status."""

    @staticmethod
    @transaction.atomic
    def extend_period(rental_request, new_end_date, admin_user=None, reason='') -> RentalRequest:
        """
        Extension de renta (2026-07-14). Admin-only, solo modo dias, solo desde
        paid/confirmed/in_operation. Valida disponibilidad del rango adicional
        [end_date actual, new_end_date) con AvailabilityEngine.is_available() (sin
        select_for_update extra: ya se toma sobre la RentalRequest y el RentalPeriod
        al inicio del metodo). Mueve RentalPeriod.end_date, recalcula
        total_rental_days/base_cost/tax_amount/grand_total (transport_total/
        setup_total no cambian, son costos de una sola vez). NO genera cobro
        automatico -- el admin gestiona la diferencia manual/offline, mismo patron
        que COD.
        """

    @staticmethod
    @transaction.atomic
    def release_on_payment_failure(rental_request) -> None:
        """
        Wompi/Nequi DECLINED/VOIDED/FAILED/REJECTED/ERROR -> status=cancelled.
        Normalmente no-op sobre RentalPeriod (aun no existe antes de confirmar pago).
        """

    @staticmethod
    @transaction.atomic
    def cancel_request(rental_request) -> RentalRequest:
        """
        Cambia status a cancelled.
        Cancela todos los RentalPeriod scheduled/active asociados (normalmente 0 filas
        si se cancela antes de pagar).
        """

    @staticmethod
    @transaction.atomic
    def complete_period(rental_request) -> None:
        """
        Marca periodos active como completed. Cambia status de RentalRequest a
        finished. Idempotente.
        """
```

---

### EquipmentBlockCommands / EquipmentBlockSelector (2026-07-14)

```python
class EquipmentBlockCommands:
    create_block(equipment_variant, block_type, start_date, end_date, reason, quantity=1, admin_user=None)
        # Override admin: NO valida contra AvailabilityEngine.is_available().
    release_block(block, admin_user=None, reason='')
        # Idempotente si ya esta STATUS_RELEASED.

class EquipmentBlockSelector:
    list_for_variant(variant_uuid, active_only=False)
    list_for_equipment(equipment_uuid, active_only=False)
    get_by_uuid(uuid)
```

---

### EquipmentReviewCommands (2026-07-23)

```python
class EquipmentReviewCommands:
    @staticmethod
    def create_review(user, equipment, rating, comment) -> EquipmentReview:
        """Valida que el usuario haya alquilado y devuelto (finished) el equipo antes de
        permitir la reseña -- guard real que el modelo no puede expresar (el modelo solo
        garantiza 1 reseña/usuario/equipo). Lanza ValueError si no cumple."""
```

---

### Configs OneToOne de Equipment — Commands (2026-07-16, patron identico entre las 4)

```python
class EquipmentLogisticsConfigCommands:      upsert(equipment, **fields);  delete(equipment)
class EquipmentCommercialConfigCommands:     upsert(equipment, **fields);  delete(equipment)
class EquipmentMarketingCommands:            upsert(equipment, **fields);  delete(equipment)
class EquipmentCommercialOptionCommands:     upsert(equipment, modality, term_months, is_enabled=True);  delete(option_uuid)
```

`upsert()` en las 3 primeras es get-or-create + update (una sola config por Equipment,
`OneToOneField`); `EquipmentCommercialOptionCommands.upsert()` es create-or-update por
`(equipment, modality, term_months)` ya que un Equipment puede tener varias opciones de plazo.

---

### catalog.py — Selector+Commands del Catalogo Enriquecido (2026-07-16)

`services/catalog.py` (657 lineas) define un par Selector/Commands por cada uno de los 11
modelos de la seccion "Catalogo Enriquecido de Equipment" (Modelos, arriba) —
`RentalIncludedItemSelector`/`Commands`, `RentalExcludedItemSelector`/`Commands`, ...,
`RentalDocumentSelector`/`Commands`, mas `EquipmentImageSelector`/`Commands` (movido aqui
desde donde vivia antes de la migracion `0022`). Los 11 pares siguen el mismo patron:

```python
class <Modelo>Selector:
    list_for_equipment(equipment_uuid) -> QuerySet
    get_by_uuid(uuid)

class <Modelo>Commands:
    create(equipment, **fields)
    update(instance, **fields)
    delete(instance)
    toggle_active(instance)             # activar/desactivar sin borrar
    duplicate(instance)                 # clonar fila (no en RentalSpecificationGroup)
    reorder(equipment_id, ordered_uuids)  # actualiza `position` en lote
```

`RentalDocumentCommands` tiene ademas `register_download(document)` (incrementa `downloads`,
usado por el endpoint publico `register-download/`). No se repiten los 11 pares completos aqui
— mismo criterio de la tabla de la seccion "Catalogo Enriquecido de Equipment".

---

### RentingCommands — Flujo Legacy

```python
class RentingCommands:
    @staticmethod
    @transaction.atomic
    def process_rental_order(user, equipment_variant, start_date, end_date, mode, shipping_address):
        """
        Flujo legacy: crea Order + OrderItem directamente (sin RentalRequest/wizard).
        Usa check_availability() para validar fechas.
        NO crea RentalPeriod (no tiene rental_request para vincular).
        """
```

---

### RentingSummaryProvider — Estadisticas

```python
class RentingSummaryProvider:
    @staticmethod
    def get_summary() -> dict:
        """
        Retorna:
        - total_equipment_variants: variantes con stock > 0
        - currently_rented_out: RentalPeriod con status=active
        - stale_equipment_count: variantes sin periodos en ultimos 30 dias
        - stale_equipment_variant_ids: lista de IDs para acciones de marketing
        - top_rented_equipment: top 5 por OrderItem (ordenes paid)
        """
```

No depende de `StockRecord` ni `InventorySelector`. Usa `RentalPeriod` directamente.

---

## Wizard Frontend — 4 Pasos (rediseñado, reemplaza los "7 pasos" de versiones previas)

> **[REESCRITO 2026-07-23]** El componente se **renombro** de `RentalRequestWizard.vue` a
> `RentalBookingWizard.vue` y se **redujo de 7 a 4 pasos visibles** consolidando varios pasos
> antiguos en pantallas mas grandes. El pago dejo de ser un paso del wizard: ahora es una
> pantalla separada (`RentalConfirmationView.vue`). Ruta y nombre de ruta **no cambiaron**
> (`/alquiler/equipo/:uuid/solicitar`, `name: 'rental-request'`) — solo el archivo/componente
> detras de esa ruta. El `import` en `router.js` conserva el alias de variable
> `RentalRequestWizard` (nombre viejo) apuntando al archivo nuevo — no es un error, solo un
> nombre de variable sin actualizar.

Ruta: `/alquiler/equipo/:uuid/solicitar`
Componente: `frontend/src/views/customer/renting/RentalBookingWizard.vue`

```
Paso 1 — Equipo              Seleccion de variante, precios, stock visible
Paso 2 — Lugar del proyecto  Direccion/ciudad/departamento/tipo de proyecto/condiciones del
                              lugar + fotos y documentos de reconocimiento (RentalProjectAttachment,
                              hasta 10 archivos, subidos DESPUES de crear la solicitud)
Paso 3 — Programacion        Fechas inicio/fin, cantidad, modo (dias/horas), prioridad
                              [verificacion de disponibilidad en el mismo paso]
Paso 4 — Confirmar           Resumen (equipo/lugar/fechas) + datos del responsable
                              (antes "Paso 3") + checkbox de terminos + boton "Confirmar reserva"
```

Los antiguos "Paso 3 — Responsable" y "Paso 5 — Contrato" se fusionaron dentro del Paso 4
actual; el antiguo "Paso 6 — Resumen" tambien vive ahi. El calculo de costos en tiempo real
(antes descrito como "Flujo del Paso 6") sigue existiendo igual, solo que ahora se muestra
dentro del Paso 4.

**Selector de modalidad comercial:** `draft.commercialType` (`'RENTAL'` por default) se envia
tal cual al crear la solicitud — el wizard no valida contra `EquipmentCommercialConfig` en el
frontend (el backend es quien decide si el equipo admite Comodato); ver seccion "Modalidad
Comercial" arriba.

### `submit()` — creacion de la solicitud (reemplaza el viejo "Paso 6/7")

```javascript
async function submit() {
  const created = await bookingService.create({
    equipment_variant: selectedVariant.value.uuid,
    commercial_type: draft.commercialType,       // 'RENTAL' | 'COMODATO'
    location_address, location_city, location_department, project_type,
    access_conditions, location_notes,
    contact_full_name, contact_doc_type, contact_doc_number,
    contact_email, contact_phone, contact_company,
    start_date, end_date, quantity, estimated_hours, rental_mode,
    delivery_time, pickup_time,                  // solo si rental_mode === 'hours'
    priority: s.priority,
    terms_accepted: draft.termsAccepted,
  });
  // POST /renting/rental-requests/ (RentalRequestListCreateAPIView)

  if (projectFiles.value.length)
    await bookingService.uploadAttachments(created.uuid, projectFiles.value.map(f => f.file));
  // POST /renting/rental-requests/{uuid}/attachments/

  if (draft.commercialType === 'COMODATO') {
    // Comodato no tiene paso de pago (create_request() ya la deja en
    // pending_validation) -- salta directo a la pantalla de resultado,
    // reusando la misma rama que ya maneja COD-Renting (mismo estado:
    // "solicitud registrada, pendiente de aprobacion", sin pago).
    router.push({ path: '/payment/result', query: { status: 'RENTAL_COD_APPROVED', rental_uuid: created.uuid } });
  } else {
    router.push({ name: 'rental-confirmation', params: { uuid: created.uuid } });
  }
}
```

### Pantalla de pago separada — `RentalConfirmationView.vue` (`/alquiler/reserva/:uuid`)

Ya NO es un paso del wizard. Ofrece el sub-selector Tarjeta(API)/PSE-Otros/Nequi/COD (ver
"Integracion con Wompi" mas abajo para el detalle completo, no se repite aqui). Tras un pago
aprobado (o una solicitud COD confirmada), redirige a `/alquiler/reserva/:uuid/exito`
(`RentalSuccessView.vue`, **ruta nueva no capturada en versiones previas de este documento**)
— pantalla final con numero corto de reserva, estado (`APPROVED`/`COD`), enlaces a "Mis
alquileres"/catalogo y boton de descarga de comprobante (`window.print()`).

---

## Flujo Completo de una Solicitud de Renta

```
1. Usuario navega a /alquiler/equipo/:uuid/solicitar

2. [Paso 1] Selecciona variante
   GET /renting/equipment/{uuid}/
   → Retorna equipment con variants, images, logistics_config, catalogo enriquecido

3. [Paso 3] Selecciona fechas
   GET /renting/equipment/{uuid}/check-availability/?variant=...&start_date=...&end_date=...
   → { available: true/false }
   Si false: muestra alert rojo "El equipo no tiene disponibilidad..."

4. [Paso 4] Revisa resumen, completa datos del responsable, acepta terminos y confirma
   POST /renting/rental-requests/
   → Serializer valida disponibilidad (segunda verificacion, best-effort)
   → RentalRequestCommands.create_request():
       a. Tercera verificacion de disponibilidad (best-effort, sin lock)
       b. Calcula costos desde EquipmentLogisticsConfig (Comodato: base_cost=0)
       c. Crea RentalRequest — status=pending_payment (Renting) o pending_validation (Comodato)
       d. NO crea RentalPeriod todavia (ver "Prevencion de Doble Reserva" abajo)
   → 201 con grand_total calculado
   POST /renting/rental-requests/{uuid}/attachments/ (si hay fotos/documentos del proyecto)

5. Comodato: salta directo a /payment/result (pendiente de aprobacion admin, sin pago)
   Renting: redirige a /alquiler/reserva/:uuid (RentalConfirmationView.vue)

6. [RentalConfirmationView] Paga
   POST /renting/rental-requests/{uuid}/process-payment/
   → WOMPI (Tarjeta, card_token presente): transaccion sincrona via WompiCommands, sin widget
   → WOMPI (PSE/Otros, sin card_token): datos del widget Wompi
   → NEQUI: crea NequiTransaction y retorna { nequi_tx_uuid }
   → COD: pending_validation, notifica a admin_notifications
   → Al aprobarse (webhook Wompi/Nequi o admin COD): confirm_payment()/approve_manual_validation()
     crea el RentalPeriod (lock+disponibilidad autoritativos) — recien AHI se bloquea la agenda
   → Redirige a /alquiler/reserva/:uuid/exito (RentalSuccessView.vue)
```

---

## Prevencion de Doble Reserva

Reescrito en la Fase 1 del Plan Maestro de Renting (2026-07-07): `pending_payment` ya NO
crea `RentalPeriod` ni bloquea agenda, asi que dos solicitudes solapadas para el mismo
equipo pueden coexistir en `pending_payment` sin conflicto -- el conflicto real solo
puede ocurrir cuando ambas intentan *confirmarse* (pagar o ser aprobadas por un admin)
para las mismas fechas. Por eso el lock de concurrencia (`select_for_update` sobre
`EquipmentVariant` + `AvailabilityEngine.is_available()`) vive en `confirm_payment()` y
`approve_manual_validation()`, no en `create_request()`.

```
Stock = 1 unidad (Escalera)

Request A: Jul 1-5  → create_request() → status=pending_payment (SIN RentalPeriod)
Request B: Jul 3-7  → create_request() → status=pending_payment (SIN RentalPeriod)
  Ambas se crean sin problema: pending_payment nunca ocupa agenda.

Request A confirma pago (Wompi APROBADO) primero:
  confirm_payment(A): lock variant, AvailabilityEngine.is_available(Jul-1,Jul-5) → TRUE
  → RentalPeriod(Jul-1,Jul-5,scheduled) creado, A.status = paid

Request B confirma pago despues (mismas fechas ya tomadas):
  confirm_payment(B): lock variant, AvailabilityEngine.is_available(Jul-3,Jul-7) → FALSE
    (occupied=1 por el periodo de A, stock=1 → (1-1)>=1 es FALSE)
  → B.status = payment_conflict, B.refund_required = True
  → Notifica al cliente y a un admin (admin_notifications) para reembolso manual.
```

Request C (Jul 10-15, sin overlap con A) confirma pago normalmente sin conflicto.

---

## Patrones de Diseno

### Service Layer (Commands + Selectors)
- **Commands**: toda escritura es `@transaction.atomic`, cero ORM en views.
- **Selectors**: toda lectura, sin efectos secundarios.

### Availability Calendar (RentalPeriod)
- Reemplaza la dependencia de `InventorySelector`/`StockRecord`.
- Autocontenido dentro del modulo renting.
- Algoritmo de solapamiento de intervalos.

### Defense in Depth (Disponibilidad)
- **Capa 1**: `goStep5()` en frontend — llama `check-availability` antes de avanzar.
- **Capa 2**: `RentalRequestInputSerializer.validate()` — retorna 400.
- **Capa 3**: `RentalRequestCommands.create_request()` — lanza `ValueError`.

### Decoupled Pricing
- Costos de logistica vienen del modelo `EquipmentLogisticsConfig`, no del usuario.
- IVA configurable via `RentalCostRule` + `RentalPricingCalculator`.
- Frontend replica el calculo para mostrar el total antes de confirmar.

---

## Integracion con Wompi

El modulo tiene su propio endpoint de inicializacion de pago (no reutiliza el de `orders`):

```
POST /renting/rental-requests/{uuid}/process-payment/
```

- Calcula `amount_in_cents` desde `rental_request.grand_total`.
- Genera `integrity_signature` = SHA256(`reference + amount + currency + WOMPI_INTEGRITY_SECRET`).
- Usa el UUID de `RentalRequest` como `reference` de Wompi.
- Guarda la referencia en `rental_request.wompi_reference`.

`initialize-payment` puede existir como endpoint auxiliar legacy, pero el wizard actual
debe usar `process-payment` para soportar Wompi, Nequi y COD desde un unico contrato.

El webhook de Wompi (`/wompi/payments/webhook/`) SI actualiza automaticamente el estado
de `RentalRequest` desde la Fase 1 del Plan Maestro (2026-07-07):
`APPROVED` → `RentalRequestCommands.confirm_payment()` (crea el `RentalPeriod` si hay
cupo, o marca `payment_conflict` si no); `DECLINED/VOIDED/FAILED` →
`RentalRequestCommands.release_on_payment_failure()` (cancela la solicitud). El mismo
patron aplica al lado Nequi en `NequiCommands.check_and_update_status()`
(`APPROVED`/`REJECTED`/`ERROR`).

### Actualizacion 2026-07-22 — Flujo hibrido Tarjeta(API)/Widget (generalizacion del ADR-001 de `payment`)

Las dos secciones de arriba describen el estado pre-ADR-001 (Widget de Wompi como unico camino).
**Estado real vigente**, verificado con smoke test E2E: el pago de Renting hoy vive en
`RentalConfirmationView.vue` (`/alquiler/reserva/:uuid`, ruta separada a la que el wizard de 7 pasos
redirige tras crear el `RentalRequest`), que ofrece el mismo sub-selector **Tarjeta / PSE-Otros**
que Shop y Servicios Tecnicos, via el composable compartido `useCardOrWidgetPayment.js` +
`CardOrWidgetPanel.vue` (fuente de verdad completa del diseño: `payment/.AGENT/docs/
ARQUITECTURA_COMPLETA_PAYMENT.md` §10.2-10.6, este documento no la duplica). Puntos especificos de
Renting dentro de ese flujo compartido:

- `process-payment/` (endpoint de este modulo, arriba) acepta ahora tambien `card_token` opcional
  y lo reenvia a `WompiCommands.initialize_transaction()` — si se pasa, la transaccion se crea
  sincronamente contra Wompi (sin abrir ningun Widget) y `Transaction.initiation_channel` queda
  `CARD_API`; si no, comportamiento identico al de siempre (Widget completo, `initiation_channel`
  `WIDGET`).
- `renting/api/views.py::process_payment()` respeta los mismos 2 kill-switches de
  `PaymentFeatureFlags` (`card_api_flow_enabled`/`widget_flow_enabled`) que `payment` — agregado
  2026-07-22, antes Renting no tenia ningun kill-switch backend para su pago online.
- `RentalConfirmationView.vue` SI oculta la opcion "Nequi Push" cuando `NEQUI_*` no esta configurado
  (`nequiEnabled`, obtenido en el mismo `onMounted` combinado que carga el resto del checkout) — a
  diferencia de `CheckoutView.vue` (Shop), que no tiene este guard todavia (gap real documentado en
  `payment/.AGENT/docs/ARQUITECTURA_COMPLETA_PAYMENT.md` §10.6, pendiente).
- **Bug real encontrado y corregido en el smoke test de esta fecha:** las tarjetas guardadas del
  cliente nunca se mostraban en este checkout — `watch(method, (m) => { if (m === 'WOMPI')
  fetchSavedCards(); })` no tenia `{ immediate: true }`, y `method` ya vale `'WOMPI'` por defecto al
  montar la vista, asi que el watcher nunca disparaba. Corregido agregando `{ immediate: true }`.
  Verificado end-to-end: pago con tarjeta guardada resuelve `Transaction.status='APPROVED'` /
  `initiation_channel='CARD_API'`, correctamente vinculado al `RentalRequest`.

---

## Integracion con Otros Modulos

```
RENTING
  ├── payment                → WompiCommands.initialize_transaction() (process_payment_selection),
  │                             NequiCommands.initialize_rental_transaction() -- [CORREGIDO
  │                             2026-07-23] la app se llama `payment`, NUNCA `wompi` (ver
  │                             IMPLEMENTATION_SUMMARY.md, regla critica #12 del proyecto).
  │                             settings.WOMPI_PUBLIC_KEY/WOMPI_WIDGET_URL se leen directo en
  │                             process_payment_selection() como fallback de la respuesta.
  ├── payment.PaymentFeatureFlags → card_api_flow_enabled/widget_flow_enabled (kill-switches,
  │                             ver "API Endpoints" -> process-payment)
  ├── orders.OrderItem       → top_rented en RentingSummaryProvider; OrderCommands.create_from_rental()
  │                             se llama desde confirm_payment()/approve_manual_validation()
  │                             (ver renting/CLAUDE.md, "Regla PaymentResult")
  ├── operations.DispatcherProfile → RentalOperation.assigned_dispatcher (mismo pool que Shop/Servicios)
  ├── notifications.NotificationCommands → dispatch_notification() -- [CORREGIDO 2026-07-23]
  │                             `create_request()` NO notifica al usuario via WebSocket en
  │                             ningun caso (solo COMODATO notifica, y solo a admin_notifications)
  ├── users.permissions      → IsBuyerOrAdmin (lectura/escritura de RentalRequest), IsAdminUser
  │                             (acciones admin) -- ambos de `users.api.permissions`
  └── core.HomeConfigView    → list_featured() para el home publico

INDEPENDIENTE DE:
  ├── inventory.StockRecord  → NO se usa para disponibilidad
  └── inventory.InventorySelector → NO se usa
```

---

## Migraciones Aplicadas

**[ACTUALIZADO 2026-07-23]** 32 migraciones a la fecha (versiones previas de este documento
listaban hasta la 0021 y omitian 0010-0012).

| Migracion | Contenido |
|-----------|-----------|
| 0001_initial | RentingCategory, RentingBrand, Equipment, EquipmentVariant, EquipmentImage, EquipmentReview, RentalLabor |
| 0002, 0003 | RentalRequest (modelo completo con todos los campos) |
| 0004 | RentalCostRule |
| 0005 | EquipmentLogisticsConfig |
| 0006 | RentalPeriod con indices compuestos |
| 0007 | Renombrado automatico de indices (sin cambio de esquema) |
| 0008 | Soporte de multiples metodos de pago en RentalRequest |
| 0009 | Prioridad de agendamiento LOW/HIGH en RentalRequest |
| 0010 | `RentalProjectAttachment` |
| 0011 | Renombrado de indices de `EquipmentImage` y otros (sin cambio de esquema) |
| 0012 | Ajustes de `Equipment.is_active` y otros campos menores |
| 0013 | Fase 1 Plan Maestro: STATUS_PAYMENT_CONFLICT, refund_required, admin_notes, delivery_time/pickup_time en RentalRequest; start_time/end_time/rental_mode + indice compuesto en RentalPeriod |
| 0014-0018 | Notificaciones de renting, RentalOperation/RentalOperationEvent, incidentes, plantillas de ciclo de vida (ver "Operaciones de Renting" abajo) |
| 0019 | `EquipmentBlock` (bloqueo manual mantenimiento/daño/inventario) |
| 0020 | Siembra `PeriodicTask` de `expire_abandoned_pending_payment_requests` (django_celery_beat, sin cambio de esquema) |
| 0021 | `EquipmentReturnInspection` (inspeccion de devolucion, opcional/aparte) |
| **0022** | **[2026-07-16]** `catalog_detail_models` -- los 11 modelos del "Catalogo Enriquecido de Equipment" completos + SEO (`meta_title`/`meta_description`/`meta_keywords`/`og_image`) en `Equipment` + extension de `EquipmentImage` (`image_type`, `position`) |
| 0023 | `EquipmentReview` gana `unique_together` (1 reseña por usuario/equipo) |
| 0024 | `EquipmentVariant.is_active` gana `db_index=True` |
| 0025 | Actualiza plantillas de notificacion de resultado de pago |
| 0026 | Elimina el FK directo `EquipmentImage.variant` (la galeria quedo 100% a nivel `Equipment`, no por variante) |
| 0027 | `remove_applies_globally_from_rentalcostrule` -- ver correccion arquitectonica en la seccion `RentalCostRule` |
| 0028 | `EquipmentMarketing` |
| 0029 | Siembra `PeriodicTask` de vencimientos de renta (`notify_rentals_expiring`) |
| **0030** | **[2026-07-22]** `commercial_type` en `RentalRequest` y `RentalPeriod` (Renting vs. Comodato) + campos relacionados |
| 0031 | Siembra plantillas de notificacion de Comodato (`rental_comodato_review_pending`, etc.) |
| 0032 | `PAYMENT_COMODATO` agregado a `RentalRequest.payment_method` choices |

---

## Pendiente / Roadmap

### Operaciones de Renting (2026-07-07)

El ciclo operativo ya no depende funcionalmente del listado generico de Orders/Operations.
`RentalOperation` mantiene una relacion 1:1 con `RentalRequest`, estado logistico propio,
programacion de entrega/recogida, transportista, vehiculo, ruta y prioridad.
`RentalOperationEvent` registra el timeline auditable. Ambos se crean/gestionan mediante
`RentalOperationCommands` y `RentalOperationSelector`.

- API admin exclusiva: `/api/v1/renting/operations/`.
- Panel exclusivo: `/panel/ordenes/renting`.
- La operacion nace automaticamente en `READY_FOR_SCHEDULING` desde
  `confirm_payment()` o `approve_manual_validation()`.
- La asignacion solo se permite despues de programar y encola los emails especificos
  `rental_dispatch_assigned` y `rental_delivery_scheduled`.
- El `OperationTicket` comun se conserva temporalmente como infraestructura compartida de
  seguimiento; no es la fuente de verdad del ciclo operativo de Renting.
- **Cerrado (2026-07-07)**: `RentalOperation.has_incident`/`incident_notes` +
  `RentalOperationCommands.report_incident()`/`resolve_incident()` (acciones
  `report-incident`/`resolve-incident`); `RentalOperationSelector.dashboard_metrics()`
  expuesto en `GET /api/v1/renting/operations/dashboard/` (8 indicadores: pendientes de
  programar, sin transportista, entregas/recogidas de hoy, en operacion, proximas a
  devolucion, retrasos, incidencias) — calculado en el backend, no desde la pagina
  actual del listado (el listado pagina a 20 por `PAGE_SIZE`, contar sobre `items`
  en el frontend subestimaba los indicadores). Emails de ciclo de vida completos:
  `rental_operation_created` (al encolar), `rental_equipment_delivered` (DELIVERED),
  `rental_pickup_scheduled` (READY_FOR_PICKUP), `rental_completed` (COMPLETED),
  sembrados en `0018_seed_rental_operation_lifecycle_templates.py`. `schedule()`
  ahora acepta `priority` opcional (LOW/HIGH) para que el operador la redefina al
  programar, tal como pide la Fase 7 del plan maestro; si no se envia, conserva la
  heredada de `RentalRequest.priority` al crear la operacion.
- **Bug real encontrado y corregido (2026-07-07)**: la accion `dispatch` del
  `RentalOperationViewSet` se llamaba literalmente `def dispatch(self, request, uuid=None)`,
  lo que sobreescribia `View.dispatch()` -- el metodo interno que DRF invoca para
  enrutar CUALQUIER solicitud a la vista. Como consecuencia, toda request al ViewSet
  (list, dashboard, schedule, etc.) ejecutaba silenciosamente la logica de esa accion
  en vez de la solicitada. No lo detectaban los tests porque `RentalOperationCommands`
  se probaba directo, sin pasar por el ViewSet. Renombrado a `mark_ready_for_delivery`
  con `url_path='dispatch'` (URL publica sin cambios) + cobertura HTTP nueva en
  `RentalOperationApiEndpointsTestCase`. Ver tambien nota en `.AGENT.md` si se agregan
  acciones nuevas: nunca nombrar un metodo de `@action` igual a un metodo de
  `View`/`APIView`/`GenericAPIView` (`dispatch`, `get_object`, `get_queryset`, etc.).

- ~~**Webhook Wompi → RentalRequest**~~: resuelto en Fase 1 (2026-07-07), ver "Integracion con Wompi".
- ~~**Panel admin de solicitudes (backend + frontend)**~~: resuelto -- endpoints
  `approve/reject/mark-delivered/mark-returned/release-period` (Fase 1) + modulo
  `RentingRequestList.vue`/`RentalRequestActionsPanel.vue` en `/panel/renta/solicitudes`
  (Fase 2).
- ~~**Calendario visual (backend + frontend ligero)**~~: resuelto -- endpoints
  `availability/`, `calendar/`, `timeline/` (Fase 1) + `AvailabilityPill.vue`/
  `AvailabilityCard.vue`/`RentalHourSelector.vue` en el paso 3 del wizard (Fase 2, sin
  grid mensual por decision explicita del usuario).
- ~~**Email de confirmacion tras aprobar**~~: resuelto (2026-07-07) -- `confirm_payment()`
  y `approve_manual_validation()` ahora capturan el `OperationTicket` devuelto por
  `ensure_ticket_for_rental()` y pasan `ticket_number`/`start_date`/`end_date` al contexto
  de `dispatch_notification()`. Plantillas `rental_payment_confirmed`/`rental_cod_confirmed`
  sembradas en `renting/migrations/0014_seed_notification_templates.py` (antes eran slugs
  muertos: no existia NINGUNA plantilla de renting en BD, asi que ningun evento de renting
  disparaba correo/WS/WhatsApp desde que se escribio el codigo). El resto de slugs de
  renting (`rental_request_created`, `rental_cod_review_pending`,
  `rental_payment_conflict_customer/admin`, `rental_request_rejected`,
  `rental_payment_failed`) siguen sin plantilla sembrada -- fuera de alcance de este
  cambio, seguir el mismo patron de migracion si se necesitan.
- ~~**Reconciliacion de pagos**~~: resuelto (2026-07-14) -- el gap real estaba en
  `payment/online/api/views.py::_sync_wompi_status()` (fallback de reconciliacion:
  polling de `PaymentResultView` + tarea periodica `reconcile_pending_wompi_transactions`),
  que solo manejaba `APPROVED` y dejaba `RentalRequest`/`Order` huerfanos en
  `pending_payment` si descubria un `DECLINED/VOIDED/FAILED` que el webhook no
  habia procesado. Ver `payment/.AGENT/docs/ARQUITECTURA_COMPLETA_PAYMENT.md`
  seccion 5.1 para el detalle completo -- el fix vive en `payment`, no en `renting`.
- ~~**Inspeccion de devolucion**~~: resuelto (2026-07-14) -- modelo
  `EquipmentReturnInspection`, ver seccion de Modelos arriba. Opcional/aparte
  (no gatea mark-returned); daño detectado crea `EquipmentBlock` automatico.
- ~~**Extension de renta**~~: resuelto (2026-07-14) -- accion `extend/` admin-only,
  ver "RentalRequestCommands" arriba. Sin cobro automatico (fuera de alcance a
  proposito, decision del usuario): la diferencia se gestiona manual/offline. UI en
  `RentalRequestActionsPanel.vue` ("Extender renta", visible solo si `rental_mode
  === 'days'`).
- ~~**Expiracion de pending_payment**~~: resuelto (2026-07-14) -- `renting/tasks.py::
  expire_abandoned_pending_payment_requests` (Celery beat, sembrada via migracion
  `0020_seed_expire_pending_payment_periodic_task.py`, corre cada hora) cancela con
  `RentalRequestCommands.release_on_payment_failure()` las `RentalRequest` que llevan
  mas de 48h en `pending_payment` sin resolverse. Solo limpieza operativa (deja de
  aparecer como "pendiente" en el panel admin) -- `pending_payment` nunca bloqueo
  agenda, no hay urgencia de disponibilidad. `pending_validation` (COD esperando
  revision de un admin) queda fuera de alcance a proposito: es un proceso de negocio,
  no un abandono.

### Completado (2026-07-16 a 2026-07-22 — no capturado en ninguna version previa de este documento)

- ~~**Catalogo de Equipment al nivel de `shop`**~~: resuelto (2026-07-16, migracion `0022`) --
  11 modelos administrables + SEO + 12 endpoints admin. Ver seccion "Catalogo Enriquecido de
  Equipment".
- ~~**Presentacion comercial/marketing por equipo**~~: resuelto (2026-07-16) -- `EquipmentMarketing`
  (precio promocional, etiquetas, mensajes de conversion).
- ~~**Modalidad Comodato**~~: resuelto (2026-07-22) -- `commercial_type`, `EquipmentCommercialConfig`/
  `EquipmentCommercialOption`, flujo completo sin pago. Ver seccion dedicada.
- ~~**Reduccion de friccion del wizard**~~: resuelto (2026-07-22, sin fecha exacta de commit
  confirmada) -- de 7 pasos a 4, componente renombrado a `RentalBookingWizard.vue`, pago
  movido a pantalla separada (`RentalConfirmationView.vue`). Ver "Wizard Frontend".
- ~~**Eliminacion de duplicacion de firma Wompi**~~: resuelto (2026-07-23, auditoria SSoT de
  Payment) -- `initialize-payment/` eliminado, `process-payment/` es el unico camino.

### Pendiente real / no verificado en esta pasada (2026-07-23)

- `labor_items`/`labor_total` en `RentalRequest` no tienen consumidor activo (ni en
  `create_request()` ni en el wizard actual) -- confirmar si se retoman o se limpian.
- No se verifico si `RentalOperationSelector.dashboard_metrics()`/el board
  `RentalOperationBoard.vue` distinguen visualmente operaciones `COMODATO` de `RENTAL` --
  candidato a revisar si el volumen de Comodato crece.
- No se releyo a fondo `services/operations.py` (274 lineas) ni `services/display.py` en esta
  pasada -- se documentaron via su uso ya confirmado en otras secciones, no via lectura linea
  por linea.
- Los slugs de notificacion `rental_request_created`, `rental_payment_conflict_customer/admin`,
  `rental_request_rejected`, `rental_payment_failed` seguian sin plantilla sembrada segun la
  ultima verificacion (2026-07-07) -- no reconfirmado en esta pasada.

---

**Ultima actualizacion:** 2026-07-23 (auditoria completa contra codigo real -- modelos,
migraciones, endpoints, services y frontend. Encontrados y documentados: 19 modelos faltantes
del "Catalogo Enriquecido de Equipment" + marketing/comercial, la modalidad Comodato completa
(2026-07-22), el rediseno del wizard de 7 a 4 pasos con renombre de componente, la eliminacion
de `initialize-payment/` [2026-07-23], y media docena de correcciones puntuales de permisos/
endpoints. Ver nota de auditoria al inicio del documento para el resumen ejecutivo).

*Version anterior: 2026-07-07 (Fase 1+2 del Plan Maestro de Renting + email de
confirmacion con ticket de servicio tras aprobar -- ver contexto completo en el plan de
implementacion de la sesion).*
