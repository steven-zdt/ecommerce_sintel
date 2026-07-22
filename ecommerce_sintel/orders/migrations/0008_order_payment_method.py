from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0007_postal_code_optional'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_method',
            field=models.CharField(
                choices=[('WOMPI', 'Wompi (online)'), ('COD', 'Pago contra entrega')],
                default='WOMPI',
                db_index=True,
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending',    'Pendiente'),
                    ('processing', 'En procesamiento'),
                    ('paid',       'Pagado'),
                    ('shipped',    'Enviado'),
                    ('delivered',  'Entregado'),
                    ('cancelled',  'Cancelado'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
    ]
