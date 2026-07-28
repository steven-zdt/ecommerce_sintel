from django.db import migrations

# Backfill del split de RentalRequest (auditoria DB-H1, 2026-07-27).
#
# Copia los valores de las columnas planas que todavia viven en la tabla
# renting_rentalrequest hacia las cuatro tablas hijas creadas en 0034. La
# migracion 0036 es la que elimina las columnas viejas, asi que este paso tiene
# que correr ANTES (de lo contrario se perderian los datos historicos).
#
# Se usan modelos historicos via apps.get_model() a proposito: las properties y
# los overrides de __init__/save() de renting/models.py NO existen aqui, y
# tampoco deben usarse -- se escribe campo a campo sobre las tablas reales.

LOCATION_FIELDS = (
    'location_address',
    'location_city',
    'location_department',
    'location_coordinates',
    'project_type',
    'access_conditions',
    'location_notes',
)

CONTACT_FIELDS = (
    'contact_full_name',
    'contact_doc_type',
    'contact_doc_number',
    'contact_email',
    'contact_phone',
    'contact_company',
    'contact_position',
)

COSTS_FIELDS = (
    'delivery_cost',
    'pickup_cost',
    'distance_km',
    'installation_cost',
    'calibration_cost',
    'training_cost',
    'startup_cost',
    'total_rental_days',
    'base_cost',
    'price_per_day_snapshot',
    'price_per_hour_snapshot',
    'labor_total',
    'transport_total',
    'setup_total',
    'tax_amount',
    'grand_total',
)

PAYMENT_FIELDS = (
    'payment_method',
    'wompi_reference',
    'wompi_transaction_id',
    'payment_status',
    'paid_at',
)

BATCH_SIZE = 500


def _values_for(rental_request, field_names):
    return {name: getattr(rental_request, name) for name in field_names}


def backfill(apps, schema_editor):
    RentalRequest = apps.get_model('renting', 'RentalRequest')
    RentalRequestLocation = apps.get_model('renting', 'RentalRequestLocation')
    RentalRequestContact = apps.get_model('renting', 'RentalRequestContact')
    RentalRequestCosts = apps.get_model('renting', 'RentalRequestCosts')
    RentalRequestPaymentInfo = apps.get_model('renting', 'RentalRequestPaymentInfo')

    existing_location = set(RentalRequestLocation.objects.values_list('rental_request_id', flat=True))
    existing_contact = set(RentalRequestContact.objects.values_list('rental_request_id', flat=True))
    existing_costs = set(RentalRequestCosts.objects.values_list('rental_request_id', flat=True))
    existing_payment = set(RentalRequestPaymentInfo.objects.values_list('rental_request_id', flat=True))

    locations = []
    contacts = []
    costs = []
    payments = []

    for rental_request in RentalRequest.objects.all().iterator(chunk_size=BATCH_SIZE):
        if rental_request.pk not in existing_location:
            locations.append(RentalRequestLocation(
                rental_request_id=rental_request.pk,
                **_values_for(rental_request, LOCATION_FIELDS)
            ))
        if rental_request.pk not in existing_contact:
            contacts.append(RentalRequestContact(
                rental_request_id=rental_request.pk,
                **_values_for(rental_request, CONTACT_FIELDS)
            ))
        if rental_request.pk not in existing_costs:
            costs.append(RentalRequestCosts(
                rental_request_id=rental_request.pk,
                **_values_for(rental_request, COSTS_FIELDS)
            ))
        if rental_request.pk not in existing_payment:
            payments.append(RentalRequestPaymentInfo(
                rental_request_id=rental_request.pk,
                **_values_for(rental_request, PAYMENT_FIELDS)
            ))

    RentalRequestLocation.objects.bulk_create(locations, batch_size=BATCH_SIZE)
    RentalRequestContact.objects.bulk_create(contacts, batch_size=BATCH_SIZE)
    RentalRequestCosts.objects.bulk_create(costs, batch_size=BATCH_SIZE)
    RentalRequestPaymentInfo.objects.bulk_create(payments, batch_size=BATCH_SIZE)


def unbackfill(apps, schema_editor):
    """
    Reversa: copia los valores de vuelta a las columnas planas (solo las que
    existan en ese punto del historial) y borra las filas hijas.
    """
    RentalRequest = apps.get_model('renting', 'RentalRequest')
    RentalRequestLocation = apps.get_model('renting', 'RentalRequestLocation')
    RentalRequestContact = apps.get_model('renting', 'RentalRequestContact')
    RentalRequestCosts = apps.get_model('renting', 'RentalRequestCosts')
    RentalRequestPaymentInfo = apps.get_model('renting', 'RentalRequestPaymentInfo')

    flat_fields = set(
        field.name for field in RentalRequest._meta.get_fields()
        if hasattr(field, 'attname')
    )

    for model, field_names in (
        (RentalRequestLocation, LOCATION_FIELDS),
        (RentalRequestContact, CONTACT_FIELDS),
        (RentalRequestCosts, COSTS_FIELDS),
        (RentalRequestPaymentInfo, PAYMENT_FIELDS),
    ):
        writable = [name for name in field_names if name in flat_fields]
        if writable:
            for child in model.objects.all().iterator(chunk_size=BATCH_SIZE):
                RentalRequest.objects.filter(pk=child.rental_request_id).update(
                    **{name: getattr(child, name) for name in writable}
                )
        model.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('renting', '0034_rentalrequestcontact_rentalrequestcosts_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill, unbackfill),
    ]
