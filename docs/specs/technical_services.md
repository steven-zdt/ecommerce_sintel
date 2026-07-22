---
app_name: technical_services
layer: service_layer
doc_type: spec
critical_rules:
  - decimal_money
  - breakdown_json_structure
  - ServiceBooking_capacity
  - contact_person_jsonfield
  - transaction_atomic
  - on_commit_notify
associated_models:
  - TechnicalService
  - ServiceVariant
  - ServiceConfiguration
  - OrderServiceDetail
  - ServiceBooking
  - ServiceCostRule
  - ServiceCostAssignment
  - ServiceMaterial
cross_app_dependencies:
  - orders
  - inventory
  - notifications
  - accounts
permissions_required:
  - IsAdminUser
  - IsAuthenticatedActiveUser
---

# App: technical_services

## Jerarquia de Modelos

```
TechnicalService (analogo a Product)
  └── ServiceVariant (analogo a ProductVariant)
        ├── ServiceMaterial (insumos requeridos)
        ├── ServiceCostAssignment (reglas de costo asignadas)
        └── ServiceBooking (slots de capacidad reservados)

Order (de orders app)
  └── OrderServiceDetail (detalle especifico del servicio)
        └── contact_person (JSONField — datos del encargado)
```

## Pricing Engine: Estrategias de Precio

```python
class ServiceVariant(SintelBaseModel):
    HOURLY = 'HOURLY'
    DAILY  = 'DAILY'
    FIXED  = 'FIXED'

    pricing_strategy    = models.CharField(choices=PRICING_STRATEGY_CHOICES)
    estimated_hours     = models.DecimalField(max_digits=6, decimal_places=2)   # Decimal
    complexity_factor   = models.DecimalField(max_digits=4, decimal_places=2)   # Decimal
    fixed_price         = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    simultaneous_capacity = models.PositiveIntegerField(default=1)
```

## Estructura del JSON breakdown (invariante)

El dict retornado por `ServiceSelector.get_variant_quotation(variant)` SIEMPRE tiene esta estructura:

```python
{
    'base_amount':      Decimal,   # costo base laboral
    'discount_pct':     Decimal,   # porcentaje de descuento
    'discount_amount':  Decimal,   # monto de descuento
    'iva_rate':         Decimal,   # porcentaje IVA (ej. Decimal('19.00'))
    'iva_amount':       Decimal,   # monto IVA
    'total_price':      Decimal,   # total final
}
```

NUNCA modificar esta estructura. El serializer `ServiceVariantSerializer` la usa en `get_price_info()`.

## ServiceBooking: Control de Capacidad Simultanea

`ServiceBooking` controla cuantas instancias del mismo `ServiceVariant` pueden ejecutarse al mismo tiempo. NO usa `StockRecord`.

```python
class ServiceBooking(SintelBaseModel):
    order_service_detail = models.ForeignKey(OrderServiceDetail, ...)
    service_variant      = models.ForeignKey(ServiceVariant, ...)
    start_time = models.DateTimeField()
    end_time   = models.DateTimeField()
    status     = models.CharField(choices=STATUS_CHOICES, default='scheduled')
```

Para verificar disponibilidad antes de crear una reserva:

```python
from django.db import transaction

@transaction.atomic
def reserve_slot(service_variant, start_time, end_time, order_service_detail):
    # Verificar capacidad actual con bloqueo
    active_count = ServiceBooking.objects.select_for_update().filter(
        service_variant=service_variant,
        status__in=['scheduled', 'active'],
        start_time__lt=end_time,
        end_time__gt=start_time,
    ).count()

    if active_count >= service_variant.simultaneous_capacity:
        raise ValidationError("No hay capacidad disponible para este servicio en las fechas seleccionadas.")

    return ServiceBooking.objects.create(
        service_variant=service_variant,
        order_service_detail=order_service_detail,
        start_time=start_time,
        end_time=end_time,
    )
```

## OrderServiceDetail.contact_person (JSONField)

El campo `contact_person` almacena los datos del encargado del servicio como JSON. El schema esta validado por `ContactPersonSerializer`:

```python
# Schema esperado en contact_person
{
    "full_name":       "string (max 150)",
    "document_type":   "CC | CE | PP | TI | NIT | OTRO",
    "document_number": "string (max 30)",
    "cargo":           "string (max 100)",
    "email":           "email valido",
    "phone":           "string (max 20)",
    "phone_alt":       "string (max 20, opcional)",
    "company":         "string (opcional)",
    "department":      "string (opcional)",
    "access_notes":    "string (opcional)",
}
```

## ServiceCostRule: Motor de Costos Descentralizado

```python
class ServiceCostRule(SintelBaseModel):
    COST_TYPE_CHOICES = [('FIXED', 'Valor fijo'), ('PERCENTAGE', 'Porcentaje')]
    CONTEXT_CHOICES   = [('TAX','Impuesto'), ('DISCOUNT','Descuento'), ('SETUP','Instalacion'), ('OPERATIONAL','Operativo')]

    name            = models.CharField(max_length=150)
    cost_type       = models.CharField(choices=COST_TYPE_CHOICES)
    context         = models.CharField(choices=CONTEXT_CHOICES)
    value           = models.DecimalField(max_digits=12, decimal_places=4)  # Decimal siempre
    applies_globally = models.BooleanField(default=False)
```

## ServiceRequestInputSerializer: Campos Requeridos

```python
class ServiceRequestInputSerializer(serializers.Serializer):
    variant_uuid     = serializers.UUIDField()       # resuelve a ServiceVariant
    quantity         = serializers.IntegerField(min_value=1)
    priority         = serializers.ChoiceField(choices=['low','medium','high','critical'])
    description      = serializers.CharField()
    address          = serializers.CharField(max_length=255)
    scheduled_at     = serializers.DateTimeField()   # debe ser en el futuro
    contact_person   = ContactPersonSerializer()     # objeto anidado
```
