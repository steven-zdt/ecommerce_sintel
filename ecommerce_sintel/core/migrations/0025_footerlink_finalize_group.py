import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_backfill_footer_groups'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='footerlink',
            name='group_name',
        ),
        migrations.AlterField(
            model_name='footerlink',
            name='group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='links', to='core.footergroup'),
        ),
    ]
