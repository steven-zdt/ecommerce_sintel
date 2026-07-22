from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_backfill_technician_profile_service_providers'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='userprofile',
            constraint=models.UniqueConstraint(
                fields=['document_type', 'document'],
                condition=models.Q(document__isnull=False),
                name='userprofile_document_unique',
            ),
        ),
    ]
