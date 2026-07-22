# ARQUITECTURA COMPLETA - MODULO RENTING

## Descripcion General

El modulo **Renting** gestiona el catalogo de equipos para alquiler y el ciclo completo de una
solicitud de renta: desde la seleccion del equipo hasta el pago via Wompi.

**Responsabilidades principales:**
- Catalogo de equipos (Equipment, EquipmentVariant, categorias, marcas, imagenes)
- Configuracion de costos logisticos por equipo (EquipmentLogisticsConfig)
- Wizard de solicitud de renta de 7 pasos (RentalRequest)
- Calendario de disponibilidad por fechas (RentalPeriod)
- Verificacion de disponibilidad en tiempo real (check-availability)
- Calculo de costos: base + logistica + IVA
- Inicializacion de pago Wompi (initialize-payment)
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
├── services/
│   ├── __init__.py            # Exports publicos
│   ├── commands.py            # Escritura atomica (Commands)
│   ├── selectors.py           # Lectura optimizada (Selectors)
│   ├── availability.py        # AvailabilityEngine (is_available/find_next_available_slot/generate_schedule)
│   ├── display.py             # Vocabulario de 7 estados visibles
│   ├── pricing.py             # RentalPricingCalculator (tax rate)
│   └── summary.py             # RentingSummaryProvider (pull-based stats)
│
├── tests.py                   # Tests de negocio (concurrencia, lifecycle, permisos)
├── tests_availability.py      # Tests unitarios de AvailabilityEngine
├── tests_endpoints.py         # Tests de API (availability/calendar/timeline + acciones admin)
│
└── migrations/
    ├── 0001_initial.py
    ├── 0002_rentalrequest_...
    ├── 0003_rentalrequest_...  # RentalRequest completo
    ├── 0004_rentalcostrule.py
    ├── 0005_equipmentlogisticsconfig.py
    ├── 0006_rentalperiod.py   # Calendario de disponibilidad
    ├── 0007_rename_indexes.py # Renombrado automatico de indices
    └── 0013_rental_lifecycle_v2.py # Fase 1 Plan Maestro: conflicto de pago + horas
```

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

    user               = ForeignKey(AUTH_USER_MODEL)
    equipment_variant  = ForeignKey(EquipmentVariant)
    status             = CharField(max_length=30, default=STATUS_PENDING_PAYMENT)
    refund_required    = BooleanField(default=False)   # True si se cobro y perdio la carrera
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

    # Costos (llenados por commands.py desde EquipmentLogisticsConfig)
    delivery_cost      = DecimalField(default=0)
    pickup_cost        = DecimalField(default=0)
    installation_cost  = DecimalField(default=0)
    calibration_cost   = DecimalField(default=0)
    training_cost      = DecimalField(default=0)
    startup_cost       = DecimalField(default=0)

    # Totales calculados
    total_rental_days  = IntegerField(default=0)
    base_cost          = DecimalField(default=0)
    transport_total    = DecimalField(default=0)
    setup_total        = DecimalField(default=0)
    tax_amount         = DecimalField(default=0)
    grand_total        = DecimalField(default=0)

    # Pago Wompi
    wompi_reference      = CharField(max_length=255, blank=True)
    wompi_transaction_id = CharField(max_length=255, blank=True)
    payment_status       = CharField(max_length=50, blank=True)
    paid_at              = DateTimeField(null=True, blank=True)
```

Creado en paso 6 (Resumen) al confirmar. Status inicial: `pending_payment`. Este estado
inicial NUNCA bloquea el calendario (ver "Prevencion de Doble Reserva" abajo, reescrita
en la Fase 1 del Plan Maestro de Renting, 2026-07-07).

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
| POST | `/rental-requests/` | IsAuthenticated | Crear solicitud (pasos 1-5) |
| GET | `/rental-requests/` | IsAuthenticated | Listar solicitudes del usuario (admin ve todas) |
| GET | `/rental-requests/{uuid}/` | IsAuthenticated | Detalle |
| POST | `/rental-requests/{uuid}/cancel/` | IsAuthenticated | Cancelar (libera RentalPeriod si existia) |
| POST | `/rental-requests/{uuid}/process-payment/` | IsAuthenticated | Seleccionar metodo de pago y continuar flujo Wompi/Nequi/COD |
| POST | `/rental-requests/{uuid}/initialize-payment/` | IsAuthenticated | Genera firma Wompi |
| POST | `/rental-requests/{uuid}/approve/` | IsAdminUser | Aprueba COD pending_validation -> confirmed (crea RentalPeriod) |
| POST | `/rental-requests/{uuid}/reject/` | IsAdminUser | Rechaza COD pending_validation -> cancelled |
| POST | `/rental-requests/{uuid}/mark-delivered/` | IsAdminUser | paid/confirmed -> in_operation (periodo scheduled -> active) |
| POST | `/rental-requests/{uuid}/mark-returned/` | IsAdminUser | in_operation -> finished (periodo active -> completed) |
| POST | `/rental-requests/{uuid}/release-period/` | IsAdminUser | Libera la agenda sin cancelar la solicitud (override admin) |
| POST | `/rental-requests/{uuid}/extend/` | IsAdminUser | Extiende `end_date` si hay disponibilidad (2026-07-14, ver "Extension de renta") |
| POST | `/rental-requests/{uuid}/return-inspection/` | IsAdminUser | Registra inspeccion de devolucion (2026-07-14, opcional/aparte, solo si `status=finished`) |

`RentalRequestViewSet` soporta filtros `?status=...&payment_method=...&refund_required=true`
via `DjangoFilterBackend` (`filterset_fields`).

**POST /rental-requests/ — payload:**
```json
{
  "equipment_variant": "<variant-uuid>",
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
  "terms_accepted": true
}
```

**Respuesta 201 (campos relevantes):**
```json
{
  "uuid": "...",
  "status": "pending_payment",
  "base_cost": "1000000.00",
  "transport_total": "22000.00",
  "setup_total": "0.00",
  "tax_amount": "194180.00",
  "grand_total": "1216180.00"
}
```

**POST /initialize-payment/ — Respuesta:**
```json
{
  "uuid": "<rental-request-uuid>",
  "amount_in_cents": 121618000,
  "currency": "COP",
  "public_key": "pub_test_...",
  "integrity_signature": "<sha256>",
  "widget_url": "https://checkout.wompi.co/widget.js"
}
```

La firma de integridad usa: `SHA256(reference + amount_in_cents + currency + WOMPI_INTEGRITY_SECRET)`.
El `reference` es el UUID de la `RentalRequest`.

**Regla critica DRF para acciones custom:**
`process-payment`, `initialize-payment` y `cancel` son metodos `@action` y deben vivir
dentro de `RentalRequestViewSet`, que es la clase registrada en `DefaultRouter`.
No ubicarlos dentro de `RentalRequestListCreateAPIView`: Django compila, pero el router
no registra la ruta y el frontend recibira 404.

---

### Otros ViewSets

| ViewSet | URL prefix | Acciones admin | Acciones publicas |
|---------|-----------|----------------|-------------------|
| EquipmentVariantViewSet | `/equipment-variants/` | list, create, partial_update, destroy | — |
| RentingCategoryViewSet | `/categories/` | CRUD completo | list, retrieve |
| RentingBrandViewSet | `/brands/` | CRUD completo | list, retrieve |
| RentalLaborViewSet | `/rental-labor/` | CRUD completo | list, retrieve |

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

## Services

### RentingSelector — Lectura

```python
class RentingSelector:
    list_all_for_admin()          # Equipment con logistics_config, variants, images
    list_available_equipment()    # Solo activos con variants.stock > 0 (DISTINCT)
    list_featured()               # is_featured=True para home feed
    get_by_uuid(uuid)             # Detalle con logistics_config, variants, images, reviews
    check_availability(variant_id, start_date, end_date, quantity=1)  # bool -- wrapper sobre AvailabilityEngine.is_available()

class EquipmentVariantSelector:
    list_for_equipment(equipment_uuid)
    get_by_uuid(variant_uuid)

class RentalRequestSelector:
    list_for_user(user)
    list_all_for_admin()
    get_by_uuid_for_user(uuid, user)
    get_by_uuid_for_admin(uuid)
```

---

### RentalRequestCommands — Escritura Atomica

```python
class RentalRequestCommands:

    @staticmethod
    @transaction.atomic
    def create_request(user, validated_data) -> RentalRequest:
        """
        1. Verifica disponibilidad (best-effort, fail-fast de UX -- YA NO toma lock).
        2. Calcula base_cost segun rental_mode (days/hours).
        3. Lee costos de EquipmentLogisticsConfig (delivery, pickup, install, etc.).
        4. Calcula subtotal, tax_amount, grand_total.
        5. Crea RentalRequest con status=pending_payment.
        6. Notifica usuario via WebSocket (on_commit).
        NO crea RentalPeriod: pending_payment nunca bloquea agenda.
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

## Wizard Frontend — 7 Pasos

Ruta: `/alquiler/equipo/:uuid/solicitar`
Componente: `frontend/src/views/customer/renting/RentalRequestWizard.vue`

```
Paso 1 — Equipo        Seleccion de variante, precios, stock visible
Paso 2 — Lugar         Direccion, ciudad, departamento, tipo de proyecto
Paso 3 — Responsable   Nombre, documento, email, telefono, empresa, cargo
Paso 4 — Configuracion Fechas inicio/fin, cantidad, modo (dias/horas), notas
                        [verificacion de disponibilidad al avanzar]
Paso 5 — Contrato      Preview del contrato + checkbox de aceptacion de terminos
Paso 6 — Resumen       Desglose completo de costos + boton Confirmar solicitud
Paso 7 — Pago          Total a pagar + boton Proceder al pago (Wompi)
```

### Flujo del Paso 4 → Paso 5

```javascript
async function goStep5() {
  // Valida fechas localmente
  // Llama GET /renting/equipment/{uuid}/check-availability/?variant=...
  // Si available=false: muestra alert rojo inline (no solo toast)
  //   - El alert desaparece cuando el usuario cambia fechas (watch)
  // Si available=true: avanza a step 5
}
```

### Flujo del Paso 6 — Calculo de Costos (Frontend)

```javascript
const baseCost = computed(() => price_per_day * totalDays * quantity);

const logisticsConfig = computed(() => equipment.value?.logistics_config || null);
const transportTotal  = computed(() => delivery_cost + pickup_cost);
const setupTotal      = computed(() => installation + calibration + training + startup);
const subtotal        = computed(() => baseCost + transportTotal + setupTotal);
const taxAmount       = computed(() => subtotal * 0.19);
const grandTotal      = computed(() => subtotal + taxAmount);
```

El desglose en el Resumen muestra cada linea condicionalmente (solo si el valor > 0).

### Flujo del Paso 7 — Pago Wompi / Nequi / COD

```javascript
async function goToPayment() {
  const res = await api.post(`renting/rental-requests/${uuid}/process-payment/`, {
    payment_method: paymentMethod.value,
  });
  await openWompiWidget(res.data, {
    redirectPath: '/mi-cuenta/pedidos',
    onApproved: () => {
      toast.success('Pago aprobado. Tu reserva esta confirmada.');
      router.push('/mi-cuenta/pedidos');
    },
  });
}
```

Usa el composable `useWompiWidget` (extendido con `options.onApproved` y `options.redirectPath`
para no interferir con el flujo de tienda que usa `cartStore.reset()`).

---

## Composable useWompiWidget — Extension para Renting

`frontend/src/composables/useWompiWidget.js`

```javascript
// Firma:
async function openWompiWidget(txData, options = {}) {
  // options.onApproved  → callback personalizado al aprobar pago
  // options.redirectPath → ruta del redirectUrl de Wompi (default: '/orden-confirmada')
}

// Uso en tienda (CheckoutView, ServiceRequestView) — sin options:
await openWompiWidget(res.data);
// → cartStore.reset() + router.push('/orden-confirmada')

// Uso en renting (RentalRequestWizard) — con options:
await openWompiWidget(res.data, {
  redirectPath: '/mi-cuenta/pedidos',
  onApproved: () => router.push('/mi-cuenta/pedidos'),
});
```

---

## Flujo Completo de una Solicitud de Renta

```
1. Usuario navega a /alquiler/equipo/:uuid/solicitar

2. [Paso 1] Selecciona variante
   GET /renting/equipment/{uuid}/
   → Retorna equipment con variants, images, logistics_config

3. [Paso 4] Selecciona fechas y avanza
   GET /renting/equipment/{uuid}/check-availability/?variant=...&start_date=...&end_date=...
   → { available: true/false }
   Si false: muestra alert rojo "El equipo no tiene disponibilidad..."

4. [Paso 5] Acepta terminos del contrato

5. [Paso 6] Revisa resumen y confirma
   POST /renting/rental-requests/
   → Serializer valida disponibilidad (segunda verificacion)
   → RentalRequestCommands.create_request():
       a. Tercera verificacion de disponibilidad
       b. Calcula costos desde EquipmentLogisticsConfig
       c. Crea RentalRequest (status=pending_payment)
       d. Crea RentalPeriod (status=scheduled) — bloquea fechas
       e. WebSocket notifica al usuario
   → 201 con grand_total calculado

6. [Paso 7] Paga
   POST /renting/rental-requests/{uuid}/process-payment/
   → WOMPI: calcula integrity_signature, actualiza rental_request.wompi_reference
     y retorna { uuid, amount_in_cents, public_key, integrity_signature, widget_url }
   → NEQUI: crea NequiTransaction y retorna { nequi_tx_uuid }
   → COD: marca la solicitud como confirmed y retorna { status, rental_uuid }
   → Frontend abre WidgetCheckout, navega a espera Nequi o muestra confirmacion COD
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

---

## Integracion con Otros Modulos

```
RENTING
  ├── orders.OrderItem       → top_rented en RentingSummaryProvider
  ├── wompi.settings.*       → WOMPI_PUBLIC_KEY, WOMPI_INTEGRITY_SECRET, WOMPI_WIDGET_URL
  ├── ecommerce.ws_notify    → notificacion WebSocket al crear RentalRequest
  ├── users.permissions      → IsAdminUser para acciones de escritura
  └── core.HomeConfigView    → list_featured() para el home publico

INDEPENDIENTE DE:
  ├── inventory.StockRecord  → NO se usa para disponibilidad
  └── inventory.InventorySelector → NO se usa
```

---

## Migraciones Aplicadas

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
| 0013 | Fase 1 Plan Maestro: STATUS_PAYMENT_CONFLICT, refund_required, admin_notes, delivery_time/pickup_time en RentalRequest; start_time/end_time/rental_mode + indice compuesto en RentalPeriod |
| 0014-0018 | Notificaciones de renting, RentalOperation/RentalOperationEvent, incidentes, plantillas de ciclo de vida (ver "Operaciones de Renting" abajo) |
| 0019 | `EquipmentBlock` (bloqueo manual mantenimiento/daño/inventario) |
| 0020 | Siembra `PeriodicTask` de `expire_abandoned_pending_payment_requests` (django_celery_beat, sin cambio de esquema) |
| 0021 | `EquipmentReturnInspection` (inspeccion de devolucion, opcional/aparte) |

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

---

**Ultima actualizacion:** 2026-07-07 (Fase 1+2 del Plan Maestro de Renting + email de
confirmacion con ticket de servicio tras aprobar -- ver contexto completo en el plan de
implementacion de la sesion).
