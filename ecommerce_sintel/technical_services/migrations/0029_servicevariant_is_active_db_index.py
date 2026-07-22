from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('technical_services', '0028_servicereview_unique_together'),
    ]

    operations = [
        migrations.AlterField(
            model_name='servicevariant',
            name='is_active',
            field=models.BooleanField(default=True, db_index=True),
        ),
    ]
