---
app_name: renting
layer: service_layer
doc_type: spec
critical_rules:
  - decimal_money
  - RentalPeriod_no_break
  - availability_check_before_create
  - transaction_atomic
  - on_commit_notify
associated_models:
  - Equipment
  - EquipmentVariant
  - RentalRequest
  - RentalPeriod
  - EquipmentLogisticsConfig
  - RentingCategory
  - RentingBrand
cross_app_dependencies:
  - orders
  - notifications
  - wompi
permissions_required:
  - IsAuthenticatedActiveUser
  - IsAdminUser
---

# App: renting

## Jerarquia de Modelos

```
Equipment (analogo a Product — tiene vendor, category, brand)
  └── EquipmentVariant (precio/hora, precio/dia, stock)
        └── RentalPeriod (periodos reservados — NO PARTIR)

RentalRequest (solicitud de alquiler via wizard 8 pasos)
  ├── equipment_variant -> EquipmentVariant
  ├── start_date, end_date
  ├── rental_mode: 'days' | 'hours'
  └── payment -> Order o directo

EquipmentLogisticsConfig (costos de logistica por equipo)
```

## Regla Critica: RentalPeriod No Se Puede Partir

Los `RentalPeriod` son bloques atomicos de tiempo reservado. Nunca dividir un periodo existente para insertar otro en el medio. Si hay solapamiento, la operacion falla.

```python
@transaction.atomic
def check_availability_and_block(variant_id, start_date, end_date):
    # Bloqueo pesimista para evitar double-booking
    conflicts = RentalPeriod.objects.select_for_update().filter(
        equipment_variant_id=variant_id,
        status__in=['active', 'reserved'],
        start_date__lt=end_date,
        end_date__gt=start_date,
    )
    if conflicts.exists():
        raise ValidationError("El equipo no esta disponible en las fechas seleccionadas.")
```

## EquipmentVariant: Precios en Decimal

```python
class EquipmentVariant(SintelBaseModel):
    rental_price_per_day  = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    rental_price_per_hour = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    stock                 = models.PositiveIntegerField(default=0)
```

## Command: RentingCommands.process_rental_order

```python
@staticmethod
@transaction.atomic
def process_rental_order(user, equipment_variant, start_date, end_date, mode, shipping_address):
    total_days = (end_date - start_date).days
    if total_days < 1:
        raise ValueError("La fecha de fin debe ser posterior a la fecha de inicio.")

    if not RentingSelector.check_availability(equipment_variant.id, start_date, end_date):
        raise ValueError("No hay disponibilidad para el equipo en las fechas seleccionadas.")

    # Calculo con Decimal — nunca float
    if mode == 'days':
        base_price = equipment_variant.rental_price_per_day * total_days
    elif mode == 'hours':
        base_price = equipment_variant.rental_price_per_hour * (total_days * 8)

    order = Order.objects.create(user=user, total_amount=base_price, status='pending')

    _user, _ctx = user, {'order_uuid': str(order.uuid), 'total_amount': str(base_price)}
    transaction.on_commit(
        lambda: NotificationCommands.dispatch_notification(
            user=_user, template_slug='rental_order_created', context=_ctx,
            ws_group=f'user_{_user.uuid}',
        )
    )
    return order
```

## Wizard de Alquiler (8 Pasos)

El wizard frontend en `/alquiler/equipo/:uuid/solicitar` crea un `RentalRequest` paso a paso:

1. Seleccion de equipo/variante
2. Lugar (direccion estructurada Colombia)
3. Responsable (datos del encargado)
4. Configuracion (fechas, modo: dias/horas)
5. Contrato (terminos y condiciones)
6. Resumen (breakdown de costos logisticos)
7. Pago (Wompi / Nequi / COD)
8. Confirmacion

El endpoint clave es `POST /api/v1/renting/rental-requests/{uuid}/process-payment/`.

Regla de implementacion DRF: `process-payment` debe vivir como metodo `@action`
dentro de `RentalRequestViewSet`, que es el ViewSet registrado en `DefaultRouter`.
No poner `@action` en `RentalRequestListCreateAPIView`; compila, pero el router no
registra la URL y el frontend recibe 404.

## RentalRequest: Estados

```python
STATUS_CHOICES = [
    ('PENDING',   'Pendiente de pago'),
    ('CONFIRMED', 'Confirmada'),
    ('ACTIVE',    'En curso'),
    ('COMPLETED', 'Completada'),
    ('CANCELLED', 'Cancelada'),
]
```

## EquipmentLogisticsConfig: Costos de Logistica

Los costos de logistica (transporte, operacion) se configuran por equipo y se incluyen en el breakdown del paso 6 del wizard:

```python
class EquipmentLogisticsConfig(SintelBaseModel):
    equipment_variant    = models.OneToOneField(EquipmentVariant, ...)
    transport_cost       = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    setup_cost           = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    insurance_rate       = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    tax_rate             = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('19.00'))
```
