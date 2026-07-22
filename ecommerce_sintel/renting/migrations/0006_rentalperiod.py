import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('renting', '0005_rentalcostrule_rentalcostassignment'),
    ]

    operations = [
        migrations.CreateModel(
            name='RentalPeriod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('start_date', models.DateField(db_index=True)),
                ('end_date', models.DateField(db_index=True)),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('status', models.CharField(
                    choices=[
                        ('scheduled', 'Programado'),
                        ('active', 'Activo'),
                        ('completed', 'Completado'),
                        ('cancelled', 'Cancelado'),
                    ],
                    db_index=True,
                    default='scheduled',
                    max_length=20,
                )),
                ('equipment_variant', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='rental_periods',
                    to='renting.equipmentvariant',
                )),
                ('rental_request', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='periods',
                    to='renting.rentalrequest',
                )),
            ],
            options={
                'verbose_name': 'periodo de alquiler',
                'verbose_name_plural': 'periodos de alquiler',
            },
        ),
        migrations.AddIndex(
            model_name='rentalperiod',
            index=models.Index(fields=['start_date', 'end_date'], name='renting_ren_start_d_idx'),
        ),
        migrations.AddIndex(
            model_name='rentalperiod',
            index=models.Index(fields=['equipment_variant', 'status'], name='renting_ren_equip_st_idx'),
        ),
    ]
