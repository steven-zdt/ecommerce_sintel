from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('technical_services', '0012_orderservicedetail_booked_slot'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderservicedetail',
            name='contact_person',
            field=models.JSONField(
                blank=True,
                null=True,
                help_text='Datos del encargado del servicio: nombre, cargo, contacto, etc.'
            ),
        ),
    ]
