from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0004_operationticket_rental_operation_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='operationassignment',
            name='status',
            field=models.CharField(
                choices=[('ACTIVE', 'Activa'), ('RELEASED', 'Liberada')],
                default='ACTIVE',
                db_index=True,
                max_length=10,
            ),
        ),
    ]
