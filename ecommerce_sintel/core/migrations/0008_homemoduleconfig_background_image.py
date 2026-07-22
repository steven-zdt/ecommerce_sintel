from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_homemoduleconfig_custom_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='homemoduleconfig',
            name='background_image',
            field=models.ImageField(blank=True, null=True, upload_to='home_modules/images/'),
        ),
    ]
