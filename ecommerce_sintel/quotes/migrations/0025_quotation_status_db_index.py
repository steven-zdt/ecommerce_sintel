from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quotes', '0024_alter_quotetemplate_is_active_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='quotation',
            name='status',
            field=models.CharField(
                choices=[
                    ('BORRADOR', 'Borrador'),
                    ('RECIBIDA', 'Recibida'),
                    ('EN_REVISION', 'En revision'),
                    ('PENDIENTE_INFORMACION', 'Pendiente informacion'),
                    ('COTIZADA', 'Cotizada'),
                    ('ENVIADA', 'Enviada'),
                    ('ACEPTADA', 'Aceptada'),
                    ('RECHAZADA', 'Rechazada'),
                    ('VENCIDA', 'Vencida'),
                    ('CANCELADA', 'Cancelada'),
                ],
                db_index=True,
                default='BORRADOR',
                max_length=25,
            ),
        ),
    ]
