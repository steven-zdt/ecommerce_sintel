"""
Migration: Remove CONTRACTOR_RATES from ServiceVariant.pricing_strategy

Converts any existing rows using CONTRACTOR_RATES to HOURLY before
altering the column choices and max_length.
"""
from django.db import migrations, models


def migrate_contractor_rates_to_hourly(apps, schema_editor):
    """Convierte filas con CONTRACTOR_RATES a HOURLY antes de alterar el campo."""
    ServiceVariant = apps.get_model('technical_services', 'ServiceVariant')
    ServiceVariant.objects.filter(pricing_strategy='CONTRACTOR_RATES').update(
        pricing_strategy='HOURLY'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('technical_services', '0013_orderservicedetail_contact_person'),
    ]

    operations = [
        # 1. Migrar datos existentes antes de alterar el campo
        migrations.RunPython(
            migrate_contractor_rates_to_hourly,
            reverse_code=migrations.RunPython.noop,
        ),
        # 2. Actualizar choices y reducir max_length (HOURLY/DAILY/FIXED caben en 6)
        migrations.AlterField(
            model_name='servicevariant',
            name='pricing_strategy',
            field=models.CharField(
                choices=[
                    ('HOURLY', 'Hourly'),
                    ('DAILY', 'Daily'),
                    ('FIXED', 'Fixed'),
                ],
                default='HOURLY',
                max_length=10,
            ),
        ),
    ]
