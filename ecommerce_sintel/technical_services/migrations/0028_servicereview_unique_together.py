from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('technical_services', '0027_service_packages'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='servicereview',
            unique_together={('user', 'service')},
        ),
    ]
