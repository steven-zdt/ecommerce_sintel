from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_homecard'),
    ]

    operations = [
        migrations.AddField(
            model_name='homecard',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='home_cards/images/'),
        ),
        migrations.AddField(
            model_name='homecard',
            name='video',
            field=models.FileField(blank=True, null=True, upload_to='home_cards/videos/'),
        ),
    ]
