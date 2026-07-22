from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('renting', '0023_equipment_review_unique_together'),
    ]

    operations = [
        migrations.AlterField(
            model_name='equipmentvariant',
            name='is_active',
            field=models.BooleanField(default=True, db_index=True),
        ),
    ]
